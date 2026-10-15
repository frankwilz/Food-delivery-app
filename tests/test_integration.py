import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pytest
from fastapi.testclient import TestClient

from app.api.routes import restaurants as restaurants_route
from app.core.config import BASE_DIR
from app.main import app

# --- Complete vertical slice (HTTP -> route -> service -> repository -> JSON file) ---


def test_full_restaurant_and_menu_flow(client, tmp_path):
    # Create a restaurant, then find it through search and filters
    restaurant = client.post(
        "/restaurants",
        json={"name": "Kelowna Curry House", "cuisine": "Indian", "address": "55 Pandosy Street", "rating": 4.4},
    )
    assert restaurant.status_code == 201
    restaurant_id = restaurant.json()["id"]
    assert [r["id"] for r in client.get("/restaurants", params={"search": "curry"}).json()] == [restaurant_id]

    # Update it, and read back the change
    assert client.patch(f"/restaurants/{restaurant_id}", json={"is_open": False}).status_code == 200
    assert client.get(f"/restaurants/{restaurant_id}").json()["is_open"] is False

    # Give it a menu, then update an item
    item = client.post(
        f"/restaurants/{restaurant_id}/menu",
        json={"name": "Butter Chicken", "price": 17.5, "category": "Mains"},
    )
    assert item.status_code == 201
    item_id = item.json()["id"]
    assert client.patch(f"/restaurants/{restaurant_id}/menu/{item_id}", json={"price": 18.25}).status_code == 200
    assert client.get(f"/restaurants/{restaurant_id}/menu").json() == [
        {**item.json(), "price": 18.25},
    ]

    # Everything went through the repositories into the (temporary) JSON files
    saved_restaurants = json.loads((tmp_path / "restaurants.json").read_text(encoding="utf-8"))
    saved_items = json.loads((tmp_path / "menu_items.json").read_text(encoding="utf-8"))
    assert any(r["id"] == restaurant_id and r["is_open"] is False for r in saved_restaurants)
    assert any(i["id"] == item_id and i["price"] == 18.25 for i in saved_items)


def test_isolated_data_starts_fresh_for_each_test(client):
    # Runs after the flow test above: its writes must not leak into this test
    assert len(client.get("/restaurants").json()) == 4
    assert len(client.get("/restaurants/1/menu").json()) == 3


# --- Error handling ---


@pytest.fixture
def server_error_client():
    # Return the 500 response instead of re-raising the error inside the test
    return TestClient(app, raise_server_exceptions=False)


def test_corrupt_data_file_returns_json_500(server_error_client, tmp_path):
    (tmp_path / "restaurants.json").write_text("{not valid json", encoding="utf-8")

    response = server_error_client.get("/restaurants")

    assert response.status_code == 500
    assert response.json() == {"detail": "Data storage error"}


def test_missing_data_file_returns_json_500(server_error_client, tmp_path, monkeypatch):
    monkeypatch.setattr(restaurants_route, "RESTAURANTS_FILE", tmp_path / "missing.json")

    response = server_error_client.get("/restaurants/1")

    assert response.status_code == 500
    assert response.json() == {"detail": "Data storage error"}


def test_malformed_json_body_returns_422(client):
    response = client.post("/restaurants", content="{bad", headers={"Content-Type": "application/json"})

    assert response.status_code == 422


def test_unknown_path_returns_json_404(client):
    response = client.get("/no-such-endpoint")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_wrong_method_returns_405(client):
    assert client.delete("/restaurants/1").status_code == 405


# --- API documentation ---


def test_docs_pages_are_served(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").json()["info"]["title"] == "Food Delivery API"


def test_every_endpoint_is_documented(client):
    paths = client.get("/openapi.json").json()["paths"]

    assert {
        "/health",
        "/restaurants",
        "/restaurants/{restaurant_id}",
        "/restaurants/{restaurant_id}/menu",
        "/restaurants/{restaurant_id}/menu/{item_id}",
    } <= paths.keys()
    for operations in paths.values():
        for operation in operations.values():
            assert operation["summary"]
            assert operation["description"]
            assert "500" in operation["responses"]
            # Every success response is backed by a response_model (a schema), never a raw dict
            success = next(code for code in operation["responses"] if code.startswith("2"))
            assert "schema" in operation["responses"][success]["content"]["application/json"]
            assert operation["responses"][success]["content"]["application/json"]["schema"]


# --- Persistence across a real server restart ---


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _request(method: str, url: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def _start_server(data_dir, port: int) -> subprocess.Popen:
    # DATA_DIR points the real app at temporary files, so data/ is never modified
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)],
        cwd=BASE_DIR,
        env={**os.environ, "DATA_DIR": str(data_dir)},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            if _request("GET", f"http://127.0.0.1:{port}/health")[0] == 200:
                return process
        except OSError:
            time.sleep(0.1)
    process.terminate()
    raise RuntimeError("uvicorn did not start")


def _stop_server(process: subprocess.Popen) -> None:
    process.terminate()
    process.wait(timeout=10)


def test_data_persists_after_server_restart(tmp_path):
    data_dir = tmp_path / "server-data"
    data_dir.mkdir()
    shutil.copy(BASE_DIR / "data" / "restaurants.json", data_dir / "restaurants.json")
    shutil.copy(BASE_DIR / "data" / "menu_items.json", data_dir / "menu_items.json")
    committed = (BASE_DIR / "data" / "restaurants.json").read_text(encoding="utf-8")
    port = _free_port()
    base = f"http://127.0.0.1:{port}"

    server = _start_server(data_dir, port)
    try:
        status, restaurant = _request(
            "POST", f"{base}/restaurants", {"name": "Restart Diner", "cuisine": "Diner", "address": "1 Reboot Road"}
        )
        assert status == 201
        status, item = _request(
            "POST", f"{base}/restaurants/{restaurant['id']}/menu", {"name": "Pancakes", "price": 8.5, "category": "Mains"}
        )
        assert status == 201
        assert _request("PATCH", f"{base}/restaurants/1", {"is_open": False})[0] == 200
    finally:
        _stop_server(server)

    server = _start_server(data_dir, port)
    try:
        assert _request("GET", f"{base}/restaurants/{restaurant['id']}") == (200, restaurant)
        assert _request("GET", f"{base}/restaurants/{restaurant['id']}/menu/{item['id']}") == (200, item)
        assert _request("GET", f"{base}/restaurants/1")[1]["is_open"] is False
    finally:
        _stop_server(server)

    # The committed representative data was never touched
    assert (BASE_DIR / "data" / "restaurants.json").read_text(encoding="utf-8") == committed
