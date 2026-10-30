"""The real gammu-smsd and python-gammu, with Gammu's dummy phone, on a real database."""

import json
import shutil
import subprocess
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from sms_gateway.app import create_app
from sms_gateway.db.migrate import upgrade
from sms_gateway.services.sms_sender import GammuSmsSender
from sms_gateway.settings import Settings
from tests.integration.test_migrations import legacy_v17

pytestmark = pytest.mark.skipif(shutil.which("gammu-smsd") is None, reason="needs gammu-smsd")

Database = tuple[Settings, Engine]
LONG_TEXT = "hello multipart " * 20


def write_config(settings: Settings, directory: Path) -> Path:
    phone = directory / "phone"
    phone.mkdir(exist_ok=True)
    path = directory / "smsdrc"
    path.write_text(
        f"""[gammu]
device = {phone}
connection = none
model = dummy
[smsd]
Service = sql
Driver = native_mysql
Host = {settings.mysql_host}
User = {settings.mysql_user}
Password = {settings.mysql_password}
Database = {settings.mysql_database}
logfile = stderr
CommTimeout = 1
ReceiveFrequency = 1
StatusFrequency = 1
"""
    )
    return path


@contextmanager
def running_smsd(config: Path) -> Iterator[None]:
    process = subprocess.Popen(
        ["gammu-smsd", "-c", str(config)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    try:
        yield
    finally:
        process.terminate()
        process.wait(timeout=15)


def wait_until(condition: Callable[[], bool], timeout: float = 20) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(0.25)
    return False


def count(engine: Engine, table: str) -> int:
    with engine.connect() as connection:
        return connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0


def test_sent_message_goes_through_the_outbox_to_sent_items(
    migrated_database: Database, tmp_path: Path
) -> None:
    settings, engine = migrated_database
    config = write_config(settings, tmp_path)
    client = TestClient(create_app(settings, GammuSmsSender(str(config))))

    response = client.post("/v1/send", json={"recipients": ["+12025550123"], "message": LONG_TEXT})
    assert response.status_code == 200

    with running_smsd(config):
        assert wait_until(lambda: count(engine, "outbox") == 0)

    parts = client.get("/v1/sentitems").json()["results"]
    assert "".join(part["TextDecoded"] for part in parts) == LONG_TEXT


def receive_on_dummy_phone(directory: Path) -> None:
    """Put a long SMS on the dummy phone, for gammu-smsd to read."""
    import gammu

    phone = gammu.StateMachine()
    phone.SetConfig(0, {"Device": str(directory / "phone"), "Connection": "none", "Model": "dummy"})
    phone.Init()
    parts = gammu.EncodeSMS(
        {
            "Class": -1,
            "Unicode": False,
            "Entries": [{"ID": "ConcatenatedTextLong", "Buffer": LONG_TEXT}],
        }
    )
    for part in parts:
        part.update(
            {
                "Number": "+12025550199",
                "SMSC": {"Number": "+12025550101", "Location": 0},
                "Folder": 1,
                "InboxFolder": 1,
                "State": "UnRead",
                "Memory": "ME",
                "Location": 0,
                "Type": "Deliver",
                "DateTime": datetime.now(),
            }
        )
        phone.AddSMS(part)


def test_received_multipart_is_exposed_as_one_complete_message(
    migrated_database: Database, tmp_path: Path
) -> None:
    settings, engine = migrated_database
    config = write_config(settings, tmp_path)
    receive_on_dummy_phone(tmp_path)

    with running_smsd(config):
        assert wait_until(lambda: count(engine, "inbox") == 3)

    client = TestClient(create_app(settings, GammuSmsSender(str(config))))
    results = client.get("/v1/inbox").json()["results"]
    assert [(m["TextDecoded"], m["Complete"], m["PartCount"]) for m in results] == [
        (LONG_TEXT, True, 3)
    ]


def test_smsd_works_on_a_database_migrated_from_the_previous_release(
    empty_database: Database, tmp_path: Path
) -> None:
    settings, engine = empty_database
    legacy_v17(engine)
    upgrade(engine)
    with running_smsd(write_config(settings, tmp_path)):
        assert wait_until(lambda: count(engine, "sentitems") == 1)


def test_health_follows_the_real_smsd_heartbeat(
    migrated_database: Database, tmp_path: Path
) -> None:
    settings, _ = migrated_database
    config = write_config(settings, tmp_path)
    client = TestClient(
        create_app(settings, GammuSmsSender(str(config))), raise_server_exceptions=False
    )

    process = subprocess.Popen(
        ["gammu-smsd", "-c", str(config)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    try:
        assert wait_until(lambda: client.get("/healthz").status_code == 200)
    finally:
        # No clean shutdown: this is what a crash leaves behind.
        process.kill()
        process.wait(timeout=15)

    assert wait_until(lambda: client.get("/healthz").json().get("phone") == "disconnected")


def test_webhook_receives_a_real_multipart_sms_as_one_post(
    migrated_database: Database, tmp_path: Path
) -> None:
    settings, engine = migrated_database
    received: list[dict[str, object]] = []

    class Receiver(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers["Content-Length"])
            received.append(json.loads(self.rfile.read(length)))
            self.send_response(204)
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = HTTPServer(("127.0.0.1", 0), Receiver)
    Thread(target=server.serve_forever, daemon=True).start()
    webhook_settings = settings.model_copy(
        update={
            "webhook_url": f"http://127.0.0.1:{server.server_port}/sms",
            "webhook_secret": "secret",
        }
    )
    config = write_config(settings, tmp_path)
    receive_on_dummy_phone(tmp_path)
    try:
        with TestClient(create_app(webhook_settings, GammuSmsSender(str(config)))):
            # Anything received before the webhook is active counts as history.
            assert wait_until(lambda: count(engine, "webhook_state") == 1)
            with running_smsd(config):
                assert wait_until(lambda: bool(received))
                # Gives a wrongly split delivery the time to show up.
                time.sleep(3)
    finally:
        server.shutdown()

    assert [(m["TextDecoded"], m["Complete"]) for m in received] == [(LONG_TEXT, True)]
