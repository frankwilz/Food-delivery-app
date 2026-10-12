import json
import os
import tempfile
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
                # Identifiers are never overwritten, so ids stay stable
                item.update({k: v for k, v in changes.items() if k not in ("id", "restaurant_id")})
                self._save(items)
                return item
        return None

    def _save(self, items: list[dict]) -> None:
        # Write to a temp file in the same folder, then swap it in with os.replace (atomic),
        # so a crash mid-write cannot leave a half-written, corrupt JSON file behind
        fd, tmp_name = tempfile.mkstemp(dir=Path(self.file_path).parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(items, f, indent=4)
                f.write("\n")
            os.replace(tmp_name, self.file_path)
        except BaseException:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
            raise
