"""State of the modem, as published by gammu-smsd in the `phones` table."""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from sms_gateway.db.models import Phone


@dataclass(frozen=True)
class PhoneStatus:
    signal: int
    network: str | None


def read_phone_status(session: Session) -> PhoneStatus | None:
    """Return the state of the phone, or `None` when gammu-smsd is not reporting.

    gammu-smsd pushes `TimeOut` forward at each status refresh, so a past value
    means a stale heartbeat. It is compared to the database clock, the one
    gammu-smsd writes with. A row can remain from a previous modem: only a fresh
    one counts, and the most recent wins.
    """
    query = (
        select(Phone.Signal, Phone.NetName)
        .where(Phone.TimeOut >= func.now())
        .order_by(Phone.TimeOut.desc())
        .limit(1)
    )
    row = session.execute(query).first()
    return PhoneStatus(signal=row.Signal, network=row.NetName) if row else None
