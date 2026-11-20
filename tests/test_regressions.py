"""5.8 (#56): regression tests for bugs found during integration and review.

Each test names the pull request that fixed its bug, so a failure points straight at what
came back. Add a new test here whenever a bug is fixed.
"""

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.core.security import create_access_token
from app.main import app
from app.repositories.json_repository import JsonRepository

ANA = {"Authorization": f"Bearer {create_access_token(1)}"}
PIZZA = 1


@pytest.fixture
def slow_saves(monkeypatch):
    """Hold the race window open: every save pauses, as a slow disk would."""
    original_save = JsonRepository.save

    def save(self, records):
        time.sleep(0.02)
        original_save(self, records)

    monkeypatch.setattr(JsonRepository, "save", save)


def send_together(requests: list) -> list:
    """Send several HTTP requests at the same moment, each from its own client, as a double click does."""
    barrier = threading.Barrier(len(requests))

    def send(request):
        method, path, body = request
        barrier.wait()
        return TestClient(app, headers=ANA).request(method, path, json=body)

    with ThreadPoolExecutor(max_workers=len(requests)) as pool:
        return list(pool.map(send, requests))


def stored(file_path) -> list[dict]:
    return json.loads(file_path.read_text(encoding="utf-8"))


def test_double_clicked_place_order_creates_one_order(client, slow_saves):
    """Regression for PR #95 (concurrent JSON writes).

    Bug: two `POST /checkout` requests for the same cart arriving together both passed the
    "has this cart already been ordered?" check before either saved, so one cart became two
    orders and the customer was charged twice. Fixed by holding the carts and orders file locks
    for the whole checkout (`transaction` in app/repositories/json_repository.py).
    """
    client.post("/cart/items", json={"menu_item_id": PIZZA, "quantity": 1}, headers=ANA)

    responses = send_together([("POST", "/checkout", None)] * 3)

    assert sorted(r.status_code for r in responses) == [201, 400, 400]  # the others find an empty cart
    assert len(stored(config.ORDERS_FILE)) == 1


def test_quick_add_clicks_keep_every_quantity(client, slow_saves):
    """Regression for PR #95 (concurrent JSON writes).

    Bug: two `POST /cart/items` requests at once both read the cart, then each saved its own
    version, so the second save erased the first and the cart showed 1 instead of 2.
    Fixed by changing the cart inside `transaction(self.cart_repository)` in CartService.
    """
    client.get("/cart", headers=ANA)  # create the cart first, so both requests change the same one

    responses = send_together([("POST", "/cart/items", {"menu_item_id": PIZZA, "quantity": 1})] * 4)

    assert all(r.status_code == 200 for r in responses)
    assert client.get("/cart", headers=ANA).json()["items"][0]["quantity"] == 4
