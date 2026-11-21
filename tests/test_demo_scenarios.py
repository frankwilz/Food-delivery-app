import json

import pytest

from app.core import config
from app.core.security import create_access_token

ANA_ID, MANAGER_ID = 1, 4
PIZZA, SALAD, WINGS_UNAVAILABLE = 1, 2, 3
CRUNCHWRAP = 4


def bearer(customer_id: int) -> dict:
    return {"Authorization": f"Bearer {create_access_token(customer_id)}"}


ANA, MANAGER = bearer(ANA_ID), bearer(MANAGER_ID)


def add(client, item_id: int, quantity: int = 1, headers=None):
    return client.post("/cart/items", json={"menu_item_id": item_id, "quantity": quantity}, headers=headers or ANA)


def stored(file_path) -> list[dict]:
    return json.loads(file_path.read_text(encoding="utf-8"))


def register_and_login(client, email: str) -> dict:
    account = {"name": "Demo Customer", "email": email, "password": "demo-password-1", "delivery_address": "5 Demo Way"}
    assert client.post("/customers", json=account).status_code == 201
    login = client.post("/auth/login", json={"email": email, "password": account["password"]})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_demo_deactivated_customer_is_locked_out_everywhere(client):
    headers = register_and_login(client, "leaving@example.com")
    assert add(client, PIZZA, headers=headers).status_code == 200

    assert client.post("/customers/me/deactivate", headers=headers).status_code == 200

    for method, path in [("GET", "/customers/me"), ("GET", "/cart"), ("POST", "/checkout"), ("GET", "/orders")]:
        response = client.request(method, path, headers=headers)
        assert response.status_code == 403, path
    assert add(client, SALAD, headers=headers).status_code == 403
    login = client.post("/auth/login", json={"email": "leaving@example.com", "password": "demo-password-1"})
    assert login.status_code == 403
    again = {"name": "X", "email": "leaving@example.com", "password": "demo-password-1", "delivery_address": "X"}
    assert client.post("/customers", json=again).status_code == 409
    assert stored(config.ORDERS_FILE) == []


def test_demo_unavailable_item_is_listed_but_cannot_be_ordered(client):
    menu = {item["id"]: item for item in client.get("/restaurants/1/menu").json()}
    assert menu[WINGS_UNAVAILABLE]["is_available"] is False

    response = add(client, WINGS_UNAVAILABLE)

    assert response.status_code == 409
    assert "Chicken Wings" in response.json()["detail"]
    assert client.get("/cart", headers=ANA).json()["items"] == []


@pytest.mark.parametrize("quantity", [0, -1, 100, 1.5, "two", None])
def test_demo_invalid_quantity_is_rejected_and_changes_nothing(client, quantity):
    add(client, PIZZA, 1)
    before = stored(config.CARTS_FILE)

    assert add(client, PIZZA, quantity).status_code == 422
    assert client.patch(f"/cart/items/{PIZZA}", json={"quantity": quantity}, headers=ANA).status_code == 422
    assert stored(config.CARTS_FILE) == before


def test_demo_quantity_above_the_maximum_in_total_is_rejected(client):
    add(client, PIZZA, 60)

    response = add(client, PIZZA, 40)

    assert response.status_code == 400
    assert client.get("/cart", headers=ANA).json()["items"][0]["quantity"] == 60


def test_demo_one_cart_cannot_mix_restaurants(client):
    add(client, PIZZA)

    response = add(client, CRUNCHWRAP)

    assert response.status_code == 409
    assert "Clear the cart" in response.json()["detail"]
    cart = client.get("/cart", headers=ANA).json()
    assert cart["restaurant_id"] == 1 and [line["menu_item_id"] for line in cart["items"]] == [PIZZA]

    assert client.delete("/cart", headers=ANA).status_code == 200
    assert add(client, CRUNCHWRAP).json()["restaurant_id"] == 2


@pytest.mark.parametrize(
    ("method", "path"),
    [("GET", "/cart"), ("POST", "/cart/items"), ("POST", "/checkout"), ("GET", "/orders"), ("GET", "/customers/me")],
)
@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer not-a-real-token"}], ids=["no-token", "bad-token"])
def test_demo_unauthorized_request_gets_401(client, method, path, headers):
    response = client.request(method, path, json={"menu_item_id": PIZZA, "quantity": 1}, headers=headers)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_demo_customer_cannot_use_manager_endpoints(client):
    response = client.patch(f"/restaurants/1/menu/{PIZZA}", json={"price": 0.01}, headers=ANA)

    assert response.status_code == 403
    assert client.get(f"/restaurants/1/menu/{PIZZA}").json()["price"] == 16.99


def test_demo_price_change_before_checkout_charges_the_new_price(client):
    add(client, PIZZA, 2)
    assert client.get("/cart", headers=ANA).json()["total"] == 33.98

    assert client.patch(f"/restaurants/1/menu/{PIZZA}", json={"price": 18.50}, headers=MANAGER).status_code == 200

    assert client.get("/cart", headers=ANA).json()["total"] == 37.00
    order = client.post("/checkout", headers=ANA).json()
    assert order["items"][0]["unit_price"] == 18.50 and order["total"] == 37.00


def test_demo_item_made_unavailable_before_checkout_blocks_it_until_available(client):
    add(client, PIZZA)
    client.patch(f"/restaurants/1/menu/{PIZZA}", json={"is_available": False}, headers=MANAGER)

    cart = client.get("/cart", headers=ANA).json()
    assert cart["items"][0]["is_orderable"] is False
    blocked = client.post("/checkout", headers=ANA)
    assert blocked.status_code == 409 and "Pepperoni Pizza" in blocked.json()["detail"]
    assert stored(config.ORDERS_FILE) == []

    client.patch(f"/restaurants/1/menu/{PIZZA}", json={"is_available": True}, headers=MANAGER)
    assert client.post("/checkout", headers=ANA).status_code == 201


def test_new_restaurant_menu_changes_flow_through_cart_into_a_fixed_order(client):
    restaurant = client.post(
        "/restaurants", json={"name": "Lagos Kitchen", "cuisine": "Nigerian", "address": "8 Jollof Lane"}, headers=MANAGER
    ).json()
    dish = client.post(
        f"/restaurants/{restaurant['id']}/menu",
        json={"name": "Jollof Rice", "price": 14.25, "category": "Mains"},
        headers=MANAGER,
    ).json()

    customer = register_and_login(client, "hungry@example.com")
    found = client.get("/restaurants", params={"search": "nigerian", "is_open": True}).json()
    assert [r["id"] for r in found] == [restaurant["id"]]
    assert [item["id"] for item in client.get(f"/restaurants/{restaurant['id']}/menu").json()] == [dish["id"]]

    add(client, dish["id"], 2, headers=customer)
    assert client.get("/cart", headers=customer).json()["total"] == 28.50

    client.patch(f"/restaurants/{restaurant['id']}/menu/{dish['id']}", json={"price": 15.00}, headers=MANAGER)
    order = client.post("/checkout", headers=customer).json()
    assert (order["restaurant_id"], order["total"]) == (restaurant["id"], 30.00)
    assert order["items"] == [
        {"menu_item_id": dish["id"], "name": "Jollof Rice", "unit_price": 15.00, "quantity": 2, "line_total": 30.00}
    ]

    client.patch(f"/restaurants/{restaurant['id']}/menu/{dish['id']}", json={"name": "Party Jollof"}, headers=MANAGER)
    client.delete(f"/restaurants/{restaurant['id']}/menu/{dish['id']}", headers=MANAGER)
    client.patch(f"/restaurants/{restaurant['id']}", json={"is_open": False}, headers=MANAGER)

    assert client.get(f"/restaurants/{restaurant['id']}/menu").json() == []
    assert client.get(f"/orders/{order['id']}", headers=customer).json() == order
    assert client.get("/orders", headers=customer).json() == [order]
    assert client.get("/cart", headers=customer).json()["items"] == []
