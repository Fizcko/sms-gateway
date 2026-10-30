"""Query helpers shared by the listing routes."""

from collections.abc import Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


def fetch_page[RowT](
    session: Session, query: Select[RowT], limit: int, offset: int
) -> tuple[Sequence[RowT], int]:
    """Return one page of `query`, and the total number of rows it matches."""
    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    total = session.scalar(count_query) or 0
    return session.scalars(query.limit(limit).offset(offset)).all(), total
