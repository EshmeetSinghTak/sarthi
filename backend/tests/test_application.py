import json

from app import application


def test_completeness_counts_nonempty():
    c = application.completeness({"full_name": "Priya", "city": "", "cgpa": "7.8"})
    assert c == {"filled": 2, "total": len(application.FIELD_KEYS)}


def test_extract_fields_filters_to_extractable_and_nonempty(monkeypatch):
    # Model returns an extra non-extractable key and an empty value — both dropped.
    canned = json.dumps({
        "full_name": "Priya Sharma",
        "phone": "9999999999",          # not extractable -> dropped
        "target_course": "",            # empty -> dropped
        "loan_amount_inr_lakh": "45",
    })
    monkeypatch.setattr(application, "_call_model", lambda prompt: canned)
    out = application.extract_fields(["Name is Priya Sharma", "Budget around 45 lakh"])
    assert out == {"full_name": "Priya Sharma", "loan_amount_inr_lakh": "45"}


def test_extract_fields_empty_facts_skips_model():
    assert application.extract_fields([]) == {}


def test_extract_fields_swallows_model_errors(monkeypatch):
    def boom(prompt):
        raise RuntimeError("model down")
    monkeypatch.setattr(application, "_call_model", boom)
    assert application.extract_fields(["something"]) == {}


def test_build_draft_shape(monkeypatch):
    monkeypatch.setattr(application.memory, "all_facts", lambda uid: ["Name is Priya"])
    monkeypatch.setattr(application, "extract_fields", lambda facts: {"full_name": "Priya"})
    draft = application.build_draft("u1")
    assert draft["fields"] == {"full_name": "Priya"}
    assert draft["ai_filled"] == ["full_name"]
    assert draft["status"] == "draft"
    assert draft["reference"] is None
    assert set(draft["documents"]) == set(application.DOCUMENT_KEYS)
    assert all(v is False for v in draft["documents"].values())


def test_public_view_adds_schema_and_completeness():
    stored = {
        "fields": {"full_name": "Priya"}, "ai_filled": ["full_name"],
        "documents": {k: False for k in application.DOCUMENT_KEYS},
        "status": "draft", "reference": None,
    }
    view = application.public_view(stored)
    assert view["schema"]["sections"] and view["schema"]["documents"]
    assert view["completeness"] == {"filled": 1, "total": len(application.FIELD_KEYS)}
