from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple, Union, cast

import cognite.client.utils._time
from cognite.client import utils
from cognite.client._api_client import APIClient
from cognite.client.data_classes import Datapoints, DatapointsList, TimeSeries

if TYPE_CHECKING:
    import sympy

    from cognite.client import CogniteClient
    from cognite.client.config import ClientConfig


class SyntheticDatapointsAPI(APIClient):
    _RESOURCE_PATH = "/timeseries/synthetic"

    def __init__(self, config: ClientConfig, api_version: Optional[str], cognite_client: CogniteClient) -> None:
        super().__init__(config, api_version, cognite_client)
        self._DPS_LIMIT_SYNTH = 10_000

    def query(
        self,
        expressions: Union[str, sympy.Expr, Sequence[Union[str, sympy.Expr]]],
        start: Union[int, str, datetime],
        end: Union[int, str, datetime],
        limit: int = None,
        variables: Dict[str, Union[str, TimeSeries]] = None,
        aggregate: str = None,
        granularity: str = None,
    ) -> Union[Datapoints, DatapointsList]:
        """`Calculate the result of a function on time series. <https://docs.cognite.com/api/v1/#operation/querySyntheticTimeseries>`_

        Args:
            expressions (Union[str, sympy.Expr, Sequence[Union[str, sympy.Expr]]]): Functions to be calculated. Supports both strings and sympy expressions. Strings can have either the API `ts{}` syntax, or contain variable names to be replaced using the `variables` parameter.
            start (Union[int, str, datetime]): Inclusive start.
            end (Union[int, str, datetime]): Exclusive end
            limit (int): Number of datapoints per expression to retrieve.
            variables (Dict[str,Union[str,TimeSeries]]): An optional map of symbol replacements.
            aggregate (str): use this aggregate when replacing entries from `variables`, does not affect time series given in the `ts{}` syntax.
            granularity (str): use this granularity with the aggregate.

        Returns:
            Union[Datapoints, DatapointsList]: A DatapointsList object containing the calculated data.

        Examples:

            Request a synthetic time series query with direct syntax

                >>> from cognite.client import CogniteClient
                >>> c = CogniteClient()
                >>> dps = c.time_series.data.synthetic.query(expressions="TS{id:123} + TS{externalId:'abc'}", start="2w-ago", end="now")

            Use variables to re-use an expression:

                >>> vars = {"A": "my_ts_external_id", "B": client.time_series.retrieve(id=1)}
                >>> dps = c.time_series.data.synthetic.query(expressions="A+B", start="2w-ago", end="now", variables=vars)

            Use sympy to build complex expressions:

                >>> from sympy import symbols, cos, sin
                >>> a = symbols('a')
                >>> dps = c.time_series.data.synthetic.query([sin(a), cos(a)], start="2w-ago", end="now", variables={"a": "my_ts_external_id"}, aggregate='interpolation', granularity='1m')
        """
        if limit is None or limit == -1:
            limit = cast(int, float("inf"))

        tasks = []
        expressions_to_iterate = (
            expressions if (isinstance(expressions, Sequence) and not isinstance(expressions, str)) else [expressions]
        )

        for i in range(len(expressions_to_iterate)):
            expression, short_expression = self._build_expression(
                expressions_to_iterate[i], variables, aggregate, granularity
            )
            query = {
                "expression": expression,
                "start": cognite.client.utils._time.timestamp_to_ms(start),
                "end": cognite.client.utils._time.timestamp_to_ms(end),
            }
            values: List[float] = []  # mypy
            query_datapoints = Datapoints(value=values, error=[])
            query_datapoints.external_id = short_expression

            tasks.append((query, query_datapoints, limit))

        datapoints_summary = utils._concurrency.execute_tasks(
            self._fetch_datapoints, tasks, max_workers=self._config.max_workers
        )

        if datapoints_summary.exceptions:
            raise datapoints_summary.exceptions[0]

        return (
            DatapointsList(datapoints_summary.results, cognite_client=self._cognite_client)
            if isinstance(expressions, List)
            else datapoints_summary.results[0]
        )

    def _fetch_datapoints(self, query: Dict[str, Any], datapoints: Datapoints, limit: int) -> Datapoints:
        while True:
            query["limit"] = min(limit, self._DPS_LIMIT_SYNTH)
            resp = self._post(url_path=self._RESOURCE_PATH + "/query", json={"items": [query]})
            data = resp.json()["items"][0]
            datapoints._extend(Datapoints._load(data, expected_fields=["value", "error"]))
            limit -= len(data["datapoints"])
            if len(data["datapoints"]) < self._DPS_LIMIT_SYNTH or limit <= 0:
                break
            query["start"] = data["datapoints"][-1]["timestamp"] + 1
        return datapoints

    @staticmethod
    def _build_expression(
        expression: Union[str, sympy.Expr],
        variables: Dict[str, Any] = None,
        aggregate: str = None,
        granularity: str = None,
    ) -> Tuple[str, str]:
        if expression.__class__.__module__.startswith("sympy."):
            expression_str = SyntheticDatapointsAPI._sympy_to_sts(expression)
            if not variables:
                raise ValueError(
                    "sympy expressions are only supported in combination with the `variables` parameter to map symbols to time series."
                )
        else:
            expression_str = cast(str, expression)
        if aggregate and granularity:
            aggregate_str = f",aggregate:'{aggregate}',granularity:'{granularity}'"
        else:
            aggregate_str = ""
        expression_with_ts: str = expression_str
        if variables:
            for k, v in variables.items():
                if isinstance(v, TimeSeries):
                    v = v.external_id
                expression_with_ts = re.sub(  # type: ignore
                    re.compile(rf"\b{k}\b"), f"ts{{externalId:'{v}'{aggregate_str}}}", expression_with_ts
                )
        return expression_with_ts, expression_str

    @staticmethod
    def _sympy_to_sts(expression: Union[str, sympy.Expr]) -> str:
        sympy_module = cast(Any, utils._auxiliary.local_import("sympy"))

        infix_ops = {sympy_module.Add: "+", sympy_module.Mul: "*"}
        functions = {
            sympy_module.cos: "cos",
            sympy_module.sin: "sin",
            sympy_module.sqrt: "sqrt",
            sympy_module.log: "ln",
            sympy_module.exp: "exp",
            sympy_module.Abs: "abs",
        }

        def process_symbol(sym: Any) -> str:
            if isinstance(sym, sympy_module.AtomicExpr):
                if isinstance(sym, sympy_module.NumberSymbol):
                    return str(sym.evalf(15))
                else:
                    return str(sym)

            infixop = infix_ops.get(sym.__class__)
            if infixop:
                return "(" + infixop.join(process_symbol(s) for s in sym.args) + ")"

            if isinstance(sym, sympy_module.Pow):
                if sym.args[1] == -1:
                    return f"(1/{process_symbol(sym.args[0])})"
                return f"pow({','.join(map(process_symbol, sym.args))})"

            if funop := functions.get(sym.__class__):
                return f"{funop}({','.join(map(process_symbol, sym.args))})"
            raise ValueError(f"Unsupported sympy class {sym.__class__} encountered in expression")

        return process_symbol(expression)
