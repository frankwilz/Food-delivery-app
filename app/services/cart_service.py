from app.core.errors import BadRequestError, ConflictError, NotFoundError
from app.repositories.cart_repository import CartRepository
from app.schemas.cart import MAX_QUANTITY, CartItemAdd
from app.services.customer_service import CustomerService
from app.services.menu_service import MenuItemNotOrderableError, MenuService
from app.services.pricing import price_lines


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
        return self.priced(self.get_or_create_active_cart(customer_id))

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
        cart = self.cart_repository.update(cart["id"], {"items": items, "restaurant_id": item["restaurant_id"]})
        return self.priced(cart)

    # --- 3.4 Update quantities ---

    def update_quantity(self, customer_id: int, menu_item_id: int, quantity: int) -> dict:
        cart = self.get_or_create_active_cart(customer_id)
        items = [dict(line) for line in cart["items"]]
        line = next((line for line in items if line["menu_item_id"] == menu_item_id), None)
        if line is None:
            raise ItemNotInCartError(menu_item_id)
        line["quantity"] = quantity
        return self.priced(self.cart_repository.update(cart["id"], {"items": items}))

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
        return self.priced(self.cart_repository.update(cart["id"], changes))

    def clear_for_customer(self, customer_id: int) -> dict:
        cart = self.get_or_create_active_cart(customer_id)
        return self.priced(self.clear(cart["id"]))

    def clear(self, cart_id: int) -> dict:
        """Empty a cart and untie it from its restaurant. Checkout calls this after saving an order (4.5)."""
        cart = self.cart_repository.update(cart_id, {"items": [], "restaurant_id": None})
        if cart is None:
            raise NotFoundError(f"Cart {cart_id} not found")
        return cart

    def mark_checked_out(self, cart_id: int) -> dict:
        """Close a cart once its order is saved (4.5). The items are kept as a record of what was ordered.

        A closed cart is no longer the customer's active cart, so `GET /cart` gives them a new, empty one.
        """
        cart = self.cart_repository.update(cart_id, {"status": "checked_out"})
        if cart is None:
            raise NotFoundError(f"Cart {cart_id} not found")
        return cart

    # --- 3.6 Subtotal and total ---

    def priced(self, cart: dict) -> dict:
        """Return the cart with line totals, subtotal and total from the **current** menu prices."""
        menu_items = []
        orderable = []
        for line in cart["items"]:
            item = self.menu_service.get_item_by_id(line["menu_item_id"])
            if item is None:
                # Menu items are only ever soft-deleted, so this only happens if the data was edited by hand
                item = {"id": line["menu_item_id"], "name": f"Menu item {line['menu_item_id']}", "price": 0}
            menu_items.append((item, line["quantity"]))
            orderable.append(self._is_orderable(item["id"]))

        pricing = price_lines(menu_items)
        for line, is_orderable in zip(pricing["items"], orderable):
            line["is_orderable"] = is_orderable
        return {
            "id": cart["id"],
            "customer_id": cart["customer_id"],
            "restaurant_id": cart["restaurant_id"],
            "status": cart["status"],
            **pricing,
        }

    def _is_orderable(self, menu_item_id: int) -> bool:
        try:
            self.menu_service.get_orderable_item(menu_item_id)
        except (MenuItemNotOrderableError, NotFoundError):
            return False
        return True
