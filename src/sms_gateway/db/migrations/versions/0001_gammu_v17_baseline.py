"""Baseline: the Gammu v17 schema, as created by the previous releases.

Databases already at v17 are stamped at this revision instead of running it.
`IF NOT EXISTS` lets a start interrupted during this revision resume; `gammu`
comes last because its presence marks an existing database.

Revision ID: 0001
Revises:
"""

from alembic import op

revision = "0001"
down_revision = None

_CODING = (
    "enum('Default_No_Compression','Unicode_No_Compression','8bit',"
    "'Default_Compression','Unicode_Compression') NOT NULL "
    "DEFAULT 'Default_No_Compression'"
)
_SENT_STATUS = (
    "'SendingOK','SendingOKNoReport','SendingError','DeliveryOK','DeliveryFailed',"
    "'DeliveryPending','DeliveryUnknown','Error'"
)
_OPTIONS = "ENGINE=MyISAM DEFAULT CHARSET=utf8mb4"
_UPDATED = "`UpdatedInDB` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"


def upgrade() -> None:
    op.execute(f"""CREATE TABLE IF NOT EXISTS `inbox` (
        {_UPDATED},
        `ReceivingDateTime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
        `Text` text NOT NULL,
        `SenderNumber` varchar(20) NOT NULL DEFAULT '',
        `Coding` {_CODING},
        `UDH` text NOT NULL,
        `SMSCNumber` varchar(20) NOT NULL DEFAULT '',
        `Class` integer NOT NULL DEFAULT -1,
        `TextDecoded` text NOT NULL,
        `ID` integer unsigned NOT NULL AUTO_INCREMENT,
        `RecipientID` text NOT NULL,
        `Processed` enum('false','true') NOT NULL DEFAULT 'false',
        `Status` integer NOT NULL DEFAULT -1,
        PRIMARY KEY (`ID`)
    ) {_OPTIONS}""")
    op.execute(f"""CREATE TABLE IF NOT EXISTS `outbox` (
        {_UPDATED},
        `InsertIntoDB` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
        `SendingDateTime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
        `SendBefore` time NOT NULL DEFAULT '23:59:59',
        `SendAfter` time NOT NULL DEFAULT '00:00:00',
        `Text` text,
        `DestinationNumber` varchar(20) NOT NULL DEFAULT '',
        `Coding` {_CODING},
        `UDH` text,
        `Class` integer DEFAULT -1,
        `TextDecoded` text NOT NULL,
        `ID` integer unsigned NOT NULL AUTO_INCREMENT,
        `MultiPart` enum('false','true') DEFAULT 'false',
        `RelativeValidity` integer DEFAULT -1,
        `SenderID` varchar(255),
        `SendingTimeOut` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
        `DeliveryReport` enum('default','yes','no') DEFAULT 'default',
        `CreatorID` text NOT NULL,
        `Retries` int(3) DEFAULT 0,
        `Priority` integer DEFAULT 0,
        `Status` enum({_SENT_STATUS},'Reserved') NOT NULL DEFAULT 'Reserved',
        `StatusCode` integer NOT NULL DEFAULT -1,
        PRIMARY KEY (`ID`),
        INDEX `outbox_date` (`SendingDateTime`, `SendingTimeOut`),
        INDEX `outbox_sender` (`SenderID`(250))
    ) {_OPTIONS}""")
    op.execute(f"""CREATE TABLE IF NOT EXISTS `outbox_multipart` (
        `Text` text,
        `Coding` {_CODING},
        `UDH` text,
        `Class` integer DEFAULT -1,
        `TextDecoded` text,
        `ID` integer unsigned NOT NULL DEFAULT 0,
        `SequencePosition` integer NOT NULL DEFAULT 1,
        `Status` enum({_SENT_STATUS},'Reserved') NOT NULL DEFAULT 'Reserved',
        `StatusCode` integer NOT NULL DEFAULT -1,
        PRIMARY KEY (`ID`, `SequencePosition`)
    ) {_OPTIONS}""")
    op.execute(f"""CREATE TABLE IF NOT EXISTS `phones` (
        `ID` text NOT NULL,
        {_UPDATED},
        `InsertIntoDB` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
        `TimeOut` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
        `Send` enum('yes','no') NOT NULL DEFAULT 'no',
        `Receive` enum('yes','no') NOT NULL DEFAULT 'no',
        `IMEI` varchar(35) NOT NULL,
        `IMSI` varchar(35) NOT NULL,
        `NetCode` varchar(10) DEFAULT 'ERROR',
        `NetName` varchar(35) DEFAULT 'ERROR',
        `Client` text NOT NULL,
        `Battery` integer NOT NULL DEFAULT -1,
        `Signal` integer NOT NULL DEFAULT -1,
        `Sent` integer NOT NULL DEFAULT 0,
        `Received` integer NOT NULL DEFAULT 0,
        PRIMARY KEY (`IMEI`)
    ) {_OPTIONS}""")
    op.execute(f"""CREATE TABLE IF NOT EXISTS `sentitems` (
        {_UPDATED},
        `InsertIntoDB` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
        `SendingDateTime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
        `DeliveryDateTime` timestamp NULL,
        `Text` text NOT NULL,
        `DestinationNumber` varchar(20) NOT NULL DEFAULT '',
        `Coding` {_CODING},
        `UDH` text NOT NULL,
        `SMSCNumber` varchar(20) NOT NULL DEFAULT '',
        `Class` integer NOT NULL DEFAULT -1,
        `TextDecoded` text NOT NULL,
        `ID` integer unsigned NOT NULL DEFAULT 0,
        `SenderID` varchar(255) NOT NULL,
        `SequencePosition` integer NOT NULL DEFAULT 1,
        `Status` enum({_SENT_STATUS}) NOT NULL DEFAULT 'SendingOK',
        `StatusError` integer NOT NULL DEFAULT -1,
        `TPMR` integer NOT NULL DEFAULT -1,
        `RelativeValidity` integer NOT NULL DEFAULT -1,
        `CreatorID` text NOT NULL,
        `StatusCode` integer NOT NULL DEFAULT -1,
        PRIMARY KEY (`ID`, `SequencePosition`),
        INDEX `sentitems_date` (`DeliveryDateTime`),
        INDEX `sentitems_tpmr` (`TPMR`),
        INDEX `sentitems_dest` (`DestinationNumber`),
        INDEX `sentitems_sender` (`SenderID`(250))
    ) {_OPTIONS}""")
    op.execute(f"""CREATE TABLE IF NOT EXISTS `gammu` (
        `Version` integer NOT NULL DEFAULT 0 PRIMARY KEY
    ) {_OPTIONS}""")
    op.execute("INSERT INTO `gammu` (`Version`) VALUES (17)")
