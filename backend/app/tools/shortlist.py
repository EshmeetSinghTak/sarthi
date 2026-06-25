"""F2 — University Shortlister.

A heuristic (not ML) matcher: given a student's field, target country, and
profile (CGPA on India's 10-point scale, GRE, budget), it ranks universities
from a hand-curated dataset and labels each Reach / Target / Safe with reasons.

Exposed to the agent as the `shortlist_universities` LangChain tool. The pure
`shortlist()` function underneath is independently testable.
"""

import json
from pathlib import Path

from langchain_core.tools import tool

from ..config import USD_PER_INR  # shared FX constant (see CLAUDE.md D7)

_DATA = json.loads(
    (Path(__file__).resolve().parent.parent.parent / "data" / "universities.json").read_text(
        encoding="utf-8"
    )
)
UNIVERSITIES = _DATA["universities"]
DATA_NOTE = _DATA["data_note"]

# Map free-text field requests onto the dataset taxonomy.
_FIELD_SYNONYMS = {
    "cs": "Computer Science",
    "computer science": "Computer Science",
    "computing": "Computer Science",
    "software": "Computer Science",
    "ai": "AI/ML",
    "ml": "AI/ML",
    "machine learning": "AI/ML",
    "artificial intelligence": "AI/ML",
    "data": "Data Science",
    "data science": "Data Science",
    "ds": "Data Science",
    "robotics": "Robotics",
    "ece": "Electrical Engineering",
    "electrical": "Electrical Engineering",
    "electronics": "Electrical Engineering",
    "mech": "Mechanical Engineering",
    "mechanical": "Mechanical Engineering",
    "civil": "Civil Engineering",
    "mba": "Business/MBA",
    "business": "Business/MBA",
    "management": "Business/MBA",
}


def _normalize_field(field: str) -> str | None:
    f = (field or "").strip().lower()
    if f in _FIELD_SYNONYMS:
        return _FIELD_SYNONYMS[f]
    # substring fallback (e.g. "robotics engineering" -> Robotics)
    for key, canon in _FIELD_SYNONYMS.items():
        if key in f:
            return canon
    return None


def _normalize_country(country: str | None) -> str | None:
    if not country:
        return None
    c = country.strip().lower()
    if c in {"us", "usa", "u.s.", "u.s.a.", "united states", "america"}:
        return "US"
    if c in {"canada", "ca"}:
        return "Canada"
    return country.strip()


def _band(cgpa: float | None, gre: int | None, uni: dict) -> str:
    """Reach / Target / Safe relative to the school's typical profile."""
    if cgpa is None:
        return "Unknown"
    gap = cgpa - uni["typical_cgpa"]
    if gre and uni.get("gre_typical"):
        # Blend in GRE gap, scaled to the CGPA scale (~10 GRE pts ≈ 0.5 CGPA).
        gap = (gap + (gre - uni["gre_typical"]) / 20.0) / 2
    if gap >= 0.7:
        band = "Safe"
    elif gap >= -0.4:
        band = "Target"
    else:
        band = "Reach"
    # The most selective schools are never truly "Safe".
    if uni["competitiveness"] >= 5 and band == "Safe":
        band = "Target"
    return band


def shortlist(
    field: str,
    country: str | None = None,
    cgpa: float | None = None,
    gre: int | None = None,
    budget_inr_lakh: float | None = None,
    years: int = 2,
    limit: int = 8,
) -> dict:
    """Rank universities for a student. Pure function; returns plain dicts."""
    canon_field = _normalize_field(field)
    canon_country = _normalize_country(country)
    budget_usd_per_year = (
        (budget_inr_lakh * 100_000 * USD_PER_INR) / max(years, 1)
        if budget_inr_lakh
        else None
    )

    scored = []
    for uni in UNIVERSITIES:
        # Field is a hard filter when we recognise it.
        field_match = canon_field in uni["fields"] if canon_field else True
        if canon_field and not field_match:
            continue
        if canon_country and uni["country"] != canon_country:
            continue

        affordable = (
            budget_usd_per_year is None or uni["tuition_usd"] <= budget_usd_per_year * 1.1
        )
        band = _band(cgpa, gre, uni)

        reasons = []
        if canon_field:
            reasons.append(f"Offers {canon_field}")
        if budget_usd_per_year is not None:
            reasons.append(
                "Within budget" if affordable else "Above stated budget"
            )
        if band != "Unknown":
            reasons.append(f"{band} for your profile")
        if uni.get("notes"):
            reasons.append(uni["notes"])

        score = 0.0
        score += 2.0 if (canon_field and field_match) else 0.5
        score += 1.0 if (canon_country and uni["country"] == canon_country) else 0.0
        score += 1.5 if affordable else 0.0
        score += {"Target": 2.0, "Safe": 1.5, "Reach": 1.0, "Unknown": 1.0}[band]
        score += max(0.0, (350 - uni["qs_rank"]) / 350)  # mild prestige nudge

        scored.append(
            {
                "name": uni["name"],
                "country": uni["country"],
                "city": uni["city"],
                "qs_rank": uni["qs_rank"],
                "est_tuition_usd_per_year": uni["tuition_usd"],
                "est_tuition_inr_lakh_per_year": round(uni["tuition_usd"] / 100_000 / USD_PER_INR, 1),
                "admission_band": band,
                "within_budget": affordable,
                "why": reasons,
                "_score": round(score, 3),
            }
        )

    scored.sort(key=lambda r: r["_score"], reverse=True)
    results = [{k: v for k, v in r.items() if k != "_score"} for r in scored[:limit]]
    return {
        "note": DATA_NOTE,
        "query": {
            "field": canon_field or field,
            "country": canon_country,
            "cgpa": cgpa,
            "gre": gre,
            "budget_inr_lakh": budget_inr_lakh,
        },
        "count": len(results),
        "results": results,
    }


@tool
def shortlist_universities(
    field: str,
    country: str | None = None,
    cgpa: float | None = None,
    gre: int | None = None,
    budget_inr_lakh: float | None = None,
) -> str:
    """Suggest universities for a student's study-abroad plan.

    Call this when the student wants university suggestions and you know at
    least their field of study. Pass whatever you know; omit unknown args.

    Args:
        field: Field of study, e.g. "Robotics", "Computer Science", "MBA".
        country: Preferred country, "US" or "Canada". Omit if open to any.
        cgpa: Student's CGPA on India's 10-point scale (e.g. 7.8).
        gre: Total GRE score out of 340, if taken.
        budget_inr_lakh: Total budget in INR lakh for the whole degree (e.g. 45).

    Returns a JSON string of ranked universities, each with an estimated cost,
    an admission band (Reach/Target/Safe), and reasons. All figures are
    approximate — present them as guidance, not official data.
    """
    return json.dumps(
        shortlist(field, country=country, cgpa=cgpa, gre=gre, budget_inr_lakh=budget_inr_lakh)
    )
