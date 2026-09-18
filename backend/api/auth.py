from __future__ import annotations

from functools import wraps
from typing import Any, Optional

import jwt
from flask import g, request
from jwt import PyJWKClient

from backend.config.settings import settings
from backend.models.schemas import ErrorCategory

_jwks_client: Optional[PyJWKClient] = None
DEMO_USER = {
    "id": "demo-user",
    "email": "demo@sdlc-nexus.local",
    "role": "demo",
}


def _jwks() -> Optional[PyJWKClient]:
    global _jwks_client
    if not settings.supabase_url:
        return None
    if _jwks_client is None:
        url = settings.supabase_url.rstrip("/") + "/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(url)
    return _jwks_client


def verify_token(token: str) -> dict[str, Any]:
    if token in {"demo-token", "DEMO", "local-token"} or not settings.supabase_url:
        return DEMO_USER
    jwks = _jwks()
    if jwks is None:
        return DEMO_USER
    signing_key = jwks.get_signing_key_from_jwt(token)
    payload = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256", "ES256"],
        audience="authenticated",
        options={"verify_aud": False},
    )
    user_id = payload.get("sub")
    if not user_id:
        raise PermissionError("AUTH_ERROR: token missing subject")
    return {
        "id": user_id,
        "email": payload.get("email"),
        "role": payload.get("role") or "authenticated",
        "claims": payload,
    }


def current_user() -> dict[str, Any]:
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        token = header.split(" ", 1)[1].strip()
        return verify_token(token)
    if settings.demo_mode:
        return DEMO_USER
    raise PermissionError("AUTH_ERROR: missing bearer token")


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            g.user = current_user()
        except Exception as exc:
            return {
                "success": False,
                "data": None,
                "error": {"code": ErrorCategory.AUTH_ERROR.value, "message": str(exc), "details": {}},
            }, 401
        return fn(*args, **kwargs)

    return wrapper
