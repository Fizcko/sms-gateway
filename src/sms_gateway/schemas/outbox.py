from datetime import datetime, time

from pydantic import BaseModel, ConfigDict


class OutboxItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ID: int
    UpdatedInDB: datetime
    InsertIntoDB: datetime
    SendingDateTime: datetime
    SendBefore: time
    SendAfter: time
    SendDays: int
    Text: str | None
    DestinationNumber: str
    Coding: str
    UDH: str | None
    Class: int | None
    TextDecoded: str
    MultiPart: str | None
    RelativeValidity: int | None
    SenderID: str | None
    SendingTimeOut: datetime | None
    DeliveryReport: str | None
    CreatorID: str
    Retries: int | None
    Priority: int | None
    Status: str
    StatusCode: int


class OutboxPage(BaseModel):
    page: int
    total_pages: int
    results: list[OutboxItem]
