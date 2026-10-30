from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

Insert = Callable[..., None]


@pytest.fixture
def add_outbox(engine: Engine) -> Insert:
    def insert(id: int, number: str = "+101", date: str = "2026-01-01 00:00:00") -> None:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO outbox (ID, DestinationNumber, SendingDateTime, TextDecoded, "
                    "CreatorID) VALUES (:id, :number, :date, 'x', 'test')"
                ),
                {"id": id, "number": number, "date": date},
            )

    return insert


@pytest.fixture
def add_sent(engine: Engine) -> Insert:
    def insert(
        id: int, position: int = 1, number: str = "+101", date: str = "2026-01-01 00:00:00"
    ) -> None:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO sentitems (ID, SequencePosition, DestinationNumber, "
                    "SendingDateTime, Text, UDH, TextDecoded, SenderID, CreatorID) VALUES "
                    "(:id, :position, :number, :date, '', '', 'x', '', 'test')"
                ),
                {"id": id, "position": position, "number": number, "date": date},
            )

    return insert


def ids(client: TestClient, path: str, **params: str) -> list[int]:
    response = client.get(path, params=params)
    assert response.status_code == 200, response.text
    return [row["ID"] for row in response.json()["results"]]


# --- Outbox filters (regression: `before`/`after` were tied to `destination`) ---


def test_outbox_before_filter_alone(client: TestClient, add_outbox: Insert) -> None:
    add_outbox(1, date="2026-01-01 00:00:00")
    add_outbox(2, date="2026-03-01 00:00:00")
    assert ids(client, "/v1/outbox", before="2026-02-01") == [1]


def test_outbox_after_filter_alone(client: TestClient, add_outbox: Insert) -> None:
    add_outbox(1, date="2026-01-01 00:00:00")
    add_outbox(2, date="2026-03-01 00:00:00")
    assert ids(client, "/v1/outbox", after="2026-02-01") == [2]


def test_outbox_destination_filter_alone(client: TestClient, add_outbox: Insert) -> None:
    add_outbox(1, number="+101")
    add_outbox(2, number="+102")
    assert ids(client, "/v1/outbox", destination="+102") == [2]


def test_outbox_item_exposes_schedule_fields(client: TestClient, add_outbox: Insert) -> None:
    add_outbox(1)
    item = client.get("/v1/outbox/1").json()
    assert (item["SendBefore"], item["SendAfter"], item["SendDays"]) == (
        "23:59:59",
        "00:00:00",
        127,
    )


def test_outbox_get_unknown_is_404(client: TestClient) -> None:
    assert client.get("/v1/outbox/999").status_code == 404


def test_outbox_delete_removes_the_item(client: TestClient, add_outbox: Insert) -> None:
    add_outbox(1)
    assert client.delete("/v1/outbox/1").status_code == 204
    assert ids(client, "/v1/outbox") == []


def test_outbox_delete_all_empties_it(client: TestClient, add_outbox: Insert) -> None:
    add_outbox(1)
    assert client.delete("/v1/outbox/all").status_code == 204
    assert ids(client, "/v1/outbox") == []


@pytest.fixture
def add_multipart(engine: Engine) -> Insert:
    def insert(id: int, position: int = 2) -> None:
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO outbox_multipart (ID, SequencePosition) VALUES (:id, :position)"),
                {"id": id, "position": position},
            )

    return insert


def multipart_ids(engine: Engine) -> list[int]:
    with engine.connect() as connection:
        return list(connection.execute(text("SELECT ID FROM outbox_multipart")).scalars())


def test_outbox_delete_removes_its_other_parts(
    client: TestClient, engine: Engine, add_outbox: Insert, add_multipart: Insert
) -> None:
    add_outbox(1)
    add_multipart(1)
    client.delete("/v1/outbox/1")
    assert multipart_ids(engine) == []


def test_outbox_delete_keeps_the_parts_of_other_messages(
    client: TestClient, engine: Engine, add_outbox: Insert, add_multipart: Insert
) -> None:
    add_outbox(1)
    add_outbox(2)
    add_multipart(2)
    client.delete("/v1/outbox/1")
    assert multipart_ids(engine) == [2]


def test_outbox_delete_all_removes_every_part(
    client: TestClient, engine: Engine, add_outbox: Insert, add_multipart: Insert
) -> None:
    add_outbox(1)
    add_multipart(1)
    client.delete("/v1/outbox/all")
    assert multipart_ids(engine) == []


# --- Sent items filters (regression: `before`/`after` were a 500) ---


def test_sentitems_before_filter(client: TestClient, add_sent: Insert) -> None:
    add_sent(1, date="2026-01-01 00:00:00")
    add_sent(2, date="2026-03-01 00:00:00")
    assert ids(client, "/v1/sentitems", before="2026-02-01") == [1]


def test_sentitems_after_filter(client: TestClient, add_sent: Insert) -> None:
    add_sent(1, date="2026-01-01 00:00:00")
    add_sent(2, date="2026-03-01 00:00:00")
    assert ids(client, "/v1/sentitems", after="2026-02-01") == [2]


def test_sentitems_destination_filter(client: TestClient, add_sent: Insert) -> None:
    add_sent(1, number="+101")
    add_sent(2, number="+102")
    assert ids(client, "/v1/sentitems", destination="+102") == [2]


def test_sentitems_list_has_one_entry_per_part(client: TestClient, add_sent: Insert) -> None:
    add_sent(1, position=1)
    add_sent(1, position=2)
    assert ids(client, "/v1/sentitems") == [1, 1]


def test_sentitems_get_returns_the_first_part(client: TestClient, add_sent: Insert) -> None:
    add_sent(1, position=2)
    add_sent(1, position=1)
    assert client.get("/v1/sentitems/1").json()["SequencePosition"] == 1


def test_sentitems_get_unknown_is_404(client: TestClient) -> None:
    assert client.get("/v1/sentitems/999").status_code == 404


def test_sentitems_delete_removes_all_parts(client: TestClient, add_sent: Insert) -> None:
    add_sent(1, position=1)
    add_sent(1, position=2)
    assert client.delete("/v1/sentitems/1").status_code == 204
    assert client.get("/v1/sentitems/1").status_code == 404


def test_sentitems_delete_all_empties_it(client: TestClient, add_sent: Insert) -> None:
    add_sent(1)
    assert client.delete("/v1/sentitems/all").status_code == 204
    assert ids(client, "/v1/sentitems") == []
