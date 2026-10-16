from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Body of GET /health."""

    status: str
