from app.repositories.restaurant_repository import RestaurantRepository


class RestaurantService:
    def __init__(self, repository: RestaurantRepository):
        self.repository = repository

    def list_restaurants(self) -> list[dict]:
        return self.repository.get_all()