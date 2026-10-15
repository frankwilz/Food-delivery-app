from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Body of every error returned by the API, e.g. {"detail": "Restaurant 9 not found"}."""

    detail: str
