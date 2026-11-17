from app.core.errors import BadRequestError, ConflictError, RestaurantNotFoundError
from app.repositories.cart_repository import CartRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.cart import MAX_QUANTITY
from app.services.cart_service import CartService
from app.services.customer_service import CustomerService
from app.services.menu_service import MenuService


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

    4.1 and 4.2 (this file so far): every check that must pass before anything is written,
    including a recheck of every item against the current menu. The checks only read data, so
    a failed checkout leaves every JSON file unchanged.
    Still to come: 4.4 save the order, 4.5 call `CartService.clear` after the order is saved.
    """

    def __init__(
        self,
        customer_service: CustomerService,
        cart_repository: CartRepository,
        restaurant_repository: RestaurantRepository,
        cart_service: CartService,
        menu_service: MenuService,
    ):
        self.customer_service = customer_service
        self.cart_repository = cart_repository
        self.restaurant_repository = restaurant_repository
        self.cart_service = cart_service
        self.menu_service = menu_service

    def checkout(self, customer_id: int) -> dict:
        cart = self.validate_cart(customer_id)
        # Until orders exist (4.4), checkout returns the validated cart. `priced` reads every price
        # from the current menu, never from the cart or the request.
        return self.cart_service.priced(cart)

    def validate_cart(self, customer_id: int) -> dict:
        """Return the customer's active cart if it can be checked out, otherwise raise a clear error."""
        # 403 deactivated, 404 unknown customer
        self.customer_service.get_active_customer(customer_id)

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

        self.revalidate_items(cart)
        return cart

    def revalidate_items(self, cart: dict) -> list[dict]:
        """Recheck every cart item against the current menu and return the current menu items.

        The menu may have changed since an item was added, so each item goes through the shared
        rule, `MenuService.get_orderable_item`, rather than a copy of it. The first item that can
        no longer be ordered stops checkout: 409 if it is unavailable or deactivated (the message
        names the item), 404 if it no longer exists at all.
        """
        return [self.menu_service.get_orderable_item(line["menu_item_id"]) for line in cart["items"]]
