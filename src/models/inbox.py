from flask_restplus import fields
from server.instance import server

inbox_item = server.api.model('inbox item', {
    'ID': fields.Integer(
        example='1'
    ),
    'UpdatedInDB': fields.DateTime(
        example='2020-05-26T19:27:55'
    ),
    'ReceivingDateTime': fields.DateTime(
        example='2020-05-25T19:59:16'
    ),
    'Text': fields.String(
        example='00480065006C006C006F00200074006800690073002000610020006D007900200066006900720073007400200053004D0053'
    ),
    'SenderNumber': fields.String(
        example='+33612345678'
    ),
    'Coding': fields.String(
        example='Default_No_Compression'
    ),
    'UDH': fields.String(
        example=''
    ),
    'SMSCNumber': fields.String(
        example='+33698765432'
    ),
    'Class': fields.Integer(
        example='-1'
    ),
    'TextDecoded': fields.String(
        example='Hello this a my first SMS'
    ),
    'RecipientID': fields.String(
        example=''
    ),
    'Processed': fields.String(
        example='false'
    ),
    'Status': fields.Integer(
        example='0'
    )
})

inbox_items = server.api.model('inbox items', {
    'page': fields.Integer(
        example='1'
    ),
    'total_pages': fields.Integer(
        example='1'
    ),
    'results': fields.List(
        fields.Nested(inbox_item)
    )
})    