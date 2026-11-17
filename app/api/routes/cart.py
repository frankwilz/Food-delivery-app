from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_customer
from app.core.config import CARTS_FILE, CUSTOMERS_FILE, MENU_ITEMS_FILE, ORDERS_FILE, RESTAURANTS_FILE
from app.repositories.cart_repository import CartRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.menu_item_repository import MenuItemRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.cart import CartItemAdd, CartItemUpdate, CartResponse
from app.schemas.error import ErrorResponse
from app.services.cart_service import CartService
from app.services.customer_service import CustomerService
from app.services.menu_service import MenuService

router = APIRouter(tags=["cart"])

NOT_SIGNED_IN = {401: {"model": ErrorResponse, "description": "The token is missing, invalid or expired"}}
DEACTIVATED = {403: {"model": ErrorResponse, "description": "The customer account has been deactivated"}}
NOT_IN_CART = {404: {"model": ErrorResponse, "description": "The menu item is not in the cart"}}
SIGNED_IN = {**NOT_SIGNED_IN, **DEACTIVATED}


# The checkout route builds its services from these too, so tests only patch the file paths here
def build_customer_service() -> CustomerService:
    return CustomerService(CustomerRepository(CUSTOMERS_FILE))


def build_menu_service() -> MenuService:
    return MenuService(MenuItemRepository(MENU_ITEMS_FILE), RestaurantRepository(RESTAURANTS_FILE))


def build_cart_repository() -> CartRepository:
    return CartRepository(CARTS_FILE)


def build_restaurant_repository() -> RestaurantRepository:
    return RestaurantRepository(RESTAURANTS_FILE)


def build_order_repository() -> OrderRepository:
    return OrderRepository(ORDERS_FILE)


def get_cart_service() -> CartService:
    return CartService(build_cart_repository(), build_menu_service(), build_customer_service())


@router.get(
    "/cart",
    response_model=CartResponse,
    summary="Get my cart",
    description=(
        "Returns the signed-in customer's active cart, creating an empty one the first time. A customer "
        "never has more than one active cart. Line totals, `subtotal` and `total` are calculated by the "
        "backend from the **current** menu prices; `total` equals `subtotal` (no delivery fee or tax yet)."
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


@router.patch(
    "/cart/items/{menu_item_id}",
    response_model=CartResponse,
    summary="Change an item's quantity",
    description="Sets the quantity of an item already in the cart. Returns the updated cart.",
    responses={**SIGNED_IN, **NOT_IN_CART},
)
def update_cart_item(
    menu_item_id: int,
    body: CartItemUpdate,
    customer: dict = Depends(get_current_customer),
    service: CartService = Depends(get_cart_service),
):
    return service.update_quantity(customer["id"], menu_item_id, body.quantity)


@router.delete(
    "/cart/items/{menu_item_id}",
    response_model=CartResponse,
    summary="Remove an item from my cart",
    description=(
        "Removes one item from the cart. When the last item is removed the cart is no longer tied to a "
        "restaurant. Returns the updated cart."
    ),
    responses={**SIGNED_IN, **NOT_IN_CART},
)
def remove_cart_item(
    menu_item_id: int,
    customer: dict = Depends(get_current_customer),
    service: CartService = Depends(get_cart_service),
):
    return service.remove_item(customer["id"], menu_item_id)


@router.delete(
    "/cart",
    response_model=CartResponse,
    summary="Empty my cart",
    description="Removes every item from the cart and unties it from its restaurant. Returns the empty cart.",
    responses=SIGNED_IN,
)
def clear_cart(customer: dict = Depends(get_current_customer), service: CartService = Depends(get_cart_service)):
    return service.clear_for_customer(customer["id"])
