from app.prompts import SYSTEM_PROMPT


def test_prompt_mentions_roi_tools():
    assert "estimate_roi" in SYSTEM_PROMPT
    assert "roi_breakdown" in SYSTEM_PROMPT
