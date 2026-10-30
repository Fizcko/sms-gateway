from typing import Any

from sms_gateway.settings import Settings

STRONG_SECRET = "test-secret-that-is-long-enough-for-hs256"


def make_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "mysql_password": "unused",
        "mysql_host": "db.invalid",
        "api_security": "None",
        "api_username": None,
        "api_password": None,
        "jwt_secret": None,
        "jwt_access_token_expires": "900",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def bearer_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "api_security": "Bearer",
        "api_username": "admin",
        "api_password": "s3cret",
        "jwt_secret": STRONG_SECRET,
    }
    values.update(overrides)
    return make_settings(**values)


class FakeSender:
    """Records the calls instead of talking to Gammu."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def send(self, number: str, message: str) -> str:
        self.calls.append((number, message))
        return str(len(self.calls))
