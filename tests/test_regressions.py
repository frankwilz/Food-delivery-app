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
    original_save = JsonRepository.save

    def save(self, records):
        time.sleep(0.02)
        original_save(self, records)

    monkeypatch.setattr(JsonRepository, "save", save)


def send_together(requests: list) -> list:
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
    """PR #95: concurrent checkout requests must not place duplicate orders."""
    assert client.post("/cart/items", json={"menu_item_id": PIZZA, "quantity": 1}, headers=ANA).status_code == 200

    responses = send_together([("POST", "/checkout", None)] * 3)

    assert sorted(r.status_code for r in responses) == [201, 400, 400]
    assert len(stored(config.ORDERS_FILE)) == 1


def test_quick_add_clicks_keep_every_quantity(client, slow_saves):
    """PR #95: concurrent cart additions must not overwrite each other's quantities."""
    assert client.get("/cart", headers=ANA).status_code == 200

    responses = send_together([("POST", "/cart/items", {"menu_item_id": PIZZA, "quantity": 1})] * 4)

    assert all(r.status_code == 200 for r in responses)
    assert client.get("/cart", headers=ANA).json()["items"][0]["quantity"] == 4
