import os
import uuid
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text

from sms_gateway.app import create_app
from sms_gateway.db.migrate import ensure_database, upgrade
from sms_gateway.settings import Settings
from tests.helpers import FakeSender, make_settings

HOST = os.environ.get("TEST_MYSQL_HOST")
PASSWORD = os.environ.get("TEST_MYSQL_PASSWORD", "test")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    if HOST is None:
        skip = pytest.mark.skip(reason="TEST_MYSQL_HOST is not set")
        for item in items:
            if "integration" in str(item.path):
                item.add_marker(skip)


def settings_for(database: str) -> Settings:
    return make_settings(
        mysql_host=HOST, mysql_user="root", mysql_password=PASSWORD, mysql_database=database
    )


@pytest.fixture
def empty_database() -> Iterator[tuple[Settings, Engine]]:
    """A new database, dropped after the test."""
    settings = settings_for(f"t_{uuid.uuid4().hex[:12]}")
    ensure_database(settings)
    engine = create_engine(settings.database_url)
    yield settings, engine
    with engine.begin() as connection:
        connection.execute(text(f"DROP DATABASE `{settings.mysql_database}`"))
    engine.dispose()


@pytest.fixture
def migrated_database(empty_database: tuple[Settings, Engine]) -> tuple[Settings, Engine]:
    upgrade(empty_database[1])
    return empty_database


@pytest.fixture
def client(migrated_database: tuple[Settings, Engine]) -> TestClient:
    return TestClient(create_app(migrated_database[0], FakeSender()))


@pytest.fixture
def engine(migrated_database: tuple[Settings, Engine]) -> Engine:
    return migrated_database[1]


InsertInbox = Callable[..., None]


@pytest.fixture
def insert_inbox(engine: Engine) -> InsertInbox:
    def insert(**columns: object) -> None:
        values: dict[str, object] = {
            "Text": "",
            "UDH": "",
            "TextDecoded": "",
            "RecipientID": "",
            "SenderNumber": "+12025550100",
        }
        values.update(columns)
        names = ", ".join(f"`{name}`" for name in values)
        binds = ", ".join(f":{name}" for name in values)
        with engine.begin() as connection:
            connection.execute(text(f"INSERT INTO inbox ({names}) VALUES ({binds})"), values)

    return insert
