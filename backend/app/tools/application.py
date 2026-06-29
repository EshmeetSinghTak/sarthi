"""F6 — draft_application agent tool. Assembles/loads the student's loan
application draft from memory and reports how much is pre-filled."""

import json
from typing import Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from .. import app_store, application


@tool
def draft_application(user_id: Annotated[str, InjectedState("user_id")] = "") -> str:
    """Pre-fill the student's education-loan application from what you remember.

    Call this when the student is ready to apply for the loan, or asks to start /
    fill the loan application. It reads their saved profile facts and drafts the
    application, then reports how many fields were pre-filled and what's still
    needed.

    Returns a JSON string with completeness (filled/total), the list of pre-filled
    fields, the list of still-missing fields, and the page to finish on. Tell the
    student how much you pre-filled, name a couple of the missing items, and point
    them to the application page to review and submit. The values are drafted from
    their own messages — remind them to verify before submitting.
    """
    stored = app_store.get_or_create(user_id, lambda: application.build_draft(user_id))
    view = application.public_view(stored)
    fields = view["fields"]
    filled = [k for k in application.FIELD_KEYS if str(fields.get(k, "")).strip()]
    missing = [k for k in application.FIELD_KEYS if not str(fields.get(k, "")).strip()]
    return json.dumps({
        "completeness": view["completeness"],
        "filled": filled,
        "missing": missing,
        "status": view["status"],
        "apply_url": "/apply",
    })
