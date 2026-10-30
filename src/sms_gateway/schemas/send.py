from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

# 20 is the size of the destination columns of the Gammu tables.
Recipient = Annotated[str, StringConstraints(pattern=r"^\+?[0-9]{3,20}$")]


class SendRequest(BaseModel):
    recipients: list[Recipient] = Field(examples=[["+12025550123", "+12025550187"]])
    message: str = Field(max_length=480, examples=["Hello, this my first sms"])


class SentSms(BaseModel):
    DestinationNumber: str
    smsID: str


class SendResponse(BaseModel):
    results: list[SentSms]
