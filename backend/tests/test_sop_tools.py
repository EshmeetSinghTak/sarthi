import pytest

from app import config, sop_store
from app.tools import sop as sop_mod


@pytest.fixture
def seeded(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SOP_DB_PATH", str(tmp_path / "t.db"))
    sop_store.init_db()


def _add(user, title, content):
    s = sop_store.create_sop(user, title)
    sop_store.add_version(user, s["id"], content, sop_mod.analyze_sop(content))
    return s


def test_review_sop_no_sop(seeded):
    assert "error" in sop_mod._review_sop("u1")


def test_review_sop_single(seeded):
    _add("u1", "CMU", "I want this program because my goal is research. " * 5)
    out = sop_mod._review_sop("u1")
    assert out["sop_title"] == "CMU"
    assert "analysis" in out and "draft" in out


def test_review_sop_needs_title_when_multiple(seeded):
    _add("u1", "CMU", "x")
    _add("u1", "MIT", "y")
    out = sop_mod._review_sop("u1")
    assert out.get("need_title") is True
    assert set(out["available"]) == {"CMU", "MIT"}


def test_review_sop_by_title_substring(seeded):
    _add("u1", "CMU Robotics", "x")
    _add("u1", "MIT EECS", "y")
    assert sop_mod._review_sop("u1", "mit")["sop_title"] == "MIT EECS"


def test_list_my_sops(seeded):
    _add("u1", "CMU", "x")
    out = sop_mod._list_my_sops("u1")
    assert [s["title"] for s in out["sops"]] == ["CMU"]


def test_tool_names():
    assert sop_mod.review_sop.name == "review_sop"
    assert sop_mod.list_my_sops.name == "list_my_sops"
