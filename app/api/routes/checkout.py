from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_checkout_service, get_current_customer
from app.schemas.order import Order
from app.schemas.error import ErrorResponse
from app.services.checkout_service import CheckoutService

router = APIRouter(tags=["checkout"])


@router.post(
    "/checkout",
    response_model=Order,
    status_code=status.HTTP_201_CREATED,
    summary="Check out my cart",
    description=(
        "Places an order from the signed-in customer's active cart and returns it. First it checks that "
        "the cart can be ordered: the customer is active, the cart exists and is not empty, its restaurant exists and is open, every quantity is valid, and every item can "
        "still be ordered from the **current** menu. Nothing is written if a check fails. The lines and "
        "totals are calculated by the backend from the current menu with the same pricing as the cart; "
        "prices or totals sent by the client are ignored. The saved order keeps a snapshot of each "
        "item's name and price and of the delivery address, so later changes never alter it. Only after "
        "the order is saved is the cart closed; `GET /cart` then returns a new, empty cart."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "The cart is empty or holds an invalid quantity"},
        401: {"model": ErrorResponse, "description": "The token is missing, invalid or expired"},
        403: {"model": ErrorResponse, "description": "The customer account has been deactivated"},
        404: {"model": ErrorResponse, "description": "The cart's restaurant or one of its menu items no longer exists"},
        409: {
            "model": ErrorResponse,
            "description": "The cart's restaurant is closed, an item in the cart is now unavailable, removed "
            "from the menu or from another restaurant, or the cart has already been checked out",
        },
    },
)
def checkout(customer: dict = Depends(get_current_customer), service: CheckoutService = Depends(get_checkout_service)):
    return service.checkout(customer["id"])
