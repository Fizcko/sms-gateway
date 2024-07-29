from flask import request
from flask_restx import Resource, reqparse
from flask_jwt_extended import ( jwt_required )
from database.models import sentitems
from database.instance import get_session
from server.instance import server
from math import ceil
from models.senditems import senditems_item, senditems_items
from resources.decorators import ( required_bearerAuth, required_basicAuth )
from environment.instance import environment_config

api = server.api
ns = api.namespace('Sent Items', description='Sent Items operations', path='/')

pagination_arguments = reqparse.RequestParser()
pagination_arguments.add_argument('page', type=int, required=False, default=1, help='Page to display')
pagination_arguments.add_argument('per_page', type=int, required=False, default=50, help='Number of results by page')

@ns.route('/v1/sentitems')
class SendItems(Resource):

    @ns.doc(description='Get all SMS located in the send items')
    @api.doc(params={'before': {'description': 'Filter SMS send before a date', 'in': 'query', 'type': 'date'}})
    @api.doc(params={'after': {'description': 'Filter SMS send after a date', 'in': 'query', 'type': 'date'}})
    @api.doc(params={'destination': {'description': 'Filter SMS send from a number', 'in': 'query', 'type': 'string'}})
    @api.expect(pagination_arguments, validate=True)
    @required_bearerAuth(environment_config["require_bearer"])
    @required_basicAuth(environment_config["require_basic"])
    @api.response(200, 'Success', senditems_items)
    def get(self):
        '''   Get all SMS located in the send items'''
        before = request.args.get('before')
        after = request.args.get('after')
        destination = request.args.get('destination')
        limit = request.args.get('limit')
        per_page = int(request.args.get('per_page')) if request.args.get('per_page') else 50
        page = int(request.args.get('page')) if request.args.get('page') else 1

        with get_session() as session:
            query = session.query(sentitems)
            query = query.filter()

            if(before):
                query = query.filter(sentitems.ReceivingDateTime < before)
            if(after):
                query = query.filter(sentitems.ReceivingDateTime > after)
            if(destination):
                query = query.filter(sentitems.DestinationNumber == destination)
            total_records = query.count()
            total_pages = ceil(total_records/per_page)
            if(per_page):
                query = query.limit(per_page)
            if(page):
                query = query.offset((page-1)*per_page)

            records = query.all()
            results = []
            for record in records:
                results.append(record.as_json())

        return {
            'page': page,
            'total_pages': total_pages,
            'results': results
        }, 200

@ns.route('/v1/sentitems/<int:id>')
class SendItemsID(Resource):

    @ns.doc(params={'id': 'ID of a SMS to get'})
    @ns.doc(description='Get a SMS located in the send items by his ID')
    @required_bearerAuth(environment_config["require_bearer"])
    @required_basicAuth(environment_config["require_basic"])
    @api.response(200, 'Success', senditems_item)
    def get(self, id: int):
        '''   Get a SMS located in the send items by his ID'''
        with get_session() as session:
            sms = session.query(sentitems).filter_by(ID=id).first()
            if(sms):
                return sms.as_json(), 200
            else:
                return {'message': 'SMS not found'}, 404

    @ns.doc(params={'id': 'ID of a SMS to delete'})
    @ns.doc(description='Delete a SMS located in the send items')
    @ns.response(204, 'Success')
    @required_bearerAuth(environment_config["require_bearer"])
    @required_basicAuth(environment_config["require_basic"])
    def delete(self, id: int):
        '''   Delete a SMS located in the send items'''
        with get_session() as session:
            sms = session.query(sentitems).filter_by(ID=id).first()
            if(sms):
                session.delete(sms)

        return {'results': 'ok'}, 204
