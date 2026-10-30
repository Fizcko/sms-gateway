"""ORM mapping of the Gammu SMSD tables, schema version 18.

gammu-smsd owns these tables and reads them by column name, so attribute names
keep Gammu's spelling. Any change here needs a migration in `db/migrations`.
"""

from datetime import datetime, time

from sqlalchemy import TIMESTAMP, Index, Integer, String, Time, func, text
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

GAMMU_SCHEMA_VERSION = 18
# Tables owned by gammu-smsd, that must match its schema. Others belong to this project.
GAMMU_TABLES = frozenset({"gammu", "inbox", "outbox", "outbox_multipart", "phones", "sentitems"})

_TABLE_OPTIONS = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4"}
_ON_UPDATE_NOW = text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
_CODING = mysql.ENUM(
    "Default_No_Compression",
    "Unicode_No_Compression",
    "8bit",
    "Default_Compression",
    "Unicode_Compression",
)
_SENT_STATUSES = (
    "SendingOK",
    "SendingOKNoReport",
    "SendingError",
    "DeliveryOK",
    "DeliveryFailed",
    "DeliveryPending",
    "DeliveryUnknown",
    "Error",
)
_BOOLEAN = mysql.ENUM("false", "true")
_YES_NO = mysql.ENUM("yes", "no")
_UNSIGNED = mysql.INTEGER(unsigned=True)


class Base(DeclarativeBase):
    pass


class GammuVersion(Base):
    __tablename__ = "gammu"
    __table_args__ = _TABLE_OPTIONS

    Version: Mapped[int] = mapped_column(Integer, primary_key=True, server_default="0")


class Inbox(Base):
    """One physical SMS part. Parts of a message share the same `MessageID`."""

    __tablename__ = "inbox"
    __table_args__ = (
        Index("inbox_message", "MessageID", "SequencePosition"),
        Index("inbox_insert", "InsertIntoDB"),
        _TABLE_OPTIONS,
    )

    UpdatedInDB: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=_ON_UPDATE_NOW)
    ReceivingDateTime: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    InsertIntoDB: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    Text: Mapped[str] = mapped_column(mysql.TEXT)
    SenderNumber: Mapped[str] = mapped_column(String(20), server_default="")
    Coding: Mapped[str] = mapped_column(_CODING, server_default="Default_No_Compression")
    UDH: Mapped[str] = mapped_column(mysql.TEXT)
    SMSCNumber: Mapped[str] = mapped_column(String(20), server_default="")
    Class: Mapped[int] = mapped_column(Integer, server_default="-1")
    TextDecoded: Mapped[str] = mapped_column(mysql.TEXT)
    ID: Mapped[int] = mapped_column(_UNSIGNED, primary_key=True, autoincrement=True)
    MessageID: Mapped[int] = mapped_column(_UNSIGNED, server_default="0")
    SequencePosition: Mapped[int] = mapped_column(Integer, server_default="1")
    PartCount: Mapped[int] = mapped_column(Integer, server_default="1")
    RecipientID: Mapped[str] = mapped_column(mysql.TEXT)
    Processed: Mapped[str] = mapped_column(_BOOLEAN, server_default="false")
    Status: Mapped[int] = mapped_column(Integer, server_default="-1")


class Outbox(Base):
    __tablename__ = "outbox"
    __table_args__ = (
        Index("outbox_date", "SendingDateTime", "SendingTimeOut"),
        Index("outbox_sender", "SenderID", mysql_length={"SenderID": 250}),
        _TABLE_OPTIONS,
    )

    UpdatedInDB: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=_ON_UPDATE_NOW)
    InsertIntoDB: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    SendingDateTime: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    SendBefore: Mapped[time] = mapped_column(Time, server_default="23:59:59")
    SendAfter: Mapped[time] = mapped_column(Time, server_default="00:00:00")
    SendDays: Mapped[int] = mapped_column(Integer, server_default="127")
    Text: Mapped[str | None] = mapped_column(mysql.TEXT)
    DestinationNumber: Mapped[str] = mapped_column(String(20), server_default="")
    Coding: Mapped[str] = mapped_column(_CODING, server_default="Default_No_Compression")
    UDH: Mapped[str | None] = mapped_column(mysql.TEXT)
    Class: Mapped[int | None] = mapped_column(Integer, server_default="-1")
    TextDecoded: Mapped[str] = mapped_column(mysql.TEXT)
    ID: Mapped[int] = mapped_column(_UNSIGNED, primary_key=True, autoincrement=True)
    MultiPart: Mapped[str | None] = mapped_column(_BOOLEAN, server_default="false")
    RelativeValidity: Mapped[int | None] = mapped_column(Integer, server_default="-1")
    SenderID: Mapped[str | None] = mapped_column(String(255))
    SendingTimeOut: Mapped[datetime | None] = mapped_column(TIMESTAMP, server_default=func.now())
    DeliveryReport: Mapped[str | None] = mapped_column(
        mysql.ENUM("default", "yes", "no"), server_default="default"
    )
    CreatorID: Mapped[str] = mapped_column(mysql.TEXT)
    Retries: Mapped[int | None] = mapped_column(mysql.INTEGER(3), server_default="0")
    Priority: Mapped[int | None] = mapped_column(Integer, server_default="0")
    Status: Mapped[str] = mapped_column(
        mysql.ENUM(*_SENT_STATUSES, "Reserved"), server_default="Reserved"
    )
    StatusCode: Mapped[int] = mapped_column(Integer, server_default="-1")


class OutboxMultipart(Base):
    __tablename__ = "outbox_multipart"
    __table_args__ = _TABLE_OPTIONS

    Text: Mapped[str | None] = mapped_column(mysql.TEXT)
    Coding: Mapped[str] = mapped_column(_CODING, server_default="Default_No_Compression")
    UDH: Mapped[str | None] = mapped_column(mysql.TEXT)
    Class: Mapped[int | None] = mapped_column(Integer, server_default="-1")
    TextDecoded: Mapped[str | None] = mapped_column(mysql.TEXT)
    ID: Mapped[int] = mapped_column(
        _UNSIGNED, primary_key=True, autoincrement=False, server_default="0"
    )
    SequencePosition: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=False, server_default="1"
    )
    Status: Mapped[str] = mapped_column(
        mysql.ENUM(*_SENT_STATUSES, "Reserved"), server_default="Reserved"
    )
    StatusCode: Mapped[int] = mapped_column(Integer, server_default="-1")


class Phone(Base):
    __tablename__ = "phones"
    __table_args__ = _TABLE_OPTIONS

    ID: Mapped[str] = mapped_column(mysql.TEXT)
    UpdatedInDB: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=_ON_UPDATE_NOW)
    InsertIntoDB: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    TimeOut: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    Send: Mapped[str] = mapped_column(_YES_NO, server_default="no")
    Receive: Mapped[str] = mapped_column(_YES_NO, server_default="no")
    IMEI: Mapped[str] = mapped_column(String(35), primary_key=True)
    IMSI: Mapped[str] = mapped_column(String(35))
    NetCode: Mapped[str | None] = mapped_column(String(10), server_default="ERROR")
    NetName: Mapped[str | None] = mapped_column(String(35), server_default="ERROR")
    Client: Mapped[str] = mapped_column(mysql.TEXT)
    Battery: Mapped[int] = mapped_column(Integer, server_default="-1")
    Signal: Mapped[int] = mapped_column(Integer, server_default="-1")
    Sent: Mapped[int] = mapped_column(Integer, server_default="0")
    Received: Mapped[int] = mapped_column(Integer, server_default="0")


class SentItem(Base):
    """One physical SMS part sent. Parts of a message share the same `ID`."""

    __tablename__ = "sentitems"
    __table_args__ = (
        Index("sentitems_date", "DeliveryDateTime"),
        Index("sentitems_tpmr", "TPMR"),
        Index("sentitems_dest", "DestinationNumber"),
        Index("sentitems_sender", "SenderID", mysql_length={"SenderID": 250}),
        _TABLE_OPTIONS,
    )

    UpdatedInDB: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=_ON_UPDATE_NOW)
    InsertIntoDB: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    SendingDateTime: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    DeliveryDateTime: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    Text: Mapped[str] = mapped_column(mysql.TEXT)
    DestinationNumber: Mapped[str] = mapped_column(String(20), server_default="")
    Coding: Mapped[str] = mapped_column(_CODING, server_default="Default_No_Compression")
    UDH: Mapped[str] = mapped_column(mysql.TEXT)
    SMSCNumber: Mapped[str] = mapped_column(String(20), server_default="")
    Class: Mapped[int] = mapped_column(Integer, server_default="-1")
    TextDecoded: Mapped[str] = mapped_column(mysql.TEXT)
    ID: Mapped[int] = mapped_column(
        _UNSIGNED, primary_key=True, autoincrement=False, server_default="0"
    )
    SenderID: Mapped[str] = mapped_column(String(255))
    SequencePosition: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=False, server_default="1"
    )
    Status: Mapped[str] = mapped_column(mysql.ENUM(*_SENT_STATUSES), server_default="SendingOK")
    StatusError: Mapped[int] = mapped_column(Integer, server_default="-1")
    TPMR: Mapped[int] = mapped_column(Integer, server_default="-1")
    RelativeValidity: Mapped[int] = mapped_column(Integer, server_default="-1")
    CreatorID: Mapped[str] = mapped_column(mysql.TEXT)
    StatusCode: Mapped[int] = mapped_column(Integer, server_default="-1")


class WebhookState(Base):
    """Project table: where the webhook starts, set once on first activation."""

    __tablename__ = "webhook_state"
    __table_args__ = _TABLE_OPTIONS

    ID: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=False, server_default="1"
    )
    StartMessageID: Mapped[int] = mapped_column(_UNSIGNED)
