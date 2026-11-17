from app.core.errors import (
    ConflictError,
    EmptyUpdateError,
    NotFoundError,
    RestaurantNotFoundError,
)
from app.repositories.menu_item_repository import MenuItemRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.menu_item import MenuItemCreate, MenuItemUpdate

__all__ = [
    "DuplicateMenuItemError",
    "EmptyUpdateError",
    "MenuItemDeactivatedError",
    "MenuItemNotFoundError",
    "MenuItemNotOrderableError",
    "MenuItemUnavailableError",
    "MenuService",
    "RestaurantNotFoundError",
]


class MenuItemNotFoundError(NotFoundError):
    def __init__(self, restaurant_id: int, item_id: int):
        super().__init__(f"Menu item {item_id} not found for restaurant {restaurant_id}")


class MenuItemNotOrderableError(ConflictError):
    """The item exists but cannot be ordered right now (409). Catch this to handle both reasons."""


class MenuItemDeactivatedError(MenuItemNotOrderableError):
    def __init__(self, item: dict):
        super().__init__(f"Menu item {item['id']} ({item['name']}) is no longer on the menu")


class MenuItemUnavailableError(MenuItemNotOrderableError):
    def __init__(self, item: dict):
        super().__init__(f"Menu item {item['id']} ({item['name']}) is currently unavailable")


class DuplicateMenuItemError(ConflictError):
    def __init__(self, restaurant_id: int, name: str):
        super().__init__(f"Restaurant {restaurant_id} already has a menu item named '{name}'")


class MenuService:
    def __init__(
        self,
        menu_repository: MenuItemRepository,
        restaurant_repository: RestaurantRepository,
    ):
        self.menu_repository = menu_repository
        self.restaurant_repository = restaurant_repository

    def list_menu_items(self, restaurant_id: int, include_inactive: bool = False) -> list[dict]:
        self._ensure_restaurant_exists(restaurant_id)
        items = self.menu_repository.get_by_restaurant_id(restaurant_id)
        if include_inactive:
            return items
        # Deactivated items are hidden from the menu; unavailable ones stay listed and are marked as such
        return [item for item in items if self._is_active(item)]

    def get_menu_item(self, restaurant_id: int, item_id: int) -> dict:
        self._ensure_restaurant_exists(restaurant_id)
        item = self.menu_repository.get_by_id(item_id)
        # An item that exists under a different restaurant is treated as not found
        if item is None or item["restaurant_id"] != restaurant_id:
            raise MenuItemNotFoundError(restaurant_id, item_id)
        return item

    def create_menu_item(self, restaurant_id: int, item: MenuItemCreate) -> dict:
        self._ensure_restaurant_exists(restaurant_id)
        self._ensure_name_unique(restaurant_id, item.name)
        return self.menu_repository.create({"restaurant_id": restaurant_id, **item.model_dump(), "is_active": True})

    def update_menu_item(self, restaurant_id: int, item_id: int, changes: MenuItemUpdate) -> dict:
        fields = changes.model_dump(exclude_unset=True)
        if not fields:
            raise EmptyUpdateError()
        self.get_menu_item(restaurant_id, item_id)
        if "name" in fields:
            self._ensure_name_unique(restaurant_id, fields["name"], ignore_item_id=item_id)
        return self.menu_repository.update(item_id, fields)

    def deactivate_menu_item(self, restaurant_id: int, item_id: int) -> dict:
        # A soft delete: the record stays in the file so existing carts and orders can still refer to it
        self.get_menu_item(restaurant_id, item_id)
        return self.menu_repository.update(item_id, {"is_active": False})

    def get_item_by_id(self, item_id: int) -> dict | None:
        """Return any menu item by id, whatever its restaurant or status, or None. Used to price carts."""
        return self.menu_repository.get_by_id(item_id)

    def get_orderable_item(self, item_id: int) -> dict:
        """Return the item if it can be ordered right now, otherwise raise a clear error.

        This is the single rule for "can this item be ordered?". The cart and checkout call it
        instead of checking `is_active` and `is_available` themselves.
        """
        item = self.menu_repository.get_by_id(item_id)
        if item is None:
            raise NotFoundError(f"Menu item {item_id} not found")
        if not self._is_active(item):
            raise MenuItemDeactivatedError(item)
        if not item["is_available"]:
            raise MenuItemUnavailableError(item)
        return item

    @staticmethod
    def _is_active(item: dict) -> bool:
        # Records saved before is_active existed have no such field and count as active
        return item.get("is_active", True)

    def _ensure_restaurant_exists(self, restaurant_id: int) -> None:
        restaurants = self.restaurant_repository.get_all()
        if not any(restaurant["id"] == restaurant_id for restaurant in restaurants):
            raise RestaurantNotFoundError(restaurant_id)

    def _ensure_name_unique(self, restaurant_id: int, name: str, ignore_item_id: int | None = None) -> None:
        # Names are compared case-insensitively, so "pepperoni pizza" clashes with "Pepperoni Pizza"
        wanted = name.strip().casefold()
        for existing in self.menu_repository.get_by_restaurant_id(restaurant_id):
            if existing["id"] != ignore_item_id and existing["name"].strip().casefold() == wanted:
                raise DuplicateMenuItemError(restaurant_id, name)
