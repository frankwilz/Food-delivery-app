"""Tests for 5.2 (#50): the customer-to-order workflow across every subsystem.

- The representative data in all five JSON files fits together.
- The full flow works through the API: register → log in → browse → add to cart → check out → view the order.
- Services reach other data only through services and repositories.
- Carts and orders survive a real server restart (see the restart test in tests/test_integration.py).
"""

import ast
import json
from pathlib import Path

import pytest

from app.core.config import BASE_DIR
from app.core.security import create_access_token

DATA = BASE_DIR / "data"
APP = BASE_DIR / "app"


def committed(file_name: str) -> list[dict]:
    return json.loads((DATA / file_name).read_text(encoding="utf-8"))


def by_id(records: list[dict]) -> dict[int, dict]:
    return {record["id"]: record for record in records}


# --- The representative data is consistent ---


@pytest.fixture(scope="module")
def data() -> dict[str, dict[int, dict]]:
    return {
        name: by_id(committed(f"{name}.json"))
        for name in ("restaurants", "menu_items", "customers", "carts", "orders")
    }


def test_every_data_file_has_records(data):
    assert all(records for records in data.values())


def test_menu_items_point_to_real_restaurants(data):
    for item in data["menu_items"].values():
        assert item["restaurant_id"] in data["restaurants"], item


def test_carts_point_to_real_customers_restaurants_and_menu_items(data):
    for cart in data["carts"].values():
        assert cart["customer_id"] in data["customers"], cart
        assert cart["status"] in ("active", "checked_out")
        if cart["items"]:
            assert cart["restaurant_id"] in data["restaurants"], cart
        else:
            assert cart["restaurant_id"] is None, cart
        for line in cart["items"]:
            item = data["menu_items"].get(line["menu_item_id"])
            assert item is not None, line
            # A cart only holds items from its own restaurant
            assert item["restaurant_id"] == cart["restaurant_id"], (cart["id"], line)
            assert type(line["quantity"]) is int and 1 <= line["quantity"] <= 99
            assert set(line) == {"menu_item_id", "quantity"}  # never a price


def test_each_customer_has_at_most_one_active_cart(data):
    active = [cart["customer_id"] for cart in data["carts"].values() if cart["status"] == "active"]
    assert len(active) == len(set(active))


def test_orders_point_to_real_records(data):
    for order in data["orders"].values():
        assert order["customer_id"] in data["customers"], order
        assert order["restaurant_id"] in data["restaurants"], order
        cart = data["carts"][order["cart_id"]]
        # The order came from one of the customer's own carts, which was closed when the order was saved
        assert cart["customer_id"] == order["customer_id"]
        assert cart["restaurant_id"] == order["restaurant_id"]
        assert cart["status"] == "checked_out"
        for line in order["items"]:
            assert data["menu_items"][line["menu_item_id"]]["restaurant_id"] == order["restaurant_id"]


def test_each_cart_became_at_most_one_order(data):
    cart_ids = [order["cart_id"] for order in data["orders"].values()]
    assert len(cart_ids) == len(set(cart_ids))


def test_order_totals_add_up(data):
    for order in data["orders"].values():
        for line in order["items"]:
            assert round(line["unit_price"] * line["quantity"], 2) == line["line_total"]
        assert round(sum(line["line_total"] for line in order["items"]), 2) == order["subtotal"] == order["total"]


def test_representative_data_supports_the_demo(data):
    customers = data["customers"].values()
    carts = data["carts"].values()
    # An active customer with a cart ready to check out, and one with no cart or orders to start fresh
    ready = [c for c in customers if c["is_active"] and any(k["customer_id"] == c["id"] and k["status"] == "active" and k["items"] for k in carts)]
    fresh = [c for c in customers if c["is_active"] and c["role"] == "customer" and not any(k["customer_id"] == c["id"] for k in carts)]
    assert ready and fresh
    # A deactivated customer whose past order is kept
    assert any(not data["customers"][o["customer_id"]]["is_active"] for o in data["orders"].values())


def test_representative_data_works_through_the_api(client):
    ben = {"Authorization": f"Bearer {create_access_token(2)}"}

    cart = client.get("/cart", headers=ben).json()
    assert cart["id"] == 3 and cart["total"] == 15.27  # 2 × 6.49 + 2.29
    assert [order["id"] for order in client.get("/orders", headers=ben).json()] == [1]

    order = client.post("/checkout", headers=ben)
    assert order.status_code == 201
    assert order.json()["id"] == 3  # continues after the two committed orders
    assert [o["id"] for o in client.get("/orders", headers=ben).json()] == [3, 1]


# --- The full workflow through the API ---


def test_full_customer_to_order_workflow(client, tmp_path):
    # Register and log in
    account = {
        "name": "Jordan Lee",
        "email": "jordan.lee@example.com",
        "password": "correct-horse-battery",
        "delivery_address": "1200 Academy Way, Kelowna",
    }
    registered = client.post("/customers", json=account)
    assert registered.status_code == 201
    login = client.post("/auth/login", json={"email": account["email"], "password": account["password"]})
    assert login.status_code == 200
    me = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/customers/me", headers=me).json()["id"] == registered.json()["id"]

    # Browse: find an open restaurant and its orderable items
    restaurant = next(r for r in client.get("/restaurants", params={"is_open": True}).json() if r["id"] == 1)
    menu = client.get(f"/restaurants/{restaurant['id']}/menu").json()
    orderable = [item for item in menu if item["is_available"]]
    assert len(orderable) >= 2

    # Fill the cart
    assert client.get("/cart", headers=me).json()["items"] == []
    client.post("/cart/items", json={"menu_item_id": orderable[0]["id"], "quantity": 2}, headers=me)
    cart = client.post("/cart/items", json={"menu_item_id": orderable[1]["id"], "quantity": 1}, headers=me).json()
    expected_total = round(orderable[0]["price"] * 2 + orderable[1]["price"], 2)
    assert cart["total"] == expected_total

    # Check out
    order = client.post("/checkout", headers=me)
    assert order.status_code == 201
    order = order.json()
    assert order["customer_id"] == registered.json()["id"]
    assert order["restaurant_id"] == restaurant["id"]
    assert order["total"] == expected_total
    assert order["delivery_address"] == account["delivery_address"]

    # View the order, and start again with an empty cart
    assert client.get("/orders", headers=me).json() == [order]
    assert client.get(f"/orders/{order['id']}", headers=me).json() == order
    assert client.get("/cart", headers=me).json()["items"] == []

    # Every step was saved through the repositories to the (temporary) JSON files
    saved_orders = json.loads((tmp_path / "orders.json").read_text(encoding="utf-8"))
    saved_carts = json.loads((tmp_path / "carts.json").read_text(encoding="utf-8"))
    assert saved_orders[-1]["id"] == order["id"]
    assert any(c["id"] == order["cart_id"] and c["status"] == "checked_out" for c in saved_carts)


# --- Services reach other data only through services and repositories ---


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def calls_open(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return any(isinstance(node, ast.Call) and getattr(node.func, "id", None) == "open" for node in ast.walk(tree))


@pytest.mark.parametrize("path", sorted((APP / "services").glob("*.py")) + sorted((APP / "api").rglob("*.py")), ids=str)
def test_routes_and_services_never_touch_data_files(path):
    # Only app/repositories reads or writes JSON, so every rule goes through a service or repository
    assert "json" not in imported_modules(path)
    assert not calls_open(path)
    assert "app.core.config" not in imported_modules(path) or path.name == "dependencies.py"


def test_checkout_uses_other_subsystems_only_through_services_and_repositories():
    modules = imported_modules(APP / "services" / "checkout_service.py")
    assert {
        "app.services.customer_service",
        "app.services.cart_service",
        "app.services.menu_service",
        "app.repositories.cart_repository",
        "app.repositories.restaurant_repository",
        "app.repositories.order_repository",
    } <= modules


def test_routes_get_services_only_from_the_shared_dependencies():
    for path in sorted((APP / "api" / "routes").glob("*.py")):
        modules = imported_modules(path)
        assert not any(module.startswith("app.repositories") for module in modules), path.name
        assert not any(module.startswith("app.api.routes") for module in modules), path.name
