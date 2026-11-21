import json

import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.core.security import create_access_token
from app.main import app
from app.repositories.restaurant_repository import RestaurantRepository

ANA_ID, CHLOE_DEACTIVATED_ID = 1, 3
PIZZA, WINGS_UNAVAILABLE = 1, 3

TOKENS = {"ana": ANA_ID, "chloe": CHLOE_DEACTIVATED_ID}
NEW_CUSTOMER = {
    "name": "Status Tester",
    "email": "status.tester@example.com",
    "password": "a-long-password",
    "delivery_address": "1 Status Street",
}


def add_pizza(client, quantity=1):
    client.post("/cart/items", json={"menu_item_id": PIZZA, "quantity": quantity}, headers=bearer("ana"))


def fill_cart_to_the_maximum(client):
    add_pizza(client, 99)


def place_an_order(client):
    add_pizza(client)
    client.post("/checkout", headers=bearer("ana"))


def cart_from_a_deleted_restaurant(client):
    config.CARTS_FILE.write_text(json.dumps([{
        "id": 1, "customer_id": ANA_ID, "restaurant_id": 99,
        "items": [{"menu_item_id": PIZZA, "quantity": 1}], "status": "active",
    }]), encoding="utf-8")


def cart_from_a_restaurant_that_closed(client):
    add_pizza(client)
    RestaurantRepository(config.RESTAURANTS_FILE).update(1, {"is_open": False})


def bearer(who):
    return {"Authorization": f"Bearer {create_access_token(TOKENS[who])}"} if who else {}


CASES = [
    ("POST", "/customers", None, NEW_CUSTOMER, None, 201),
    ("POST", "/customers", None, {**NEW_CUSTOMER, "email": "ana.souza@example.com"}, None, 409),
    ("POST", "/customers", None, {**NEW_CUSTOMER, "email": "not-an-email"}, None, 422),
    ("GET", "/customers/me", "ana", None, None, 200),
    ("GET", "/customers/me", None, None, None, 401),
    ("GET", "/customers/me", "chloe", None, None, 403),
    ("PATCH", "/customers/me", "ana", {"delivery_address": "2 New Road"}, None, 200),
    ("PATCH", "/customers/me", "ana", {}, None, 400),
    ("PATCH", "/customers/me", None, {"name": "X"}, None, 401),
    ("PATCH", "/customers/me", "chloe", {"name": "X"}, None, 403),
    ("PATCH", "/customers/me", "ana", {"email": "ben.carter@example.com"}, None, 409),
    ("PATCH", "/customers/me", "ana", {"role": "manager"}, None, 422),
    ("POST", "/customers/me/deactivate", "ana", None, None, 200),
    ("POST", "/customers/me/deactivate", None, None, None, 401),
    ("POST", "/customers/me/deactivate", "chloe", None, None, 403),
    ("POST", "/auth/login", None, {"email": "ana.souza@example.com", "password": "Ana-demo-2026"}, None, 200),
    ("POST", "/auth/login", None, {"email": "ana.souza@example.com", "password": "wrong-password"}, None, 401),
    ("POST", "/auth/login", None, {"email": "chloe.martin@example.com", "password": "Chloe-demo-2026"}, None, 403),
    ("POST", "/auth/login", None, {"email": "ana.souza@example.com"}, None, 422),
    ("GET", "/cart", "ana", None, None, 200),
    ("GET", "/cart", None, None, None, 401),
    ("GET", "/cart", "chloe", None, None, 403),
    ("DELETE", "/cart", "ana", None, add_pizza, 200),
    ("DELETE", "/cart", None, None, None, 401),
    ("DELETE", "/cart", "chloe", None, None, 403),
    ("POST", "/cart/items", "ana", {"menu_item_id": PIZZA, "quantity": 1}, None, 200),
    ("POST", "/cart/items", "ana", {"menu_item_id": PIZZA, "quantity": 1}, fill_cart_to_the_maximum, 400),
    ("POST", "/cart/items", None, {"menu_item_id": PIZZA, "quantity": 1}, None, 401),
    ("POST", "/cart/items", "chloe", {"menu_item_id": PIZZA, "quantity": 1}, None, 403),
    ("POST", "/cart/items", "ana", {"menu_item_id": 999, "quantity": 1}, None, 404),
    ("POST", "/cart/items", "ana", {"menu_item_id": WINGS_UNAVAILABLE, "quantity": 1}, None, 409),
    ("POST", "/cart/items", "ana", {"menu_item_id": PIZZA, "quantity": 0}, None, 422),
    ("PATCH", f"/cart/items/{PIZZA}", "ana", {"quantity": 2}, add_pizza, 200),
    ("PATCH", f"/cart/items/{PIZZA}", None, {"quantity": 2}, None, 401),
    ("PATCH", f"/cart/items/{PIZZA}", "chloe", {"quantity": 2}, None, 403),
    ("PATCH", f"/cart/items/{PIZZA}", "ana", {"quantity": 2}, None, 404),
    ("PATCH", f"/cart/items/{PIZZA}", "ana", {"quantity": 0}, add_pizza, 422),
    ("DELETE", f"/cart/items/{PIZZA}", "ana", None, add_pizza, 200),
    ("DELETE", f"/cart/items/{PIZZA}", None, None, None, 401),
    ("DELETE", f"/cart/items/{PIZZA}", "chloe", None, None, 403),
    ("DELETE", f"/cart/items/{PIZZA}", "ana", None, None, 404),
    ("DELETE", "/cart/items/not-a-number", "ana", None, None, 422),
    ("POST", "/checkout", "ana", None, add_pizza, 201),
    ("POST", "/checkout", "ana", None, None, 400),
    ("POST", "/checkout", None, None, None, 401),
    ("POST", "/checkout", "chloe", None, None, 403),
    ("POST", "/checkout", "ana", None, cart_from_a_deleted_restaurant, 404),
    ("POST", "/checkout", "ana", None, cart_from_a_restaurant_that_closed, 409),
    ("GET", "/orders", "ana", None, place_an_order, 200),
    ("GET", "/orders", None, None, None, 401),
    ("GET", "/orders", "chloe", None, None, 403),
    ("GET", "/orders/1", "ana", None, place_an_order, 200),
    ("GET", "/orders/1", None, None, None, 401),
    ("GET", "/orders/1", "chloe", None, None, 403),
    ("GET", "/orders/1", "ana", None, None, 404),
    ("GET", "/orders/not-a-number", "ana", None, None, 422),
]


def documented_codes() -> dict[tuple[str, str], set[int]]:
    paths = TestClient(app).get("/openapi.json").json()["paths"]
    return {
        (method.upper(), path): {int(code) for code in operation["responses"]}
        for path, operations in paths.items()
        for method, operation in operations.items()
    }


def template_of(path: str) -> str:
    parts = path.strip("/").split("/")
    for template in TestClient(app).get("/openapi.json").json()["paths"]:
        template_parts = template.strip("/").split("/")
        if len(template_parts) == len(parts) and all(
            t == p or t.startswith("{") for t, p in zip(template_parts, parts)
        ):
            return template
    raise AssertionError(f"No documented path matches {path}")


@pytest.mark.parametrize(
    ("method", "path", "who", "body", "setup", "expected"),
    CASES,
    ids=[f"{method} {path} {expected}" for method, path, _, _, _, expected in CASES],
)
def test_endpoint_returns_its_documented_status(client, method, path, who, body, setup, expected):
    if setup:
        setup(client)

    response = client.request(method, path, json=body, headers=bearer(who))

    assert response.status_code == expected, response.text
    assert expected in documented_codes()[(method, template_of(path))]
    if expected >= 400:
        assert "detail" in response.json()
    if expected == 401:
        assert response.headers["WWW-Authenticate"] == "Bearer"


def test_every_documented_status_of_the_new_endpoints_is_tested():
    tested = {(method, template_of(path), expected) for method, path, _, _, _, expected in CASES}
    new_endpoints = ("/customers", "/auth", "/cart", "/checkout", "/orders")

    untested = sorted(
        (method, path, code)
        for (method, path), codes in documented_codes().items()
        if path.startswith(new_endpoints)
        for code in codes - {500}
        if (method, path, code) not in tested
    )

    assert untested == []
