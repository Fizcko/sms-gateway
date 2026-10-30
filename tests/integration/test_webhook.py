import hashlib
import hmac
import json
from collections.abc import Callable
from datetime import datetime, timedelta

import httpx
import pytest
from sqlalchemy import Engine, text

from sms_gateway.db.session import Database
from sms_gateway.services.purge import purge_old_messages
from sms_gateway.services.webhook import DeliveryFailedError, WebhookWorker, retry_delay
from sms_gateway.settings import Settings
from tests.integration.conftest import InsertInbox

SECRET = "webhook-secret"
Database_ = tuple[Settings, Engine]


class App:
    """Plays the application receiving the webhook."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.status = 200

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(self.status)

    @property
    def ids(self) -> list[int]:
        return [json.loads(request.content)["ID"] for request in self.requests]


@pytest.fixture
def app() -> App:
    return App()


MakeWorker = Callable[..., WebhookWorker]


@pytest.fixture
def make_worker(migrated_database: Database_, app: App) -> MakeWorker:
    def make(delay: int = 600) -> WebhookWorker:
        settings = migrated_database[0].model_copy(
            update={
                "webhook_url": "https://app.example/sms",
                "webhook_secret": SECRET,
                "webhook_incomplete_delay": delay,
            }
        )
        return WebhookWorker(
            settings, Database(settings), httpx.Client(transport=httpx.MockTransport(app))
        )

    return make


@pytest.fixture
def worker(make_worker: MakeWorker) -> WebhookWorker:
    """Activated on the empty database, so every inserted message is new."""
    worker = make_worker()
    worker.start_message_id()
    return worker


def processed_flags(engine: Engine) -> list[str]:
    with engine.connect() as connection:
        query = text("SELECT Processed FROM inbox ORDER BY ID")
        return list(connection.execute(query).scalars())


def add_parts(insert: InsertInbox, message_id: int, positions: tuple[int, ...], count: int) -> None:
    for position in positions:
        insert(
            ID=message_id + position - 1,
            MessageID=message_id,
            SequencePosition=position,
            PartCount=count,
            TextDecoded=f"p{position}",
        )


def test_single_message_is_posted(
    worker: WebhookWorker, app: App, insert_inbox: InsertInbox
) -> None:
    add_parts(insert_inbox, 1, (1,), 1)
    worker.deliver_pending()
    assert app.ids == [1]


def test_payload_has_the_message_fields(
    worker: WebhookWorker, app: App, insert_inbox: InsertInbox
) -> None:
    add_parts(insert_inbox, 1, (1,), 1)
    worker.deliver_pending()
    body = json.loads(app.requests[0].content)
    assert (body["SenderNumber"], body["TextDecoded"], body["Complete"]) == (
        "+12025550100",
        "p1",
        True,
    )


def test_signature_is_the_hmac_of_the_raw_body(
    worker: WebhookWorker, app: App, insert_inbox: InsertInbox
) -> None:
    add_parts(insert_inbox, 1, (1,), 1)
    worker.deliver_pending()
    request = app.requests[0]
    digest = hmac.new(SECRET.encode(), request.content, hashlib.sha256).hexdigest()
    assert request.headers["X-Gateway-Signature"] == f"sha256={digest}"


def test_accepted_message_is_marked_processed(
    worker: WebhookWorker, engine: Engine, insert_inbox: InsertInbox
) -> None:
    add_parts(insert_inbox, 1, (1,), 1)
    worker.deliver_pending()
    assert processed_flags(engine) == ["true"]


def test_accepted_message_is_not_sent_twice(
    worker: WebhookWorker, app: App, insert_inbox: InsertInbox
) -> None:
    add_parts(insert_inbox, 1, (1,), 1)
    worker.deliver_pending()
    worker.deliver_pending()
    assert app.ids == [1]


def test_complete_multipart_is_one_post_with_the_whole_text(
    worker: WebhookWorker, app: App, insert_inbox: InsertInbox
) -> None:
    add_parts(insert_inbox, 1, (1, 2, 3), 3)
    worker.deliver_pending()
    assert [json.loads(r.content)["TextDecoded"] for r in app.requests] == ["p1p2p3"]


def test_incomplete_multipart_is_not_sent(
    worker: WebhookWorker, app: App, insert_inbox: InsertInbox
) -> None:
    add_parts(insert_inbox, 1, (1, 2), 3)
    worker.deliver_pending()
    assert app.ids == []


def test_recent_incomplete_multipart_stays_pending(
    worker: WebhookWorker, engine: Engine, insert_inbox: InsertInbox
) -> None:
    add_parts(insert_inbox, 1, (1,), 3)
    worker.deliver_pending()
    assert processed_flags(engine) == ["false"]


def test_incomplete_multipart_does_not_block_the_next_message(
    worker: WebhookWorker, app: App, insert_inbox: InsertInbox
) -> None:
    add_parts(insert_inbox, 1, (1,), 3)
    add_parts(insert_inbox, 5, (1,), 1)
    worker.deliver_pending()
    assert app.ids == [5]


def test_expired_incomplete_multipart_is_marked_processed_without_post(
    make_worker: MakeWorker, app: App, engine: Engine, insert_inbox: InsertInbox
) -> None:
    worker = make_worker(delay=0)
    worker.start_message_id()
    add_parts(insert_inbox, 1, (1,), 3)
    worker.deliver_pending()
    assert (app.ids, processed_flags(engine)) == ([], ["true"])


def test_expired_incomplete_multipart_is_logged(
    make_worker: MakeWorker, insert_inbox: InsertInbox, caplog: pytest.LogCaptureFixture
) -> None:
    worker = make_worker(delay=0)
    worker.start_message_id()
    add_parts(insert_inbox, 1, (1,), 3)
    worker.deliver_pending()
    assert "still has 1 of 3 parts" in caplog.text


def test_late_part_completing_an_expired_message_sends_it(
    make_worker: MakeWorker, app: App, insert_inbox: InsertInbox
) -> None:
    worker = make_worker(delay=0)
    worker.start_message_id()
    add_parts(insert_inbox, 1, (1,), 2)
    worker.deliver_pending()
    add_parts(insert_inbox, 1, (2,), 2)
    worker.deliver_pending()
    assert [json.loads(r.content)["TextDecoded"] for r in app.requests] == ["p1p2"]


def test_refused_message_stays_pending(
    worker: WebhookWorker, app: App, engine: Engine, insert_inbox: InsertInbox
) -> None:
    app.status = 500
    add_parts(insert_inbox, 1, (1,), 1)
    with pytest.raises(DeliveryFailedError):
        worker.deliver_pending()
    assert processed_flags(engine) == ["false"]


def test_refused_message_blocks_the_following_ones(
    worker: WebhookWorker, app: App, insert_inbox: InsertInbox
) -> None:
    app.status = 500
    add_parts(insert_inbox, 1, (1,), 1)
    add_parts(insert_inbox, 2, (1,), 1)
    with pytest.raises(DeliveryFailedError):
        worker.deliver_pending()
    assert app.ids == [1]


def test_messages_are_delivered_in_order_once_the_app_is_back(
    worker: WebhookWorker, app: App, insert_inbox: InsertInbox
) -> None:
    app.status = 503
    add_parts(insert_inbox, 1, (1,), 1)
    add_parts(insert_inbox, 2, (1,), 1)
    with pytest.raises(DeliveryFailedError):
        worker.deliver_pending()
    app.requests.clear()
    app.status = 200
    worker.deliver_pending()
    assert app.ids == [1, 2]


def test_network_error_keeps_the_message_pending(
    migrated_database: Database_, engine: Engine, insert_inbox: InsertInbox
) -> None:
    def unreachable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    settings = migrated_database[0].model_copy(
        update={"webhook_url": "https://app.example/sms", "webhook_secret": SECRET}
    )
    worker = WebhookWorker(
        settings, Database(settings), httpx.Client(transport=httpx.MockTransport(unreachable))
    )
    worker.start_message_id()
    add_parts(insert_inbox, 1, (1,), 1)
    with pytest.raises(DeliveryFailedError):
        worker.deliver_pending()
    assert processed_flags(engine) == ["false"]


def test_redirect_counts_as_a_refusal(
    worker: WebhookWorker, app: App, insert_inbox: InsertInbox
) -> None:
    app.status = 302
    add_parts(insert_inbox, 1, (1,), 1)
    with pytest.raises(DeliveryFailedError):
        worker.deliver_pending()


def test_history_is_not_sent_on_first_activation(
    make_worker: MakeWorker, app: App, insert_inbox: InsertInbox
) -> None:
    add_parts(insert_inbox, 1, (1,), 1)
    make_worker().deliver_pending()
    assert app.ids == []


def test_history_is_left_untouched_on_first_activation(
    make_worker: MakeWorker, engine: Engine, insert_inbox: InsertInbox
) -> None:
    add_parts(insert_inbox, 1, (1,), 1)
    make_worker().deliver_pending()
    assert processed_flags(engine) == ["false"]


def test_message_after_activation_is_sent(
    make_worker: MakeWorker, app: App, insert_inbox: InsertInbox
) -> None:
    add_parts(insert_inbox, 1, (1,), 1)
    worker = make_worker()
    worker.deliver_pending()
    add_parts(insert_inbox, 2, (1,), 1)
    worker.deliver_pending()
    assert app.ids == [2]


def test_message_received_while_stopped_is_sent_at_the_next_start(
    make_worker: MakeWorker, app: App, insert_inbox: InsertInbox
) -> None:
    make_worker().start_message_id()
    add_parts(insert_inbox, 1, (1,), 1)
    make_worker().deliver_pending()
    assert app.ids == [1]


def test_part_without_message_id_yet_is_ignored(
    worker: WebhookWorker, app: App, insert_inbox: InsertInbox
) -> None:
    insert_inbox(ID=1, MessageID=0)
    worker.deliver_pending()
    assert app.ids == []


@pytest.mark.parametrize(
    ("failures", "delay"), [(1, 5), (2, 10), (3, 20), (6, 160), (7, 300), (50, 300)]
)
def test_retry_delay_grows_up_to_five_minutes(failures: int, delay: int) -> None:
    assert retry_delay(failures) == delay


# --- Purge ---

LONG_AGO = datetime.now() - timedelta(days=30)
RECENTLY = datetime.now() - timedelta(days=1)


def purge(migrated_database: Database_, start: int | None = None) -> None:
    with Database(migrated_database[0]).session() as session:
        purge_old_messages(session, 7, start)


def inbox_ids(engine: Engine) -> list[int]:
    with engine.connect() as connection:
        return list(connection.execute(text("SELECT ID FROM inbox ORDER BY ID")).scalars())


def sent_ids(engine: Engine) -> list[int]:
    with engine.connect() as connection:
        return list(connection.execute(text("SELECT ID FROM sentitems ORDER BY ID")).scalars())


def add_sent(engine: Engine, id: int, date: datetime) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO sentitems (ID, SendingDateTime, Text, UDH, TextDecoded, SenderID, "
                "CreatorID) VALUES (:id, :date, '', '', 'x', '', 't')"
            ),
            {"id": id, "date": date},
        )


def test_purge_removes_old_messages(
    migrated_database: Database_, engine: Engine, insert_inbox: InsertInbox
) -> None:
    insert_inbox(ID=1, MessageID=1, ReceivingDateTime=LONG_AGO)
    purge(migrated_database)
    assert inbox_ids(engine) == []


def test_purge_keeps_recent_messages(
    migrated_database: Database_, engine: Engine, insert_inbox: InsertInbox
) -> None:
    insert_inbox(ID=1, MessageID=1, ReceivingDateTime=RECENTLY)
    purge(migrated_database)
    assert inbox_ids(engine) == [1]


def test_purge_keeps_a_message_with_a_recent_part(
    migrated_database: Database_, engine: Engine, insert_inbox: InsertInbox
) -> None:
    insert_inbox(ID=1, MessageID=1, ReceivingDateTime=LONG_AGO)
    insert_inbox(ID=2, MessageID=1, SequencePosition=2, ReceivingDateTime=RECENTLY)
    purge(migrated_database)
    assert inbox_ids(engine) == [1, 2]


def test_purge_removes_old_sent_items(migrated_database: Database_, engine: Engine) -> None:
    add_sent(engine, 1, LONG_AGO)
    add_sent(engine, 2, RECENTLY)
    purge(migrated_database)
    assert sent_ids(engine) == [2]


def test_purge_never_touches_the_outbox(migrated_database: Database_, engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO outbox (ID, SendingDateTime, TextDecoded, CreatorID) "
                "VALUES (1, :date, 'x', 't')"
            ),
            {"date": LONG_AGO},
        )
    purge(migrated_database)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM outbox")).scalar() == 1


def test_purge_keeps_a_message_waiting_for_the_webhook(
    migrated_database: Database_, engine: Engine, insert_inbox: InsertInbox
) -> None:
    insert_inbox(ID=5, MessageID=5, ReceivingDateTime=LONG_AGO)
    purge(migrated_database, start=1)
    assert inbox_ids(engine) == [5]


def test_purge_removes_a_delivered_message(
    migrated_database: Database_, engine: Engine, insert_inbox: InsertInbox
) -> None:
    insert_inbox(ID=5, MessageID=5, ReceivingDateTime=LONG_AGO, Processed="true")
    purge(migrated_database, start=1)
    assert inbox_ids(engine) == []


def test_purge_removes_history_older_than_the_webhook(
    migrated_database: Database_, engine: Engine, insert_inbox: InsertInbox
) -> None:
    insert_inbox(ID=1, MessageID=1, ReceivingDateTime=LONG_AGO)
    purge(migrated_database, start=1)
    assert inbox_ids(engine) == []
