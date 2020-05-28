from server.instance import server

import datetime
import time

from flask import g, request

app = server.app

@app.before_request
def start_timer():
    g.start = time.time()

@app.after_request
def log_request(response):

    if (
        request.path == "/favicon.ico"
        or request.path.startswith("/swaggerui")
    ):
        return response

    now = time.time()
    duration = round(now - g.start, 6)
    timestamp = datetime.datetime.now().isoformat()

    ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)

    host = request.host.split(":", 1)[0]
    params = dict(request.args)

    output = "{}:{}:{}:{}:{}:{}:{}:{}".format(
        timestamp,
        request.method,
        request.path,
        response.status_code,
        duration,
        ip_address,
        host,
        params
    )

    app.logger.info(output)

    return response