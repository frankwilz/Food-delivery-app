from app.repositories.menu_item_repository import MenuItemRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.menu_item import MenuItemCreate, MenuItemUpdate


class NotFoundError(Exception):
    pass


class RestaurantNotFoundError(NotFoundError):
    def __init__(self, restaurant_id: int):
        super().__init__(f"Restaurant {restaurant_id} not found")


class MenuItemNotFoundError(NotFoundError):
    def __init__(self, restaurant_id: int, item_id: int):
        super().__init__(f"Menu item {item_id} not found for restaurant {restaurant_id}")


class MenuService:
    def __init__(
        self,
        menu_repository: MenuItemRepository,
        restaurant_repository: RestaurantRepository,
    ):
        self.menu_repository = menu_repository
        self.restaurant_repository = restaurant_repository

    def list_menu_items(self, restaurant_id: int) -> list[dict]:
        self._ensure_restaurant_exists(restaurant_id)
        return self.menu_repository.get_by_restaurant_id(restaurant_id)

    def get_menu_item(self, restaurant_id: int, item_id: int) -> dict:
        self._ensure_restaurant_exists(restaurant_id)
        item = self.menu_repository.get_by_id(item_id)
        # An item that exists under a different restaurant is treated as not found
        if item is None or item["restaurant_id"] != restaurant_id:
            raise MenuItemNotFoundError(restaurant_id, item_id)
        return item

    def create_menu_item(self, restaurant_id: int, item: MenuItemCreate) -> dict:
        self._ensure_restaurant_exists(restaurant_id)
        return self.menu_repository.create({"restaurant_id": restaurant_id, **item.model_dump()})

    def update_menu_item(self, restaurant_id: int, item_id: int, changes: MenuItemUpdate) -> dict:
        self.get_menu_item(restaurant_id, item_id)
        return self.menu_repository.update(item_id, changes.model_dump(exclude_unset=True))

    def _ensure_restaurant_exists(self, restaurant_id: int) -> None:
        restaurants = self.restaurant_repository.get_all()
        if not any(restaurant["id"] == restaurant_id for restaurant in restaurants):
            raise RestaurantNotFoundError(restaurant_id)
