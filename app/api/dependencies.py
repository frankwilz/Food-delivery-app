"""How every route gets its services, and who is signed in.

Each repository is built from its data file path in one function below, and each service is built
from repositories and other services through FastAPI dependencies. Routes ask for a service with
`Depends(get_..._service)` and never open a data file or build a service themselves.

File paths are read from `app.core.config` when a request arrives, not when this module is imported,
so tests (and `DATA_DIR`) only need to change them in one place.
"""

from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core import config
from app.repositories.cart_repository import CartRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.menu_item_repository import MenuItemRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.error import ErrorResponse
from app.services.auth_service import AuthService, NotAuthenticatedError, RoleRequiredError
from app.services.cart_service import CartService
from app.services.checkout_service import CheckoutService
from app.services.customer_service import CustomerService
from app.services.menu_service import MenuService
from app.services.order_service import OrderService
from app.services.restaurant_service import RestaurantService

# --- Repositories: the only place a data file path is turned into a repository ---


def get_customer_repository() -> CustomerRepository:
    return CustomerRepository(config.CUSTOMERS_FILE)


def get_restaurant_repository() -> RestaurantRepository:
    return RestaurantRepository(config.RESTAURANTS_FILE)


def get_menu_item_repository() -> MenuItemRepository:
    return MenuItemRepository(config.MENU_ITEMS_FILE)


def get_cart_repository() -> CartRepository:
    return CartRepository(config.CARTS_FILE)


def get_order_repository() -> OrderRepository:
    return OrderRepository(config.ORDERS_FILE)


# --- Services: built from the repositories and services they need ---


def get_customer_service(repository: CustomerRepository = Depends(get_customer_repository)) -> CustomerService:
    return CustomerService(repository)


def get_restaurant_service(repository: RestaurantRepository = Depends(get_restaurant_repository)) -> RestaurantService:
    return RestaurantService(repository)


def get_menu_service(
    menu_items: MenuItemRepository = Depends(get_menu_item_repository),
    restaurants: RestaurantRepository = Depends(get_restaurant_repository),
) -> MenuService:
    return MenuService(menu_items, restaurants)


def get_cart_service(
    carts: CartRepository = Depends(get_cart_repository),
    menu_service: MenuService = Depends(get_menu_service),
    customer_service: CustomerService = Depends(get_customer_service),
) -> CartService:
    return CartService(carts, menu_service, customer_service)


def get_checkout_service(
    customer_service: CustomerService = Depends(get_customer_service),
    carts: CartRepository = Depends(get_cart_repository),
    restaurants: RestaurantRepository = Depends(get_restaurant_repository),
    cart_service: CartService = Depends(get_cart_service),
    menu_service: MenuService = Depends(get_menu_service),
    orders: OrderRepository = Depends(get_order_repository),
) -> CheckoutService:
    return CheckoutService(customer_service, carts, restaurants, cart_service, menu_service, orders)


def get_order_service(orders: OrderRepository = Depends(get_order_repository)) -> OrderService:
    return OrderService(orders)


# Declares the "Bearer token" scheme in /docs, which adds the Authorize button.
# auto_error=False lets a missing header reach get_current_customer, so every 401
# has the same JSON shape as the other errors.
bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Paste the `access_token` returned by `POST /auth/login`.",
)


def get_auth_service(repository: CustomerRepository = Depends(get_customer_repository)) -> AuthService:
    return AuthService(repository)


# --- Who is signed in ---


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
