"""The JSON file store shared by every repository, and the locks that keep it consistent.

FastAPI runs plain `def` routes in a thread pool, so two requests can touch the same data file at
the same moment. Every change is a read → modify → write of the whole file, so without a lock two
requests can both read the old file and the second save silently overwrites the first (a lost
update, or two records with the same id).

There is one re-entrant lock per data file, shared by every repository object for that file:

- Each repository method holds its file's lock for its whole read-modify-write, so `create` and
  `update` can never lose another request's change.
- A service that checks something and then writes (e.g. "is this email taken? then create") wraps
  both steps in `transaction(...)`, so no other request can change the file in between. It can name
  several repositories, e.g. checkout locks the carts and orders files together.

The locks are re-entrant, so a method that already holds a lock can call another that takes it again.
`transaction` always takes the locks in the same order (sorted by file path), so two transactions
over the same files cannot deadlock.

These are in-process locks: they protect one server process with any number of threads, which is
how the app runs (`uvicorn app.main:app`). Running several worker processes on the same data files
would need file-system locks or a real database instead.
"""

import json
import os
import tempfile
import threading
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path

_locks: dict[Path, threading.RLock] = {}
_locks_guard = threading.Lock()  # protects _locks itself while a new file's lock is created


def lock_for(file_path: Path) -> threading.RLock:
    """The one lock for this data file, whichever repository object asks for it."""
    key = Path(file_path).resolve()
    with _locks_guard:
        if key not in _locks:
            _locks[key] = threading.RLock()
        return _locks[key]


@contextmanager
def transaction(*repositories: "JsonRepository") -> Iterator[None]:
    """Hold the locks of every repository's data file until the block ends.

    Use it in a service around a check followed by a write, so the check is still true when the
    write happens:

        with transaction(self.repository):
            if self.repository.get_by_email(email) is not None:
                raise DuplicateEmailError(email)
            self.repository.create(...)
    """
    paths = sorted({Path(repo.file_path).resolve() for repo in repositories}, key=str)
    with ExitStack() as stack:
        for path in paths:
            stack.enter_context(lock_for(path))
        yield


class JsonRepository:
    """Base class for repositories that store a list of records in one JSON file.

    Subclasses wrap every read-modify-write in `with self.lock:`.
    """

    def __init__(self, file_path: Path):
        self.file_path = file_path

    @property
    def lock(self) -> threading.RLock:
        return lock_for(self.file_path)

    def load(self) -> list[dict]:
        # Reads take the lock too: on Windows, os.replace in save() fails if the file is open elsewhere
        with self.lock, open(self.file_path, encoding="utf-8") as f:
            return json.load(f)

    def get_all(self) -> list[dict]:
        return self.load()

    def save(self, records: list[dict]) -> None:
        # Write to a temp file in the same folder, then swap it in with os.replace (atomic),
        # so a crash mid-write cannot leave a half-written, corrupt JSON file behind
        with self.lock:
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
