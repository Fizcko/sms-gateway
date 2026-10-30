"""The schema must stay the one of the Gammu in the image, whatever its version.

A failure here after changing GAMMU_VERSION is expected when Gammu changed its schema:
follow "Upgrading Gammu" in docs/architecture.md.
"""

import re
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, inspect, text

from sms_gateway.db.migrate import _REVISION_OF_GAMMU_VERSION
from sms_gateway.db.models import GAMMU_SCHEMA_VERSION, GAMMU_TABLES, Base
from tests.integration.test_migrations import official_schema

CORE_HEADER = Path(__file__).parent.parent / "gammu_upstream" / "core.h"
HELP = "Gammu changed its schema: see 'Upgrading Gammu' in docs/architecture.md"
TABLES = sorted(GAMMU_TABLES)
PROJECT_TABLES = {"alembic_version"} | (set(Base.metadata.tables) - GAMMU_TABLES)


def bundled_schema_version() -> int:
    match = re.search(r"#define SMSD_DB_VERSION \((\d+)\)", CORE_HEADER.read_text())
    assert match is not None, "SMSD_DB_VERSION not found in Gammu's core.h"
    return int(match.group(1))


@pytest.fixture
def reference(engine: Engine) -> Iterator[Engine]:
    """A database created by Gammu's own script, next to the migrated one."""
    name = f"{engine.url.database}_official"
    with engine.begin() as connection:
        connection.execute(text(f"CREATE DATABASE `{name}`"))
    database = create_engine(engine.url.set(database=name))
    official_schema(database)
    yield database
    database.dispose()
    with engine.begin() as connection:
        connection.execute(text(f"DROP DATABASE `{name}`"))


def columns(engine: Engine, table: str) -> dict[str, tuple[str, bool, str | None]]:
    return {
        column["name"]: (str(column["type"]), column["nullable"], column["default"])
        for column in inspect(engine).get_columns(table)
    }


def indexes(engine: Engine, table: str) -> dict[str | None, tuple[object, bool]]:
    inspector = inspect(engine)
    found: dict[str | None, tuple[object, bool]] = {
        index["name"]: (index["column_names"], bool(index["unique"]))
        for index in inspector.get_indexes(table)
    }
    found["PRIMARY"] = (inspector.get_pk_constraint(table)["constrained_columns"], True)
    return found


def test_schema_version_is_the_one_of_the_bundled_gammu() -> None:
    assert GAMMU_SCHEMA_VERSION == bundled_schema_version(), HELP


def test_bundled_schema_version_can_be_adopted() -> None:
    assert bundled_schema_version() in _REVISION_OF_GAMMU_VERSION, HELP


def test_same_tables_as_the_bundled_gammu(engine: Engine, reference: Engine) -> None:
    migrated = set(inspect(engine).get_table_names()) - PROJECT_TABLES
    assert migrated == set(inspect(reference).get_table_names()), HELP


@pytest.mark.parametrize("table", TABLES)
def test_same_columns_as_the_bundled_gammu(engine: Engine, reference: Engine, table: str) -> None:
    assert columns(engine, table) == columns(reference, table), HELP


@pytest.mark.parametrize("table", TABLES)
def test_same_indexes_as_the_bundled_gammu(engine: Engine, reference: Engine, table: str) -> None:
    assert indexes(engine, table) == indexes(reference, table), HELP
