"""Thread running the webhook deliveries and the purge next to the API."""

import logging
import time
from threading import Event, Thread

from sqlalchemy.exc import SQLAlchemyError

from sms_gateway.db.session import Database
from sms_gateway.services.purge import purge_old_messages
from sms_gateway.services.webhook import DeliveryFailedError, WebhookWorker, retry_delay

logger = logging.getLogger(__name__)

_TICK_SECONDS = 1
_DELIVERY_INTERVAL_SECONDS = 2
_PURGE_INTERVAL_SECONDS = 24 * 3600
_PURGE_RETRY_SECONDS = 300


class BackgroundWorker:
    """Does nothing, and starts no thread, when neither feature is configured."""

    def __init__(
        self, database: Database, webhook: WebhookWorker | None, retention_days: int | None
    ) -> None:
        self._database = database
        self._webhook = webhook
        self._retention_days = retention_days
        self._stop = Event()
        self._thread: Thread | None = None
        self._failures = 0

    @property
    def enabled(self) -> bool:
        return self._webhook is not None or self._retention_days is not None

    def start(self) -> None:
        if self.enabled:
            self._thread = Thread(target=self._run, name="sms-gateway-background", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=30)

    def _run(self) -> None:
        next_delivery = next_purge = time.monotonic()
        while not self._stop.wait(_TICK_SECONDS):
            now = time.monotonic()
            if self._webhook is not None and now >= next_delivery:
                next_delivery = now + self._deliver(self._webhook)
            if self._retention_days is not None and now >= next_purge:
                next_purge = now + self._purge(self._retention_days)

    def _deliver(self, webhook: WebhookWorker) -> int:
        """Return the seconds to wait before the next delivery cycle."""
        try:
            webhook.deliver_pending()
        except (DeliveryFailedError, SQLAlchemyError) as error:
            self._failures += 1
            delay = retry_delay(self._failures)
            logger.warning("Webhook delivery failed, retry in %s s: %s", delay, error)
            return delay
        self._failures = 0
        return _DELIVERY_INTERVAL_SECONDS

    def _purge(self, days: int) -> int:
        """Return the seconds to wait before the next purge."""
        try:
            start = self._webhook.start_message_id() if self._webhook is not None else None
            with self._database.session() as session:
                purge_old_messages(session, days, start)
        except SQLAlchemyError:
            logger.exception("Purge failed")
            return _PURGE_RETRY_SECONDS
        return _PURGE_INTERVAL_SECONDS
