import re
from pathlib import Path

import pytest
from sqlalchemy import Engine, inspect, text

from sms_gateway.db.migrate import UnsupportedSchemaError, upgrade
from sms_gateway.db.models import GAMMU_SCHEMA_VERSION, Base
from sms_gateway.settings import Settings

UPSTREAM_SCRIPT = Path(__file__).parent.parent / "gammu_upstream" / "mysql.sql"
Database = tuple[Settings, Engine]


def run_script(engine: Engine, script: str) -> None:
    without_comments = re.sub(r"^--.*$", "", script, flags=re.MULTILINE)
    with engine.begin() as connection:
        for statement in without_comments.split(";"):
            if statement.strip():
                connection.execute(text(statement))


def official_schema(engine: Engine) -> None:
    """The schema created by the script of the Gammu in the image."""
    run_script(engine, UPSTREAM_SCRIPT.read_text())


def legacy_v17(engine: Engine) -> None:
    """The v17 schema the previous releases created, with one row of each kind."""
    upgrade(engine, target="0001")
    run_script(
        engine,
        """
        DROP TABLE alembic_version;
        INSERT INTO inbox (UpdatedInDB, Text, UDH, TextDecoded, RecipientID)
            VALUES ('2020-01-01 00:00:00', '', '', 'old', '');
        INSERT INTO outbox (TextDecoded, CreatorID) VALUES ('queued', 'test');
        """,
    )


def gammu_version(engine: Engine) -> int | None:
    with engine.connect() as connection:
        return connection.execute(text("SELECT Version FROM gammu")).scalar()


def value(engine: Engine, query: str) -> object:
    with engine.connect() as connection:
        return connection.execute(text(query)).scalar()


def test_new_database_reaches_the_schema_version_of_gammu(empty_database: Database) -> None:
    upgrade(empty_database[1])
    assert gammu_version(empty_database[1]) == GAMMU_SCHEMA_VERSION


def test_new_database_has_exactly_one_version_row(empty_database: Database) -> None:
    upgrade(empty_database[1])
    assert value(empty_database[1], "SELECT COUNT(*) FROM gammu") == 1


def test_every_table_ends_on_innodb(empty_database: Database) -> None:
    upgrade(empty_database[1])
    others = value(
        empty_database[1],
        "SELECT COUNT(*) FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = DATABASE() AND ENGINE <> 'InnoDB'",
    )
    assert others == 0


@pytest.mark.parametrize("table", sorted(Base.metadata.tables))
def test_orm_columns_match_the_migrated_table(empty_database: Database, table: str) -> None:
    upgrade(empty_database[1])
    in_database = {column["name"] for column in inspect(empty_database[1]).get_columns(table)}
    assert in_database == {column.name for column in Base.metadata.tables[table].columns}


def test_legacy_database_reaches_the_schema_version_of_gammu(empty_database: Database) -> None:
    legacy_v17(empty_database[1])
    upgrade(empty_database[1])
    assert gammu_version(empty_database[1]) == GAMMU_SCHEMA_VERSION


def test_legacy_inbox_rows_become_single_part_messages(empty_database: Database) -> None:
    legacy_v17(empty_database[1])
    upgrade(empty_database[1])
    assert (
        value(
            empty_database[1],
            "SELECT MessageID = ID AND SequencePosition = 1 AND PartCount = 1 FROM inbox",
        )
        == 1
    )


def test_legacy_inbox_rows_keep_their_update_date(empty_database: Database) -> None:
    legacy_v17(empty_database[1])
    upgrade(empty_database[1])
    assert str(value(empty_database[1], "SELECT UpdatedInDB FROM inbox")) == "2020-01-01 00:00:00"


def test_legacy_queued_messages_stay_eligible_every_day(empty_database: Database) -> None:
    legacy_v17(empty_database[1])
    upgrade(empty_database[1])
    assert value(empty_database[1], "SELECT SendDays FROM outbox") == 127


def test_official_v18_database_is_adopted_and_moved_to_innodb(empty_database: Database) -> None:
    official_schema(empty_database[1])
    upgrade(empty_database[1])
    assert (
        value(
            empty_database[1],
            "SELECT ENGINE FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'inbox'",
        )
        == "InnoDB"
    )


def test_running_migrations_twice_changes_nothing(migrated_database: Database) -> None:
    upgrade(migrated_database[1])
    assert gammu_version(migrated_database[1]) == GAMMU_SCHEMA_VERSION


def test_interrupted_v18_migration_resumes(empty_database: Database) -> None:
    legacy_v17(empty_database[1])
    run_script(
        empty_database[1], "ALTER TABLE inbox ADD COLUMN PartCount integer NOT NULL DEFAULT 1"
    )
    upgrade(empty_database[1])
    assert gammu_version(empty_database[1]) == GAMMU_SCHEMA_VERSION


def test_older_gammu_schema_is_refused(empty_database: Database) -> None:
    official_schema(empty_database[1])
    run_script(empty_database[1], "UPDATE gammu SET Version = 16")
    with pytest.raises(UnsupportedSchemaError, match="16"):
        upgrade(empty_database[1])


def test_empty_version_table_is_refused(empty_database: Database) -> None:
    official_schema(empty_database[1])
    run_script(empty_database[1], "DELETE FROM gammu")
    with pytest.raises(UnsupportedSchemaError):
        upgrade(empty_database[1])


def test_migration_removes_orphan_outbox_parts(empty_database: Database) -> None:
    upgrade(empty_database[1], target="0003")
    run_script(
        empty_database[1],
        """
        INSERT INTO outbox (ID, TextDecoded, CreatorID) VALUES (1, 'x', 't');
        INSERT INTO outbox_multipart (ID, SequencePosition) VALUES (1, 2), (9, 2);
        """,
    )
    upgrade(empty_database[1])
    assert value(empty_database[1], "SELECT GROUP_CONCAT(ID) FROM outbox_multipart") == "1"
