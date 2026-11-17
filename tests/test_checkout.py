"""Tests for checkout: 4.1 (#43) validate the cart, 4.2 (#44) revalidate the menu, 4.3 (#45) order total,
4.4 (#46) create and persist the order, 4.5 (#47) close the cart after checkout."""

import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.core.errors import ForbiddenError, RestaurantNotFoundError
from app.core.security import create_access_token
from app.main import app
from app.repositories.cart_repository import CartRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.menu_item_repository import MenuItemRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.services.cart_service import CartService
from app.services.checkout_service import (
    CheckoutService,
    EmptyCartError,
    InvalidCartQuantityError,
    RestaurantClosedError,
)
from app.services.customer_service import CustomerService
from app.services.menu_service import MenuItemDeactivatedError, MenuItemUnavailableError, MenuService
from app.services import checkout_service as checkout_module

ANA_ID, CHLOE_DEACTIVATED_ID = 1, 3
PIZZA, SALAD = 1, 2  # restaurant 1, both orderable


# These tests count and number carts and orders from 1, so they start with none (see conftest.py)
pytestmark = pytest.mark.usefixtures("no_carts_or_orders")


def auth(customer_id: int) -> dict:
    return {"Authorization": f"Bearer {create_access_token(customer_id)}"}


ANA = auth(ANA_ID)
MANAGER = auth(4)  # restaurant and menu changes need a manager (2.5)


def data_files(tmp_path) -> dict[str, str]:
    """Contents of every data file, to check that a failed checkout wrote nothing."""
    return {path.name: path.read_text(encoding="utf-8") for path in sorted(tmp_path.glob("*.json"))}


def write_carts(tmp_path, carts: list[dict]) -> None:
    (tmp_path / "carts.json").write_text(json.dumps(carts), encoding="utf-8")


def cart_record(**changes) -> dict:
    return {
        "id": 1,
        "customer_id": ANA_ID,
        "restaurant_id": 1,
        "items": [{"menu_item_id": PIZZA, "quantity": 2}],
        "status": "active",
        **changes,
    }


@pytest.fixture
def checkout_service(tmp_path) -> CheckoutService:
    customers = CustomerService(CustomerRepository(tmp_path / "customers.json"))
    restaurants = RestaurantRepository(tmp_path / "restaurants.json")
    carts = CartRepository(tmp_path / "carts.json")
    menu = MenuService(MenuItemRepository(tmp_path / "menu_items.json"), restaurants)
    orders = OrderRepository(tmp_path / "orders.json")
    return CheckoutService(customers, carts, restaurants, CartService(carts, menu, customers), menu, orders)


# --- success ---


def test_checkout_of_a_valid_cart_returns_it_priced(client):
    client.post("/cart/items", json={"menu_item_id": PIZZA, "quantity": 2}, headers=ANA)
    client.post("/cart/items", json={"menu_item_id": SALAD, "quantity": 1}, headers=ANA)

    response = client.post("/checkout", headers=ANA)

    assert response.status_code == 201
    body = response.json()
    assert body["restaurant_id"] == 1
    assert body["total"] == 43.47  # 2 × 16.99 + 9.49


def test_checkout_uses_current_menu_prices(client):
    client.post("/cart/items", json={"menu_item_id": PIZZA, "quantity": 2}, headers=ANA)
    client.patch(f"/restaurants/1/menu/{PIZZA}", json={"price": 20}, headers=MANAGER)

    assert client.post("/checkout", headers=ANA).json()["total"] == 40.0


def test_client_supplied_totals_are_ignored(client):
    client.post("/cart/items", json={"menu_item_id": PIZZA, "quantity": 1}, headers=ANA)

    response = client.post("/checkout", json={"total": 0.01}, headers=ANA)

    assert response.json()["total"] == 16.99


# --- failures: each writes nothing ---


def test_checkout_requires_sign_in(client):
    assert client.post("/checkout").status_code == 401


def test_deactivated_customer_gets_403(client, tmp_path):
    write_carts(tmp_path, [cart_record(customer_id=CHLOE_DEACTIVATED_ID)])
    before = data_files(tmp_path)

    response = client.post("/checkout", headers=auth(CHLOE_DEACTIVATED_ID))

    assert response.status_code == 403
    assert data_files(tmp_path) == before


def test_no_cart_returns_400_and_does_not_create_one(client, tmp_path):
    before = data_files(tmp_path)

    response = client.post("/checkout", headers=ANA)

    assert response.status_code == 400
    assert "empty" in response.json()["detail"]
    assert data_files(tmp_path) == before


def test_empty_cart_returns_400(client, tmp_path):
    client.get("/cart", headers=ANA)
    before = data_files(tmp_path)

    response = client.post("/checkout", headers=ANA)

    assert response.status_code == 400
    assert data_files(tmp_path) == before


def test_missing_restaurant_returns_404(client, tmp_path):
    write_carts(tmp_path, [cart_record(restaurant_id=99)])
    before = data_files(tmp_path)

    response = client.post("/checkout", headers=ANA)

    assert response.status_code == 404
    assert response.json()["detail"] == "Restaurant 99 not found"
    assert data_files(tmp_path) == before


def test_closed_restaurant_returns_409(client, tmp_path):
    client.post("/cart/items", json={"menu_item_id": PIZZA, "quantity": 1}, headers=ANA)
    client.patch("/restaurants/1", json={"is_open": False}, headers=MANAGER)
    before = data_files(tmp_path)

    response = client.post("/checkout", headers=ANA)

    assert response.status_code == 409
    assert "closed" in response.json()["detail"]
    assert data_files(tmp_path) == before


@pytest.mark.parametrize("quantity", [0, -1, 1.5, "2", 1000])
def test_invalid_stored_quantity_returns_400(client, tmp_path, quantity):
    write_carts(tmp_path, [cart_record(items=[{"menu_item_id": PIZZA, "quantity": quantity}])])
    before = data_files(tmp_path)

    response = client.post("/checkout", headers=ANA)

    assert response.status_code == 400
    assert "invalid quantity" in response.json()["detail"]
    assert data_files(tmp_path) == before


def test_another_customers_cart_is_not_used(client, tmp_path):
    write_carts(tmp_path, [cart_record(customer_id=2)])

    assert client.post("/checkout", headers=ANA).status_code == 400


def test_checked_out_cart_is_not_used(client, tmp_path):
    write_carts(tmp_path, [cart_record(status="checked_out")])

    assert client.post("/checkout", headers=ANA).status_code == 400


# --- service layer ---


def test_service_validate_cart_errors(checkout_service, tmp_path):
    with pytest.raises(ForbiddenError):
        checkout_service.validate_cart(CHLOE_DEACTIVATED_ID)
    with pytest.raises(EmptyCartError):
        checkout_service.validate_cart(ANA_ID)

    write_carts(tmp_path, [cart_record(restaurant_id=99)])
    with pytest.raises(RestaurantNotFoundError):
        checkout_service.validate_cart(ANA_ID)

    write_carts(tmp_path, [cart_record(restaurant_id=3)])  # Okanagan Sushi is closed
    with pytest.raises(RestaurantClosedError):
        checkout_service.validate_cart(ANA_ID)

    write_carts(tmp_path, [cart_record(items=[{"menu_item_id": PIZZA, "quantity": 0}])])
    with pytest.raises(InvalidCartQuantityError):
        checkout_service.validate_cart(ANA_ID)


def test_service_validate_cart_returns_the_cart(checkout_service, tmp_path):
    write_carts(tmp_path, [cart_record()])

    assert checkout_service.validate_cart(ANA_ID)["id"] == 1


def test_checkout_responses_are_documented(client):
    responses = client.get("/openapi.json").json()["paths"]["/checkout"]["post"]["responses"]

    assert {"400", "401", "403", "404", "409"} <= set(responses)


# --- 4.2: revalidate every item against the current menu ---


def add_pizza_and_salad(client) -> None:
    client.post("/cart/items", json={"menu_item_id": PIZZA, "quantity": 2}, headers=ANA)
    client.post("/cart/items", json={"menu_item_id": SALAD, "quantity": 1}, headers=ANA)


def test_item_made_unavailable_after_adding_returns_409_naming_it(client, tmp_path):
    add_pizza_and_salad(client)
    client.patch(f"/restaurants/1/menu/{SALAD}", json={"is_available": False}, headers=MANAGER)
    before = data_files(tmp_path)

    response = client.post("/checkout", headers=ANA)

    assert response.status_code == 409
    assert response.json()["detail"] == f"Menu item {SALAD} (Caesar Salad) is currently unavailable"
    assert data_files(tmp_path) == before


def test_item_deactivated_after_adding_returns_409_naming_it(client, tmp_path):
    add_pizza_and_salad(client)
    client.delete(f"/restaurants/1/menu/{PIZZA}", headers=MANAGER)
    before = data_files(tmp_path)

    response = client.post("/checkout", headers=ANA)

    assert response.status_code == 409
    assert response.json()["detail"] == f"Menu item {PIZZA} (Pepperoni Pizza) is no longer on the menu"
    assert data_files(tmp_path) == before


def test_item_available_again_can_be_checked_out(client):
    add_pizza_and_salad(client)
    client.patch(f"/restaurants/1/menu/{SALAD}", json={"is_available": False}, headers=MANAGER)
    assert client.post("/checkout", headers=ANA).status_code == 409

    client.patch(f"/restaurants/1/menu/{SALAD}", json={"is_available": True}, headers=MANAGER)

    assert client.post("/checkout", headers=ANA).status_code == 201


def test_item_missing_from_the_menu_file_returns_404(client, tmp_path):
    write_carts(tmp_path, [cart_record(items=[{"menu_item_id": 999, "quantity": 1}])])
    before = data_files(tmp_path)

    response = client.post("/checkout", headers=ANA)

    assert response.status_code == 404
    assert response.json()["detail"] == "Menu item 999 not found"
    assert data_files(tmp_path) == before


def test_price_change_after_adding_is_used_at_checkout(client):
    add_pizza_and_salad(client)
    client.patch(f"/restaurants/1/menu/{PIZZA}", json={"price": 18.5}, headers=MANAGER)
    client.patch(f"/restaurants/1/menu/{SALAD}", json={"price": 10}, headers=MANAGER)

    body = client.post("/checkout", headers=ANA).json()

    assert [(line["menu_item_id"], line["unit_price"], line["line_total"]) for line in body["items"]] == [
        (PIZZA, 18.5, 37.0),
        (SALAD, 10.0, 10.0),
    ]
    assert body["total"] == 47.0


def test_a_price_written_into_the_cart_file_is_ignored(client, tmp_path):
    # Even if a price ends up in the stored cart, checkout reads it from the menu
    write_carts(tmp_path, [cart_record(items=[{"menu_item_id": PIZZA, "quantity": 1, "price": 0.01}])])

    assert client.post("/checkout", headers=ANA).json()["total"] == 16.99


def test_service_revalidation_errors(checkout_service, client):
    add_pizza_and_salad(client)

    client.patch(f"/restaurants/1/menu/{SALAD}", json={"is_available": False}, headers=MANAGER)
    with pytest.raises(MenuItemUnavailableError):
        checkout_service.validate_cart(ANA_ID)

    client.patch(f"/restaurants/1/menu/{SALAD}", json={"is_available": True, "is_active": False}, headers=MANAGER)
    with pytest.raises(MenuItemDeactivatedError):
        checkout_service.validate_cart(ANA_ID)


def test_revalidation_uses_the_shared_orderable_item_rule(checkout_service, client, monkeypatch):
    add_pizza_and_salad(client)
    checked = []
    original = checkout_service.menu_service.get_orderable_item

    def spy(item_id):
        checked.append(item_id)
        return original(item_id)

    monkeypatch.setattr(checkout_service.menu_service, "get_orderable_item", spy)

    checkout_service.validate_cart(ANA_ID)

    assert checked == [PIZZA, SALAD]


def test_revalidate_items_returns_current_menu_items(checkout_service, client):
    add_pizza_and_salad(client)
    client.patch(f"/restaurants/1/menu/{PIZZA}", json={"price": 18.5}, headers=MANAGER)
    cart = checkout_service.cart_repository.get_active_for_customer(ANA_ID)

    items = checkout_service.revalidate_items(cart)

    assert [(item["id"], item["price"]) for item in items] == [(PIZZA, 18.5), (SALAD, 9.49)]


# --- 4.3: authoritative order total ---


def test_checkout_returns_the_order_lines_and_totals(client):
    add_pizza_and_salad(client)

    body = client.post("/checkout", headers=ANA).json()

    assert {key: body[key] for key in ("restaurant_id", "items", "subtotal", "total")} == {
        "restaurant_id": 1,
        "items": [
            {"menu_item_id": PIZZA, "name": "Pepperoni Pizza", "unit_price": 16.99, "quantity": 2, "line_total": 33.98},
            {"menu_item_id": SALAD, "name": "Caesar Salad", "unit_price": 9.49, "quantity": 1, "line_total": 9.49},
        ],
        "subtotal": 43.47,
        "total": 43.47,
    }


def test_order_total_matches_the_cart_total(client):
    add_pizza_and_salad(client)
    cart = client.get("/cart", headers=ANA).json()

    order = client.post("/checkout", headers=ANA).json()

    assert (order["subtotal"], order["total"]) == (cart["subtotal"], cart["total"])
    assert [line["line_total"] for line in order["items"]] == [line["line_total"] for line in cart["items"]]


def test_price_changed_between_adding_and_checkout_uses_the_new_price(client):
    client.post("/cart/items", json={"menu_item_id": PIZZA, "quantity": 3}, headers=ANA)
    client.patch(f"/restaurants/1/menu/{PIZZA}", json={"price": 12.5}, headers=MANAGER)

    body = client.post("/checkout", headers=ANA).json()

    assert body["items"][0]["unit_price"] == 12.5
    assert body["items"][0]["line_total"] == 37.5
    assert body["total"] == 37.5


@pytest.mark.parametrize(
    "body",
    [
        {"total": 0.01},
        {"subtotal": 0, "total": 0},
        {"items": [{"menu_item_id": PIZZA, "quantity": 1, "unit_price": 0.01, "line_total": 0.01}], "total": 0.01},
    ],
)
def test_any_price_or_total_sent_by_the_client_is_ignored(client, body):
    client.post("/cart/items", json={"menu_item_id": PIZZA, "quantity": 2}, headers=ANA)

    response = client.post("/checkout", json=body, headers=ANA)

    assert response.json()["items"][0]["unit_price"] == 16.99
    assert response.json()["total"] == 33.98


def test_checkout_uses_the_shared_pricing_function(checkout_service, client, monkeypatch):
    add_pizza_and_salad(client)
    calls = []
    original = checkout_module.price_lines

    def spy(lines):
        calls.append([(item["id"], quantity) for item, quantity in lines])
        return original(lines)

    monkeypatch.setattr(checkout_module, "price_lines", spy)

    checkout_service.checkout(ANA_ID)

    assert calls == [[(PIZZA, 2), (SALAD, 1)]]


def test_service_calculate_totals_uses_the_menu_items_given(checkout_service):
    cart = cart_record(items=[{"menu_item_id": PIZZA, "quantity": 2, "price": 0.01}])
    menu_items = [{"id": PIZZA, "name": "Pepperoni Pizza", "price": 20}]

    totals = checkout_service.calculate_totals(cart, menu_items)

    assert totals["items"][0]["line_total"] == 40.0
    assert totals["total"] == 40.0


# --- 4.4: create and persist the order ---


def stored_orders(tmp_path) -> list[dict]:
    return json.loads((tmp_path / "orders.json").read_text(encoding="utf-8"))


def test_checkout_returns_201_with_the_saved_order(client, tmp_path):
    add_pizza_and_salad(client)
    before = datetime.now(timezone.utc)

    response = client.post("/checkout", headers=ANA)

    assert response.status_code == 201
    order = response.json()
    created_at = datetime.fromisoformat(order.pop("created_at"))
    assert before - timedelta(seconds=1) <= created_at <= datetime.now(timezone.utc)
    assert order == {
        "id": 1,
        "customer_id": ANA_ID,
        "cart_id": 1,
        "restaurant_id": 1,
        "items": [
            {"menu_item_id": PIZZA, "name": "Pepperoni Pizza", "unit_price": 16.99, "quantity": 2, "line_total": 33.98},
            {"menu_item_id": SALAD, "name": "Caesar Salad", "unit_price": 9.49, "quantity": 1, "line_total": 9.49},
        ],
        "subtotal": 43.47,
        "total": 43.47,
        "delivery_address": "1155 Bernard Avenue, Kelowna",
        "status": "placed",
    }


def test_order_is_saved_to_the_orders_file(client, tmp_path):
    add_pizza_and_salad(client)

    order = client.post("/checkout", headers=ANA).json()

    saved = stored_orders(tmp_path)
    assert len(saved) == 1
    assert saved[0]["id"] == order["id"]
    assert saved[0]["items"] == order["items"]
    assert saved[0]["delivery_address"] == "1155 Bernard Avenue, Kelowna"
    # The stored line is a snapshot of the name and price, not just an id
    assert saved[0]["items"][0]["name"] == "Pepperoni Pizza"
    assert saved[0]["items"][0]["unit_price"] == 16.99


def test_order_snapshot_does_not_change_with_the_menu_or_profile(client, tmp_path):
    add_pizza_and_salad(client)
    client.post("/checkout", headers=ANA)
    saved = stored_orders(tmp_path)

    client.patch(f"/restaurants/1/menu/{PIZZA}", json={"price": 99, "name": "Renamed Pizza"}, headers=MANAGER)
    client.patch("/customers/me", json={"delivery_address": "1 New Street, Kelowna"}, headers=ANA)

    assert stored_orders(tmp_path) == saved


def test_failed_checkout_does_not_create_an_order(client, tmp_path):
    add_pizza_and_salad(client)
    client.patch(f"/restaurants/1/menu/{SALAD}", json={"is_available": False}, headers=MANAGER)

    assert client.post("/checkout", headers=ANA).status_code == 409
    assert stored_orders(tmp_path) == []


def test_order_ids_stay_stable_across_new_repositories(client, tmp_path):
    add_pizza_and_salad(client)
    first = client.post("/checkout", headers=ANA).json()

    # A new repository reading the same file, as after a restart, sees the same order and continues the ids
    repository = OrderRepository(tmp_path / "orders.json")
    assert repository.get_by_id(first["id"])["total"] == first["total"]
    assert repository.create({"customer_id": 2})["id"] == first["id"] + 1


def test_order_repository_get_by_customer(tmp_path):
    repository = OrderRepository(tmp_path / "orders.json")
    ana_first = repository.create({"customer_id": ANA_ID, "total": 1})
    repository.create({"customer_id": 2, "total": 2})
    ana_second = repository.create({"customer_id": ANA_ID, "total": 3})

    assert repository.get_by_customer(ANA_ID) == [ana_first, ana_second]
    assert repository.get_by_customer(99) == []
    assert repository.get_by_id(99) is None


def test_service_checkout_saves_and_returns_the_order(checkout_service, client, tmp_path):
    add_pizza_and_salad(client)

    order = checkout_service.checkout(ANA_ID)

    assert order["status"] == "placed"
    assert order["customer_id"] == ANA_ID
    assert stored_orders(tmp_path) == [order]


def test_service_build_order_takes_snapshots(checkout_service):
    customer = {"id": ANA_ID, "delivery_address": "12 Snapshot Street"}
    menu_items = [{"id": PIZZA, "name": "Pepperoni Pizza", "price": 16.99}]

    order = checkout_service.build_order(customer, cart_record(), menu_items)

    assert order["delivery_address"] == "12 Snapshot Street"
    assert order["items"] == [
        {"menu_item_id": PIZZA, "name": "Pepperoni Pizza", "unit_price": 16.99, "quantity": 2, "line_total": 33.98}
    ]
    assert order["status"] == "placed"
    assert datetime.fromisoformat(order["created_at"]).tzinfo is not None


def test_checkout_201_is_documented(client):
    responses = client.get("/openapi.json").json()["paths"]["/checkout"]["post"]["responses"]

    assert "201" in responses


# --- 4.5: close the cart only after the order is saved ---


def stored_carts(tmp_path) -> list[dict]:
    return json.loads((tmp_path / "carts.json").read_text(encoding="utf-8"))


@pytest.fixture
def server_error_client():
    # Return the 500 response instead of re-raising the error inside the test
    return TestClient(app, raise_server_exceptions=False)


def test_checkout_closes_the_cart(client, tmp_path):
    add_pizza_and_salad(client)

    order = client.post("/checkout", headers=ANA).json()

    cart = stored_carts(tmp_path)[0]
    assert cart["id"] == order["cart_id"]
    assert cart["status"] == "checked_out"
    # The items stay as a record of what was ordered
    assert [line["menu_item_id"] for line in cart["items"]] == [PIZZA, SALAD]


def test_after_checkout_get_cart_returns_a_new_empty_cart(client):
    add_pizza_and_salad(client)
    order = client.post("/checkout", headers=ANA).json()

    cart = client.get("/cart", headers=ANA).json()

    assert cart["id"] != order["cart_id"]
    assert cart["status"] == "active"
    assert cart["items"] == [] and cart["restaurant_id"] is None and cart["total"] == 0.0


def test_new_cart_after_checkout_can_use_another_restaurant(client):
    add_pizza_and_salad(client)
    client.post("/checkout", headers=ANA)

    response = client.post("/cart/items", json={"menu_item_id": 4, "quantity": 1}, headers=ANA)

    assert response.status_code == 200
    assert response.json()["restaurant_id"] == 2


def test_checking_out_twice_creates_only_one_order(client, tmp_path):
    add_pizza_and_salad(client)

    first = client.post("/checkout", headers=ANA)
    second = client.post("/checkout", headers=ANA)

    assert first.status_code == 201
    assert second.status_code == 400  # the closed cart is no longer active, so there is nothing to check out
    assert len(stored_orders(tmp_path)) == 1


def test_order_save_failure_leaves_the_cart_unchanged(server_error_client, tmp_path, monkeypatch):
    add_pizza_and_salad(server_error_client)
    carts_before = stored_carts(tmp_path)

    def failing_save(self, records):
        raise OSError("disk full")

    monkeypatch.setattr(OrderRepository, "save", failing_save)

    response = server_error_client.post("/checkout", headers=ANA)

    assert response.status_code == 500
    assert response.json() == {"detail": "Data storage error"}
    assert stored_carts(tmp_path) == carts_before
    assert stored_orders(tmp_path) == []


def test_after_a_failed_save_the_same_cart_can_be_checked_out(server_error_client, tmp_path, monkeypatch):
    add_pizza_and_salad(server_error_client)
    original_save = OrderRepository.save

    def failing_save(self, records):
        raise OSError("disk full")

    monkeypatch.setattr(OrderRepository, "save", failing_save)
    assert server_error_client.post("/checkout", headers=ANA).status_code == 500

    monkeypatch.setattr(OrderRepository, "save", original_save)
    assert server_error_client.post("/checkout", headers=ANA).status_code == 201
    assert len(stored_orders(tmp_path)) == 1


def test_cart_is_closed_only_after_the_order_is_saved(checkout_service, client, monkeypatch):
    add_pizza_and_salad(client)
    events = []
    original_create = checkout_service.order_repository.create
    original_close = checkout_service.cart_service.mark_checked_out

    def create(order):
        events.append("order saved")
        return original_create(order)

    def close(cart_id):
        events.append("cart closed")
        return original_close(cart_id)

    monkeypatch.setattr(checkout_service.order_repository, "create", create)
    monkeypatch.setattr(checkout_service.cart_service, "mark_checked_out", close)

    checkout_service.checkout(ANA_ID)

    assert events == ["order saved", "cart closed"]


def test_order_saved_but_cart_not_closed_is_not_ordered_twice(checkout_service, client, tmp_path, monkeypatch):
    add_pizza_and_salad(client)

    def crash(cart_id):
        raise OSError("crashed before closing the cart")

    # Only this service instance crashes; the API below builds fresh services
    monkeypatch.setattr(checkout_service.cart_service, "mark_checked_out", crash)
    with pytest.raises(OSError):
        checkout_service.checkout(ANA_ID)
    assert stored_carts(tmp_path)[0]["status"] == "active"

    # Trying again finds the saved order for this cart, closes the cart and refuses a second order
    response = client.post("/checkout", headers=ANA)

    assert response.status_code == 409
    assert response.json()["detail"] == "Cart 1 has already been checked out as order 1"
    assert len(stored_orders(tmp_path)) == 1
    assert stored_carts(tmp_path)[0]["status"] == "checked_out"


def test_service_mark_checked_out(checkout_service, client):
    add_pizza_and_salad(client)

    cart = checkout_service.cart_service.mark_checked_out(1)

    assert cart["status"] == "checked_out"
    assert checkout_service.cart_repository.get_active_for_customer(ANA_ID) is None
    with pytest.raises(Exception):
        checkout_service.cart_service.mark_checked_out(999)


def test_order_repository_get_by_cart_id(tmp_path):
    repository = OrderRepository(tmp_path / "orders.json")
    order = repository.create({"customer_id": ANA_ID, "cart_id": 7})

    assert repository.get_by_cart_id(7) == order
    assert repository.get_by_cart_id(8) is None
