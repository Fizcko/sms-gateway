"""Application configuration, read from the environment (or a `.env` file)."""

from datetime import timedelta
from enum import StrEnum
from typing import Self

from pydantic import Field, HttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

DEFAULT_TOKEN_LIFETIME_SECONDS = 900


class AuthMode(StrEnum):
    NONE = "None"
    BEARER = "Bearer"
    BASIC = "Basic"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_version: str = "3.0.0"
    server_ip: str = "0.0.0.0"
    server_port: int = 5000

    gammu_smsd_conf: str = "/etc/gammu-smsdrc"

    mysql_host: str = "localhost"
    mysql_user: str = "root"
    mysql_password: str
    mysql_database: str = "smsd"

    api_security: AuthMode = AuthMode.NONE
    api_username: str | None = None
    api_password: str | None = None

    jwt_secret: str | None = None
    jwt_algorithm: str = "HS256"
    jwt_access_token_expires: str = str(DEFAULT_TOKEN_LIFETIME_SECONDS)

    webhook_url: HttpUrl | None = None
    webhook_secret: str | None = None
    webhook_timeout: float = Field(default=10, gt=0)
    webhook_incomplete_delay: int = Field(default=600, ge=0)

    retention_days: int | None = Field(default=None, ge=1)

    @field_validator(
        "api_username",
        "api_password",
        "jwt_secret",
        "webhook_url",
        "webhook_secret",
        "retention_days",
        mode="before",
    )
    @classmethod
    def _blank_value_is_missing(cls, value: object) -> object:
        """Compose passes unset optional variables as empty strings."""
        return None if value == "" else value

    @property
    def auth_mode(self) -> AuthMode:
        return self.api_security

    @property
    def token_lifetime(self) -> timedelta | None:
        """Token lifetime, in seconds in the environment. `None` means no expiration."""
        raw = self.jwt_access_token_expires
        seconds = int(raw) if raw.isdecimal() else DEFAULT_TOKEN_LIFETIME_SECONDS
        return timedelta(seconds=seconds) if seconds else None

    @property
    def database_url(self) -> URL:
        return self._url(self.mysql_database)

    @property
    def server_url(self) -> URL:
        """Same server, no database selected: used to create the database."""
        return self._url(None)

    def _url(self, database: str | None) -> URL:
        host, _, port = self.mysql_host.partition(":")
        return URL.create(
            "mysql+pymysql",
            username=self.mysql_user,
            password=self.mysql_password,
            host=host,
            port=int(port) if port else None,
            database=database,
            query={"charset": "utf8mb4"},
        )

    @model_validator(mode="after")
    def _require_secrets_of_the_auth_mode(self) -> Self:
        """Refuse to start with an auth mode whose secrets are missing."""
        missing: list[str] = []
        if self.auth_mode is not AuthMode.NONE:
            if not self.api_username:
                missing.append("API_USERNAME")
            if not self.api_password:
                missing.append("API_PASSWORD")
        if self.auth_mode is AuthMode.BEARER and not self.jwt_secret:
            missing.append("JWT_SECRET")
        if missing:
            raise ValueError(f"API_SECURITY={self.auth_mode.value} requires: {', '.join(missing)}")
        if self.webhook_url is not None and not self.webhook_secret:
            raise ValueError("WEBHOOK_URL requires: WEBHOOK_SECRET")
        return self
