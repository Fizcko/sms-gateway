from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SentItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ID: int
    UpdatedInDB: datetime
    InsertIntoDB: datetime
    SendingDateTime: datetime
    DeliveryDateTime: datetime | None
    Text: str
    DestinationNumber: str
    Coding: str
    UDH: str
    SMSCNumber: str
    Class: int
    TextDecoded: str
    SenderID: str
    SequencePosition: int
    Status: str
    StatusError: int
    TPMR: int
    RelativeValidity: int
    CreatorID: str
    StatusCode: int


class SentItemPage(BaseModel):
    page: int
    total_pages: int
    results: list[SentItemSchema]
