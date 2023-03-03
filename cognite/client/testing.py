from contextlib import contextmanager
from unittest.mock import MagicMock

from cognite.client import CogniteClient
from cognite.client._api.annotations import AnnotationsAPI
from cognite.client._api.assets import AssetsAPI
from cognite.client._api.data_sets import DataSetsAPI
from cognite.client._api.datapoints import DatapointsAPI
from cognite.client._api.diagrams import DiagramsAPI
from cognite.client._api.entity_matching import EntityMatchingAPI
from cognite.client._api.events import EventsAPI
from cognite.client._api.extractionpipelines import (
    ExtractionPipelineConfigsAPI,
    ExtractionPipelineRunsAPI,
    ExtractionPipelinesAPI,
)
from cognite.client._api.files import FilesAPI
from cognite.client._api.functions import FunctionCallsAPI, FunctionsAPI, FunctionSchedulesAPI
from cognite.client._api.geospatial import GeospatialAPI
from cognite.client._api.iam import (
    IAMAPI,
    APIKeysAPI,
    GroupsAPI,
    SecurityCategoriesAPI,
    ServiceAccountsAPI,
    SessionsAPI,
    TokenAPI,
)
from cognite.client._api.labels import LabelsAPI
from cognite.client._api.login import LoginAPI
from cognite.client._api.raw import RawAPI, RawDatabasesAPI, RawRowsAPI, RawTablesAPI
from cognite.client._api.relationships import RelationshipsAPI
from cognite.client._api.sequences import SequencesAPI, SequencesDataAPI
from cognite.client._api.synthetic_time_series import SyntheticDatapointsAPI
from cognite.client._api.templates import (
    TemplateGroupsAPI,
    TemplateGroupVersionsAPI,
    TemplateInstancesAPI,
    TemplatesAPI,
    TemplateViewsAPI,
)
from cognite.client._api.three_d import (
    ThreeDAPI,
    ThreeDAssetMappingAPI,
    ThreeDFilesAPI,
    ThreeDModelsAPI,
    ThreeDRevisionsAPI,
)
from cognite.client._api.time_series import TimeSeriesAPI
from cognite.client._api.transformations import (
    TransformationJobsAPI,
    TransformationNotificationsAPI,
    TransformationsAPI,
    TransformationSchedulesAPI,
    TransformationSchemaAPI,
)
from cognite.client._api.vision import VisionAPI


class CogniteClientMock(MagicMock):
    def __init__(self, *args: Any, **kwargs: Any):
        if "parent" in kwargs:
            super().__init__(*args, **kwargs)
            return None
        super().__init__(*args, spec=CogniteClient, **kwargs)
        self.annotations = MagicMock(spec_set=AnnotationsAPI)
        self.assets = MagicMock(spec_set=AssetsAPI)
        self.data_sets = MagicMock(spec_set=DataSetsAPI)
        self.diagrams = MagicMock(spec_set=DiagramsAPI)
        self.entity_matching = MagicMock(spec_set=EntityMatchingAPI)
        self.events = MagicMock(spec_set=EventsAPI)
        self.extraction_pipelines = MagicMock(spec=ExtractionPipelinesAPI)
        self.extraction_pipelines.config = MagicMock(spec_set=ExtractionPipelineConfigsAPI)
        self.extraction_pipelines.runs = MagicMock(spec_set=ExtractionPipelineRunsAPI)
        self.files = MagicMock(spec_set=FilesAPI)
        self.functions = MagicMock(spec=FunctionsAPI)
        self.functions.calls = MagicMock(spec_set=FunctionCallsAPI)
        self.functions.schedules = MagicMock(spec_set=FunctionSchedulesAPI)
        self.geospatial = MagicMock(spec_set=GeospatialAPI)
        self.iam = MagicMock(spec=IAMAPI)
        self.iam.api_keys = MagicMock(spec_set=APIKeysAPI)
        self.iam.groups = MagicMock(spec_set=GroupsAPI)
        self.iam.security_categories = MagicMock(spec_set=SecurityCategoriesAPI)
        self.iam.service_accounts = MagicMock(spec_set=ServiceAccountsAPI)
        self.iam.sessions = MagicMock(spec_set=SessionsAPI)
        self.iam.token = MagicMock(spec_set=TokenAPI)
        self.labels = MagicMock(spec_set=LabelsAPI)
        self.login = MagicMock(spec_set=LoginAPI)
        self.raw = MagicMock(spec=RawAPI)
        self.raw.databases = MagicMock(spec_set=RawDatabasesAPI)
        self.raw.rows = MagicMock(spec_set=RawRowsAPI)
        self.raw.tables = MagicMock(spec_set=RawTablesAPI)
        self.relationships = MagicMock(spec_set=RelationshipsAPI)
        self.sequences = MagicMock(spec=SequencesAPI)
        self.sequences.data = MagicMock(spec_set=SequencesDataAPI)
        self.templates = MagicMock(spec=TemplatesAPI)
        self.templates.groups = MagicMock(spec_set=TemplateGroupsAPI)
        self.templates.instances = MagicMock(spec_set=TemplateInstancesAPI)
        self.templates.versions = MagicMock(spec_set=TemplateGroupVersionsAPI)
        self.templates.views = MagicMock(spec_set=TemplateViewsAPI)
        self.three_d = MagicMock(spec=ThreeDAPI)
        self.three_d.asset_mappings = MagicMock(spec_set=ThreeDAssetMappingAPI)
        self.three_d.files = MagicMock(spec_set=ThreeDFilesAPI)
        self.three_d.models = MagicMock(spec_set=ThreeDModelsAPI)
        self.three_d.revisions = MagicMock(spec_set=ThreeDRevisionsAPI)
        self.time_series = MagicMock(spec=TimeSeriesAPI)
        self.time_series.data = MagicMock(spec=DatapointsAPI)
        self.time_series.data.synthetic = MagicMock(spec_set=SyntheticDatapointsAPI)
        self.datapoints = self.time_series.data
        self.transformations = MagicMock(spec=TransformationsAPI)
        self.transformations.jobs = MagicMock(spec_set=TransformationJobsAPI)
        self.transformations.notifications = MagicMock(spec_set=TransformationNotificationsAPI)
        self.transformations.schedules = MagicMock(spec_set=TransformationSchedulesAPI)
        self.transformations.schema = MagicMock(spec_set=TransformationSchemaAPI)
        self.vision = MagicMock(spec_set=VisionAPI)


@contextmanager
def monkeypatch_cognite_client():
    cognite_client_mock = CogniteClientMock()
    CogniteClient.__new__ = lambda *args, **kwargs: cognite_client_mock
    (yield cognite_client_mock)
    CogniteClient.__new__ = lambda cls, *args, **kwargs: object.__new__(cls)
