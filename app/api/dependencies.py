"""Dependencies shared by more than one router."""

from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import CUSTOMERS_FILE
from app.repositories.customer_repository import CustomerRepository
from app.schemas.error import ErrorResponse
from app.services.auth_service import AuthService, NotAuthenticatedError, RoleRequiredError

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
    """Return the active customer identified by `Authorization: Bearer <token>`.

    Raises a 401 if the header or token is missing, invalid or expired, and a 403 if the
    account has been deactivated.

    Add `customer: dict = Depends(get_current_customer)` to any route that needs a signed-in customer.
    """
    if credentials is None:
        raise NotAuthenticatedError()
    return service.get_customer_for_token(credentials.credentials)


def require_role(role: str) -> Callable[..., dict]:
    """Build a dependency that only lets through a signed-in, active account with this role.

    401 without a valid token, 403 if the account is deactivated or has another role. Use it as
    `dependencies=[Depends(require_manager)]` on a route, or as a parameter to get the account.
    """

    def check_role(customer: dict = Depends(get_current_customer)) -> dict:
        if customer["role"] != role:
            raise RoleRequiredError(role)
        return customer

    return check_role


# Created once, so every manager-only route shares the same dependency
require_manager = require_role("manager")

# The extra error responses of a manager-only route, for its `responses=` in /docs
MANAGER_ONLY = {
    401: {"model": ErrorResponse, "description": "The token is missing, invalid or expired"},
    403: {"model": ErrorResponse, "description": "The account is not a manager, or has been deactivated"},
}
