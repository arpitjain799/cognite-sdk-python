import functools
import inspect
from concurrent.futures import CancelledError
from typing import Dict


class MockFuture:
    def __init__(self, fn, args, kwargs):
        self._task = functools.partial(fn, *args, **kwargs)
        self._result = None
        self._is_cancelled = False

    def result(self):
        if self._is_cancelled:
            raise CancelledError

        if self._result is None:  # Blocks until done
            self._result = self._task()
        return self._result

    def cancel(self):
        self._is_cancelled = True


def mock_as_completed(dct: Dict) -> MockFuture:
    # Will raise StopIteration when done (we want this):
    return iter(dct.copy())


class MockPriorityThreadPoolExecutor:
    def __init__(self, max_workers: int = None):
        if max_workers != 1:
            raise RuntimeError("WASM says max max_workers is -e^(i*pi), or one if you wondered")

    def submit(self, fn, *args, **kwargs):
        if "priority" in inspect.signature(fn).parameters:
            raise TypeError(f"Given function {fn} cannot accept reserved parameter name `priority`")
        kwargs.pop("priority", None)

        fake_future = MockFuture(fn, args, kwargs)
        return fake_future

    def shutdown(self, wait: bool = False):
        return None

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.shutdown()
