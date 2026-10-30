from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query, status

from sms_gateway.api.dependencies import DatabaseDep, PaginationDep
from sms_gateway.api.errors import ApiError
from sms_gateway.schemas.inbox import InboxMessage, InboxPage
from sms_gateway.schemas.pagination import total_pages
from sms_gateway.services import inbox as service

router = APIRouter(tags=["Inbox"])


@router.get("/v1/inbox", summary="Get the received messages", response_model=InboxPage)
def list_messages(
    database: DatabaseDep,
    pagination: PaginationDep,
    before: Annotated[datetime | None, Query(description="Received before a date")] = None,
    after: Annotated[datetime | None, Query(description="Received after a date")] = None,
    sender: Annotated[str | None, Query(description="Received from a number")] = None,
) -> InboxPage:
    with database.session() as session:
        messages, total = service.list_messages(
            session,
            service.InboxFilter(before=before, after=after, sender=sender),
            limit=pagination.per_page,
            offset=pagination.offset,
        )
    return InboxPage(
        page=pagination.page,
        total_pages=total_pages(total, pagination.per_page),
        results=messages,
    )


@router.delete(
    "/v1/inbox/all", summary="Delete all received messages", status_code=status.HTTP_204_NO_CONTENT
)
def delete_all(database: DatabaseDep) -> None:
    with database.session() as session:
        service.delete_all(session)


@router.get("/v1/inbox/{id}", summary="Get a received message", response_model=InboxMessage)
def get_message(id: int, database: DatabaseDep) -> InboxMessage:
    with database.session() as session:
        message = service.get_message(session, id)
    if message is None:
        raise ApiError(404, "SMS not found")
    return message


@router.delete(
    "/v1/inbox/{id}",
    summary="Delete a received message and all its parts",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_message(id: int, database: DatabaseDep) -> None:
    with database.session() as session:
        service.delete_message(session, id)
