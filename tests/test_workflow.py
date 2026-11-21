"""5.2 (#50): representative data and the customer-to-order workflow.

Adapted from Zay Lin Myat's retained implementation in commit 96d7b74 (closed PR #86).
These checks exercise API behavior and persisted relationships, without depending on route internals.
"""

import shutil

import pytest
from data_consistency import load_and_check

from app.core.config import BASE_DIR

DATA = BASE_DIR / "data"


def test_representative_data_has_valid_relationships_and_totals():
    data = load_and_check(DATA)
    for name, records in data.items():
        assert records, f"{name}.json has no representative records"


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
