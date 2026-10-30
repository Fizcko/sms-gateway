"""Error responses: always JSON with a `message`, never internal details."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

logger = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        message: str,
        details: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.details = details
        self.headers = headers


async def _api_error(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, ApiError)
    content = {"message": error.message}
    if error.details is not None:
        content["details"] = error.details
    return JSONResponse(content, error.status_code, headers=error.headers)


async def _validation_error(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, RequestValidationError)
    errors = {".".join(str(part) for part in item["loc"]): item["msg"] for item in error.errors()}
    return JSONResponse({"message": "Input payload validation failed", "errors": errors}, 400)


async def _http_error(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, HTTPException)
    if error.status_code == 404:
        content = {"message": "Page not found", "details": str(error.detail)}
    else:
        content = {"message": str(error.detail)}
    return JSONResponse(content, error.status_code, headers=error.headers)


async def _unexpected_error(request: Request, error: Exception) -> JSONResponse:
    """The stack trace goes to the logs only: it can reveal internals to clients."""
    logger.error(
        "Unhandled error on %s %s",
        request.method,
        request.url.path,
        exc_info=(type(error), error, error.__traceback__),
    )
    return JSONResponse(
        {"message": "Internal error", "details": "An unexpected error occurred."}, 500
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, _api_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(HTTPException, _http_error)
    app.add_exception_handler(Exception, _unexpected_error)
