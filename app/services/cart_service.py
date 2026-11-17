from app.core.errors import BadRequestError, ConflictError, NotFoundError
from app.repositories.cart_repository import CartRepository
from app.schemas.cart import MAX_QUANTITY, CartItemAdd
from app.services.customer_service import CustomerService
from app.services.menu_service import MenuService


class DifferentRestaurantError(ConflictError):
    def __init__(self, item: dict, cart_restaurant_id: int):
        super().__init__(
            f"Menu item {item['id']} ({item['name']}) is from restaurant {item['restaurant_id']}, but the cart "
            f"has items from restaurant {cart_restaurant_id}. Clear the cart to order from another restaurant."
        )


class ItemNotInCartError(NotFoundError):
    def __init__(self, menu_item_id: int):
        super().__init__(f"Menu item {menu_item_id} is not in the cart")


class QuantityLimitError(BadRequestError):
    def __init__(self, menu_item_id: int, quantity: int):
        super().__init__(
            f"The cart would hold {quantity} of menu item {menu_item_id}; the most allowed is {MAX_QUANTITY}"
        )


class CartService:
    """Business rules for the shopping cart. Routes call this; this calls the repositories.

    Every public method takes the customer id and first checks the customer is active
    (`CustomerService.get_active_customer`), so a deactivated customer gets a 403.
    """

    def __init__(
        self,
        cart_repository: CartRepository,
        menu_service: MenuService,
        customer_service: CustomerService,
    ):
        self.cart_repository = cart_repository
        self.menu_service = menu_service
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

    # --- 3.3 Add items ---

    def add_item(self, customer_id: int, data: CartItemAdd) -> dict:
        cart = self.get_or_create_active_cart(customer_id)
        # 404 if the item does not exist, 409 if it is deactivated or unavailable
        item = self.menu_service.get_orderable_item(data.menu_item_id)
        if cart["items"] and cart["restaurant_id"] != item["restaurant_id"]:
            raise DifferentRestaurantError(item, cart["restaurant_id"])

        items = [dict(line) for line in cart["items"]]
        existing = next((line for line in items if line["menu_item_id"] == item["id"]), None)
        if existing is None:
            items.append({"menu_item_id": item["id"], "quantity": data.quantity})
        else:
            new_quantity = existing["quantity"] + data.quantity
            if new_quantity > MAX_QUANTITY:
                raise QuantityLimitError(item["id"], new_quantity)
            existing["quantity"] = new_quantity

        # The first item decides which restaurant the cart belongs to
        return self.cart_repository.update(cart["id"], {"items": items, "restaurant_id": item["restaurant_id"]})

    # --- 3.4 Update quantities ---

    def update_quantity(self, customer_id: int, menu_item_id: int, quantity: int) -> dict:
        cart = self.get_or_create_active_cart(customer_id)
        items = [dict(line) for line in cart["items"]]
        line = next((line for line in items if line["menu_item_id"] == menu_item_id), None)
        if line is None:
            raise ItemNotInCartError(menu_item_id)
        line["quantity"] = quantity
        return self.cart_repository.update(cart["id"], {"items": items})

    # --- 3.5 Remove items and clear ---

    def remove_item(self, customer_id: int, menu_item_id: int) -> dict:
        cart = self.get_or_create_active_cart(customer_id)
        items = [line for line in cart["items"] if line["menu_item_id"] != menu_item_id]
        if len(items) == len(cart["items"]):
            raise ItemNotInCartError(menu_item_id)
        changes = {"items": items}
        if not items:
            # An empty cart is no longer tied to a restaurant
            changes["restaurant_id"] = None
        return self.cart_repository.update(cart["id"], changes)

    def clear_for_customer(self, customer_id: int) -> dict:
        cart = self.get_or_create_active_cart(customer_id)
        return self.clear(cart["id"])

    def clear(self, cart_id: int) -> dict:
        """Empty a cart and untie it from its restaurant. Checkout calls this after saving an order (4.5)."""
        cart = self.cart_repository.update(cart_id, {"items": [], "restaurant_id": None})
        if cart is None:
            raise NotFoundError(f"Cart {cart_id} not found")
        return cart
