"""Alembic environment: always runs on the connection given by `db.migrate`."""

from alembic import context

from sms_gateway.db.models import Base

context.configure(
    connection=context.config.attributes["connection"],
    target_metadata=Base.metadata,
)
with context.begin_transaction():
    context.run_migrations()
