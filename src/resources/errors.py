from server.instance import server

app = server.app
jwt = server.jwt

@app.errorhandler
def default_error_handler(error):
    return {"message": "Internal error",'details': str(error)}, 500

@app.errorhandler(Exception)
def default_exception_handler(error):
    return {"message": "Internal error",'details': str(error)}, 500

@app.errorhandler(404)
def resource_not_found(err):
    return {"message": "Page not found",'details': str(err)}, 404
