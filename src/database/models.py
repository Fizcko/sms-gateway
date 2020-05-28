from sqlalchemy import Index, Column, Integer, String, DateTime, Boolean, Enum, TIMESTAMP, func, Time
from sqlalchemy.sql import expression
from sqlalchemy.dialects import mysql
from sqlalchemy.dialects.mysql import VARCHAR, TEXT, INTEGER
from sqlalchemy import event
from database.instance import Base, db_session
from datetime import datetime, time

import json

class gammu(Base):
    __tablename__ = 'gammu'
    Version = Column(Integer, nullable=False, server_default='0', primary_key=True)
    __table_args__ = {'mysql_engine':'MyISAM', 'mysql_charset':'utf8mb4'}

@event.listens_for(gammu.__table__, 'after_create')
def insert_initial_values(*args, **kwargs):
    newValue =  gammu(Version = '17')
    db_session.add(newValue)
    db_session.flush()

class inbox(Base):
    __tablename__ = 'inbox'
    UpdatedInDB = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    ReceivingDateTime = Column(TIMESTAMP, nullable=False, server_default=func.now())
    Text = Column(TEXT, nullable=False)
    SenderNumber = Column(String(20), nullable=False, server_default='')
    Coding = Column(mysql.ENUM('Default_No_Compression','Unicode_No_Compression','8bit','Default_Compression','Unicode_Compression'), nullable=False, server_default='Default_No_Compression')
    UDH = Column(TEXT, nullable=False)
    SMSCNumber = Column(String(20), nullable=False, server_default='')
    Class = Column(Integer, nullable=False, server_default='-1')
    TextDecoded = Column(TEXT, nullable=False)
    ID = Column(INTEGER(unsigned=True), nullable=False, primary_key=True, autoincrement=True)
    RecipientID = Column(TEXT, nullable=False)
    Processed = Column(mysql.ENUM('false','true'), nullable=False, server_default='false')
    Status = Column(Integer, nullable=False, server_default="-1")
    __table_args__ = {'mysql_engine':'MyISAM', 'mysql_charset':'utf8mb4'}
 
    def as_json(self):
        return {
            'ID': self.ID,
            'UpdatedInDB': datetime.isoformat(self.UpdatedInDB),
            'ReceivingDateTime': datetime.isoformat(self.ReceivingDateTime),
            'Text': self.Text,
            'SenderNumber': self.SenderNumber,
            'Coding': self.Coding,
            'UDH': self.UDH,
            'SMSCNumber': self.SMSCNumber,
            'Class': self.Class,
            'TextDecoded': self.TextDecoded,
            'RecipientID': self.RecipientID,
            'Processed': self.Processed,
            'Status': self.Status
        }

    def __repr__(self):
        return json.dumps(self.as_json())

class outbox(Base):
    __tablename__ = 'outbox'
    UpdatedInDB = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    InsertIntoDB = Column(TIMESTAMP, nullable=False, server_default=func.now())
    SendingDateTime = Column(TIMESTAMP, nullable=False, server_default=func.now())
    SendBefore = Column(Time, nullable=False, server_default='23:59:59')
    SendAfter = Column(Time, nullable=False, server_default='00:00:00')
    Text = Column(TEXT)
    DestinationNumber = Column(VARCHAR(20), nullable=False, server_default='')
    Coding = Column(mysql.ENUM('Default_No_Compression','Unicode_No_Compression','8bit','Default_Compression','Unicode_Compression'), nullable=False, server_default='Default_No_Compression')
    UDH = Column(TEXT)
    Class = Column(Integer, server_default='-1')
    TextDecoded = Column(TEXT, nullable=False)
    ID = Column(INTEGER(unsigned=True), nullable=False, primary_key=True, autoincrement=True)
    MultiPart = Column(mysql.ENUM('false','true'), server_default='false')
    RelativeValidity = Column(Integer, server_default="-1")
    SenderID = Column(VARCHAR(255))
    SendingTimeOut = Column(TIMESTAMP, nullable=True, server_default=func.now())
    DeliveryReport = Column(mysql.ENUM('default','yes','no'), server_default='default')
    CreatorID = Column(TEXT, nullable=False)
    Retries = Column(INTEGER(3), server_default='0')
    Priority = Column(INTEGER, server_default='0')
    Status = Column(mysql.ENUM('SendingOK','SendingOKNoReport','SendingError','DeliveryOK','DeliveryFailed','DeliveryPending','DeliveryUnknown','Error','Reserved'), nullable=False, server_default='Reserved')
    StatusCode = Column(Integer, nullable=False, server_default="-1")
    __table_args__ = (
        Index('outbox_date', "SendingDateTime", "SendingTimeOut"), 
        Index('outbox_sender', "SenderID", mysql_length={'SenderID': 250}), 
        {'mysql_engine':'MyISAM', 'mysql_charset':'utf8mb4'},
    )

    def as_json(self):
        return {
            'ID': self.ID,
            'UpdatedInDB': datetime.isoformat(self.UpdatedInDB),
            'InsertIntoDB': datetime.isoformat(self.InsertIntoDB),
            'SendingDateTime': datetime.isoformat(self.SendingDateTime),
            'SendBefore': time.isoformat(self.SendBefore),
            'SendAfter': time.isoformat(self.SendAfter),
            'Text': self.Text,
            'DestinationNumber': self.DestinationNumber,
            'Coding': self.Coding,
            'UDH': self.UDH,
            'Class': self.Class,
            'TextDecoded': self.TextDecoded,
            'MultiPart': self.MultiPart,
            'RelativeValidity': self.RelativeValidity,
            'SenderID': self.SenderID,
            'SendingTimeOut': datetime.isoformat(self.SendingTimeOut),
            'DeliveryReport': self.DeliveryReport,
            'CreatorID': self.CreatorID,
            'Retries': self.Retries,
            'Priority': self.Priority,
            'Status': self.Status,
            'StatusCode': self.StatusCode
        }

    def __repr__(self):
        return json.dumps(self.as_json())

class outbox_multipart(Base):
    __tablename__ = 'outbox_multipart'
    Text = Column(TEXT)
    Coding = Column(mysql.ENUM('Default_No_Compression','Unicode_No_Compression','8bit','Default_Compression','Unicode_Compression'), nullable=False, server_default='Default_No_Compression')
    UDH = Column(TEXT)
    Class = Column(Integer, server_default='-1')
    TextDecoded = Column(TEXT)
    ID = Column(INTEGER(unsigned=True), nullable=False, primary_key=True, server_default='0')
    SequencePosition = Column(Integer, nullable=False, primary_key=True, server_default="1")
    Status = Column(mysql.ENUM('SendingOK','SendingOKNoReport','SendingError','DeliveryOK','DeliveryFailed','DeliveryPending','DeliveryUnknown','Error','Reserved'), nullable=False, server_default='Reserved')
    StatusCode = Column(Integer, nullable=False, server_default="-1")
    __table_args__ = {'mysql_engine':'MyISAM', 'mysql_charset':'utf8mb4'}

class phones(Base):
    __tablename__ = 'phones'
    ID = Column(TEXT, nullable=False)
    UpdatedInDB = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    InsertIntoDB = Column(TIMESTAMP, nullable=False, server_default=func.now())
    TimeOut = Column(TIMESTAMP, nullable=False, server_default=func.now())
    Send = Column(mysql.ENUM('yes','no'), nullable=False, server_default='no')
    Receive = Column(mysql.ENUM('yes','no'), nullable=False, server_default='no')
    IMEI = Column(VARCHAR(35), nullable=False, primary_key=True)
    IMSI = Column(VARCHAR(35), nullable=False)
    NetCode = Column(VARCHAR(10), server_default='ERROR')
    NetName = Column(VARCHAR(35), server_default='ERROR')
    Client = Column(TEXT, nullable=False)
    Battery = Column(Integer, nullable=False, server_default='-1')
    Signal = Column(Integer, nullable=False, server_default='-1')
    Sent = Column(Integer, nullable=False, server_default='0')
    Received = Column(Integer, nullable=False, server_default='0')
    __table_args__ = {'mysql_engine':'MyISAM', 'mysql_charset':'utf8mb4'}

class sentitems(Base):
    __tablename__ = 'sentitems'
    UpdatedInDB = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    InsertIntoDB = Column(TIMESTAMP, nullable=False, server_default=func.now())
    SendingDateTime = Column(TIMESTAMP, nullable=False, server_default=func.now())
    DeliveryDateTime = Column(TIMESTAMP, nullable=True)
    Text = Column(TEXT, nullable=False)
    DestinationNumber = Column(VARCHAR(20), nullable=False, server_default='')
    Coding = Column(mysql.ENUM('Default_No_Compression','Unicode_No_Compression','8bit','Default_Compression','Unicode_Compression'), nullable=False, server_default='Default_No_Compression')
    UDH = Column(TEXT, nullable=False)
    SMSCNumber =  Column(VARCHAR(20), nullable=False, server_default='')
    Class = Column(Integer, nullable=False, server_default='-1')
    TextDecoded = Column(TEXT, nullable=False)
    ID = Column(INTEGER(unsigned=True), nullable=False, primary_key=True, server_default='0')
    SenderID = Column(VARCHAR(255), nullable=False)
    SequencePosition = Column(Integer, nullable=False, primary_key=True, server_default="1")
    Status = Column(mysql.ENUM('SendingOK','SendingOKNoReport','SendingError','DeliveryOK','DeliveryFailed','DeliveryPending','DeliveryUnknown','Error'), nullable=False, server_default='SendingOK')
    StatusError = Column(Integer, nullable=False, server_default='-1')
    TPMR = Column(Integer, nullable=False, server_default='-1')
    RelativeValidity = Column(Integer, nullable=False, server_default='-1')
    CreatorID = Column(TEXT, nullable=False)
    StatusCode = Column(Integer, nullable=False, server_default="-1")
    __table_args__ = (
        Index('sentitems_date', "DeliveryDateTime"), 
        Index('sentitems_tpmr', "TPMR"), 
        Index('sentitems_dest', "DestinationNumber"), 
        Index('sentitems_sender', "SenderID", mysql_length={'SenderID': 250}),
        {'mysql_engine':'MyISAM', 'mysql_charset':'utf8mb4'},
    )

    def as_json(self):
        return {
            'ID': self.ID,
            'UpdatedInDB': datetime.isoformat(self.UpdatedInDB),
            'InsertIntoDB': datetime.isoformat(self.InsertIntoDB),
            'SendingDateTime': datetime.isoformat(self.SendingDateTime),
            'DeliveryDateTime': datetime.isoformat(self.DeliveryDateTime) if self.DeliveryDateTime else None,
            'Text': self.Text,
            'DestinationNumber': self.DestinationNumber,
            'Coding': self.Coding,
            'UDH': self.UDH,
            'SMSCNumber': self.SMSCNumber,
            'Class': self.Class,
            'TextDecoded': self.TextDecoded,
            'SenderID': self.SenderID,
            'SequencePosition': self.SequencePosition,
            'Status': self.Status,
            'StatusError': self.StatusError,
            'TPMR': self.TPMR,
            'RelativeValidity': self.RelativeValidity,
            'CreatorID': self.CreatorID,
            'StatusCode': self.StatusCode
        }

    def __repr__(self):
        return json.dumps(self.as_json())
