"""Security core: JWT auth, password hashing, RBAC dependencies, rate limit.

Phase 6 security model for a government-scale CCTV platform:

- tokens: signed JWT (HS256) issued by ``/api/auth/login``
- roles: ADMIN > OPERATOR > INVESTIGATOR > AUDITOR > VIEWER
- every sensitive route declares ``require_roles(...)``
- when ``AUTH_REQUIRED=false`` (development), requests without a token are
  admitted under a synthetic ``DEV`` principal so the existing UI keeps working.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)

ROLE_RANK = {"VIEWER": 0, "AUDITOR": 1, "INVESTIGATOR": 2, "OPERATOR": 3, "ADMIN": 4}


# ---------------------------------------------------------------------------
# Minimal HS256 JWT built on the standard library (no third-party dependency).
# ---------------------------------------------------------------------------
def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(segment: str) -> bytes:
    pad = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + pad)


def _jwt_sign(encoded_head: str, encoded_payload: str, secret: str) -> str:
    signing_input = f"{encoded_head}.{encoded_payload}".encode("ascii")
    digest = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return _b64url(digest)


def _jwt_encode(payload: dict[str, Any], secret: str, algorithm: str = "HS256") -> str:
    if algorithm != "HS256":
        raise ValueError("Only HS256 is supported")
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_head = _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = _jwt_sign(encoded_head, encoded_payload, secret)
    return f"{encoded_head}.{encoded_payload}.{signature}"


def _jwt_decode(token: str, secret: str, algorithm: str = "HS256") -> dict[str, Any]:
    if algorithm != "HS256":
        raise ValueError("Only HS256 is supported")
    try:
        head_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError:
        raise ValueError("Malformed token")
    expected = _jwt_sign(head_b64, payload_b64, secret)
    if not hmac.compare_digest(expected, signature_b64):
        raise ValueError("Invalid signature")
    payload = json.loads(_b64url_decode(payload_b64))
    if payload.get("exp") and int(time.time()) > int(payload["exp"]):
        raise ValueError("Token expired")
    return payload


class Principal:
    """Authenticated request identity."""

    def __init__(
        self,
        user_id: str,
        email: str,
        name: str,
        role: str,
        token: str | None = None,
        dev: bool = False,
    ) -> None:
        self.user_id = user_id
        self.email = email
        self.name = name
        self.role = role
        self.token = token
        self.dev = dev

    @property
    def rank(self) -> int:
        return ROLE_RANK.get(self.role.upper(), 0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "dev": self.dev,
        }


def hash_password(password: str, salt: bytes | None = None) -> str:
    """PBKDF2-HMAC-SHA256 password hash (stdlib, no extra deps)."""
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return f"pbkdf2${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt_hex, digest_hex = stored.split("$")
        if algo != "pbkdf2":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
        return hmac.compare_digest(digest, expected)
    except (ValueError, TypeError):
        return False


def create_access_token(principal: dict[str, Any], settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    now = int(time.time())
    payload = {
        "sub": principal["user_id"],
        "email": principal["email"],
        "name": principal["name"],
        "role": principal["role"].upper(),
        "iat": now,
        "exp": now + settings.jwt_expire_minutes * 60,
    }
    return _jwt_encode(payload, settings.secret_key, settings.jwt_algorithm)


def decode_token(token: str, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    return _jwt_decode(token, settings.secret_key, settings.jwt_algorithm)


@lru_cache(maxsize=16)
def _dev_principal() -> Principal:
    return Principal(
        user_id="DEV-0000",
        email=get_settings().default_admin_email,
        name="Development Operator",
        role="ADMIN",
        dev=True,
    )


def get_current_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Principal:
    settings = get_settings()
    token = credentials.credentials if credentials else None

    if token:
        try:
            payload = decode_token(token, settings)
            return Principal(
                user_id=str(payload.get("sub", "")),
                email=payload.get("email", ""),
                name=payload.get("name", "Operator"),
                role=payload.get("role", "VIEWER"),
                token=token,
            )
        except (ValueError, KeyError):
            raise HTTPException(status_code=401, detail={"code": "INVALID_TOKEN", "message": "Invalid or expired token."})

    if settings.auth_required:
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "Authentication required."},
        )
    return _dev_principal()


def require_roles(*roles: str) -> Callable[[Principal], Principal]:
    required_rank = max(ROLE_RANK.get(r.upper(), 0) for r in roles)

    def _check(principal: Principal = Depends(get_current_principal)) -> Principal:
        if principal.rank < required_rank:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "FORBIDDEN",
                    "message": f"Requires role(s) {'|'.join(roles)}, got {principal.role}.",
                },
            )
        return principal

    return _check


def assert_roles(principal: Principal, *roles: str) -> Principal:
    """Inline (non-dependency) role check for services/plain callables."""
    required_rank = max(ROLE_RANK.get(r.upper(), 0) for r in roles)
    if principal.rank < required_rank:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "FORBIDDEN",
                "message": f"Requires role(s) {'|'.join(roles)}, got {principal.role}.",
            },
        )
    return principal


class RateLimiter:
    """Coarse in-memory sliding-window limiter (single-process development).

    Production deployments should front this with a shared store (Redis).
    """

    def __init__(self, window_seconds: int = 60, max_hits: int = 600) -> None:
        self.window = window_seconds
        self.max_hits = max_hits
        self._buckets: dict[str, list[float]] = {}

    def allow(self, key: str, now: float | None = None) -> bool:
        now = now or time.time()
        hits = [t for t in self._buckets.get(key, []) if now - t < self.window]
        self._buckets[key] = hits
        if len(hits) >= self.max_hits:
            return False
        hits.append(now)
        return True


_rate_limiter = RateLimiter()


def enforce_rate_limit(request: Request) -> None:
    if not get_settings().rate_limit_enabled:
        return
    client = request.client.host if request.client else "unknown"
    key = f"{client}:{request.url.path}"
    if not _rate_limiter.allow(key):
        raise HTTPException(
            status_code=429,
            detail={"code": "RATE_LIMITED", "message": "Too many requests. Slow down."},
        )


class RateLimitMiddleware:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        from starlette.requests import Request

        request = Request(scope, receive)
        try:
            enforce_rate_limit(request)
        except HTTPException as exc:
            response = exc
        else:
            from starlette.responses import JSONResponse

            response = None
        if response is not None:
            from starlette.responses import JSONResponse

            await JSONResponse(status_code=response.status_code, content=response.detail)(scope, receive, send)
            return
        await self.app(scope, receive, send)


# ---------------------------------------------------------------------------
# Original Phase 5 helpers (unchanged behaviour below).
# ---------------------------------------------------------------------------


_UNSAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
_EXTENSION_RE = re.compile(r"\.([A-Za-z0-9]+)$")
_PATH_IN_MESSAGE_RE = re.compile(r"[A-Za-z]:[\\/][^\s'\"]+|[\\/](?:[A-Za-z0-9_.-]+[\\/]){2,}[A-Za-z0-9_.-]*")


def sanitize_error_message(exc: BaseException, limit: int = 300) -> str:
    text = re.sub(r"\s+", " ", str(exc)).strip()
    text = _PATH_IN_MESSAGE_RE.sub("<path>", text)
    return f"{type(exc).__name__}: {text[:limit]}"


def sanitize_basename(filename: str) -> str:
    name = Path(filename).name
    name = _UNSAFE_FILENAME_RE.sub("_", name).strip("._")
    return name or "unnamed"


def extract_extension(filename: str) -> str:
    match = _EXTENSION_RE.search(filename)
    return match.group(1).lower() if match else ""


def is_allowed_video(filename: str, settings: Settings) -> bool:
    return extract_extension(filename) in settings.allowed_video_extensions_list


def is_allowed_evidence(filename: str, settings: Settings) -> bool:
    return extract_extension(filename) in settings.allowed_evidence_extensions_list


def validate_upload_size(size: int, settings: Settings) -> None:
    if size > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail={
                "code": "UPLOAD_TOO_LARGE",
                "message": (
                    f"Upload exceeds the maximum allowed size of "
                    f"{settings.max_upload_size_mb} MB (got {size / 1024 / 1024:.1f} MB)."
                ),
            },
        )