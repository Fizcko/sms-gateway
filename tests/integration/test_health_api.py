from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

AddPhone = Callable[..., None]
FRESH = "NOW() + INTERVAL 60 SECOND"
EXPIRED = "NOW() - INTERVAL 60 SECOND"


@pytest.fixture
def add_phone(engine: Engine) -> AddPhone:
    def insert(
        timeout: str, imei: str = "111", signal: int = 74, network: str = "T-Mobile"
    ) -> None:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO phones (ID, IMEI, IMSI, Client, `Signal`, NetName, TimeOut) "
                    f"VALUES ('', :imei, '222', 'Gammu', :signal, :network, {timeout})"
                ),
                {"imei": imei, "signal": signal, "network": network},
            )

    return insert


def test_phone_with_a_fresh_heartbeat_is_connected(client: TestClient, add_phone: AddPhone) -> None:
    add_phone(FRESH)
    response = client.get("/healthz")
    assert (response.status_code, response.json()) == (
        200,
        {
            "status": "healthy",
            "database": "connected",
            "phone": "connected",
            "signal": 74,
            "network": "T-Mobile",
        },
    )


def test_no_phone_row_is_unhealthy(client: TestClient) -> None:
    response = client.get("/healthz")
    assert (response.status_code, response.json()) == (
        500,
        {
            "status": "unhealthy",
            "database": "connected",
            "phone": "disconnected",
            "error": "No recent status from gammu-smsd",
        },
    )


def test_expired_heartbeat_is_disconnected(client: TestClient, add_phone: AddPhone) -> None:
    add_phone(EXPIRED)
    assert client.get("/healthz").json()["phone"] == "disconnected"


def test_fresh_row_wins_over_an_expired_one(client: TestClient, add_phone: AddPhone) -> None:
    add_phone(EXPIRED, imei="old", network="Old")
    add_phone(FRESH, imei="new", network="New")
    assert client.get("/healthz").json()["network"] == "New"


def test_health_never_exposes_phone_identifiers(client: TestClient, add_phone: AddPhone) -> None:
    add_phone(FRESH)
    assert set(client.get("/healthz").json()) == {
        "status",
        "database",
        "phone",
        "signal",
        "network",
    }
