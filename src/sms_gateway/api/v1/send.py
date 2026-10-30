from fastapi import APIRouter

from sms_gateway.api.dependencies import SmsSenderDep
from sms_gateway.schemas.send import SendRequest, SendResponse, SentSms

router = APIRouter(tags=["Send"])


@router.post("/v1/send", summary="Send a SMS", response_model=SendResponse)
def send(payload: SendRequest, sender: SmsSenderDep) -> SendResponse:
    return SendResponse(
        results=[
            SentSms(DestinationNumber=number, smsID=sender.send(number, payload.message))
            for number in payload.recipients
        ]
    )
