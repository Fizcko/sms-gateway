"""Add the webhook marker, and remove the parts left behind by outbox deletes.

Revision ID: 0004
Revises: 0003
"""

from alembic import op

revision = "0004"
down_revision = "0003"


def upgrade() -> None:
    op.execute("""CREATE TABLE IF NOT EXISTS `webhook_state` (
        `ID` integer NOT NULL DEFAULT 1 PRIMARY KEY,
        `StartMessageID` integer unsigned NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
    # Runs before gammu-smsd starts, so no message is being injected.
    op.execute("DELETE FROM `outbox_multipart` WHERE `ID` NOT IN (SELECT `ID` FROM `outbox`)")
