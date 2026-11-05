from fastapi.middleware.cors import CORSMiddleware
import json
import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.routes import menu, restaurants
from app.core.errors import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.schemas.error import ErrorResponse
from app.schemas.health import HealthResponse

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


# Services raise domain errors; this table is the one place they become HTTP status codes,
# so routes need no try/except. Subclasses (e.g. RestaurantNotFoundError) use their base's code.
DOMAIN_ERROR_STATUS = {
    BadRequestError: status.HTTP_400_BAD_REQUEST,
    ForbiddenError: status.HTTP_403_FORBIDDEN,
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
}


def domain_error(request: Request, exc: Exception) -> JSONResponse:
    status_code = next(code for error, code in DOMAIN_ERROR_STATUS.items() if isinstance(exc, error))
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})


for error_class in DOMAIN_ERROR_STATUS:
    app.add_exception_handler(error_class, domain_error)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns `{\"status\": \"ok\"}` while the API is running.",
)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


app.include_router(restaurants.router)
app.include_router(menu.router)
