from datetime import datetime, timedelta

from sms_gateway.db.models import Inbox
from sms_gateway.services.inbox import assemble_message

T0 = datetime(2026, 1, 1, 12, 0, 0)


def part(position: int, count: int = 3, text: str = "", **overrides: object) -> Inbox:
    values: dict[str, object] = {
        "ID": 10 + position,
        "MessageID": 11,
        "SequencePosition": position,
        "PartCount": count,
        "TextDecoded": text,
        "Text": "",
        "UpdatedInDB": T0,
        "ReceivingDateTime": T0,
        "InsertIntoDB": T0,
        "SenderNumber": "+12025550100",
        "Coding": "Default_No_Compression",
        "UDH": f"udh{position}",
        "SMSCNumber": "",
        "Class": -1,
        "RecipientID": "",
        "Processed": "false",
        "Status": 0,
    }
    values.update(overrides)
    return Inbox(**values)


def test_text_is_joined_in_sequence_order_whatever_the_row_order() -> None:
    message = assemble_message([part(3, text="c"), part(1, text="a"), part(2, text="b")])
    assert message.TextDecoded == "abc"


def test_whole_text_stored_in_first_part_is_not_duplicated() -> None:
    message = assemble_message([part(1, text="whole"), part(2), part(3)])
    assert message.TextDecoded == "whole"


def test_message_id_is_exposed_as_id() -> None:
    assert assemble_message([part(2), part(3)]).ID == 11


def test_message_with_all_parts_is_complete() -> None:
    assert assemble_message([part(1), part(2), part(3)]).Complete is True


def test_message_with_a_missing_part_is_incomplete() -> None:
    message = assemble_message([part(1), part(3)])
    assert (message.Complete, message.PartCount, message.ReceivedParts) == (False, 3, 2)


def test_duplicated_position_counts_as_one_received_part() -> None:
    assert assemble_message([part(1), part(1, ID=99), part(2)]).ReceivedParts == 2


def test_single_part_message_is_complete() -> None:
    assert assemble_message([part(1, count=1)]).Complete is True


def test_message_date_is_the_earliest_part_date() -> None:
    later = T0 + timedelta(minutes=5)
    message = assemble_message([part(2, ReceivingDateTime=later), part(3, ReceivingDateTime=T0)])
    assert message.ReceivingDateTime == T0


def test_processed_only_when_every_part_is_processed() -> None:
    message = assemble_message([part(1, Processed="true"), part(2, Processed="false")])
    assert message.Processed == "false"


def test_part_attributes_come_from_the_lowest_position() -> None:
    assert assemble_message([part(3), part(2)]).UDH == "udh2"
