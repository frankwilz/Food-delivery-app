from app.repositories.json_repository import JsonRepository


class MenuItemRepository(JsonRepository):
    """The only code allowed to read or write data/menu_items.json."""

    def get_by_restaurant_id(self, restaurant_id: int) -> list[dict]:
        return [item for item in self.get_all() if item["restaurant_id"] == restaurant_id]

    def get_by_id(self, item_id: int) -> dict | None:
        for item in self.get_all():
            if item["id"] == item_id:
                return item
        return None

    def create(self, item_data: dict) -> dict:
        items = self.get_all()
        new_item = {"id": self.next_id(items), **item_data}
        items.append(new_item)
        self.save(items)
        return new_item

    def update(self, item_id: int, changes: dict) -> dict | None:
        items = self.get_all()
        for item in items:
            if item["id"] == item_id:
                # Identifiers are never overwritten, so ids stay stable
                item.update({k: v for k, v in changes.items() if k not in ("id", "restaurant_id")})
                self.save(items)
                return item
        return None
