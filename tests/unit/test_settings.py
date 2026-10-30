from datetime import timedelta

import pytest
from pydantic import ValidationError

from sms_gateway.settings import AuthMode
from tests.helpers import STRONG_SECRET, bearer_settings, make_settings


def test_token_lifetime_is_expressed_in_seconds() -> None:
    assert make_settings(jwt_access_token_expires="60").token_lifetime == timedelta(seconds=60)


def test_token_lifetime_zero_disables_expiration() -> None:
    assert make_settings(jwt_access_token_expires="0").token_lifetime is None


def test_token_lifetime_not_numeric_falls_back_to_default() -> None:
    assert make_settings(jwt_access_token_expires="soon").token_lifetime == timedelta(seconds=900)


def test_unknown_security_value_refuses_the_start() -> None:
    with pytest.raises(ValidationError):
        make_settings(api_security="bearer")


def test_webhook_url_requires_a_secret() -> None:
    with pytest.raises(ValidationError, match="WEBHOOK_SECRET"):
        make_settings(webhook_url="https://app.example/sms")


def test_invalid_webhook_url_refuses_the_start() -> None:
    with pytest.raises(ValidationError):
        make_settings(webhook_url="not a url", webhook_secret="s")


def test_blank_webhook_url_means_no_webhook() -> None:
    assert make_settings(webhook_url="").webhook_url is None


def test_blank_retention_means_no_purge() -> None:
    assert make_settings(retention_days="").retention_days is None


def test_retention_under_one_day_refuses_the_start() -> None:
    with pytest.raises(ValidationError):
        make_settings(retention_days=0)


def test_database_password_is_required() -> None:
    from sms_gateway.settings import Settings

    with pytest.raises(ValidationError):
        Settings(_env_file=None, mysql_password=None)


def test_bearer_mode_requires_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        bearer_settings(jwt_secret=None)


def test_bearer_mode_refuses_blank_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        bearer_settings(jwt_secret="")


@pytest.mark.parametrize("mode", ["Bearer", "Basic"])
def test_secured_modes_require_api_credentials(mode: str) -> None:
    with pytest.raises(ValidationError, match="API_USERNAME, API_PASSWORD"):
        make_settings(api_security=mode, jwt_secret=STRONG_SECRET)


def test_no_auth_mode_starts_without_any_secret() -> None:
    assert make_settings().auth_mode is AuthMode.NONE


def test_special_characters_in_database_password_are_preserved() -> None:
    settings = make_settings(mysql_password="p@ss/w:rd")
    assert settings.database_url.password == "p@ss/w:rd"


def test_database_host_can_carry_a_port() -> None:
    settings = make_settings(mysql_host="db:3307")
    assert (settings.database_url.host, settings.database_url.port) == ("db", 3307)
