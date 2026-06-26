import pytest
from fastapi.testclient import TestClient

from app import config


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SOP_DB_PATH", str(tmp_path / "sop_api.db"))
    from app.server import app

    with TestClient(app) as c:
        yield c


def test_create_and_get_sop(client):
    r = client.post("/sops", json={"title": "CMU"})
    assert r.status_code == 201
    sid = r.json()["id"]
    g = client.get(f"/sops/{sid}")
    assert g.status_code == 200
    assert g.json()["sop"]["title"] == "CMU"
    assert g.json()["latest"] is None


def test_save_version_returns_analysis(client):
    sid = client.post("/sops", json={"title": "X"}).json()["id"]
    r = client.post(f"/sops/{sid}/versions", json={"content": "word " * 800})
    assert r.status_code == 201
    body = r.json()
    assert body["analysis"]["length_flag"] == "ok"
    assert body["analysis"]["word_count"] == 800
    assert client.get(f"/sops/{sid}/versions").json()["versions"][0]["id"] == body["version"]["id"]


def test_list_sops_scoped_to_user(client):
    client.post("/sops", json={"title": "A"})
    assert len(client.get("/sops").json()["sops"]) == 1


def test_cross_user_access_is_404(client):
    sid = client.post("/sops", json={"title": "Private"}).json()["id"]
    from app.server import app

    with TestClient(app) as other:  # fresh cookie jar = different anonymous user
        assert other.get(f"/sops/{sid}").status_code == 404
        assert other.post(f"/sops/{sid}/versions", json={"content": "x"}).status_code == 404
