from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_customer
from app.core.config import CARTS_FILE, CUSTOMERS_FILE, MENU_ITEMS_FILE, RESTAURANTS_FILE
from app.repositories.cart_repository import CartRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.menu_item_repository import MenuItemRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.cart import CartItemAdd, CartResponse
from app.schemas.error import ErrorResponse
from app.services.cart_service import CartService
from app.services.customer_service import CustomerService
from app.services.menu_service import MenuService

router = APIRouter(tags=["cart"])

NOT_SIGNED_IN = {401: {"model": ErrorResponse, "description": "The token is missing, invalid or expired"}}
DEACTIVATED = {403: {"model": ErrorResponse, "description": "The customer account has been deactivated"}}
SIGNED_IN = {**NOT_SIGNED_IN, **DEACTIVATED}


def build_customer_service() -> CustomerService:
    return CustomerService(CustomerRepository(CUSTOMERS_FILE))


def build_menu_service() -> MenuService:
    return MenuService(MenuItemRepository(MENU_ITEMS_FILE), RestaurantRepository(RESTAURANTS_FILE))


def build_cart_repository() -> CartRepository:
    return CartRepository(CARTS_FILE)


def get_cart_service() -> CartService:
    return CartService(build_cart_repository(), build_menu_service(), build_customer_service())


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


@router.post(
    "/cart/items",
    response_model=CartResponse,
    summary="Add an item to my cart",
    description=(
        "Adds a menu item to the cart. Adding an item that is already in the cart increases its quantity. "
        "The first item decides the cart's restaurant; items from another restaurant are refused until the "
        "cart is emptied. Unavailable or removed items are refused. Returns the updated cart."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "The combined quantity would exceed the maximum"},
        **SIGNED_IN,
        404: {"model": ErrorResponse, "description": "The menu item does not exist"},
        409: {
            "model": ErrorResponse,
            "description": "The item is from a different restaurant, unavailable or removed from the menu",
        },
    },
)
def add_cart_item(
    body: CartItemAdd,
    customer: dict = Depends(get_current_customer),
    service: CartService = Depends(get_cart_service),
):
    return service.add_item(customer["id"], body)
