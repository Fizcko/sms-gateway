from pydantic import BaseModel


class HealthOk(BaseModel):
    status: str = "healthy"
    database: str = "connected"
    phone: str = "connected"
    signal: int
    network: str | None


class HealthError(BaseModel):
    status: str = "unhealthy"
    database: str
    phone: str | None = None
    error: str
