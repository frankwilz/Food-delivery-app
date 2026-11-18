"""5.2 (#50): representative data and the customer-to-order workflow.

Adapted from Zay Lin Myat's retained implementation in commit 96d7b74 (closed PR #86).
These checks exercise API behavior and persisted relationships, without depending on route internals.
"""

import json
import shutil
from decimal import Decimal

import pytest

from app.core.config import BASE_DIR
from app.schemas.cart import MAX_QUANTITY, Cart
from app.schemas.customer import Customer
from app.schemas.menu_item import MenuItem
from app.schemas.order import Order
from app.schemas.restaurant import Restaurant

DATA = BASE_DIR / "data"
SCHEMAS = {
    "restaurants": Restaurant,
    "menu_items": MenuItem,
    "customers": Customer,
    "carts": Cart,
    "orders": Order,
}


def test_representative_data_has_valid_relationships_and_totals():
    data = {}
    for name, schema in SCHEMAS.items():
        records = json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))
        assert records, name
        assert len({record["id"] for record in records}) == len(records), name
        for record in records:
            schema.model_validate(record)
        data[name] = {record["id"]: record for record in records}

    for item in data["menu_items"].values():
        assert item["restaurant_id"] in data["restaurants"]

    active_customers = []
    for cart in data["carts"].values():
        assert cart["customer_id"] in data["customers"]
        if cart["status"] == "active":
            active_customers.append(cart["customer_id"])
        assert cart["restaurant_id"] in data["restaurants"] if cart["items"] else cart["restaurant_id"] is None
        for line in cart["items"]:
            assert set(line) == {"menu_item_id", "quantity"}  # Prices belong to the menu or order snapshot.
            assert type(line["quantity"]) is int and 1 <= line["quantity"] <= MAX_QUANTITY
            assert data["menu_items"][line["menu_item_id"]]["restaurant_id"] == cart["restaurant_id"]
    assert len(active_customers) == len(set(active_customers))

    ordered_carts = []
    for order in data["orders"].values():
        assert order["customer_id"] in data["customers"]
        assert order["restaurant_id"] in data["restaurants"]
        cart = data["carts"][order["cart_id"]]
        ordered_carts.append(cart["id"])
        assert cart["status"] == "checked_out"
        assert (cart["customer_id"], cart["restaurant_id"]) == (order["customer_id"], order["restaurant_id"])
        assert [(line["menu_item_id"], line["quantity"]) for line in order["items"]] == [
            (line["menu_item_id"], line["quantity"]) for line in cart["items"]
        ]
        for line in order["items"]:
            assert data["menu_items"][line["menu_item_id"]]["restaurant_id"] == order["restaurant_id"]
            assert Decimal(str(line["unit_price"])) * line["quantity"] == Decimal(str(line["line_total"]))
        total = sum(Decimal(str(line["line_total"])) for line in order["items"])
        assert total == Decimal(str(order["subtotal"])) == Decimal(str(order["total"]))
    assert len(ordered_carts) == len(set(ordered_carts))


@pytest.fixture
def seeded_demo(isolated_data, tmp_path):
    """Opt into committed cart/order history; ordinary tests start with empty history."""
    for name in ("carts.json", "orders.json"):
        shutil.copy(DATA / name, tmp_path / name)


def test_representative_data_supports_a_real_login_and_checkout(client, seeded_demo):
    login = client.post(
        "/auth/login", json={"email": "ben.carter@example.com", "password": "Ben-demo-2026"}
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    cart = client.get("/cart", headers=headers)
    assert cart.status_code == 200
    assert cart.json()["id"] == 3
    assert cart.json()["total"] == 15.27
    history = client.get("/orders", headers=headers)
    assert history.status_code == 200
    assert [order["id"] for order in history.json()] == [1]

    checkout = client.post("/checkout", headers=headers)
    assert checkout.status_code == 201
    order = checkout.json()
    assert (order["id"], order["cart_id"], order["total"]) == (3, 3, 15.27)
    assert client.get(f"/orders/{order['id']}", headers=headers).json() == order
    assert [row["id"] for row in client.get("/orders", headers=headers).json()] == [3, 1]


def test_full_customer_to_order_workflow(client):
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
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.get("/customers/me", headers=headers).json() == registered.json()

    restaurants = client.get("/restaurants", params={"is_open": True})
    assert restaurants.status_code == 200
    assert any(restaurant["id"] == 1 for restaurant in restaurants.json())
    menu = client.get("/restaurants/1/menu")
    assert menu.status_code == 200
    items = [item for item in menu.json() if item["is_available"] and item["is_active"]]
    first, second = items[:2]

    empty_cart = client.get("/cart", headers=headers)
    assert empty_cart.status_code == 200 and empty_cart.json()["items"] == []
    for item in (first, second):
        added = client.post("/cart/items", json={"menu_item_id": item["id"], "quantity": 1}, headers=headers)
        assert added.status_code == 200
    updated = client.patch(f"/cart/items/{first['id']}", json={"quantity": 2}, headers=headers)
    assert updated.status_code == 200
    cart = updated.json()
    expected_total = round(first["price"] * 2 + second["price"], 2)
    assert cart["total"] == expected_total

    checkout = client.post("/checkout", headers=headers)
    assert checkout.status_code == 201
    order = checkout.json()
    assert (order["customer_id"], order["cart_id"], order["restaurant_id"]) == (
        registered.json()["id"], cart["id"], 1
    )
    assert order["total"] == expected_total
    assert order["delivery_address"] == account["delivery_address"]
    assert [(line["menu_item_id"], line["quantity"]) for line in order["items"]] == [
        (first["id"], 2), (second["id"], 1)
    ]
    retrieved = client.get(f"/orders/{order['id']}", headers=headers)
    assert retrieved.status_code == 200 and retrieved.json() == order
    history = client.get("/orders", headers=headers)
    assert history.status_code == 200 and history.json() == [order]
    new_cart = client.get("/cart", headers=headers)
    assert new_cart.status_code == 200
    assert new_cart.json()["id"] != cart["id"] and new_cart.json()["items"] == []
