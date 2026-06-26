import pytest

from app import config, sop_store


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SOP_DB_PATH", str(tmp_path / "sop.db"))
    sop_store.init_db()


def test_create_and_list(db):
    s = sop_store.create_sop("u1", "CMU Robotics")
    assert s["title"] == "CMU Robotics" and s["user_id"] == "u1"
    sops = sop_store.list_sops("u1")
    assert len(sops) == 1 and sops[0]["id"] == s["id"]
    assert sops[0]["latest_version_id"] is None


def test_append_only_versions_and_latest(db):
    s = sop_store.create_sop("u1", "X")
    sop_store.add_version("u1", s["id"], "draft one", {"word_count": 2})
    sop_store.add_version("u1", s["id"], "draft two longer", {"word_count": 3})
    latest = sop_store.get_latest_version("u1", s["id"])
    assert latest["content"] == "draft two longer"
    assert latest["analysis"] == {"word_count": 3}
    assert len(sop_store.list_versions("u1", s["id"])) == 2


def test_restore_as_new_version(db):
    s = sop_store.create_sop("u1", "X")
    v1 = sop_store.add_version("u1", s["id"], "original", {"word_count": 1})
    sop_store.add_version("u1", s["id"], "edited", {"word_count": 1})
    old = sop_store.get_version("u1", s["id"], v1["id"])
    sop_store.add_version("u1", s["id"], old["content"], {"word_count": 1})
    assert sop_store.get_latest_version("u1", s["id"])["content"] == "original"
    assert len(sop_store.list_versions("u1", s["id"])) == 3


def test_ownership_isolation(db):
    s = sop_store.create_sop("u1", "Private")
    sop_store.add_version("u1", s["id"], "secret", {"word_count": 1})
    assert sop_store.get_sop("u2", s["id"]) is None
    assert sop_store.get_latest_version("u2", s["id"]) is None
    assert sop_store.get_version("u2", s["id"], 1) is None
    assert sop_store.add_version("u2", s["id"], "hack", {"word_count": 1}) is None
    assert sop_store.list_sops("u2") == []
    assert sop_store.list_versions("u2", s["id"]) == []
