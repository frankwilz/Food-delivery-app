import json
import os
import tempfile
from pathlib import Path


class RestaurantRepository:
    """The only code allowed to read or write data/restaurants.json."""

    def __init__(self, file_path: Path):
        self.file_path = file_path

    def get_all(self) -> list[dict]:
        with open(self.file_path, encoding="utf-8") as f:
            return json.load(f)

    def get_by_id(self, restaurant_id: int) -> dict | None:
        for restaurant in self.get_all():
            if restaurant["id"] == restaurant_id:
                return restaurant
        return None

    def create(self, restaurant_data: dict) -> dict:
        restaurants = self.get_all()
        # max + 1 keeps IDs unique and stable even if restaurants are ever removed
        new_id = max((restaurant["id"] for restaurant in restaurants), default=0) + 1
        new_restaurant = {"id": new_id, **restaurant_data}
        restaurants.append(new_restaurant)
        self._save(restaurants)
        return new_restaurant

    def update(self, restaurant_id: int, changes: dict) -> dict | None:
        restaurants = self.get_all()
        for restaurant in restaurants:
            if restaurant["id"] == restaurant_id:
                # The id is never overwritten, so identifiers (and menu links) stay stable
                restaurant.update({key: value for key, value in changes.items() if key != "id"})
                self._save(restaurants)
                return restaurant
        return None

    def _save(self, restaurants: list[dict]) -> None:
        # Write to a temp file in the same folder, then swap it in with os.replace (atomic),
        # so a crash mid-write cannot leave a half-written, corrupt JSON file behind
        fd, tmp_name = tempfile.mkstemp(dir=Path(self.file_path).parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(restaurants, f, indent=4)
                f.write("\n")
            os.replace(tmp_name, self.file_path)
        except BaseException:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
            raise
