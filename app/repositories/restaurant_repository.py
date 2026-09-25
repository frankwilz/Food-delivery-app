import json
from pathlib import Path


class RestaurantRepository:
    def __init__(self, file_path: Path):
        self.file_path = file_path

    def get_all(self) -> list[dict]:
        with open(self.file_path, encoding="utf-8") as f:
            return json.load(f)