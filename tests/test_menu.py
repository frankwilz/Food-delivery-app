"""Tests for the menu vertical slice: route -> MenuService -> MenuRepository -> menu_items.json.

Every test runs against temporary copies of the data files (see the autouse
`isolated_data` fixture in conftest.py), so data/menu_items.json is never modified.
"""
import json

import pytest

from app.core.config import BASE_DIR
from app.repositories.menu_repository import MenuRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.menu_item import MenuItemCreate, MenuItemUpdate
from app.services.menu_service import (
    DuplicateMenuItemError,
    EmptyUpdateError,
    MenuItemNotFoundError,
    MenuService,
    RestaurantNotFoundError,
)

NEW_ITEM = {
    "name": "Garlic Bread",
    "description": "Toasted baguette with garlic butter",
    "price": 6.49,
    "category": "Appetizer",
}


# ---------------------------------------------------------------- GET menu


def test_list_menu_returns_only_that_restaurants_items(client):
    response = client.get("/restaurants/1/menu")

    assert response.status_code == 200
    items = response.json()
    assert len(items) == 4
    assert all(item["restaurant_id"] == 1 for item in items)
    assert items[0] == {
        "id": 1,
        "restaurant_id": 1,
        "name": "Pepperoni Pizza",
        "description": "Classic pepperoni with mozzarella on a hand-tossed crust",
        "price": 16.99,
        "category": "Pizza",
        "is_available": True,
    }


def test_list_menu_unknown_restaurant_returns_404(client):
    response = client.get("/restaurants/999/menu")

    assert response.status_code == 404
    assert response.json() == {"detail": "Restaurant 999 not found"}


def test_list_menu_invalid_restaurant_id_returns_422(client):
    assert client.get("/restaurants/abc/menu").status_code == 422
    assert client.get("/restaurants/0/menu").status_code == 422


# ----------------------------------------------------------- GET menu item


def test_get_menu_item_found(client):
    response = client.get("/restaurants/2/menu/6")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 6
    assert body["name"] == "Chicken Quesadilla"
    assert body["restaurant_id"] == 2


def test_get_menu_item_not_found_returns_404(client):
    response = client.get("/restaurants/1/menu/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Menu item 999 not found for restaurant 1"


def test_get_menu_item_from_another_restaurant_returns_404(client):
    # Item 5 exists but belongs to restaurant 2.
    response = client.get("/restaurants/1/menu/5")

    assert response.status_code == 404


def test_get_menu_item_unknown_restaurant_returns_404(client):
    response = client.get("/restaurants/999/menu/1")

    assert response.status_code == 404
    assert response.json()["detail"] == "Restaurant 999 not found"


# --------------------------------------------------------------- POST item


def test_add_menu_item_returns_201_with_new_id(client):
    response = client.post("/restaurants/1/menu", json=NEW_ITEM)

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 8  # max existing id (7) + 1
    assert body["restaurant_id"] == 1
    assert body["name"] == "Garlic Bread"
    assert body["is_available"] is True  # default


def test_added_menu_item_is_persisted_and_retrievable(client):
    created = client.post("/restaurants/1/menu", json=NEW_ITEM).json()

    assert client.get(f"/restaurants/1/menu/{created['id']}").json() == created
    assert len(client.get("/restaurants/1/menu").json()) == 5


def test_add_menu_item_unknown_restaurant_returns_404(client):
    response = client.post("/restaurants/999/menu", json=NEW_ITEM)

    assert response.status_code == 404


@pytest.mark.parametrize(
    "bad_body",
    [
        {**NEW_ITEM, "price": 0},  # price must be > 0
        {**NEW_ITEM, "price": -3},
        {**NEW_ITEM, "price": "free"},  # wrong type
        {**NEW_ITEM, "name": ""},  # empty name
        {k: v for k, v in NEW_ITEM.items() if k != "name"},  # missing required field
        {**NEW_ITEM, "id": 50},  # client may not choose the id
        {**NEW_ITEM, "restaurant_id": 2},  # restaurant comes from the URL
    ],
)
def test_add_menu_item_invalid_body_returns_422(client, bad_body):
    response = client.post("/restaurants/1/menu", json=bad_body)

    assert response.status_code == 422


def test_add_duplicate_name_returns_409(client):
    response = client.post("/restaurants/1/menu", json={**NEW_ITEM, "name": "  pepperoni PIZZA "})

    assert response.status_code == 409


def test_same_name_allowed_at_different_restaurant(client):
    response = client.post("/restaurants/2/menu", json={**NEW_ITEM, "name": "Pepperoni Pizza"})

    assert response.status_code == 201


# -------------------------------------------------------------- PATCH item


def test_update_menu_item_changes_only_sent_fields(client):
    response = client.patch("/restaurants/1/menu/2", json={"price": 17.25, "is_available": False})

    assert response.status_code == 200
    body = response.json()
    assert body["price"] == 17.25
    assert body["is_available"] is False
    assert body["name"] == "Margherita Pizza"  # unchanged
    assert client.get("/restaurants/1/menu/2").json() == body  # persisted


def test_update_menu_item_not_found_returns_404(client):
    assert client.patch("/restaurants/1/menu/999", json={"price": 5}).status_code == 404


def test_update_item_through_wrong_restaurant_returns_404(client):
    response = client.patch("/restaurants/1/menu/5", json={"price": 1.0})

    assert response.status_code == 404
    assert client.get("/restaurants/2/menu/5").json()["price"] == 2.49  # untouched


def test_update_with_empty_body_returns_400(client):
    assert client.patch("/restaurants/1/menu/1", json={}).status_code == 400


def test_update_with_invalid_price_returns_422(client):
    assert client.patch("/restaurants/1/menu/1", json={"price": -1}).status_code == 422


def test_update_cannot_change_id_or_restaurant(client):
    response = client.patch("/restaurants/1/menu/1", json={"id": 99, "restaurant_id": 2})

    assert response.status_code == 422


def test_update_to_duplicate_name_returns_409(client):
    response = client.patch("/restaurants/1/menu/2", json={"name": "Caesar Salad"})

    assert response.status_code == 409


def test_update_keeping_own_name_is_allowed(client):
    response = client.patch("/restaurants/1/menu/2", json={"name": "Margherita Pizza", "price": 15.0})

    assert response.status_code == 200


# --------------------------------------------------------------- repository


def test_repository_get_by_restaurant(tmp_path):
    repository = MenuRepository(tmp_path / "menu_items.json")

    items = repository.get_by_restaurant(2)

    assert [item["id"] for item in items] == [5, 6, 7]


def test_repository_get_by_id_missing_returns_none(tmp_path):
    repository = MenuRepository(tmp_path / "menu_items.json")

    assert repository.get_by_id(999) is None


def test_repository_create_writes_to_file(tmp_path):
    path = tmp_path / "menu_items.json"
    repository = MenuRepository(path)

    created = repository.create({"restaurant_id": 2, "name": "Churros", "description": "",
                                 "price": 3.0, "category": "Dessert", "is_available": True})

    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert created["id"] == 8
    assert on_disk[-1] == created


def test_repository_create_in_empty_file_starts_at_id_1(tmp_path):
    path = tmp_path / "empty.json"
    path.write_text("[]", encoding="utf-8")

    created = MenuRepository(path).create({"restaurant_id": 1, "name": "X", "price": 1.0})

    assert created["id"] == 1


def test_repository_update_never_changes_identifiers(tmp_path):
    repository = MenuRepository(tmp_path / "menu_items.json")

    updated = repository.update(1, {"id": 42, "restaurant_id": 2, "price": 1.5})

    assert updated["id"] == 1
    assert updated["restaurant_id"] == 1
    assert updated["price"] == 1.5


def test_repository_update_missing_returns_none(tmp_path):
    repository = MenuRepository(tmp_path / "menu_items.json")

    assert repository.update(999, {"price": 1.0}) is None


def test_repository_missing_file_raises_error(tmp_path):
    repository = MenuRepository(tmp_path / "does_not_exist.json")

    with pytest.raises(FileNotFoundError):
        repository.get_all()


def test_data_survives_restart(tmp_path):
    """Simulates a server restart: a brand-new repository/service reading the same file
    sees the item created by the previous one, with the same id."""
    first = MenuService(MenuRepository(tmp_path / "menu_items.json"),
                        RestaurantRepository(tmp_path / "restaurants.json"))
    created = first.add_menu_item(1, MenuItemCreate(**NEW_ITEM))

    restarted = MenuService(MenuRepository(tmp_path / "menu_items.json"),
                            RestaurantRepository(tmp_path / "restaurants.json"))

    assert restarted.get_menu_item(1, created.id) == created


# ------------------------------------------------------------------ service


@pytest.fixture
def service(tmp_path):
    return MenuService(MenuRepository(tmp_path / "menu_items.json"),
                       RestaurantRepository(tmp_path / "restaurants.json"))


def test_service_raises_for_unknown_restaurant(service):
    with pytest.raises(RestaurantNotFoundError):
        service.list_menu(999)


def test_service_raises_for_item_owned_by_other_restaurant(service):
    with pytest.raises(MenuItemNotFoundError):
        service.get_menu_item(1, 5)


def test_service_rejects_duplicate_name(service):
    with pytest.raises(DuplicateMenuItemError):
        service.add_menu_item(2, MenuItemCreate(**{**NEW_ITEM, "name": "crunchy taco"}))


def test_service_rejects_empty_update(service):
    with pytest.raises(EmptyUpdateError):
        service.update_menu_item(1, 1, MenuItemUpdate())


# ------------------------------------------------------------ data integrity


def test_committed_menu_data_is_valid_and_consistent():
    """The real data files: every item validates, ids are unique, and every
    restaurant_id points to a restaurant that exists."""
    from app.schemas.menu_item import MenuItem

    items = json.loads((BASE_DIR / "data" / "menu_items.json").read_text(encoding="utf-8"))
    restaurants = json.loads((BASE_DIR / "data" / "restaurants.json").read_text(encoding="utf-8"))
    restaurant_ids = {r["id"] for r in restaurants}

    for item in items:
        MenuItem(**item)
    assert len({item["id"] for item in items}) == len(items)
    assert all(item["restaurant_id"] in restaurant_ids for item in items)


def test_menu_endpoints_are_documented(client):
    paths = client.get("/openapi.json").json()["paths"]

    menu = paths["/restaurants/{restaurant_id}/menu"]
    item = paths["/restaurants/{restaurant_id}/menu/{item_id}"]
    assert {"get", "post"} <= menu.keys()
    assert {"get", "patch"} <= item.keys()
    assert "404" in menu["get"]["responses"]
    assert "409" in menu["post"]["responses"]
    assert menu["get"]["description"]
