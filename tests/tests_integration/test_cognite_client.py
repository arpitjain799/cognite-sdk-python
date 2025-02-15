import pytest

from cognite.client.exceptions import CogniteAPIError


@pytest.fixture
def cognite_client_with_wrong_base_url(cognite_client, monkeypatch):
    monkeypatch.setattr(cognite_client.config, "base_url", "https://cognitedata.com")
    yield cognite_client


class TestCogniteClient:
    def test_wrong_base_url_resulting_in_301(self, cognite_client_with_wrong_base_url):
        with pytest.raises(CogniteAPIError):
            cognite_client_with_wrong_base_url.assets.list(limit=1)

    def test_post(self, cognite_client):
        with pytest.raises(CogniteAPIError) as e:
            cognite_client.post("/login", json={})
        assert e.value.code == 404

    def test_put(self, cognite_client):
        with pytest.raises(CogniteAPIError) as e:
            cognite_client.put("/login")
        assert e.value.code == 404

    def test_delete(self, cognite_client):
        with pytest.raises(CogniteAPIError) as e:
            cognite_client.delete("/login")
        assert e.value.code == 404
