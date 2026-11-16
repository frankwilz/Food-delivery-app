"""Dependencies shared by more than one router."""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import CUSTOMERS_FILE
from app.repositories.customer_repository import CustomerRepository
from app.services.auth_service import AuthService, NotAuthenticatedError

# Declares the "Bearer token" scheme in /docs, which adds the Authorize button.
# auto_error=False lets a missing header reach get_current_customer, so every 401
# has the same JSON shape as the other errors.
bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Paste the `access_token` returned by `POST /auth/login`.",
)


def get_auth_service() -> AuthService:
    return AuthService(CustomerRepository(CUSTOMERS_FILE))


def get_current_customer(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    service: AuthService = Depends(get_auth_service),
) -> dict:
    """Return the customer identified by `Authorization: Bearer <token>`, or raise a 401.

    Add `customer: dict = Depends(get_current_customer)` to any route that needs a signed-in customer.
    """
    if credentials is None:
        raise NotAuthenticatedError()
    return service.get_customer_for_token(credentials.credentials)
