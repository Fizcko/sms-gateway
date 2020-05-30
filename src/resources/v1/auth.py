from flask import request
from flask_restplus import Resource
from flask_jwt_extended import (create_access_token, get_jwt_identity, jwt_required)
import os

from server.instance import server
from models.auth import login_post, token_response

app, api = server.app, server.api
ns = api.namespace('Authentication', description='Authentication operations', path='/')

@ns.route('/v1/login')
class login(Resource):

    @ns.expect(login_post, validate=True)
    @ns.doc(description='Get a token for requests')
    @api.response(200, 'Success', token_response)
    def post(self):
        '''   Get a token for requests'''
        json_data = request.json
        username = json_data["username"]
        password = json_data["password"]
        expected_username = os.environ.get("API_USERNAME", "admin")
        expected_password = os.environ.get("API_PASSWORD", "admin")

        if username != expected_username or password != expected_password:
            return {"message": "Bad username or password"}, 401

        # Identity can be any data that is json serializable
        access_token = create_access_token(identity=username)
        return {'access_token': access_token}, 200

@ns.route('/v1/refresh')
class refresh(Resource):

    @ns.doc(description='Get a new token for requests')
    @api.response(200, 'Success', token_response)
    @api.doc(security='Bearer')
    @jwt_required
    def get(self):
        '''   Get a token for requests'''
        current_user = get_jwt_identity()
        access_token = create_access_token(identity=current_user)
        return {'access_token': access_token}, 200
