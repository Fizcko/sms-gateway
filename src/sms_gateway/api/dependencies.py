"""Objects shared by the routes, created once per application by `create_app`."""

from typing import Annotated

from fastapi import Depends, Query, Request
from pydantic import BaseModel

from sms_gateway.db.session import Database
from sms_gateway.services.sms_sender import SmsSender
from sms_gateway.settings import Settings


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_database(request: Request) -> Database:
    database: Database = request.app.state.database
    return database


def get_sms_sender(request: Request) -> SmsSender:
    sender: SmsSender = request.app.state.sms_sender
    return sender


class Pagination(BaseModel):
    page: int = 1
    per_page: int = 50

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page


def get_pagination(
    page: Annotated[int, Query(ge=1, description="Page to display")] = 1,
    per_page: Annotated[int, Query(ge=1, description="Number of results by page")] = 50,
) -> Pagination:
    return Pagination(page=page, per_page=per_page)


SettingsDep = Annotated[Settings, Depends(get_settings)]
DatabaseDep = Annotated[Database, Depends(get_database)]
SmsSenderDep = Annotated[SmsSender, Depends(get_sms_sender)]
PaginationDep = Annotated[Pagination, Depends(get_pagination)]
