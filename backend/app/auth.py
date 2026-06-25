"""Anonymous signed-cookie identity (Option A).

The server is the sole source of a user's identity. A user_id is a random
opaque token that the server mints and returns in an httpOnly cookie, signed
with SARTHI_SECRET_KEY (HMAC-SHA256). On every request we read the cookie and
verify the signature — so a client cannot forge or change their user_id, and
the request body is never trusted for identity.

This closes the spoofing/IDOR gap from the security review while staying
anonymous (no login). Real accounts can layer on top later.
"""

import base64
import hashlib
import hmac
import secrets as _secrets
import uuid

from fastapi import Request, Response

from .config import settings

COOKIE_NAME = "sarthi_uid"
_MAX_AGE = 60 * 60 * 24 * 365  # 1 year


def _sign(uid: str) -> str:
    sig = hmac.new(settings.secret_key.encode(), uid.encode(), hashlib.sha256).digest()
    return f"{uid}.{base64.urlsafe_b64encode(sig).decode().rstrip('=')}"


def _verify(token: str) -> str | None:
    try:
        uid, sig = token.rsplit(".", 1)
    except ValueError:
        return None
    expected = _sign(uid).rsplit(".", 1)[1]
    # Constant-time compare to avoid signature timing leaks.
    if hmac.compare_digest(sig, expected):
        return uid
    return None


def resolve_user(request: Request) -> tuple[str, bool]:
    """Return (user_id, is_new). is_new means a cookie must be set."""
    token = request.cookies.get(COOKIE_NAME)
    if token:
        uid = _verify(token)
        if uid:
            return uid, False
    # Mint a fresh anonymous identity.
    return f"u_{uuid.uuid4().hex}", True


def set_cookie(response: Response, user_id: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        _sign(user_id),
        max_age=_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


def generate_secret() -> str:
    """Convenience for producing a SARTHI_SECRET_KEY."""
    return _secrets.token_urlsafe(48)
