"""Reassembly of received SMS parts into logical messages.

gammu-smsd stores one `inbox` row per physical part and links the parts through
`MessageID`. The API only exposes logical messages. Rules are described in
docs/business/rules.md.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from sms_gateway.db.models import Inbox
from sms_gateway.schemas.inbox import InboxMessage

# gammu-smsd inserts a part, then sets its MessageID in a second statement.
# Until then the row has this value and belongs to no message.
_MESSAGE_ID_NOT_ASSIGNED = 0


@dataclass(frozen=True)
class InboxFilter:
    before: datetime | None = None
    after: datetime | None = None
    sender: str | None = None


def assemble_message(parts: Sequence[Inbox]) -> InboxMessage:
    """Build a message from the stored parts of one `MessageID`.

    gammu-smsd puts the whole decoded text in the first part when the parts are
    delivered together (the others stay empty), and each part's own text when
    they arrive separately. Joining in sequence order is right in both cases.
    Part-level attributes come from the part with the lowest position.
    """
    ordered = sorted(parts, key=lambda part: (part.SequencePosition, part.ID))
    first = ordered[0]
    part_count = max(part.PartCount for part in ordered)
    received_parts = len({part.SequencePosition for part in ordered})
    return InboxMessage(
        ID=first.MessageID,
        UpdatedInDB=max(part.UpdatedInDB for part in ordered),
        ReceivingDateTime=min(part.ReceivingDateTime for part in ordered),
        InsertIntoDB=min(part.InsertIntoDB for part in ordered),
        Text="".join(part.Text for part in ordered),
        SenderNumber=first.SenderNumber,
        Coding=first.Coding,
        UDH=first.UDH,
        SMSCNumber=first.SMSCNumber,
        Class=first.Class,
        TextDecoded="".join(part.TextDecoded for part in ordered),
        RecipientID=first.RecipientID,
        Processed="true" if all(part.Processed == "true" for part in ordered) else "false",
        Status=first.Status,
        PartCount=part_count,
        ReceivedParts=received_parts,
        Complete=received_parts >= part_count,
    )


def list_messages(
    session: Session, filters: InboxFilter, limit: int, offset: int
) -> tuple[list[InboxMessage], int]:
    """Return one page of messages and the total number of matching messages.

    Pagination and date filters apply to messages, not parts. A message's date
    is the reception date of its earliest part.
    """
    received_at = func.min(Inbox.ReceivingDateTime)
    message_ids = (
        select(Inbox.MessageID)
        .where(Inbox.MessageID != _MESSAGE_ID_NOT_ASSIGNED)
        .group_by(Inbox.MessageID)
    )
    if filters.sender is not None:
        message_ids = message_ids.where(Inbox.SenderNumber == filters.sender)
    if filters.before is not None:
        message_ids = message_ids.having(received_at < filters.before)
    if filters.after is not None:
        message_ids = message_ids.having(received_at > filters.after)

    total = session.scalar(select(func.count()).select_from(message_ids.subquery())) or 0
    page_ids = session.scalars(
        message_ids.order_by(Inbox.MessageID).limit(limit).offset(offset)
    ).all()
    parts = session.scalars(select(Inbox).where(Inbox.MessageID.in_(page_ids))).all()

    parts_by_message: dict[int, list[Inbox]] = {message_id: [] for message_id in page_ids}
    for part in parts:
        parts_by_message[part.MessageID].append(part)
    return [assemble_message(group) for group in parts_by_message.values()], total


def get_message(session: Session, message_id: int) -> InboxMessage | None:
    """A message is only reachable by its `MessageID`, not by a later part's `ID`."""
    if message_id == _MESSAGE_ID_NOT_ASSIGNED:
        return None
    parts = session.scalars(select(Inbox).where(Inbox.MessageID == message_id)).all()
    return assemble_message(parts) if parts else None


def delete_message(session: Session, message_id: int) -> None:
    if message_id != _MESSAGE_ID_NOT_ASSIGNED:
        session.execute(delete(Inbox).where(Inbox.MessageID == message_id))


def delete_all(session: Session) -> None:
    session.execute(delete(Inbox))
