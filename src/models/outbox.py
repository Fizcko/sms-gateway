from flask_restplus import fields
from server.instance import server
from datetime import time

class TimeFormat(fields.Raw):
    def format(self, value):
        return time.strftime(value, "%H:%M")

outbox_item = server.api.model('outbox item', {
    'ID': fields.Integer(
        example='1'
    ),
    'UpdatedInDB': fields.DateTime(
        example='2020-05-26T19:27:55'
    ),
    'InsertIntoDB': fields.DateTime(
        example='2020-05-25T19:59:16'
    ),
    'SendingDateTime': fields.DateTime(
        example='2020-05-25T19:59:16'
    ),
    'SendBefore': TimeFormat(
        example='23:59:59'
    ),
    'SendAfter': TimeFormat(
        example='00:00:00'
    ),
    'Text': fields.String(
        example='00480065006C006C006F00200074006800690073002000610020006D007900200066006900720073007400200053004D0053'
    ),
    'DestinationNumber': fields.String(
        example='+33698765432'
    ),
    'Coding': fields.String(
        example='Default_No_Compression'
    ),
    'UDH': fields.String(
        example=None
    ),
    'Class': fields.Integer(
        example='-1'
    ),
    'TextDecoded': fields.String(
        example='Hello this a my first SMS'
    ),
    'MultiPart': fields.String(
        example='false'
    ),
    'RelativeValidity': fields.Integer(
        example='-1'
    ),
    'SenderID': fields.String(
        example='+33612345678'
    ),
    'SendingTimeOut': fields.DateTime(
        example='2020-05-25T19:59:16'
    ),
    'DeliveryReport': fields.String(
        example='default'
    ),
    'CreatorID': fields.String(
        example='Gammu 1.40.0'
    ),
    'Retries': fields.Integer(
        example='0'
    ),
    'Priority': fields.Integer(
        example='0'
    ),
    'Status': fields.String(
        example='Reserved'
    ),
    'StatusCode': fields.Integer(
        example='-1'
    )
})

outbox_items = server.api.model('outbox items', {
    'page': fields.Integer(
        example='1'
    ),
    'total_pages': fields.Integer(
        example='1'
    ),
    'results': fields.List(
        fields.Nested(outbox_item)
    )
})    