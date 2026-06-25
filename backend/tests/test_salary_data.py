import json

from app import config


def _load(name):
    return json.loads((config.BACKEND_DIR / "data" / name).read_text(encoding="utf-8"))


def test_salary_priors_cover_every_field_and_country():
    salary = _load("salary_priors.json")
    taxonomy = _load("universities.json")["fields_taxonomy"]
    for country in ("US", "Canada"):
        assert salary["living_cost_usd_per_year"][country] > 0
        for field in taxonomy:
            assert salary["starting_salary_usd"][country][field] > 0


def test_salary_priors_has_data_note():
    salary = _load("salary_priors.json")
    assert salary["data_note"].strip()
