"""Routes and behaviours that need no database (the host of the engine is invalid)."""

import base64
import json
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

import jwt
import pytest
from fastapi.testclient import TestClient

from sms_gateway.api.security import LoginLimiter, create_access_token
from sms_gateway.app import SWAGGER_ASSETS_DIR, create_app
from sms_gateway.settings import Settings
from tests.helpers import STRONG_SECRET, FakeSender, bearer_settings, make_settings

SEND = {"recipients": ["+12025550101"], "message": "hello"}


def client_for(settings: Settings, sender: FakeSender | None = None) -> TestClient:
    app = create_app(settings, sender or FakeSender())
    return TestClient(app, raise_server_exceptions=False)


def basic_header(username: str, password: str) -> dict[str, str]:
    encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {encoded}"}


def bearer_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def bearer_client() -> TestClient:
    return client_for(bearer_settings())


# --- Send ---


def test_send_queues_one_message_per_recipient() -> None:
    sender = FakeSender()
    response = client_for(make_settings(), sender).post(
        "/v1/send", json={"recipients": ["+101", "+102"], "message": "hi"}
    )
    assert response.status_code == 200
    assert sender.calls == [("+101", "hi"), ("+102", "hi")]


def test_send_returns_the_outbox_id_of_each_recipient() -> None:
    response = client_for(make_settings()).post("/v1/send", json=SEND)
    assert response.json() == {"results": [{"DestinationNumber": "+12025550101", "smsID": "1"}]}


def test_send_accepts_a_message_of_480_characters() -> None:
    response = client_for(make_settings()).post(
        "/v1/send", json={"recipients": ["+101"], "message": "x" * 480}
    )
    assert response.status_code == 200


def test_send_refuses_a_message_over_480_characters() -> None:
    response = client_for(make_settings()).post(
        "/v1/send", json={"recipients": ["+101"], "message": "x" * 481}
    )
    assert response.status_code == 400


def test_validation_errors_keep_the_api_error_format() -> None:
    response = client_for(make_settings()).post("/v1/send", json={"message": "hi"})
    body = response.json()
    assert body["message"] == "Input payload validation failed"
    assert "body.recipients" in body["errors"]


@pytest.mark.parametrize("number", ["+12025550123", "2025550123", "55555"])
def test_send_accepts_international_national_and_short_numbers(number: str) -> None:
    response = client_for(make_settings()).post(
        "/v1/send", json={"recipients": [number], "message": "hi"}
    )
    assert response.status_code == 200


@pytest.mark.parametrize("number", ["+1 202 555 0123", "CARRIER", "12", "+" + "1" * 21, ""])
def test_send_refuses_a_malformed_number(number: str) -> None:
    response = client_for(make_settings()).post(
        "/v1/send", json={"recipients": [number], "message": "hi"}
    )
    assert response.status_code == 400


def test_send_refuses_the_whole_request_on_one_malformed_number() -> None:
    sender = FakeSender()
    client_for(make_settings(), sender).post(
        "/v1/send", json={"recipients": ["+12025550123", "nope"], "message": "hi"}
    )
    assert sender.calls == []


# --- Login limit ---


def _fail_logins(client: TestClient, count: int) -> None:
    for _ in range(count):
        client.post("/v1/login", json={"username": "admin", "password": "nope"})


GOOD_LOGIN = {"username": "admin", "password": "s3cret"}


def test_login_is_blocked_after_five_failures(bearer_client: TestClient) -> None:
    _fail_logins(bearer_client, 5)
    response = bearer_client.post("/v1/login", json=GOOD_LOGIN)
    assert (response.status_code, response.json()["message"]) == (429, "Too many login attempts")


def test_blocked_login_says_when_to_retry(bearer_client: TestClient) -> None:
    _fail_logins(bearer_client, 5)
    response = bearer_client.post("/v1/login", json=GOOD_LOGIN)
    assert 0 < int(response.headers["Retry-After"]) <= 300


def test_login_still_works_after_four_failures(bearer_client: TestClient) -> None:
    _fail_logins(bearer_client, 4)
    assert bearer_client.post("/v1/login", json=GOOD_LOGIN).status_code == 200


def test_successful_login_resets_the_failures(bearer_client: TestClient) -> None:
    _fail_logins(bearer_client, 4)
    bearer_client.post("/v1/login", json=GOOD_LOGIN)
    _fail_logins(bearer_client, 4)
    assert bearer_client.post("/v1/login", json=GOOD_LOGIN).status_code == 200


def test_forwarded_header_does_not_escape_the_login_limit(bearer_client: TestClient) -> None:
    _fail_logins(bearer_client, 5)
    response = bearer_client.post(
        "/v1/login", json=GOOD_LOGIN, headers={"X-Forwarded-For": "203.0.113.9"}
    )
    assert response.status_code == 429


def test_failures_expire_after_the_window() -> None:
    limiter = LoginLimiter()
    for _ in range(limiter.MAX_FAILURES):
        limiter.record_failure("client")
    with patch("sms_gateway.api.security.time.monotonic", return_value=1e12):
        limiter.check("client")


def test_limit_applies_per_client() -> None:
    limiter = LoginLimiter()
    for _ in range(limiter.MAX_FAILURES):
        limiter.record_failure("one")
    limiter.check("other")


# --- Background worker ---


def test_no_background_thread_without_webhook_or_retention() -> None:
    app = create_app(make_settings(), FakeSender())
    assert app.state.background.enabled is False


# --- Authentication modes ---


def test_no_auth_mode_leaves_sms_routes_open() -> None:
    assert client_for(make_settings()).post("/v1/send", json=SEND).status_code == 200


def test_bearer_mode_refuses_a_request_without_token(bearer_client: TestClient) -> None:
    response = bearer_client.post("/v1/send", json=SEND)
    assert (response.status_code, response.json()["message"]) == (
        401,
        "Missing Authorization Header",
    )


def test_bearer_mode_accepts_a_login_token(bearer_client: TestClient) -> None:
    login = bearer_client.post("/v1/login", json={"username": "admin", "password": "s3cret"})
    token = login.json()["access_token"]
    response = bearer_client.post("/v1/send", json=SEND, headers=bearer_header(token))
    assert response.status_code == 200


def test_bearer_mode_refuses_a_forged_token(bearer_client: TestClient) -> None:
    forged = jwt.encode({"sub": "admin"}, "another-secret-long-enough-for-hs256-xx", "HS256")
    response = bearer_client.post("/v1/send", json=SEND, headers=bearer_header(forged))
    assert response.status_code == 422


def test_bearer_mode_refuses_an_expired_token(bearer_client: TestClient) -> None:
    expired = jwt.encode({"sub": "admin", "exp": 1}, STRONG_SECRET, "HS256")
    response = bearer_client.post("/v1/send", json=SEND, headers=bearer_header(expired))
    assert (response.status_code, response.json()["message"]) == (401, "Token has expired")


def test_token_has_no_expiration_when_lifetime_is_zero() -> None:
    token = create_access_token(bearer_settings(jwt_access_token_expires="0"), "admin")
    assert "exp" not in jwt.decode(token, STRONG_SECRET, algorithms=["HS256"])


def test_token_expires_after_the_configured_seconds() -> None:
    token = create_access_token(bearer_settings(jwt_access_token_expires="60"), "admin")
    claims = jwt.decode(token, STRONG_SECRET, algorithms=["HS256"])
    assert claims["exp"] - claims["iat"] == 60


def _basic_client() -> TestClient:
    return client_for(
        make_settings(api_security="Basic", api_username="admin", api_password="s3cret")
    )


def test_basic_mode_accepts_valid_credentials() -> None:
    response = _basic_client().post("/v1/send", json=SEND, headers=basic_header("admin", "s3cret"))
    assert response.status_code == 200


def test_basic_mode_refuses_wrong_credentials() -> None:
    response = _basic_client().post("/v1/send", json=SEND, headers=basic_header("admin", "nope"))
    assert (response.status_code, response.json()["message"]) == (401, "Basic authenfication fail")


def test_basic_mode_refuses_a_request_without_credentials() -> None:
    assert _basic_client().post("/v1/send", json=SEND).status_code == 401


def test_login_refuses_wrong_credentials(bearer_client: TestClient) -> None:
    response = bearer_client.post("/v1/login", json={"username": "admin", "password": "nope"})
    assert (response.status_code, response.json()["message"]) == (401, "Bad username or password")


def test_login_is_refused_when_no_credentials_are_configured() -> None:
    response = client_for(make_settings()).post(
        "/v1/login", json={"username": "admin", "password": "admin"}
    )
    assert response.status_code == 401


# --- Refresh (regression: was a 500 outside Bearer mode) ---


def test_refresh_returns_a_token_for_the_same_identity(bearer_client: TestClient) -> None:
    token = create_access_token(bearer_settings(), "admin")
    response = bearer_client.get("/v1/refresh", headers=bearer_header(token))
    claims = jwt.decode(response.json()["access_token"], STRONG_SECRET, algorithms=["HS256"])
    assert claims["sub"] == "admin"


@pytest.mark.parametrize(
    "settings_factory",
    [
        make_settings,
        lambda: make_settings(api_security="Basic", api_username="a", api_password="b"),
    ],
)
def test_refresh_without_token_is_401_in_every_mode(
    settings_factory: Callable[[], Settings],
) -> None:
    assert client_for(settings_factory()).get("/v1/refresh").status_code == 401


# --- Errors ---


class ExplodingSender:
    def send(self, number: str, message: str) -> str:
        raise RuntimeError("secret internal detail")


def test_unexpected_error_does_not_expose_internals() -> None:
    app = create_app(make_settings(), ExplodingSender())
    response = TestClient(app, raise_server_exceptions=False).post("/v1/send", json=SEND)
    assert response.status_code == 500
    assert response.json() == {
        "message": "Internal error",
        "details": "An unexpected error occurred.",
    }


def test_unexpected_error_is_logged_with_its_stack_trace(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app(make_settings(), ExplodingSender())
    TestClient(app, raise_server_exceptions=False).post("/v1/send", json=SEND)
    assert "secret internal detail" in caplog.text


def test_unknown_route_returns_the_api_404_format() -> None:
    response = client_for(make_settings()).get("/nope")
    assert (response.status_code, response.json()["message"]) == (404, "Page not found")


def test_health_reports_an_unreachable_database_without_details() -> None:
    response = client_for(make_settings()).get("/healthz")
    assert response.status_code == 500
    assert response.json() == {
        "status": "unhealthy",
        "database": "disconnected",
        "error": "Unable to connect to database",
    }


# --- Documentation ---


def test_swagger_ui_is_served_at_the_root_from_local_assets() -> None:
    response = client_for(make_settings()).get("/")
    assert response.status_code == 200
    assert "/swaggerui/swagger-ui-bundle.js" in response.text


def test_swagger_assets_are_bundled() -> None:
    assert client_for(make_settings()).get("/swaggerui/swagger-ui-bundle.js").status_code == 200


def test_swagger_ui_can_render_the_generated_openapi_version() -> None:
    """Regression: Swagger UI 4 shows "Unable to render" on the OpenAPI 3.1 of FastAPI."""
    openapi = client_for(make_settings()).get("/openapi.json").json()["openapi"]
    package = json.loads((Path(SWAGGER_ASSETS_DIR) / "package.json").read_text())
    assert openapi.startswith("3.1")
    assert int(package["version"].split(".")[0]) >= 5


def test_openapi_lists_every_public_route() -> None:
    paths = client_for(make_settings()).get("/openapi.json").json()["paths"]
    assert set(paths) == {
        "/healthz",
        "/v1/login",
        "/v1/refresh",
        "/v1/send",
        "/v1/inbox",
        "/v1/inbox/all",
        "/v1/inbox/{id}",
        "/v1/outbox",
        "/v1/outbox/all",
        "/v1/outbox/{id}",
        "/v1/sentitems",
        "/v1/sentitems/all",
        "/v1/sentitems/{id}",
    }
