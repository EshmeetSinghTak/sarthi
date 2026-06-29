from fastapi.testclient import TestClient

from app import application
from app.server import app


def test_get_creates_and_put_saves_and_submit(monkeypatch):
    # Avoid a live model call: stub extraction.
    monkeypatch.setattr(application, "extract_fields", lambda facts: {"full_name": "Priya"})
    with TestClient(app) as client:
        got = client.get("/application")
        assert got.status_code == 200
        view = got.json()["application"]
        assert "schema" in view and "completeness" in view

        put = client.put("/application", json={"fields": {"full_name": "Priya S", "city": "Nagpur"},
                                               "documents": {"passport": True}})
        assert put.status_code == 200
        assert put.json()["application"]["fields"]["city"] == "Nagpur"

        sub = client.post("/application/submit")
        assert sub.status_code == 200
        out = sub.json()["application"]
        assert out["status"] == "submitted"
        assert out["reference"].startswith("SARTHI-")

        # Reset returns a fresh draft (no longer submitted, no stale edits).
        reset = client.post("/application/reset")
        assert reset.status_code == 200
        fresh = reset.json()["application"]
        assert fresh["status"] == "draft"
        assert fresh["reference"] is None
        assert fresh["fields"].get("city", "") == ""
