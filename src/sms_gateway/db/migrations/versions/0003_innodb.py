"""Move every Gammu table to InnoDB (transactions, crash recovery).

Revision ID: 0003
Revises: 0002
"""

from alembic import op
from sqlalchemy import text

revision = "0003"
down_revision = "0002"

_TABLES = ("gammu", "inbox", "outbox", "outbox_multipart", "phones", "sentitems")


def upgrade() -> None:
    engines = op.get_bind().execute(
        text(
            "SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE()"
        )
    )
    engine_of = {name: engine for name, engine in engines}
    for table in _TABLES:
        if engine_of[table] != "InnoDB":
            op.execute(f"ALTER TABLE `{table}` ENGINE=InnoDB")
