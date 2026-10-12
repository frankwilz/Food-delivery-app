import json
from pathlib import Path


class MenuItemRepository:
    def __init__(self, file_path: Path):
        self.file_path = file_path

    def get_all(self) -> list[dict]:
        with open(self.file_path, encoding="utf-8") as f:
            return json.load(f)

    def get_by_restaurant_id(self, restaurant_id: int) -> list[dict]:
        return [item for item in self.get_all() if item["restaurant_id"] == restaurant_id]

    def get_by_id(self, item_id: int) -> dict | None:
        for item in self.get_all():
            if item["id"] == item_id:
                return item
        return None

    def create(self, item_data: dict) -> dict:
        items = self.get_all()
        # max + 1 keeps IDs unique even if items are ever removed
        new_id = max((item["id"] for item in items), default=0) + 1
        new_item = {"id": new_id, **item_data}
        items.append(new_item)
        self._save(items)
        return new_item

    def update(self, item_id: int, changes: dict) -> dict | None:
        items = self.get_all()
        for item in items:
            if item["id"] == item_id:
                item.update(changes)
                self._save(items)
                return item
        return None

    def _save(self, items: list[dict]) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=4)
            f.write("\n")
