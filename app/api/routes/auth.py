from fastapi import APIRouter, Depends

from app.api.dependencies import get_auth_service
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.error import ErrorResponse
from app.services.auth_service import AuthService

router = APIRouter()

INVALID_CREDENTIALS = {401: {"model": ErrorResponse, "description": "The email or password is incorrect"}}


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    summary="Log in",
    description=(
        "Checks a customer's email (case-insensitive) and password and returns a signed token. "
        "Send it on later requests as `Authorization: Bearer <access_token>`, or paste it into the "
        "**Authorize** button in `/docs`. A wrong email and a wrong password give the same 401."
    ),
    responses=INVALID_CREDENTIALS,
)
def login(credentials: LoginRequest, service: AuthService = Depends(get_auth_service)):
    return TokenResponse(access_token=service.login(credentials.email, credentials.password))
