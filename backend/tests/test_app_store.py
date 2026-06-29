from app import app_store


def _builder():
    return {
        "fields": {"full_name": "Priya"},
        "ai_filled": ["full_name"],
        "documents": {"passport": False},
        "status": "draft",
        "reference": None,
    }


def test_get_or_create_persists_then_returns_same(tmp_path, monkeypatch):
    monkeypatch.setattr(app_store.config, "APPLICATION_DB_PATH", str(tmp_path / "a.db"))
    app_store.init_db()
    first = app_store.get_or_create("u1", _builder)
    assert first["fields"]["full_name"] == "Priya"
    # second call does NOT rebuild (builder would raise if called)
    second = app_store.get_or_create("u1", lambda: (_ for _ in ()).throw(AssertionError("rebuilt")))
    assert second["fields"]["full_name"] == "Priya"


def test_save_updates_fields_and_documents(tmp_path, monkeypatch):
    monkeypatch.setattr(app_store.config, "APPLICATION_DB_PATH", str(tmp_path / "a.db"))
    app_store.init_db()
    app_store.get_or_create("u1", _builder)
    saved = app_store.save("u1", {"full_name": "Priya S", "city": "Nagpur"}, {"passport": True})
    assert saved["fields"]["city"] == "Nagpur"
    assert saved["documents"]["passport"] is True
    assert saved["ai_filled"] == ["full_name"]  # unchanged


def test_submit_sets_status_and_reference(tmp_path, monkeypatch):
    monkeypatch.setattr(app_store.config, "APPLICATION_DB_PATH", str(tmp_path / "a.db"))
    app_store.init_db()
    app_store.get_or_create("u1", _builder)
    done = app_store.submit("u1", "SARTHI-ABC123")
    assert done["status"] == "submitted"
    assert done["reference"] == "SARTHI-ABC123"


def test_delete_removes_row(tmp_path, monkeypatch):
    monkeypatch.setattr(app_store.config, "APPLICATION_DB_PATH", str(tmp_path / "a.db"))
    app_store.init_db()
    app_store.get_or_create("u1", _builder)
    assert app_store.delete("u1") is True
    assert app_store.get("u1") is None
    assert app_store.delete("u1") is False  # nothing left to delete


def test_isolation_between_users(tmp_path, monkeypatch):
    monkeypatch.setattr(app_store.config, "APPLICATION_DB_PATH", str(tmp_path / "a.db"))
    app_store.init_db()
    app_store.get_or_create("u1", _builder)
    assert app_store.get("u2") is None
