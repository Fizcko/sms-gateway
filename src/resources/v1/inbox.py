from flask import request
from flask_restplus import Resource, reqparse
from flask_jwt_extended import ( jwt_required )
from database.models import inbox
from database.instance import db_session
from server.instance import server
from math import ceil
from models.inbox import inbox_item, inbox_items

api = server.api
ns = api.namespace('Inbox', description='Inbox operations', path='/')

pagination_arguments = reqparse.RequestParser()
pagination_arguments.add_argument('page', type=int, required=False, default=1, help='Page to display')
pagination_arguments.add_argument('per_page', type=int, required=False, default=50, help='Number of results by page')

@ns.route('/v1/inbox')
class Inbox(Resource):

    @ns.doc(description='Get all SMS located in the inbox')
    @api.doc(params={'before': {'description': 'Filter SMS received before a date', 'in': 'query', 'type': 'date'}})
    @api.doc(params={'after': {'description': 'Filter SMS received after a date', 'in': 'query', 'type': 'date'}})
    @api.doc(params={'sender': {'description': 'Filter SMS received from a number', 'in': 'query', 'type': 'string'}})
    @api.expect(pagination_arguments, validate=True)
    @api.doc(security='Bearer')
    @jwt_required
    @api.response(200, 'Success', inbox_items)
    def get(self):
        '''   Get all SMS located in the inbox'''
        before = request.args.get('before')
        after = request.args.get('after')
        sender = request.args.get('sender')
        limit = request.args.get('limit')
        per_page = int(request.args.get('per_page')) if request.args.get('per_page') else 50
        page = int(request.args.get('page')) if request.args.get('page') else 1

        query = db_session.query(inbox)
        query = query.filter()

        if(before):
            query = query.filter(inbox.ReceivingDateTime < before)
        if(after):
            query = query.filter(inbox.ReceivingDateTime > after)
        if(sender):
            query = query.filter(inbox.SenderNumber == sender)
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

@ns.route('/v1/inbox/<int:id>')
class InboxID(Resource):

    @ns.doc(params={'id': 'ID of a SMS to get'})
    @ns.doc(description='Get a SMS located in the inbox by his ID')
    @api.doc(security='Bearer')
    @jwt_required
    @api.response(200, 'Success', inbox_item)
    def get(self, id: int):
        '''   Get a SMS located in the inbox by his ID'''
        sms = inbox.query.filter_by(ID=id).first()
        if(sms):
            return sms.as_json(), 200
        else:
            return {'message': 'SMS not found'}, 404

    @ns.doc(params={'id': 'ID of a SMS to delete'})
    @ns.doc(description='Delete a SMS located in the inbox')
    @ns.response(204, 'Success')
    @api.doc(security='Bearer')
    @jwt_required
    def delete(self, id: int):
        '''   Delete a SMS located in the inbox'''
        sms = inbox.query.filter_by(ID=id).first()
        if(sms):
            db_session.delete(sms)
            db_session.commit()
        return {'results': 'ok'}, 204