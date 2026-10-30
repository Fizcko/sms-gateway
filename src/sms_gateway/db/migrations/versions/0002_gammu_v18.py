"""Upgrade to the Gammu v18 schema, as documented by Gammu 1.44+.

MariaDB commits DDL immediately and MyISAM has no transactions, so each step is
safe to replay after an interruption. The version is written last: until then
gammu-smsd keeps refusing the database.

Revision ID: 0002
Revises: 0001
"""

from alembic import op
from sqlalchemy import inspect

revision = "0002"
down_revision = "0001"


def _add_column(table: str, name: str, definition: str) -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns(table)}
    if name not in columns:
        op.execute(f"ALTER TABLE `{table}` ADD COLUMN `{name}` {definition}")


def _add_index(table: str, name: str, columns: str) -> None:
    indexes = {index["name"] for index in inspect(op.get_bind()).get_indexes(table)}
    if name not in indexes:
        op.execute(f"CREATE INDEX `{name}` ON `{table}` ({columns})")


def upgrade() -> None:
    _add_column(
        "inbox",
        "InsertIntoDB",
        "timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP AFTER `ReceivingDateTime`",
    )
    _add_column("inbox", "MessageID", "integer unsigned NOT NULL DEFAULT 0 AFTER `ID`")
    _add_column("inbox", "SequencePosition", "integer NOT NULL DEFAULT 1 AFTER `MessageID`")
    _add_column("inbox", "PartCount", "integer NOT NULL DEFAULT 1 AFTER `SequencePosition`")
    # Gammu's upgrade rule: historical parts cannot be linked reliably, so each
    # existing row becomes its own message. Reassigning UpdatedInDB stops
    # ON UPDATE from rewriting the history.
    op.execute(
        "UPDATE `inbox` SET `MessageID` = `ID`, `UpdatedInDB` = `UpdatedInDB` WHERE `MessageID` = 0"
    )
    _add_index("inbox", "inbox_message", "`MessageID`, `SequencePosition`")
    _add_index("inbox", "inbox_insert", "`InsertIntoDB`")
    # 127 = every day of the week: queued messages stay eligible.
    _add_column("outbox", "SendDays", "integer NOT NULL DEFAULT 127 AFTER `SendAfter`")
    op.execute("UPDATE `gammu` SET `Version` = 18")
