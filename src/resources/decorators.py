from server.instance import server
from flask_jwt_extended import ( verify_jwt_in_request )
from flask_basicauth import BasicAuth

app = server.app
basic_auth = BasicAuth(app)

def required_bearerAuth(bearerAuth = True): 
    def decorator(fn):
        def decorated(*args,**kwargs): 
            if bearerAuth:
                verify_jwt_in_request()
            return fn(*args,**kwargs)
        return decorated   
    return decorator

def required_basicAuth(basicAuth = True): 
    def decorator(fn):
        def decorated(*args,**kwargs): 
            if basicAuth:
                if not basic_auth.authenticate():
                    return {'message': 'Basic authenfication fail', 'details': 'Wrong username or password.'}, 401
            return fn(*args,**kwargs)
        return decorated   
    return decorator
