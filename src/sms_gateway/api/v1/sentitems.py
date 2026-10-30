from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from sms_gateway.api.dependencies import DatabaseDep, PaginationDep
from sms_gateway.api.errors import ApiError
from sms_gateway.db.models import SentItem
from sms_gateway.schemas.pagination import total_pages
from sms_gateway.schemas.sentitems import SentItemPage, SentItemSchema
from sms_gateway.services.queries import fetch_page

router = APIRouter(tags=["Sent Items"])


def _first_part(session: Session, id: int) -> SentItem | None:
    query = select(SentItem).where(SentItem.ID == id).order_by(SentItem.SequencePosition).limit(1)
    return session.scalars(query).first()


@router.get("/v1/sentitems", summary="Get all sent SMS parts", response_model=SentItemPage)
def list_sent_items(
    database: DatabaseDep,
    pagination: PaginationDep,
    before: Annotated[datetime | None, Query(description="Sent before a date")] = None,
    after: Annotated[datetime | None, Query(description="Sent after a date")] = None,
    destination: Annotated[str | None, Query(description="Sent to a number")] = None,
) -> SentItemPage:
    query = select(SentItem)
    if before is not None:
        query = query.where(SentItem.SendingDateTime < before)
    if after is not None:
        query = query.where(SentItem.SendingDateTime > after)
    if destination is not None:
        query = query.where(SentItem.DestinationNumber == destination)
    query = query.order_by(SentItem.ID, SentItem.SequencePosition)
    with database.session() as session:
        rows, total = fetch_page(session, query, pagination.per_page, pagination.offset)
        results = [SentItemSchema.model_validate(row) for row in rows]
    return SentItemPage(
        page=pagination.page,
        total_pages=total_pages(total, pagination.per_page),
        results=results,
    )


@router.delete(
    "/v1/sentitems/all", summary="Delete all sent SMS", status_code=status.HTTP_204_NO_CONTENT
)
def delete_all(database: DatabaseDep) -> None:
    with database.session() as session:
        session.execute(delete(SentItem))


@router.get(
    "/v1/sentitems/{id}", summary="Get the first part of a sent SMS", response_model=SentItemSchema
)
def get_sent_item(id: int, database: DatabaseDep) -> SentItemSchema:
    with database.session() as session:
        row = _first_part(session, id)
        if row is None:
            raise ApiError(404, "SMS not found")
        return SentItemSchema.model_validate(row)


@router.delete(
    "/v1/sentitems/{id}",
    summary="Delete a sent SMS and all its parts",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_sent_item(id: int, database: DatabaseDep) -> None:
    with database.session() as session:
        session.execute(delete(SentItem).where(SentItem.ID == id))
