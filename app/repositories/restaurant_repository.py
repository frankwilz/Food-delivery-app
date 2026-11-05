from app.repositories.json_repository import JsonRepository


class RestaurantRepository(JsonRepository):
    """The only code allowed to read or write data/restaurants.json."""

    def get_by_id(self, restaurant_id: int) -> dict | None:
        for restaurant in self.get_all():
            if restaurant["id"] == restaurant_id:
                return restaurant
        return None

    def create(self, restaurant_data: dict) -> dict:
        restaurants = self.get_all()
        new_restaurant = {"id": self.next_id(restaurants), **restaurant_data}
        restaurants.append(new_restaurant)
        self.save(restaurants)
        return new_restaurant

    def update(self, restaurant_id: int, changes: dict) -> dict | None:
        restaurants = self.get_all()
        for restaurant in restaurants:
            if restaurant["id"] == restaurant_id:
                # The id is never overwritten, so identifiers (and menu links) stay stable
                restaurant.update({key: value for key, value in changes.items() if key != "id"})
                self.save(restaurants)
                return restaurant
        return None
