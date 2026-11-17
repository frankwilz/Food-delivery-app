from app.repositories.cart_repository import CartRepository
from app.services.customer_service import CustomerService


class CartService:
    """Business rules for the shopping cart. Routes call this; this calls the repositories.

    Every public method takes the customer id and first checks the customer is active
    (`CustomerService.get_active_customer`), so a deactivated customer gets a 403.
    """

    def __init__(self, cart_repository: CartRepository, customer_service: CustomerService):
        self.cart_repository = cart_repository
        self.customer_service = customer_service

    # --- 3.2 Create/retrieve the active cart ---

    def get_or_create_active_cart(self, customer_id: int) -> dict:
        """Return the customer's stored active cart, creating an empty one if they have none."""
        self.customer_service.get_active_customer(customer_id)
        cart = self.cart_repository.get_active_for_customer(customer_id)
        if cart is None:
            # Only created when none exists, so a customer never has two active carts
            cart = self.cart_repository.create(
                {"customer_id": customer_id, "restaurant_id": None, "items": [], "status": "active"}
            )
        return cart

    def get_cart(self, customer_id: int) -> dict:
        return self.get_or_create_active_cart(customer_id)
