import json
import os
import tempfile
from pathlib import Path


class JsonRepository:
    """Base class for repositories that store a list of records in one JSON file."""

    def __init__(self, file_path: Path):
        self.file_path = file_path

    def load(self) -> list[dict]:
        with open(self.file_path, encoding="utf-8") as f:
            return json.load(f)

    def get_all(self) -> list[dict]:
        return self.load()

    def save(self, records: list[dict]) -> None:
        # Write to a temp file in the same folder, then swap it in with os.replace (atomic),
        # so a crash mid-write cannot leave a half-written, corrupt JSON file behind
        fd, tmp_name = tempfile.mkstemp(dir=Path(self.file_path).parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=4)
                f.write("\n")
            os.replace(tmp_name, self.file_path)
        except BaseException:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
            raise

    @staticmethod
    def next_id(records: list[dict]) -> int:
        # max + 1 keeps ids unique and stable even if records are ever removed
        return max((record["id"] for record in records), default=0) + 1
