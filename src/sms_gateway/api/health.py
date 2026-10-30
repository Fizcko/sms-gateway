import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from sms_gateway.api.dependencies import DatabaseDep
from sms_gateway.schemas.health import HealthError, HealthOk
from sms_gateway.services.phone_status import read_phone_status

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Actuator"])


def _unhealthy(error: HealthError) -> JSONResponse:
    return JSONResponse(error.model_dump(exclude_none=True), 500)


@router.get(
    "/healthz",
    summary="Get system, database and phone status",
    response_model=HealthOk,
    responses={500: {"model": HealthError}},
)
def healthz(database: DatabaseDep) -> HealthOk | JSONResponse:
    """Healthy only if the gateway can really send: database up, gammu-smsd reporting."""
    try:
        with database.session() as session:
            session.execute(text("SELECT 1"))
            phone = read_phone_status(session)
    except SQLAlchemyError:
        logger.exception("Database health check failed")
        return _unhealthy(
            HealthError(database="disconnected", error="Unable to connect to database")
        )
    if phone is None:
        return _unhealthy(
            HealthError(
                database="connected",
                phone="disconnected",
                error="No recent status from gammu-smsd",
            )
        )
    return HealthOk(signal=phone.signal, network=phone.network)
