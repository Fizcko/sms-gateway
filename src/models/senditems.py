from flask_restx import fields
from server.instance import server

senditems_item = server.api.model('senditems item', {
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
    'DeliveryDateTime': fields.DateTime(
        example=None
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
    'SMSCNumber': fields.String(
        example='+33612345678'
    ),
    'Class': fields.Integer(
        example='-1'
    ),
    'TextDecoded': fields.String(
        example='Hello this a my first SMS'
    ),
    'SenderID': fields.String(
        example=''
    ),
    'SequencePosition': fields.Integer(
        example='1'
    ),
    'Status': fields.String(
        example='SendingOKNoReport'
    ),
    'StatusError': fields.Integer(
        example='-1'
    ),
    'TPMR': fields.Integer(
        example='19'
    ),
    'RelativeValidity': fields.Integer(
        example='255'
    ),
    'CreatorID': fields.String(
        example='Gammu 1.40.0'
    ),
    'StatusCode': fields.Integer(
        example='-1'
    ),
})

senditems_items = server.api.model('senditems items', {
    'page': fields.Integer(
        example='1'
    ),
    'total_pages': fields.Integer(
        example='1'
    ),
    'results': fields.List(
        fields.Nested(senditems_item)
    )
})    
