"""Tests for 4.1 (#43): validate the cart before checkout."""

import json

import pytest

from app.core.errors import ForbiddenError, RestaurantNotFoundError
from app.core.security import create_access_token
from app.repositories.cart_repository import CartRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.menu_item_repository import MenuItemRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.services.cart_service import CartService
from app.services.checkout_service import (
    CheckoutService,
    EmptyCartError,
    InvalidCartQuantityError,
    RestaurantClosedError,
)
from app.services.customer_service import CustomerService
from app.services.menu_service import MenuService

ANA_ID, CHLOE_DEACTIVATED_ID = 1, 3
PIZZA, SALAD = 1, 2  # restaurant 1


def auth(customer_id: int) -> dict:
    return {"Authorization": f"Bearer {create_access_token(customer_id)}"}


ANA = auth(ANA_ID)


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
    return CheckoutService(customers, carts, restaurants, CartService(carts, menu, customers))


# --- success ---


def test_checkout_of_a_valid_cart_returns_it_priced(client):
    client.post("/cart/items", json={"menu_item_id": PIZZA, "quantity": 2}, headers=ANA)
    client.post("/cart/items", json={"menu_item_id": SALAD, "quantity": 1}, headers=ANA)

    response = client.post("/checkout", headers=ANA)

    assert response.status_code == 200
    body = response.json()
    assert body["restaurant_id"] == 1
    assert body["total"] == 43.47  # 2 × 16.99 + 9.49


def test_checkout_uses_current_menu_prices(client):
    client.post("/cart/items", json={"menu_item_id": PIZZA, "quantity": 2}, headers=ANA)
    client.patch(f"/restaurants/1/menu/{PIZZA}", json={"price": 20})

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
    client.patch("/restaurants/1", json={"is_open": False})
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
