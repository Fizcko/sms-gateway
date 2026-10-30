"""Bring the database to the latest schema, before gammu-smsd and the API start.

Run with `python -m sms_gateway.db.migrate`.
"""

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from pymysql.constants import ER
from sqlalchemy import Connection, Engine, create_engine, inspect, text
from sqlalchemy.exc import OperationalError

from sms_gateway.settings import Settings

logger = logging.getLogger(__name__)

# The revision that produced each Gammu schema version, for databases created
# before Alembic was introduced.
_REVISION_OF_GAMMU_VERSION = {17: "0001", 18: "0002"}


class UnsupportedSchemaError(RuntimeError):
    """The database holds a Gammu schema that no migration starts from."""


def ensure_database(settings: Settings) -> None:
    """Create the database if it does not exist yet."""
    probe = create_engine(settings.database_url)
    try:
        with probe.connect():
            return
    except OperationalError as error:
        if error.orig is None or error.orig.args[0] != ER.BAD_DB_ERROR:
            raise
    finally:
        probe.dispose()

    server = create_engine(settings.server_url)
    try:
        quoted = server.dialect.identifier_preparer.quote(settings.mysql_database)
        with server.begin() as connection:
            connection.execute(text(f"CREATE DATABASE {quoted} CHARACTER SET utf8mb4"))
    finally:
        server.dispose()


def _revision_to_stamp(connection: Connection) -> str | None:
    """Return the revision of a database not tracked by Alembic yet, if any.

    A database without any `gammu` table is new (or stopped during the baseline)
    and goes through every migration.
    """
    tables = inspect(connection).get_table_names()
    if "alembic_version" in tables or "gammu" not in tables:
        return None
    version = connection.execute(text("SELECT MAX(Version) FROM gammu")).scalar()
    revision = _REVISION_OF_GAMMU_VERSION.get(version) if isinstance(version, int) else None
    if revision is None:
        raise UnsupportedSchemaError(
            f"Gammu schema version {version} cannot be migrated: "
            f"supported versions are {sorted(_REVISION_OF_GAMMU_VERSION)}"
        )
    return revision


def upgrade(engine: Engine, target: str = "head") -> None:
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        revision = _revision_to_stamp(connection)
        if revision is not None:
            logger.info("Existing Gammu database detected, at revision %s", revision)
            command.stamp(config, revision)
        command.upgrade(config, target)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = Settings()
    ensure_database(settings)
    engine = create_engine(settings.database_url)
    try:
        upgrade(engine)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
