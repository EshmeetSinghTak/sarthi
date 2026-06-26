import json

from app import config


def test_sop_config_constants():
    assert config.SOP_TARGET_WORDS_MIN == 700
    assert config.SOP_TARGET_WORDS_MAX == 1000
    assert config.SOP_LONG_SENTENCE_WORDS == 40
    assert config.SOP_DB_PATH


def test_sop_cliches_data():
    data = json.loads(
        (config.BACKEND_DIR / "data" / "sop_cliches.json").read_text(encoding="utf-8")
    )
    assert data["note"].strip()
    assert isinstance(data["cliches"], list) and len(data["cliches"]) >= 5
    # stored lowercase so case-insensitive matching is a simple substring test
    assert all(c == c.lower() for c in data["cliches"])
