from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_customer
from app.api.routes import cart as cart_route
from app.schemas.error import ErrorResponse
from app.schemas.order import Order
from app.services.order_service import OrderService

router = APIRouter(tags=["orders"])

SIGNED_IN = {
    401: {"model": ErrorResponse, "description": "The token is missing, invalid or expired"},
    403: {"model": ErrorResponse, "description": "The customer account has been deactivated"},
}


def get_order_service() -> OrderService:
    # Built from the cart route's builders, so it reads the same orders file that checkout writes
    return OrderService(cart_route.build_order_repository())


@router.get(
    "/orders",
    response_model=list[Order],
    summary="List my orders",
    description="Returns the signed-in customer's orders, newest first. Other customers' orders are never included.",
    responses=SIGNED_IN,
)
def list_orders(customer: dict = Depends(get_current_customer), service: OrderService = Depends(get_order_service)):
    return service.list_for_customer(customer["id"])


@router.get(
    "/orders/{order_id}",
    response_model=Order,
    summary="Get one of my orders",
    description=(
        "Returns one of the signed-in customer's orders. An order that does not exist and an order that "
        "belongs to another customer both return 404. Item names, prices and the delivery address are as "
        "they were at checkout."
    ),
    responses={**SIGNED_IN, 404: {"model": ErrorResponse, "description": "No such order for this customer"}},
)
def get_order(
    order_id: int,
    customer: dict = Depends(get_current_customer),
    service: OrderService = Depends(get_order_service),
):
    return service.get_for_customer(customer["id"], order_id)
