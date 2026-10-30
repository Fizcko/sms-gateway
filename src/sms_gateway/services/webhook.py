"""Push received messages to the application configured in `WEBHOOK_URL`.

The database is the queue: a message is pending while one of its parts has
`Processed='false'`, so nothing is lost when the application or this process is
down. Rules are described in docs/business/rules.md.
"""

import hashlib
import hmac
import logging

import httpx
from sqlalchemy import func, literal_column, select, update

from sms_gateway.db.models import Inbox, WebhookState
from sms_gateway.db.session import Database
from sms_gateway.schemas.inbox import InboxMessage
from sms_gateway.services.inbox import assemble_message
from sms_gateway.settings import Settings

logger = logging.getLogger(__name__)

_STATE_ID = 1
_BATCH_SIZE = 100
_RETRY_BASE_SECONDS = 5
_RETRY_MAX_SECONDS = 300


class DeliveryFailedError(Exception):
    """The application did not accept a message: retry it later."""


def retry_delay(failures: int) -> int:
    """Seconds to wait after a number of consecutive failed cycles (at least 1)."""
    delay: int = _RETRY_BASE_SECONDS * 2 ** (failures - 1)
    return min(delay, _RETRY_MAX_SECONDS)


def sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class WebhookWorker:
    def __init__(self, settings: Settings, database: Database, client: httpx.Client) -> None:
        if settings.webhook_url is None or settings.webhook_secret is None:
            raise ValueError("The webhook needs WEBHOOK_URL and WEBHOOK_SECRET")
        self._url = str(settings.webhook_url)
        self._secret = settings.webhook_secret
        self._timeout = settings.webhook_timeout
        self._incomplete_delay = settings.webhook_incomplete_delay
        self._database = database
        self._client = client
        self._start_id: int | None = None

    def start_message_id(self) -> int:
        """Messages up to this ID are history, and are never sent.

        The marker is written on first activation only, so that messages received
        while the webhook is later disabled are still sent when it comes back.
        """
        if self._start_id is None:
            with self._database.session() as session:
                state = session.get(WebhookState, _STATE_ID)
                if state is None:
                    highest = session.scalar(select(func.max(Inbox.MessageID))) or 0
                    state = WebhookState(ID=_STATE_ID, StartMessageID=highest)
                    session.add(state)
                self._start_id = state.StartMessageID
        return self._start_id

    def deliver_pending(self) -> None:
        """Handle every pending message, oldest first.

        Raises `DeliveryFailedError` at the first refusal, which keeps the order:
        later messages wait for the retry. A message still missing parts does not
        block the others.
        """
        start = self.start_message_id()
        after = start
        while True:
            with self._database.session() as session:
                message_ids = session.scalars(
                    select(Inbox.MessageID)
                    .where(Inbox.MessageID > after, Inbox.Processed == "false")
                    .distinct()
                    .order_by(Inbox.MessageID)
                    .limit(_BATCH_SIZE)
                ).all()
            if not message_ids:
                return
            for message_id in message_ids:
                self._handle(message_id)
            after = message_ids[-1]

    def _handle(self, message_id: int) -> None:
        with self._database.session() as session:
            parts = session.scalars(select(Inbox).where(Inbox.MessageID == message_id)).all()
            message = assemble_message(parts)
            part_ids = [part.ID for part in parts]
            # On the database clock, the one that wrote InsertIntoDB.
            age = session.scalar(
                select(
                    func.timestampdiff(literal_column("SECOND"), message.InsertIntoDB, func.now())
                )
            )

        if message.Complete:
            self._post(message)
        elif (age or 0) >= self._incomplete_delay:
            logger.warning(
                "Message %s still has %s of %s parts: not sent to the webhook",
                message_id,
                message.ReceivedParts,
                message.PartCount,
            )
        else:
            return
        with self._database.session() as session:
            session.execute(update(Inbox).where(Inbox.ID.in_(part_ids)).values(Processed="true"))

    def _post(self, message: InboxMessage) -> None:
        body = message.model_dump_json().encode()
        try:
            response = self._client.post(
                self._url,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Gateway-Signature": sign(self._secret, body),
                },
                timeout=self._timeout,
                follow_redirects=False,
            )
        except httpx.HTTPError as error:
            raise DeliveryFailedError(f"message {message.ID}: {type(error).__name__}") from error
        if not response.is_success:
            raise DeliveryFailedError(f"message {message.ID}: HTTP {response.status_code}")
