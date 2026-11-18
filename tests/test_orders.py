"""Tests for 4.6 (#48): retrieve one order and the customer's order list."""

import json

import pytest

from app.core.security import create_access_token
from app.repositories.order_repository import OrderRepository
from app.services.order_service import OrderNotFoundError, OrderService

ANA_ID, BEN_ID, CHLOE_DEACTIVATED_ID = 1, 2, 3
PIZZA, SALAD, CRUNCHWRAP = 1, 2, 4  # Pizza and salad: restaurant 1. Crunchwrap: restaurant 2.


def auth(customer_id: int) -> dict:
    return {"Authorization": f"Bearer {create_access_token(customer_id)}"}


ANA, BEN = auth(ANA_ID), auth(BEN_ID)
MANAGER = auth(4)


def place_order(client, headers, *items: tuple[int, int]) -> dict:
    for menu_item_id, quantity in items:
        assert client.post("/cart/items", json={"menu_item_id": menu_item_id, "quantity": quantity}, headers=headers).status_code == 200
    response = client.post("/checkout", headers=headers)
    assert response.status_code == 201
    return response.json()


def write_orders(tmp_path, orders: list[dict]) -> None:
    (tmp_path / "orders.json").write_text(json.dumps(orders), encoding="utf-8")


def order_record(order_id: int, customer_id: int, created_at: str) -> dict:
    return {
        "id": order_id,
        "customer_id": customer_id,
        "cart_id": order_id,
        "restaurant_id": 1,
        "items": [{"menu_item_id": PIZZA, "name": "Pepperoni Pizza", "unit_price": 16.99, "quantity": 1, "line_total": 16.99}],
        "subtotal": 16.99,
        "total": 16.99,
        "delivery_address": "1155 Bernard Avenue, Kelowna",
        "status": "placed",
        "created_at": created_at,
    }


# --- GET /orders ---


def test_list_orders_is_empty_before_any_checkout(client):
    response = client.get("/orders", headers=ANA)

    assert response.status_code == 200
    assert response.json() == []


def test_list_orders_returns_the_customers_orders_newest_first(client):
    first = place_order(client, ANA, (PIZZA, 1))
    second = place_order(client, ANA, (CRUNCHWRAP, 2))

    orders = client.get("/orders", headers=ANA).json()

    assert [order["id"] for order in orders] == [second["id"], first["id"]]
    assert orders[0] == second


def test_list_orders_sorts_by_time_not_by_file_order(client, tmp_path):
    write_orders(
        tmp_path,
        [
            order_record(1, ANA_ID, "2026-11-10T12:00:00+00:00"),
            order_record(2, ANA_ID, "2026-11-12T09:30:00+00:00"),
            order_record(3, ANA_ID, "2026-11-11T18:15:00+00:00"),
        ],
    )

    assert [order["id"] for order in client.get("/orders", headers=ANA).json()] == [2, 3, 1]


def test_list_orders_never_includes_another_customers_orders(client):
    ana_order = place_order(client, ANA, (PIZZA, 1))
    ben_order = place_order(client, BEN, (SALAD, 1))

    assert [order["id"] for order in client.get("/orders", headers=ANA).json()] == [ana_order["id"]]
    assert [order["id"] for order in client.get("/orders", headers=BEN).json()] == [ben_order["id"]]


# --- GET /orders/{order_id} ---


def test_get_order_returns_it(client):
    order = place_order(client, ANA, (PIZZA, 2), (SALAD, 1))

    response = client.get(f"/orders/{order['id']}", headers=ANA)

    assert response.status_code == 200
    assert response.json() == order


def test_get_missing_order_returns_404(client):
    response = client.get("/orders/999", headers=ANA)

    assert response.status_code == 404
    assert response.json() == {"detail": "Order 999 not found"}


def test_get_another_customers_order_returns_the_same_404(client):
    ben_order = place_order(client, BEN, (PIZZA, 1))

    response = client.get(f"/orders/{ben_order['id']}", headers=ANA)

    assert response.status_code == 404
    assert response.json() == {"detail": f"Order {ben_order['id']} not found"}


# --- Snapshots ---


def test_menu_price_change_after_checkout_does_not_change_the_order(client):
    order = place_order(client, ANA, (PIZZA, 2))

    client.patch(f"/restaurants/1/menu/{PIZZA}", json={"price": 25, "name": "Deluxe Pizza"}, headers=MANAGER)

    stored = client.get(f"/orders/{order['id']}", headers=ANA).json()
    assert stored["items"][0]["name"] == "Pepperoni Pizza"
    assert stored["items"][0]["unit_price"] == 16.99
    assert stored["total"] == 33.98
    assert client.get("/orders", headers=ANA).json()[0]["total"] == 33.98


def test_address_change_after_checkout_does_not_change_the_order(client):
    order = place_order(client, ANA, (PIZZA, 1))

    client.patch("/customers/me", json={"delivery_address": "1 New Street, Kelowna"}, headers=ANA)

    assert client.get(f"/orders/{order['id']}", headers=ANA).json()["delivery_address"] == "1155 Bernard Avenue, Kelowna"


# --- Sign-in ---


@pytest.mark.parametrize("path", ["/orders", "/orders/1"])
def test_orders_require_sign_in(client, path):
    response = client.get(path)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize("path", ["/orders", "/orders/1"])
def test_deactivated_customer_gets_403(client, path):
    assert client.get(path, headers=auth(CHLOE_DEACTIVATED_ID)).status_code == 403


def test_orders_endpoints_are_documented(client):
    paths = client.get("/openapi.json").json()["paths"]

    assert {"401", "403"} <= set(paths["/orders"]["get"]["responses"])
    assert {"401", "403", "404"} <= set(paths["/orders/{order_id}"]["get"]["responses"])


# --- Service layer ---


@pytest.fixture
def service(tmp_path) -> OrderService:
    write_orders(
        tmp_path,
        [
            order_record(1, ANA_ID, "2026-11-10T12:00:00+00:00"),
            order_record(2, BEN_ID, "2026-11-11T12:00:00+00:00"),
            order_record(3, ANA_ID, "2026-11-12T12:00:00+00:00"),
        ],
    )
    return OrderService(OrderRepository(tmp_path / "orders.json"))


def test_service_list_for_customer(service):
    assert [order["id"] for order in service.list_for_customer(ANA_ID)] == [3, 1]
    assert service.list_for_customer(99) == []


def test_service_get_for_customer(service):
    assert service.get_for_customer(ANA_ID, 3)["id"] == 3
    with pytest.raises(OrderNotFoundError):
        service.get_for_customer(ANA_ID, 2)  # Ben's
    with pytest.raises(OrderNotFoundError):
        service.get_for_customer(ANA_ID, 99)
