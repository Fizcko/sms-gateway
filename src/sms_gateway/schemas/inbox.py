from datetime import datetime

from pydantic import BaseModel


class InboxMessage(BaseModel):
    """A logical message, reassembled from its physical parts."""

    ID: int
    UpdatedInDB: datetime
    ReceivingDateTime: datetime
    InsertIntoDB: datetime
    Text: str
    SenderNumber: str
    Coding: str
    UDH: str
    SMSCNumber: str
    Class: int
    TextDecoded: str
    RecipientID: str
    Processed: str
    Status: int
    PartCount: int
    ReceivedParts: int
    Complete: bool


class InboxPage(BaseModel):
    page: int
    total_pages: int
    results: list[InboxMessage]
