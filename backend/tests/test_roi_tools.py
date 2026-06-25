import json

from app.tools import estimate_roi, roi_breakdown


def test_estimate_roi_tool_returns_json_list():
    out = estimate_roi.invoke({"field": "Computer Science", "country": "US"})
    data = json.loads(out)
    assert data["count"] > 0
    assert "monthly_emi_inr" in data["results"][0]


def test_estimate_roi_tool_accepts_university_list():
    out = estimate_roi.invoke(
        {"field": "Robotics", "universities": ["Carnegie Mellon University"]}
    )
    data = json.loads(out)
    assert data["count"] == 1
    assert data["results"][0]["name"] == "Carnegie Mellon University"


def test_roi_breakdown_tool_returns_grid():
    out = roi_breakdown.invoke(
        {"university": "Arizona State University", "field": "Computer Science"}
    )
    data = json.loads(out)
    assert "sensitivity_grid" in data
    assert data["university"] == "Arizona State University"
