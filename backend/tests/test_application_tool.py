import json

from app import application, app_store
from app.tools import draft_application


def test_draft_application_returns_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(app_store.config, "APPLICATION_DB_PATH", str(tmp_path / "a.db"))
    app_store.init_db()
    monkeypatch.setattr(application, "build_draft",
                        lambda uid: {"fields": {"full_name": "Priya"}, "ai_filled": ["full_name"],
                                     "documents": {}, "status": "draft", "reference": None})
    out = draft_application.invoke({"user_id": "u1"})
    data = json.loads(out)
    assert data["completeness"]["filled"] == 1
    assert "full_name" in data["filled"]
    assert "email" in data["missing"]
    assert data["apply_url"] == "/apply"
