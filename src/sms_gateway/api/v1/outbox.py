from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import delete, select

from sms_gateway.api.dependencies import DatabaseDep, PaginationDep
from sms_gateway.api.errors import ApiError
from sms_gateway.db.models import Outbox, OutboxMultipart
from sms_gateway.schemas.outbox import OutboxItem, OutboxPage
from sms_gateway.schemas.pagination import total_pages
from sms_gateway.services.queries import fetch_page

router = APIRouter(tags=["Outbox"])


@router.get("/v1/outbox", summary="Get all SMS located in the outbox", response_model=OutboxPage)
def list_outbox(
    database: DatabaseDep,
    pagination: PaginationDep,
    before: Annotated[datetime | None, Query(description="Sending before a date")] = None,
    after: Annotated[datetime | None, Query(description="Sending after a date")] = None,
    destination: Annotated[str | None, Query(description="Sent to a number")] = None,
) -> OutboxPage:
    query = select(Outbox)
    if before is not None:
        query = query.where(Outbox.SendingDateTime < before)
    if after is not None:
        query = query.where(Outbox.SendingDateTime > after)
    if destination is not None:
        query = query.where(Outbox.DestinationNumber == destination)
    with database.session() as session:
        rows, total = fetch_page(
            session, query.order_by(Outbox.ID), pagination.per_page, pagination.offset
        )
        results = [OutboxItem.model_validate(row) for row in rows]
    return OutboxPage(
        page=pagination.page,
        total_pages=total_pages(total, pagination.per_page),
        results=results,
    )


@router.delete(
    "/v1/outbox/all",
    summary="Delete all SMS located in the outbox",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_all(database: DatabaseDep) -> None:
    with database.session() as session:
        session.execute(delete(OutboxMultipart))
        session.execute(delete(Outbox))


@router.get("/v1/outbox/{id}", summary="Get a SMS of the outbox", response_model=OutboxItem)
def get_outbox_item(id: int, database: DatabaseDep) -> OutboxItem:
    with database.session() as session:
        row = session.get(Outbox, id)
        if row is None:
            raise ApiError(404, "SMS not found")
        return OutboxItem.model_validate(row)


@router.delete(
    "/v1/outbox/{id}", summary="Delete a SMS of the outbox", status_code=status.HTTP_204_NO_CONTENT
)
def delete_outbox_item(id: int, database: DatabaseDep) -> None:
    with database.session() as session:
        session.execute(delete(OutboxMultipart).where(OutboxMultipart.ID == id))
        session.execute(delete(Outbox).where(Outbox.ID == id))
