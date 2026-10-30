"""API authentication: JWT bearer tokens and HTTP basic."""

import hmac
import time
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from threading import Lock
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.params import Depends as DependsParam
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
)

from sms_gateway.api.dependencies import SettingsDep
from sms_gateway.api.errors import ApiError
from sms_gateway.settings import AuthMode, Settings

_bearer_scheme = HTTPBearer(auto_error=False)
_basic_scheme = HTTPBasic(auto_error=False)


class LoginLimiter:
    """Counts failed logins per client, in memory: a restart resets the counters."""

    MAX_FAILURES = 5
    WINDOW_SECONDS = 300

    def __init__(self) -> None:
        self._failures: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def check(self, client: str) -> None:
        """Refuse a client over the limit, even with the right password."""
        now = time.monotonic()
        with self._lock:
            recent = self._recent(client, now)
            if len(recent) >= self.MAX_FAILURES:
                retry_after = int(recent[0] + self.WINDOW_SECONDS - now) + 1
                raise ApiError(
                    429, "Too many login attempts", headers={"Retry-After": str(retry_after)}
                )

    def record_failure(self, client: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._recent(client, now).append(now)
            # Forget clients that stopped trying, so the table cannot grow forever.
            for known in [key for key in self._failures if not self._recent(key, now)]:
                del self._failures[known]

    def reset(self, client: str) -> None:
        with self._lock:
            self._failures.pop(client, None)

    def _recent(self, client: str, now: float) -> list[float]:
        kept = [at for at in self._failures[client] if now - at < self.WINDOW_SECONDS]
        self._failures[client] = kept
        return kept


def credentials_are_valid(settings: Settings, username: str, password: str) -> bool:
    """Constant-time check. Always false when no credentials are configured."""
    if not settings.api_username or not settings.api_password:
        return False
    username_ok = hmac.compare_digest(username.encode(), settings.api_username.encode())
    password_ok = hmac.compare_digest(password.encode(), settings.api_password.encode())
    return username_ok and password_ok


def create_access_token(settings: Settings, identity: str) -> str:
    if not settings.jwt_secret:
        raise ApiError(401, "Bad username or password")
    now = datetime.now(UTC)
    claims: dict[str, object] = {
        "sub": identity,
        "iat": now,
        "nbf": now,
        "jti": str(uuid.uuid4()),
        "type": "access",
    }
    if settings.token_lifetime is not None:
        claims["exp"] = now + settings.token_lifetime
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def read_token_identity(settings: Settings, token: str) -> str:
    """Return the identity of a valid token. Status codes match API v2."""
    if not settings.jwt_secret:
        raise ApiError(401, "Missing Authorization Header")
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub"]},
        )
    except jwt.ExpiredSignatureError as error:
        raise ApiError(401, "Token has expired") from error
    except jwt.InvalidTokenError as error:
        raise ApiError(422, "Invalid token") from error
    identity: str = claims["sub"]
    return identity


def require_bearer(
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> str:
    if credentials is None:
        raise ApiError(401, "Missing Authorization Header")
    return read_token_identity(settings, credentials.credentials)


def require_basic(
    settings: SettingsDep,
    credentials: Annotated[HTTPBasicCredentials | None, Depends(_basic_scheme)],
) -> None:
    if credentials is None or not credentials_are_valid(
        settings, credentials.username, credentials.password
    ):
        raise ApiError(
            401,
            "Basic authenfication fail",
            "Wrong username or password.",
            {"WWW-Authenticate": "Basic"},
        )


def auth_dependencies(mode: AuthMode) -> list[DependsParam]:
    """The dependencies protecting the SMS routes for the configured mode."""
    if mode is AuthMode.BEARER:
        return [Depends(require_bearer)]
    if mode is AuthMode.BASIC:
        return [Depends(require_basic)]
    return []
