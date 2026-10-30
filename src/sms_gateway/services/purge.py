"""Removal of old SMS, when `RETENTION_DAYS` is set."""

from sqlalchemy import case, delete, func, or_, select, text
from sqlalchemy.orm import Session

from sms_gateway.db.models import Inbox, SentItem


def purge_old_messages(session: Session, days: int, webhook_start_id: int | None = None) -> None:
    """Delete inbox messages and sent items older than `days`, on the database clock.

    A message goes as a whole, once its latest part is old enough. One still
    waiting for the webhook stays. The outbox is never purged: it is a work queue.
    """
    cutoff = text(f"NOW() - INTERVAL {int(days)} DAY")
    old_messages = (
        select(Inbox.MessageID)
        .where(Inbox.MessageID != 0)
        .group_by(Inbox.MessageID)
        .having(func.max(Inbox.ReceivingDateTime) < cutoff)
    )
    if webhook_start_id is not None:
        unprocessed = func.sum(case((Inbox.Processed == "false", 1), else_=0))
        old_messages = old_messages.having(
            or_(Inbox.MessageID <= webhook_start_id, unprocessed == 0)
        )
    message_ids = session.scalars(old_messages).all()
    session.execute(delete(Inbox).where(Inbox.MessageID.in_(message_ids)))
    session.execute(delete(SentItem).where(SentItem.SendingDateTime < cutoff))
