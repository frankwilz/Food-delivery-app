from app.repositories.menu_repository import MenuRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.menu_item import MenuItem, MenuItemCreate, MenuItemUpdate


class RestaurantNotFoundError(Exception):
    def __init__(self, restaurant_id: int):
        super().__init__(f"Restaurant {restaurant_id} not found")


class MenuItemNotFoundError(Exception):
    def __init__(self, restaurant_id: int, item_id: int):
        super().__init__(f"Menu item {item_id} not found for restaurant {restaurant_id}")


class DuplicateMenuItemError(Exception):
    def __init__(self, restaurant_id: int, name: str):
        super().__init__(f"Restaurant {restaurant_id} already has a menu item named '{name}'")


class EmptyUpdateError(Exception):
    def __init__(self):
        super().__init__("Update request must include at least one field")


class MenuService:
    """Business rules for menus. Routes call this; this calls the repositories."""

    def __init__(self, menu_repository: MenuRepository, restaurant_repository: RestaurantRepository):
        self.menu_repository = menu_repository
        self.restaurant_repository = restaurant_repository

    def list_menu(self, restaurant_id: int) -> list[MenuItem]:
        self._ensure_restaurant_exists(restaurant_id)
        return [MenuItem(**item) for item in self.menu_repository.get_by_restaurant(restaurant_id)]

    def get_menu_item(self, restaurant_id: int, item_id: int) -> MenuItem:
        self._ensure_restaurant_exists(restaurant_id)
        return MenuItem(**self._get_owned_item(restaurant_id, item_id))

    def add_menu_item(self, restaurant_id: int, data: MenuItemCreate) -> MenuItem:
        self._ensure_restaurant_exists(restaurant_id)
        self._ensure_name_unique(restaurant_id, data.name)
        created = self.menu_repository.create({"restaurant_id": restaurant_id, **data.model_dump()})
        return MenuItem(**created)

    def update_menu_item(self, restaurant_id: int, item_id: int, data: MenuItemUpdate) -> MenuItem:
        self._ensure_restaurant_exists(restaurant_id)
        changes = data.model_dump(exclude_unset=True, exclude_none=True)
        if not changes:
            raise EmptyUpdateError()
        self._get_owned_item(restaurant_id, item_id)
        if "name" in changes:
            self._ensure_name_unique(restaurant_id, changes["name"], ignore_item_id=item_id)
        updated = self.menu_repository.update(item_id, changes)
        return MenuItem(**updated)

    # ---- validation helpers ------------------------------------------------

    def _ensure_restaurant_exists(self, restaurant_id: int) -> None:
        # Uses get_all() so this works with the M0 RestaurantRepository; can switch to
        # get_by_id() once the restaurant backend adds it.
        if not any(r["id"] == restaurant_id for r in self.restaurant_repository.get_all()):
            raise RestaurantNotFoundError(restaurant_id)

    def _get_owned_item(self, restaurant_id: int, item_id: int) -> dict:
        """Return the item only if it exists AND belongs to this restaurant."""
        item = self.menu_repository.get_by_id(item_id)
        if item is None or item["restaurant_id"] != restaurant_id:
            raise MenuItemNotFoundError(restaurant_id, item_id)
        return item

    def _ensure_name_unique(self, restaurant_id: int, name: str, ignore_item_id: int | None = None) -> None:
        wanted = name.strip().casefold()
        for item in self.menu_repository.get_by_restaurant(restaurant_id):
            if item["id"] != ignore_item_id and item["name"].strip().casefold() == wanted:
                raise DuplicateMenuItemError(restaurant_id, name)
