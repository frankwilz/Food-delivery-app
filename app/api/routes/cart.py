from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_customer
from app.core.config import CARTS_FILE, CUSTOMERS_FILE
from app.repositories.cart_repository import CartRepository
from app.repositories.customer_repository import CustomerRepository
from app.schemas.cart import CartResponse
from app.schemas.error import ErrorResponse
from app.services.cart_service import CartService
from app.services.customer_service import CustomerService

router = APIRouter(tags=["cart"])

NOT_SIGNED_IN = {401: {"model": ErrorResponse, "description": "The token is missing, invalid or expired"}}
DEACTIVATED = {403: {"model": ErrorResponse, "description": "The customer account has been deactivated"}}
SIGNED_IN = {**NOT_SIGNED_IN, **DEACTIVATED}


def build_customer_service() -> CustomerService:
    return CustomerService(CustomerRepository(CUSTOMERS_FILE))


def build_cart_repository() -> CartRepository:
    return CartRepository(CARTS_FILE)


def get_cart_service() -> CartService:
    return CartService(build_cart_repository(), build_customer_service())


@router.get(
    "/cart",
    response_model=CartResponse,
    summary="Get my cart",
    description=(
        "Returns the signed-in customer's active cart, creating an empty one the first time. A customer "
        "never has more than one active cart."
    ),
    responses=SIGNED_IN,
)
def get_cart(customer: dict = Depends(get_current_customer), service: CartService = Depends(get_cart_service)):
    return service.get_cart(customer["id"])
