from app.core.errors import NotFoundError
from app.repositories.order_repository import OrderRepository


class OrderNotFoundError(NotFoundError):
    def __init__(self, order_id: int):
        super().__init__(f"Order {order_id} not found")


class OrderService:
    """Reading orders. Orders are created only by `CheckoutService.checkout`."""

    def __init__(self, order_repository: OrderRepository):
        self.order_repository = order_repository

    def list_for_customer(self, customer_id: int) -> list[dict]:
        """The customer's orders, newest first."""
        orders = self.order_repository.get_by_customer(customer_id)
        # created_at is an ISO-8601 UTC string, so it sorts by time; the id breaks ties
        return sorted(orders, key=lambda order: (order["created_at"], order["id"]), reverse=True)

    def get_for_customer(self, customer_id: int, order_id: int) -> dict:
        """One of the customer's orders. Another customer's order is reported as not found,
        so the response does not reveal which order ids exist."""
        order = self.order_repository.get_by_id(order_id)
        if order is None or order["customer_id"] != customer_id:
            raise OrderNotFoundError(order_id)
        return order
