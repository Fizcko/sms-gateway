from fastapi.testclient import TestClient

from tests.integration.conftest import InsertInbox


def insert_three_parts(insert_inbox: InsertInbox, message_id: int = 1) -> None:
    for position, part_text in enumerate(("a", "b", "c"), start=1):
        insert_inbox(
            ID=message_id + position - 1,
            MessageID=message_id,
            SequencePosition=position,
            PartCount=3,
            TextDecoded=part_text,
        )


def test_list_returns_one_entry_per_message(client: TestClient, insert_inbox: InsertInbox) -> None:
    insert_three_parts(insert_inbox)
    results = client.get("/v1/inbox").json()["results"]
    assert [(m["ID"], m["TextDecoded"]) for m in results] == [(1, "abc")]


def test_incomplete_message_is_listed_and_flagged(
    client: TestClient, insert_inbox: InsertInbox
) -> None:
    insert_inbox(ID=1, MessageID=1, SequencePosition=1, PartCount=2, TextDecoded="a")
    message = client.get("/v1/inbox").json()["results"][0]
    assert (message["Complete"], message["PartCount"], message["ReceivedParts"]) == (False, 2, 1)


def test_part_without_message_id_yet_is_hidden(
    client: TestClient, insert_inbox: InsertInbox
) -> None:
    insert_inbox(ID=1, MessageID=0)
    assert client.get("/v1/inbox").json()["results"] == []


def test_pagination_counts_messages_not_parts(
    client: TestClient, insert_inbox: InsertInbox
) -> None:
    insert_three_parts(insert_inbox, message_id=1)
    insert_three_parts(insert_inbox, message_id=4)
    body = client.get("/v1/inbox", params={"per_page": 1, "page": 2}).json()
    assert (body["page"], body["total_pages"], [m["ID"] for m in body["results"]]) == (2, 2, [4])


def test_sender_filter(client: TestClient, insert_inbox: InsertInbox) -> None:
    insert_inbox(ID=1, MessageID=1, SenderNumber="+101")
    insert_inbox(ID=2, MessageID=2, SenderNumber="+102")
    results = client.get("/v1/inbox", params={"sender": "+102"}).json()["results"]
    assert [m["ID"] for m in results] == [2]


def test_before_filter_uses_the_message_date(client: TestClient, insert_inbox: InsertInbox) -> None:
    insert_inbox(ID=1, MessageID=1, ReceivingDateTime="2026-01-01 00:00:00")
    insert_inbox(ID=2, MessageID=2, ReceivingDateTime="2026-03-01 00:00:00")
    results = client.get("/v1/inbox", params={"before": "2026-02-01"}).json()["results"]
    assert [m["ID"] for m in results] == [1]


def test_after_filter_uses_the_message_date(client: TestClient, insert_inbox: InsertInbox) -> None:
    insert_inbox(ID=1, MessageID=1, ReceivingDateTime="2026-01-01 00:00:00")
    insert_inbox(ID=2, MessageID=2, ReceivingDateTime="2026-03-01 00:00:00")
    results = client.get("/v1/inbox", params={"after": "2026-02-01"}).json()["results"]
    assert [m["ID"] for m in results] == [2]


def test_invalid_date_filter_is_refused(client: TestClient) -> None:
    assert client.get("/v1/inbox", params={"before": "yesterday"}).status_code == 400


def test_page_zero_is_refused(client: TestClient) -> None:
    assert client.get("/v1/inbox", params={"page": 0}).status_code == 400


def test_per_page_zero_is_refused(client: TestClient) -> None:
    assert client.get("/v1/inbox", params={"per_page": 0}).status_code == 400


def test_get_by_message_id_returns_the_whole_message(
    client: TestClient, insert_inbox: InsertInbox
) -> None:
    insert_three_parts(insert_inbox)
    assert client.get("/v1/inbox/1").json()["TextDecoded"] == "abc"


def test_get_by_id_of_a_later_part_is_404(client: TestClient, insert_inbox: InsertInbox) -> None:
    insert_three_parts(insert_inbox)
    assert client.get("/v1/inbox/2").status_code == 404


def test_get_unknown_message_is_404(client: TestClient) -> None:
    response = client.get("/v1/inbox/999")
    assert (response.status_code, response.json()["message"]) == (404, "SMS not found")


def test_delete_removes_every_part_of_the_message(
    client: TestClient, insert_inbox: InsertInbox
) -> None:
    insert_three_parts(insert_inbox)
    assert client.delete("/v1/inbox/1").status_code == 204
    assert client.get("/v1/inbox").json()["results"] == []


def test_delete_by_id_of_a_later_part_removes_nothing(
    client: TestClient, insert_inbox: InsertInbox
) -> None:
    insert_three_parts(insert_inbox)
    client.delete("/v1/inbox/2")
    assert client.get("/v1/inbox/1").json()["ReceivedParts"] == 3


def test_delete_unknown_message_is_204(client: TestClient) -> None:
    assert client.delete("/v1/inbox/999").status_code == 204


def test_delete_all_empties_the_inbox(client: TestClient, insert_inbox: InsertInbox) -> None:
    insert_three_parts(insert_inbox)
    assert client.delete("/v1/inbox/all").status_code == 204
    assert client.get("/v1/inbox").json()["results"] == []
