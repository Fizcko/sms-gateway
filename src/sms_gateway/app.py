"""FastAPI application factory."""

import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import datetime

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from sms_gateway.api import health
from sms_gateway.api.errors import register_error_handlers
from sms_gateway.api.security import LoginLimiter, auth_dependencies
from sms_gateway.api.v1 import auth, inbox, outbox, send, sentitems
from sms_gateway.db.session import Database
from sms_gateway.services.background import BackgroundWorker
from sms_gateway.services.sms_sender import GammuSmsSender, SmsSender
from sms_gateway.services.webhook import WebhookWorker
from sms_gateway.settings import AuthMode, Settings

logger = logging.getLogger("sms_gateway.access")

_SWAGGER_ASSETS = "/swaggerui"
# Installed by the Dockerfile, see the swagger-ui stage.
SWAGGER_ASSETS_DIR = "/usr/local/share/swagger-ui"
_NOT_LOGGED_PREFIXES = ("/favicon.ico", _SWAGGER_ASSETS)


async def _log_request(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    started = time.perf_counter()
    response = await call_next(request)
    if not request.url.path.startswith(_NOT_LOGGED_PREFIXES):
        client = request.client.host if request.client else None
        logger.info(
            "%s:%s:%s:%s:%.6f:%s:%s:%s",
            datetime.now().isoformat(),
            request.method,
            request.url.path,
            response.status_code,
            time.perf_counter() - started,
            request.headers.get("X-Forwarded-For", client),
            request.url.hostname,
            dict(request.query_params),
        )
    return response


def create_app(settings: Settings | None = None, sms_sender: SmsSender | None = None) -> FastAPI:
    resolved = settings or Settings()
    if resolved.auth_mode is AuthMode.NONE:
        logger.warning("API authentication is disabled (API_SECURITY=%s)", resolved.api_security)

    database = Database(resolved)
    http_client = httpx.Client()
    webhook = WebhookWorker(resolved, database, http_client) if resolved.webhook_url else None
    background = BackgroundWorker(database, webhook, resolved.retention_days)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        background.start()
        yield
        background.stop()
        http_client.close()
        database.engine.dispose()

    # The docs are served from local assets: gateways may have no internet access.
    app = FastAPI(
        title="SMS Gateway",
        description="This REST API allow you to send and receive SMS",
        version=resolved.app_version,
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.settings = resolved
    app.state.database = database
    app.state.background = background
    app.state.login_limiter = LoginLimiter()
    app.state.sms_sender = sms_sender or GammuSmsSender(resolved.gammu_smsd_conf)

    register_error_handlers(app)
    app.middleware("http")(_log_request)
    app.mount(_SWAGGER_ASSETS, StaticFiles(directory=SWAGGER_ASSETS_DIR), name="swaggerui")

    @app.get("/", include_in_schema=False)
    def swagger_ui() -> HTMLResponse:
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title=app.title,
            swagger_js_url=f"{_SWAGGER_ASSETS}/swagger-ui-bundle.js",
            swagger_css_url=f"{_SWAGGER_ASSETS}/swagger-ui.css",
            swagger_favicon_url=f"{_SWAGGER_ASSETS}/favicon-32x32.png",
        )

    app.include_router(health.router)
    app.include_router(auth.router)
    protection = auth_dependencies(resolved.auth_mode)
    for module in (send, inbox, outbox, sentitems):
        app.include_router(module.router, dependencies=protection)
    return app
