"""Tests for the shopping cart."""

import json

import pytest

from app.core.errors import ForbiddenError, NotFoundError
from app.core.security import create_access_token
from app.repositories.cart_repository import CartRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.menu_item_repository import MenuItemRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.cart import MAX_QUANTITY, CartItemAdd
from app.services.cart_service import CartService, DifferentRestaurantError, ItemNotInCartError, QuantityLimitError
from app.services.customer_service import CustomerService
from app.services.menu_service import MenuItemDeactivatedError, MenuItemUnavailableError, MenuService

# From data/customers.json and data/menu_items.json
ANA_ID, BEN_ID, CHLOE_DEACTIVATED_ID = 1, 2, 3
PIZZA, SALAD, WINGS_UNAVAILABLE = 1, 2, 3  # restaurant 1: 16.99, 9.49, unavailable
CRUNCHWRAP = 4  # restaurant 2: 6.49


def auth(customer_id: int) -> dict:
    return {"Authorization": f"Bearer {create_access_token(customer_id)}"}


ANA, BEN, CHLOE = auth(ANA_ID), auth(BEN_ID), auth(CHLOE_DEACTIVATED_ID)


def stored_carts(tmp_path) -> list[dict]:
    return json.loads((tmp_path / "carts.json").read_text(encoding="utf-8"))


def add(client, item_id: int, quantity: int = 1, headers=None):
    return client.post("/cart/items", json={"menu_item_id": item_id, "quantity": quantity}, headers=headers or ANA)


@pytest.fixture
def service(tmp_path) -> CartService:
    return CartService(
        CartRepository(tmp_path / "carts.json"),
        MenuService(MenuItemRepository(tmp_path / "menu_items.json"), RestaurantRepository(tmp_path / "restaurants.json")),
        CustomerService(CustomerRepository(tmp_path / "customers.json")),
    )


# --- 3.2 GET /cart: create/retrieve the active cart ---


def test_get_cart_creates_an_empty_active_cart(client, tmp_path):
    response = client.get("/cart", headers=ANA)

    assert response.status_code == 200
    assert response.json() == {"id": 1, "customer_id": ANA_ID, "restaurant_id": None, "items": [], "status": "active"}
    assert stored_carts(tmp_path) == [
        {"id": 1, "customer_id": ANA_ID, "restaurant_id": None, "items": [], "status": "active"}
    ]


def test_repeated_get_cart_never_creates_a_second_active_cart(client, tmp_path):
    first = client.get("/cart", headers=ANA).json()
    second = client.get("/cart", headers=ANA).json()

    assert first["id"] == second["id"]
    assert len(stored_carts(tmp_path)) == 1


def test_each_customer_gets_their_own_cart(client, tmp_path):
    ana_cart = client.get("/cart", headers=ANA).json()
    ben_cart = client.get("/cart", headers=BEN).json()

    assert ana_cart["id"] != ben_cart["id"]
    assert ben_cart["customer_id"] == BEN_ID
    assert len(stored_carts(tmp_path)) == 2


def test_cart_is_persisted_and_survives_a_new_service(client, service):
    cart_id = client.get("/cart", headers=ANA).json()["id"]

    # A fresh service reading the same file finds the same cart, as after a restart
    assert service.get_cart(ANA_ID)["id"] == cart_id


def test_deactivated_customer_gets_403_and_no_cart(client, tmp_path):
    response = client.get("/cart", headers=CHLOE)

    assert response.status_code == 403
    assert "deactivated" in response.json()["detail"]
    assert stored_carts(tmp_path) == []


def test_get_cart_requires_sign_in(client):
    assert client.get("/cart").status_code == 401


def test_service_get_cart_rejects_deactivated_customer(service):
    with pytest.raises(ForbiddenError):
        service.get_cart(CHLOE_DEACTIVATED_ID)


def test_repository_finds_only_the_active_cart(tmp_path):
    repository = CartRepository(tmp_path / "carts.json")
    repository.create({"customer_id": ANA_ID, "restaurant_id": None, "items": [], "status": "checked_out"})
    active = repository.create({"customer_id": ANA_ID, "restaurant_id": None, "items": [], "status": "active"})

    assert repository.get_active_for_customer(ANA_ID) == active
    assert repository.get_active_for_customer(BEN_ID) is None


def test_get_cart_is_documented(client):
    responses = client.get("/openapi.json").json()["paths"]["/cart"]["get"]["responses"]

    assert {"401", "403"} <= set(responses)


# --- 3.3 POST /cart/items ---


def test_add_item_returns_the_updated_cart(client, tmp_path):
    response = add(client, PIZZA, 2)

    assert response.status_code == 200
    body = response.json()
    assert body["restaurant_id"] == 1
    assert body["items"] == [{"menu_item_id": PIZZA, "quantity": 2}]
    assert stored_carts(tmp_path)[0]["items"] == [{"menu_item_id": PIZZA, "quantity": 2}]


def test_cart_stores_ids_and_quantities_only(client, tmp_path):
    add(client, PIZZA, 2)

    assert stored_carts(tmp_path)[0]["items"] == [{"menu_item_id": PIZZA, "quantity": 2}]


def test_adding_the_same_item_again_increases_its_quantity(client):
    add(client, PIZZA, 2)
    body = add(client, PIZZA, 3).json()

    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 5


def test_first_item_sets_the_cart_restaurant(client, tmp_path):
    add(client, CRUNCHWRAP)

    assert stored_carts(tmp_path)[0]["restaurant_id"] == 2


def test_items_are_added_to_the_right_customers_cart(client):
    add(client, PIZZA, headers=ANA)

    assert client.get("/cart", headers=BEN).json()["items"] == []


def test_item_from_a_different_restaurant_returns_409_and_changes_nothing(client, tmp_path):
    add(client, PIZZA)
    before = stored_carts(tmp_path)

    response = add(client, CRUNCHWRAP)

    assert response.status_code == 409
    assert "restaurant" in response.json()["detail"]
    assert stored_carts(tmp_path) == before


def test_unknown_item_returns_404(client):
    response = add(client, 999)

    assert response.status_code == 404
    assert response.json()["detail"] == "Menu item 999 not found"


def test_unavailable_item_returns_409(client):
    response = add(client, WINGS_UNAVAILABLE)

    assert response.status_code == 409
    assert "unavailable" in response.json()["detail"]


def test_deactivated_item_returns_409(client):
    client.delete(f"/restaurants/1/menu/{SALAD}")

    response = add(client, SALAD)

    assert response.status_code == 409
    assert "no longer on the menu" in response.json()["detail"]


@pytest.mark.parametrize("quantity", [0, -1, 1.5, 2.0, "2", True, None, MAX_QUANTITY + 1])
def test_add_invalid_quantity_returns_422(client, tmp_path, quantity):
    response = client.post("/cart/items", json={"menu_item_id": PIZZA, "quantity": quantity}, headers=ANA)

    assert response.status_code == 422
    assert all(cart["items"] == [] for cart in stored_carts(tmp_path))


@pytest.mark.parametrize("body", [{}, {"quantity": 1}, {"menu_item_id": PIZZA}, {"menu_item_id": PIZZA, "quantity": 1, "price": 0.01}])
def test_add_invalid_body_returns_422(client, body):
    assert client.post("/cart/items", json=body, headers=ANA).status_code == 422


def test_add_beyond_the_maximum_combined_quantity_returns_400(client):
    add(client, PIZZA, MAX_QUANTITY)

    response = add(client, PIZZA, 1)

    assert response.status_code == 400
    assert str(MAX_QUANTITY) in response.json()["detail"]


def test_add_item_requires_sign_in(client):
    assert client.post("/cart/items", json={"menu_item_id": PIZZA, "quantity": 1}).status_code == 401


def test_deactivated_customer_cannot_add_items(client):
    assert add(client, PIZZA, headers=CHLOE).status_code == 403


def test_service_add_item_rules(service):
    service.add_item(ANA_ID, CartItemAdd(menu_item_id=PIZZA, quantity=1))

    with pytest.raises(DifferentRestaurantError):
        service.add_item(ANA_ID, CartItemAdd(menu_item_id=CRUNCHWRAP, quantity=1))
    with pytest.raises(MenuItemUnavailableError):
        service.add_item(ANA_ID, CartItemAdd(menu_item_id=WINGS_UNAVAILABLE, quantity=1))
    with pytest.raises(NotFoundError):
        service.add_item(ANA_ID, CartItemAdd(menu_item_id=999, quantity=1))
    with pytest.raises(QuantityLimitError):
        service.add_item(ANA_ID, CartItemAdd(menu_item_id=PIZZA, quantity=MAX_QUANTITY))


def test_service_add_deactivated_item(service):
    service.menu_service.deactivate_menu_item(1, SALAD)

    with pytest.raises(MenuItemDeactivatedError):
        service.add_item(ANA_ID, CartItemAdd(menu_item_id=SALAD, quantity=1))


def test_add_item_is_documented(client):
    responses = client.get("/openapi.json").json()["paths"]["/cart/items"]["post"]["responses"]

    assert {"400", "401", "403", "404", "409"} <= set(responses)


# --- 3.4 PATCH /cart/items/{menu_item_id} ---


def test_update_quantity(client, tmp_path):
    add(client, PIZZA, 1)

    response = client.patch(f"/cart/items/{PIZZA}", json={"quantity": 4}, headers=ANA)

    assert response.status_code == 200
    assert response.json()["items"][0]["quantity"] == 4
    assert stored_carts(tmp_path)[0]["items"] == [{"menu_item_id": PIZZA, "quantity": 4}]


def test_update_changes_only_that_item(client):
    add(client, PIZZA, 1)
    add(client, SALAD, 2)

    body = client.patch(f"/cart/items/{PIZZA}", json={"quantity": 5}, headers=ANA).json()

    assert {line["menu_item_id"]: line["quantity"] for line in body["items"]} == {PIZZA: 5, SALAD: 2}


def test_update_item_not_in_cart_returns_404(client):
    add(client, PIZZA)

    response = client.patch(f"/cart/items/{SALAD}", json={"quantity": 2}, headers=ANA)

    assert response.status_code == 404
    assert response.json()["detail"] == f"Menu item {SALAD} is not in the cart"


@pytest.mark.parametrize("quantity", [0, -3, 2.5, 3.0, "3", MAX_QUANTITY + 1])
def test_update_invalid_quantity_returns_422_and_changes_nothing(client, tmp_path, quantity):
    add(client, PIZZA, 1)
    before = stored_carts(tmp_path)

    response = client.patch(f"/cart/items/{PIZZA}", json={"quantity": quantity}, headers=ANA)

    assert response.status_code == 422
    assert stored_carts(tmp_path) == before


def test_update_requires_sign_in(client):
    assert client.patch(f"/cart/items/{PIZZA}", json={"quantity": 2}).status_code == 401


def test_deactivated_customer_cannot_update(client):
    assert client.patch(f"/cart/items/{PIZZA}", json={"quantity": 2}, headers=CHLOE).status_code == 403


def test_service_update_item_not_in_cart(service):
    with pytest.raises(ItemNotInCartError):
        service.update_quantity(ANA_ID, PIZZA, 2)


def test_update_is_documented(client):
    responses = client.get("/openapi.json").json()["paths"]["/cart/items/{menu_item_id}"]["patch"]["responses"]

    assert {"401", "403", "404", "422"} <= set(responses)
