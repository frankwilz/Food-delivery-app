import json
import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.routes import menu, restaurants
from app.schemas.error import ErrorResponse

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Food Delivery API",
    # Every endpoint reads a JSON data file, so any of them can fail with this storage error
    responses={500: {"model": ErrorResponse, "description": "The data file could not be read or written"}},
)


@app.exception_handler(OSError)
@app.exception_handler(json.JSONDecodeError)
def data_storage_error(request: Request, exc: Exception) -> JSONResponse:
    # A missing, unreadable or corrupt data file returns the same JSON error shape as every
    # other error, instead of a plain-text 500; the details go to the server log, not the client
    logger.exception("Data storage error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Data storage error"},
    )


@app.get("/health", summary="Health check", description="Returns `{\"status\": \"ok\"}` while the API is running.")
def health():
    return {"status": "ok"}


app.include_router(restaurants.router)
app.include_router(menu.router)
