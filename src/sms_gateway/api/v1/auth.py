from typing import Annotated

from fastapi import APIRouter, Depends, Request

from sms_gateway.api.dependencies import SettingsDep
from sms_gateway.api.errors import ApiError
from sms_gateway.api.security import (
    LoginLimiter,
    create_access_token,
    credentials_are_valid,
    require_bearer,
)
from sms_gateway.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(tags=["Authentication"])


@router.post("/v1/login", summary="Get a bearer token", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, settings: SettingsDep) -> TokenResponse:
    # The direct peer only: X-Forwarded-For can be forged to escape the limit.
    client = request.client.host if request.client else "unknown"
    limiter: LoginLimiter = request.app.state.login_limiter
    limiter.check(client)
    if not credentials_are_valid(settings, payload.username, payload.password):
        limiter.record_failure(client)
        raise ApiError(401, "Bad username or password")
    limiter.reset(client)
    return TokenResponse(access_token=create_access_token(settings, payload.username))


@router.get(
    "/v1/refresh",
    summary="Exchange a valid bearer token for a new one",
    response_model=TokenResponse,
)
def refresh(
    settings: SettingsDep, identity: Annotated[str, Depends(require_bearer)]
) -> TokenResponse:
    """A refresh always needs a valid token, whatever `API_SECURITY` is."""
    return TokenResponse(access_token=create_access_token(settings, identity))
