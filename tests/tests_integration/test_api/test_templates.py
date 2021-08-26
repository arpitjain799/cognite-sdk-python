from cognite.client.data_classes.events import Event
from cognite.client.data_classes.templates import Source, TemplateInstanceUpdate, View, ViewResolver
import uuid

import pytest

from cognite.client import CogniteClient
from cognite.client.data_classes import (
    ConstantResolver,
    TemplateGroup,
    TemplateGroupList,
    TemplateGroupVersion,
    TemplateGroupVersionList,
    TemplateInstance,
    TemplateInstanceList,
)
from cognite.client.exceptions import CogniteNotFoundError

API = CogniteClient()
API_GROUPS = API.templates.groups
API_VERSION = API.templates.versions
API_INSTANCES = API.templates.instances
API_VIEWS = API.templates.views


@pytest.fixture
def new_template_group():
    external_id = uuid.uuid4().hex[0:20]
    username = API.login.status().user
    template_group = API_GROUPS.create(
        TemplateGroup(
            external_id=external_id, description="some description", owners=[username, external_id + "@cognite.com"]
        )
    )
    yield template_group, external_id
    API_GROUPS.delete(external_ids=external_id)
    assert API_GROUPS.retrieve_multiple(external_ids=template_group.external_id) is None


@pytest.fixture
def new_template_group_version(new_template_group):
    new_group, ext_id = new_template_group
    schema = """
    type Demographics @template {
        "The amount of people"
        populationSize: Int,
        "The population growth rate"
        growthRate: Float,
    }

    type Country @template {
        name: String,
        testView: Long,
        demographics: Demographics,
        deaths: TimeSeries,
        confirmed: TimeSeries,
    }"""
    version = TemplateGroupVersion(schema)
    new_version = API_VERSION.upsert(ext_id, version=version)
    yield new_group, ext_id, new_version
    print(ext_id, new_version.version)
    API_VERSION.delete(ext_id, new_version.version)


@pytest.fixture
def new_template_instance(new_template_group_version):
    new_group, ext_id, new_version = new_template_group_version
    template_instance_1 = TemplateInstance(
        external_id="norway",
        template_name="Country",
        field_resolvers={
            "name": ConstantResolver("Norway"),
            "testView": ViewResolver("test", {"type": "bar"}),
            "demographics": ConstantResolver("norway_demographics"),
            "deaths": ConstantResolver("Norway_deaths"),
            "confirmed": ConstantResolver("Norway_confirmed"),
        },
    )
    instance = API_INSTANCES.create(ext_id, new_version.version, template_instance_1)
    yield new_group, ext_id, new_version, instance
    API_INSTANCES.delete(ext_id, new_version.version, instance.external_id)


@pytest.fixture
def new_view(new_template_group_version):
    events = []
    for i in range(0, 1001):
        events.append(Event(external_id="test_evt_templates_1_" + str(i), type="test_templates_1", start_time=i * 1000))
    try:
        API.events.create(events)
    except:
        # We only generate this data once for a given project, to prevent issues with eventual consistency etc.
        None

    new_group, ext_id, new_version = new_template_group_version
    view = View(
        external_id="test",
        source=Source(
            type="events",
            filter={"startTime": {"min": "$minStartTime"}, "type": "test_templates_1"},
            mappings={"test_type": "type", "startTime": "startTime"},
        ),
    )
    view = API_VIEWS.create(ext_id, new_version.version, view)
    yield new_group, ext_id, new_version, view
    try:
        API_VIEWS.delete(ext_id, new_version.version, view.external_id)
    except:
        None


class TestTemplatesAPI:
    def test_groups_get_single(self, new_template_group):
        new_group, ext_id = new_template_group
        res = API_GROUPS.retrieve_multiple(external_ids=[new_group.external_id])
        assert isinstance(res[0], TemplateGroup)
        assert new_group.external_id == ext_id

    def test_groups_retrieve_unknown(self, new_template_group):
        with pytest.raises(CogniteNotFoundError):
            API_GROUPS.retrieve_multiple(external_ids=["this does not exist"])
        assert API_GROUPS.retrieve_multiple(external_ids="this does not exist") is None

    def test_groups_list_filter(self, new_template_group):
        new_group, ext_id = new_template_group
        res = API_GROUPS.list(owners=[ext_id + "@cognite.com"])
        assert len(res) == 1
        assert isinstance(res, TemplateGroupList)

    def test_groups_upsert(self, new_template_group):
        new_group, ext_id = new_template_group
        res = API_GROUPS.upsert(TemplateGroup(ext_id))
        assert isinstance(res, TemplateGroup)

    def test_versions_list(self, new_template_group_version):
        new_group, ext_id, new_version = new_template_group_version
        res = API_VERSION.list(ext_id)
        assert len(res) == 1
        assert isinstance(res, TemplateGroupVersionList)

    def test_instances_get_single(self, new_template_instance):
        new_group, ext_id, new_version, new_instance = new_template_instance
        res = API_INSTANCES.retrieve_multiple(ext_id, new_version.version, new_instance.external_id)
        assert isinstance(res, TemplateInstance)
        assert res.external_id == new_instance.external_id

    def test_instances_list(self, new_template_instance):
        new_group, ext_id, new_version, new_instance = new_template_instance
        res = API_INSTANCES.list(ext_id, new_version.version, template_names=["Country"])
        assert isinstance(res, TemplateInstanceList)
        assert len(res) == 1

    def test_instances_upsert(self, new_template_instance):
        new_group, ext_id, new_version, new_instance = new_template_instance
        upserted_instance = TemplateInstance(
            external_id="norway",
            template_name="Demographics",
            field_resolvers={"populationSize": ConstantResolver(5328000), "growthRate": ConstantResolver(value=0.02)},
        )
        res = API_INSTANCES.upsert(ext_id, new_version.version, upserted_instance)
        assert res.external_id == new_instance.external_id

    def test_instances_update_add(self, new_template_instance):
        new_group, ext_id, new_version, new_instance = new_template_instance
        upserted_instance = TemplateInstanceUpdate(external_id="norway").field_resolvers.add(
            {"name": ConstantResolver("Patched")}
        )
        res = API_INSTANCES.update(ext_id, new_version.version, upserted_instance)
        assert res.external_id == new_instance.external_id and res.field_resolvers["name"] == ConstantResolver(
            "Patched"
        )

    def test_instances_update_remove(self, new_template_instance):
        new_group, ext_id, new_version, new_instance = new_template_instance
        upserted_instance = TemplateInstanceUpdate(external_id="norway").field_resolvers.remove(["name"])
        res = API_INSTANCES.update(ext_id, new_version.version, upserted_instance)
        assert res.external_id == new_instance.external_id and "name" not in res.field_resolvers

    def test_instances_update_set(self, new_template_instance):
        new_group, ext_id, new_version, new_instance = new_template_instance
        upserted_instance = TemplateInstanceUpdate(external_id="norway").field_resolvers.set(
            {"name": ConstantResolver("Patched")}
        )
        res = API_INSTANCES.update(ext_id, new_version.version, upserted_instance)
        assert res.external_id == new_instance.external_id and res.field_resolvers == {
            "name": ConstantResolver("Patched")
        }

    def test_query(self, new_template_instance):
        new_group, ext_id, new_version, new_instance = new_template_instance
        query = """
        { 
        countryList 
            { 
                name, 
                deaths { 
                    externalId, 
                    datapoints(limit: 2) { 
                        timestamp, value 
                    } 
                }, 
                confirmed { 
                    externalId, 
                    datapoints(limit: 2) { 
                        timestamp, value 
                    } 
                } 
            } 
        }
        """
        res = API.templates.graphql_query(ext_id, 1, query)
        assert res.data is not None

    def test_view_list(self, new_view):
        new_group, ext_id, new_version, view = new_view
        first_element = [
            res for res in API_VIEWS.list(ext_id, new_version.version) if res.external_id == view.external_id
        ][0]
        assert first_element == view

    def test_view_delete(self, new_view):
        new_group, ext_id, new_version, view = new_view
        API_VIEWS.delete(ext_id, new_version.version, [view.external_id])
        assert (
            len([res for res in API_VIEWS.list(ext_id, new_version.version) if res.external_id == view.external_id])
            == 0
        )

    def test_view_resolve(self, new_view):
        new_group, ext_id, new_version, view = new_view
        res = API_VIEWS.resolve(
            ext_id, new_version.version, view.external_id, input={"minStartTime": 10 * 1000}, limit=10
        )
        assert res == [{"startTime": (i + 10) * 1000, "test_type": "test_templates_1"} for i in range(0, 10)]

    def test_view_resolve_pagination(self, new_view):
        new_group, ext_id, new_version, view = new_view
        res = API_VIEWS.resolve(ext_id, new_version.version, view.external_id, input={"minStartTime": 0}, limit=-1)
        assert res == [{"startTime": i * 1000, "test_type": "test_templates_1"} for i in range(0, 1001)]

    def test_view_upsert(self, new_view):
        new_group, ext_id, new_version, view = new_view
        view.source.mappings["another_type"] = "type"
        res = API_VIEWS.upsert(ext_id, new_version.version, [view])
        assert res == view
