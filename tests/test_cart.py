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
from app.services.pricing import price_lines

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
    assert response.json() == {
        "id": 1,
        "customer_id": ANA_ID,
        "restaurant_id": None,
        "status": "active",
        "items": [],
        "subtotal": 0.0,
        "total": 0.0,
    }
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
    assert [(line["menu_item_id"], line["quantity"]) for line in body["items"]] == [(PIZZA, 2)]
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


# --- 3.5 DELETE /cart/items/{menu_item_id} and DELETE /cart ---


def test_remove_one_item(client):
    add(client, PIZZA)
    add(client, SALAD)

    response = client.delete(f"/cart/items/{PIZZA}", headers=ANA)

    assert response.status_code == 200
    assert [line["menu_item_id"] for line in response.json()["items"]] == [SALAD]
    assert response.json()["restaurant_id"] == 1


def test_remove_item_not_in_cart_returns_404(client):
    response = client.delete(f"/cart/items/{PIZZA}", headers=ANA)

    assert response.status_code == 404
    assert response.json()["detail"] == f"Menu item {PIZZA} is not in the cart"


def test_removing_the_last_item_resets_the_restaurant(client, tmp_path):
    add(client, PIZZA)

    body = client.delete(f"/cart/items/{PIZZA}", headers=ANA).json()

    assert body["items"] == []
    assert body["restaurant_id"] is None
    assert stored_carts(tmp_path)[0]["restaurant_id"] is None
    # So an item from another restaurant can now be added
    assert add(client, CRUNCHWRAP).status_code == 200


def test_clear_cart_empties_it_and_resets_the_restaurant(client, tmp_path):
    add(client, PIZZA, 2)
    add(client, SALAD)

    response = client.delete("/cart", headers=ANA)

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["restaurant_id"] is None
    cart = stored_carts(tmp_path)[0]
    assert cart["items"] == [] and cart["restaurant_id"] is None and cart["status"] == "active"
    assert add(client, CRUNCHWRAP).status_code == 200


def test_clearing_an_empty_cart_succeeds(client):
    assert client.delete("/cart", headers=ANA).status_code == 200


@pytest.mark.parametrize("path", [f"/cart/items/{PIZZA}", "/cart"])
def test_remove_and_clear_require_sign_in(client, path):
    assert client.delete(path).status_code == 401


@pytest.mark.parametrize("path", [f"/cart/items/{PIZZA}", "/cart"])
def test_deactivated_customer_cannot_remove_or_clear(client, path):
    assert client.delete(path, headers=CHLOE).status_code == 403


def test_service_clear_by_cart_id(service):
    cart = service.add_item(ANA_ID, CartItemAdd(menu_item_id=PIZZA, quantity=1))

    cleared = service.clear(cart["id"])

    assert cleared["items"] == [] and cleared["restaurant_id"] is None


def test_service_clear_unknown_cart(service):
    with pytest.raises(NotFoundError):
        service.clear(999)


def test_service_remove_item_not_in_cart(service):
    with pytest.raises(ItemNotInCartError):
        service.remove_item(ANA_ID, PIZZA)


def test_remove_and_clear_are_documented(client):
    paths = client.get("/openapi.json").json()["paths"]

    assert {"401", "403", "404"} <= set(paths["/cart/items/{menu_item_id}"]["delete"]["responses"])
    assert {"401", "403"} <= set(paths["/cart"]["delete"]["responses"])


# --- 3.6 Subtotal and total ---


def test_cart_lines_are_priced_from_the_menu(client):
    body = add(client, PIZZA, 2).json()

    assert body["items"] == [
        {
            "menu_item_id": PIZZA,
            "name": "Pepperoni Pizza",
            "unit_price": 16.99,
            "quantity": 2,
            "line_total": 33.98,
            "is_orderable": True,
        }
    ]
    assert body["subtotal"] == 33.98
    assert body["total"] == 33.98


def test_totals_for_several_items_and_quantities(client):
    add(client, PIZZA, 3)  # 3 × 16.99 = 50.97
    body = add(client, SALAD, 2).json()  # 2 × 9.49 = 18.98

    assert [line["line_total"] for line in body["items"]] == [50.97, 18.98]
    assert body["subtotal"] == 69.95
    assert body["total"] == 69.95


def test_every_cart_response_is_priced(client):
    add(client, PIZZA, 1)

    assert client.patch(f"/cart/items/{PIZZA}", json={"quantity": 4}, headers=ANA).json()["total"] == 67.96
    assert client.get("/cart", headers=ANA).json()["total"] == 67.96
    add(client, SALAD, 1)
    assert client.delete(f"/cart/items/{PIZZA}", headers=ANA).json()["total"] == 9.49
    assert client.delete("/cart", headers=ANA).json()["total"] == 0.0


def test_price_change_is_reflected_in_the_next_cart_response(client):
    add(client, PIZZA, 2)

    client.patch(f"/restaurants/1/menu/{PIZZA}", json={"price": 18.5})

    body = client.get("/cart", headers=ANA).json()
    assert body["items"][0]["unit_price"] == 18.5
    assert body["total"] == 37.0


def test_prices_are_never_stored_in_the_cart(client, tmp_path):
    add(client, PIZZA, 2)

    assert stored_carts(tmp_path)[0]["items"] == [{"menu_item_id": PIZZA, "quantity": 2}]


def test_item_that_became_unavailable_stays_in_the_cart_marked_not_orderable(client):
    add(client, PIZZA)

    client.patch(f"/restaurants/1/menu/{PIZZA}", json={"is_available": False})

    line = client.get("/cart", headers=ANA).json()["items"][0]
    assert line["is_orderable"] is False


def test_pricing_avoids_float_errors():
    # With floats, 0.1 + 0.2 == 0.30000000000000004
    result = price_lines([({"id": 1, "name": "A", "price": 0.1}, 1), ({"id": 2, "name": "B", "price": 0.2}, 1)])

    assert result["subtotal"] == 0.3


def test_pricing_rounds_half_up_to_cents():
    result = price_lines([({"id": 1, "name": "A", "price": 1.005}, 1), ({"id": 2, "name": "B", "price": 0.125}, 3)])

    assert [line["line_total"] for line in result["items"]] == [1.01, 0.38]
    assert result["subtotal"] == 1.39
    assert result["total"] == result["subtotal"]


def test_pricing_empty_cart():
    assert price_lines([]) == {"items": [], "subtotal": 0.0, "total": 0.0}
