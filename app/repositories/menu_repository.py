import json
import os
import tempfile
from pathlib import Path


class MenuRepository:
    """The only code allowed to read or write data/menu_items.json.

    Menu items live in their own file and point to their restaurant through
    `restaurant_id` (see "Design decision: menu storage" in README.md).
    """

    def __init__(self, file_path: Path):
        self.file_path = Path(file_path)

    # ---- reads -------------------------------------------------------------

    def get_all(self) -> list[dict]:
        with open(self.file_path, encoding="utf-8") as f:
            return json.load(f)

    def get_by_restaurant(self, restaurant_id: int) -> list[dict]:
        return [item for item in self.get_all() if item["restaurant_id"] == restaurant_id]

    def get_by_id(self, item_id: int) -> dict | None:
        for item in self.get_all():
            if item["id"] == item_id:
                return item
        return None

    # ---- writes ------------------------------------------------------------

    def create(self, item_data: dict) -> dict:
        """Assign the next id (max existing id + 1), append the item and save."""
        items = self.get_all()
        new_item = {"id": self._next_id(items), **item_data}
        items.append(new_item)
        self._save(items)
        return new_item

    def update(self, item_id: int, changes: dict) -> dict | None:
        """Merge `changes` into the stored item. Returns None if the id does not exist.

        `id` and `restaurant_id` are never overwritten so identifiers stay stable.
        """
        items = self.get_all()
        for index, item in enumerate(items):
            if item["id"] == item_id:
                safe_changes = {k: v for k, v in changes.items() if k not in ("id", "restaurant_id")}
                items[index] = {**item, **safe_changes}
                self._save(items)
                return items[index]
        return None

    # ---- helpers -----------------------------------------------------------

    @staticmethod
    def _next_id(items: list[dict]) -> int:
        return max((item["id"] for item in items), default=0) + 1

    def _save(self, items: list[dict]) -> None:
        """Write to a temp file in the same folder, then atomically replace the original,
        so a crash mid-write cannot leave a half-written JSON file behind."""
        fd, tmp_name = tempfile.mkstemp(dir=self.file_path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(items, f, indent=4)
                f.write("\n")
            os.replace(tmp_name, self.file_path)
        except BaseException:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
            raise
