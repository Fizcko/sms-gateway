from waitress import serve
from flask import Flask
from flask_restplus import Api, Resource, fields
from flask_jwt_extended import (JWTManager)

import logging
import datetime

from environment.instance import environment_config
from environment.instance import jwt_config
from environment.instance import database_config
from database.instance import init_db

class Server(object):
    
    def __init__(self):
        
        self.app = Flask(__name__)
        self.app.name = "backend"

        # Swagger UI
        self.app.config['SWAGGER_UI_DOC_EXPANSION'] = 'list'

        # Exceptions are re-raised rather than being handled by the app’s error handlers.
        self.app.config['PROPAGATE_EXCEPTIONS'] = True

        # flask_jwt_extended
        self.app.config['JWT_SECRET_KEY'] = jwt_config["secret"]
        self.app.config['JWT_ALGORITHM'] = jwt_config["algorithm"]
        ## How long (in seconds) an access token should live before it expires
        self.app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(seconds=jwt_config["token_expires"])
        # The key of the error message in a JSON error response
        self.app.config['JWT_ERROR_MESSAGE_KEY'] = "message"

        authorizations = {
            'Bearer': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'Authorization',
                'description': "Type in the *'Value'* input box below: **'Bearer XXX'**, where XXX is the token"
            }
        }

        self.api = Api(self.app, 
            version='1.0', 
            title='SMS Gateway',
            description='This REST API allow you to send and receive SMS', 
            doc = environment_config["swagger-url"],
            authorizations=authorizations
        )
        
        self.jwt = JWTManager(self.app)

    def run(self):
        
        init_db()
        
        logger = logging.getLogger('waitress')
        logger.setLevel(logging.INFO)
        logger = logging.getLogger('backend')
        logger.setLevel(logging.INFO)

        serve(
            self.app,
            host=environment_config["ip"],
            port=environment_config["port"]
        )

server = Server()
