from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.restaurant import RestaurantCreate, RestaurantUpdate


class RestaurantNotFoundError(Exception):
    def __init__(self, restaurant_id: int):
        super().__init__(f"Restaurant {restaurant_id} not found")


class DuplicateRestaurantError(Exception):
    def __init__(self, name: str, address: str):
        super().__init__(f"A restaurant named '{name}' already exists at '{address}'")


class EmptyUpdateError(Exception):
    def __init__(self):
        super().__init__("Update request must include at least one field")


class RestaurantService:
    """Business rules for restaurants. Routes call this; this calls the repository."""

    def __init__(self, repository: RestaurantRepository):
        self.repository = repository

    def list_restaurants(
        self,
        search: str | None = None,
        cuisine: str | None = None,
        is_open: bool | None = None,
        min_rating: float | None = None,
    ) -> list[dict]:
        """Return all restaurants, narrowed by any filters given (filters combine with AND)."""
        restaurants = self.repository.get_all()

        if search:
            # Case-insensitive substring match on the name or the cuisine
            term = search.strip().casefold()
            restaurants = [
                r for r in restaurants
                if term in r["name"].casefold() or term in r["cuisine"].casefold()
            ]
        if cuisine:
            # Exact cuisine match, ignoring case
            wanted = cuisine.strip().casefold()
            restaurants = [r for r in restaurants if r["cuisine"].casefold() == wanted]
        if is_open is not None:
            restaurants = [r for r in restaurants if r["is_open"] == is_open]
        if min_rating is not None:
            restaurants = [r for r in restaurants if r["rating"] >= min_rating]

        return restaurants

    def get_restaurant(self, restaurant_id: int) -> dict:
        restaurant = self.repository.get_by_id(restaurant_id)
        if restaurant is None:
            raise RestaurantNotFoundError(restaurant_id)
        return restaurant

    def create_restaurant(self, data: RestaurantCreate) -> dict:
        self._ensure_not_duplicate(data.name, data.address)
        return self.repository.create(data.model_dump())

    def update_restaurant(self, restaurant_id: int, changes: RestaurantUpdate) -> dict:
        fields = changes.model_dump(exclude_unset=True)
        if not fields:
            raise EmptyUpdateError()
        current = self.get_restaurant(restaurant_id)
        if "name" in fields or "address" in fields:
            self._ensure_not_duplicate(
                fields.get("name", current["name"]),
                fields.get("address", current["address"]),
                ignore_id=restaurant_id,
            )
        return self.repository.update(restaurant_id, fields)

    def _ensure_not_duplicate(self, name: str, address: str, ignore_id: int | None = None) -> None:
        # Same name at a different address is allowed (chains); same name AND address is a duplicate
        key = (name.strip().casefold(), address.strip().casefold())
        for r in self.repository.get_all():
            if r["id"] != ignore_id and (r["name"].strip().casefold(), r["address"].strip().casefold()) == key:
                raise DuplicateRestaurantError(name, address)
