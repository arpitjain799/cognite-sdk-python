import pytest

from cognite.client import ClientConfig, CogniteClient
from cognite.client._api_client import APIClient
from cognite.client.credentials import Token
from cognite.client.testing import CogniteClientMock, monkeypatch_cognite_client
from tests.utils import all_mock_children, all_subclasses


def test_ensure_all_apis_are_available_on_cognite_mock():
    mocked_apis = all_mock_children(CogniteClientMock())
    available = {v.__class__ for v in mocked_apis.values()}
    expected = set(all_subclasses(APIClient))
    # Any new APIs that have not been added to CogniteClientMock?
    assert not expected.difference(available)
    # Any removed APIs that are still available on CogniteClientMock?
    assert not available.difference(expected)


@pytest.mark.parametrize("api", list(all_mock_children(CogniteClientMock()).values()))
def test_ensure_all_apis_are_specced_on_cognite_mock(api):
    # All APIs raise when trying to access a non-existing attribute:
    with pytest.raises(AttributeError):
        api.does_not_exist

    # ...but only APIs that do not contain other APIs have spec_set=True.
    if api._spec_set is True:
        assert not api._mock_children
        with pytest.raises(AttributeError):
            api.does_not_exist = 42
    else:
        assert api._mock_children
        api.does_not_exist = 42


def test_cognite_client_accepts_arguments_during_and_after_mock():
    with monkeypatch_cognite_client():
        CogniteClient(ClientConfig(client_name="bla", project="bla", credentials=Token("bla")))
    CogniteClient(ClientConfig(client_name="bla", project="bla", credentials=Token("bla")))


def test_client_mock_can_access_attributes_not_explicitly_defined_on_children():
    c_mock = CogniteClientMock()
    assert c_mock.config.max_workers
