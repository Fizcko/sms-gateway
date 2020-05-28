from flask import request
from flask_restplus import Resource, reqparse
from flask_jwt_extended import ( jwt_required )
from database.models import outbox
from database.instance import db_session
from server.instance import server
from math import ceil
from models.outbox import outbox_item, outbox_items

api = server.api
ns = api.namespace('Outbox', description='Outbox operations', path='/')

pagination_arguments = reqparse.RequestParser()
pagination_arguments.add_argument('page', type=int, required=False, default=1, help='Page to display')
pagination_arguments.add_argument('per_page', type=int, required=False, default=50, help='Number of results by page')

@ns.route('/v1/outbox')
class Outbox(Resource):

    @ns.doc(description='Get all SMS located in the outbox')
    @api.doc(params={'before': {'description': 'Filter SMS send before a date', 'in': 'query', 'type': 'date'}})
    @api.doc(params={'after': {'description': 'Filter SMS send after a date', 'in': 'query', 'type': 'date'}})
    @api.doc(params={'destination': {'description': 'Filter SMS send to a number', 'in': 'query', 'type': 'string'}})
    @api.expect(pagination_arguments, validate=True)
    @api.doc(security='Bearer')
    @jwt_required
    @api.response(200, 'Success', outbox_items)
    def get(self):
        '''   Get all SMS located in the outbox'''
        before = request.args.get('before')
        after = request.args.get('after')
        destination = request.args.get('destination')
        limit = request.args.get('limit')
        per_page = int(request.args.get('per_page')) if request.args.get('per_page') else 50
        page = int(request.args.get('page')) if request.args.get('page') else 1

        query = db_session.query(outbox)
        query = query.filter()

        if(destination):
            query = query.filter(outbox.SendingDateTime < before)
        if(destination):
            query = query.filter(outbox.SendingDateTime > after)
        if(destination):
            query = query.filter(outbox.DestinationNumber == destination)
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

@ns.route('/v1/outbox/<int:id>')
class OutboxID(Resource):

    @ns.doc(params={'id': 'ID of a SMS to get'})
    @ns.doc(description='Get a SMS located in the outbox by his ID')
    @api.doc(security='Bearer')
    @jwt_required
    @api.response(200, 'Success', outbox_item)
    def get(self, id: int):
        '''   Get a SMS located in the outbox by his ID'''
        sms = outbox.query.filter_by(ID=id).first()
        if(sms):
            return sms.as_json(), 200
        else:
            return {'message': 'SMS not found'}, 404

    @ns.doc(params={'id': 'ID of a SMS to delete'})
    @ns.doc(description='Delete a SMS located in the outbox')
    @ns.response(204, 'Success')
    @api.doc(security='Bearer')
    @jwt_required
    def delete(self, id: int):
        '''   Delete a SMS located in the outbox'''
        sms = outbox.query.filter_by(ID=id).first()
        if(sms):
            db_session.delete(sms)
            db_session.commit()
        return {'results': 'ok'}, 204
