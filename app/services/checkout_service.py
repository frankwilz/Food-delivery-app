from datetime import datetime, timezone

from app.core.errors import BadRequestError, ConflictError, RestaurantNotFoundError
from app.repositories.cart_repository import CartRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.cart import MAX_QUANTITY
from app.services.cart_service import CartService
from app.services.customer_service import CustomerService
from app.services.menu_service import MenuService
from app.services.pricing import price_lines


class EmptyCartError(BadRequestError):
    def __init__(self):
        super().__init__("The cart is empty. Add at least one item before checking out.")


class InvalidCartQuantityError(BadRequestError):
    def __init__(self, menu_item_id: int, quantity):
        super().__init__(
            f"Menu item {menu_item_id} has an invalid quantity ({quantity!r}); it must be a whole number "
            f"from 1 to {MAX_QUANTITY}"
        )


class RestaurantClosedError(ConflictError):
    def __init__(self, restaurant: dict):
        super().__init__(f"Restaurant {restaurant['id']} ({restaurant['name']}) is closed and not accepting orders")


class CheckoutService:
    """Turns a customer's active cart into an order.

    4.1 and 4.2: every check that must pass before anything is written, including a recheck of
    every item against the current menu. The checks only read data, so a failed checkout leaves
    every JSON file unchanged.
    4.3: the order's lines and totals come from `price_lines`, the same function the cart uses.
    4.4: the order is built from those totals plus snapshots, and saved.
    Still to come: 4.5 close the cart after the order is saved.
    """

    def __init__(
        self,
        customer_service: CustomerService,
        cart_repository: CartRepository,
        restaurant_repository: RestaurantRepository,
        cart_service: CartService,
        menu_service: MenuService,
        order_repository: OrderRepository,
    ):
        self.customer_service = customer_service
        self.cart_repository = cart_repository
        self.restaurant_repository = restaurant_repository
        self.cart_service = cart_service
        self.menu_service = menu_service
        self.order_repository = order_repository

    def checkout(self, customer_id: int) -> dict:
        """Check the cart, then build and save the order, and return it."""
        customer, cart, menu_items = self.prepare(customer_id)
        return self.order_repository.create(self.build_order(customer, cart, menu_items))

    def build_order(self, customer: dict, cart: dict, menu_items: list[dict]) -> dict:
        """The order record to save. Nothing in it refers back to live data that could change it later."""
        return {
            "customer_id": customer["id"],
            **self.calculate_totals(cart, menu_items),
            # A snapshot, so a later profile change does not move a past delivery
            "delivery_address": customer["delivery_address"],
            "status": "placed",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def validate_cart(self, customer_id: int) -> dict:
        """Return the customer's active cart if it can be checked out, otherwise raise a clear error."""
        _, cart, _ = self.prepare(customer_id)
        return cart

    def calculate_totals(self, cart: dict, menu_items: list[dict]) -> dict:
        """Price the order with the shared pricing function (3.6), from the current menu items.

        `menu_items` come from `revalidate_items`, so every price is the menu's current one. Prices
        in the cart file or the request are never read; the request has no body at all.
        """
        quantities = [line["quantity"] for line in cart["items"]]
        return {"restaurant_id": cart["restaurant_id"], **price_lines(list(zip(menu_items, quantities)))}

    def prepare(self, customer_id: int) -> tuple[dict, dict, list[dict]]:
        """Run every check and return the customer, their cart and its current menu items, in cart order."""
        # 403 deactivated, 404 unknown customer
        customer = self.customer_service.get_active_customer(customer_id)

        # Read only: unlike GET /cart, checkout never creates a cart
        cart = self.cart_repository.get_active_for_customer(customer_id)
        if cart is None or not cart["items"]:
            raise EmptyCartError()

        restaurant = self.restaurant_repository.get_by_id(cart["restaurant_id"])
        if restaurant is None:
            raise RestaurantNotFoundError(cart["restaurant_id"])
        # Team rule: a closed restaurant cannot take orders
        if not restaurant.get("is_open", True):
            raise RestaurantClosedError(restaurant)

        # The API already rejects bad quantities, but the file could have been edited by hand
        for line in cart["items"]:
            quantity = line["quantity"]
            if type(quantity) is not int or not 1 <= quantity <= MAX_QUANTITY:
                raise InvalidCartQuantityError(line["menu_item_id"], quantity)

        return customer, cart, self.revalidate_items(cart)

    def revalidate_items(self, cart: dict) -> list[dict]:
        """Recheck every cart item against the current menu and return the current menu items.

        The menu may have changed since an item was added, so each item goes through the shared
        rule, `MenuService.get_orderable_item`, rather than a copy of it. The first item that can
        no longer be ordered stops checkout: 409 if it is unavailable or deactivated (the message
        names the item), 404 if it no longer exists at all.
        """
        return [self.menu_service.get_orderable_item(line["menu_item_id"]) for line in cart["items"]]
