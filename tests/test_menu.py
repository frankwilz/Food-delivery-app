import json

import pytest

from app.core.config import BASE_DIR
from app.repositories.menu_item_repository import MenuItemRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.menu_item import MenuItem, MenuItemCreate
from app.services.menu_service import MenuService

VALID_ITEM = {
    "name": "Garlic Bread",
    "description": "Toasted with garlic butter",
    "price": 5.99,
    "category": "Appetizers",
}


# --- GET /restaurants/{restaurant_id}/menu ---


def test_list_menu_returns_only_that_restaurants_items(client):
    response = client.get("/restaurants/1/menu")

    assert response.status_code == 200
    data = response.json()
    assert [item["id"] for item in data] == [1, 2, 3]
    assert all(item["restaurant_id"] == 1 for item in data)
    assert data[0]["name"] == "Pepperoni Pizza"


def test_list_menu_unknown_restaurant_returns_404(client):
    response = client.get("/restaurants/999/menu")

    assert response.status_code == 404
    assert response.json()["detail"] == "Restaurant 999 not found"


def test_list_menu_non_integer_restaurant_id_returns_422(client):
    response = client.get("/restaurants/abc/menu")

    assert response.status_code == 422


# --- GET /restaurants/{restaurant_id}/menu/{item_id} ---


def test_get_menu_item_returns_item(client):
    response = client.get("/restaurants/2/menu/4")

    assert response.status_code == 200
    assert response.json() == {
        "id": 4,
        "restaurant_id": 2,
        "name": "Crunchwrap Supreme",
        "description": "Seasoned beef, nacho cheese and a crunchy tostada shell",
        "price": 6.49,
        "category": "Mains",
        "is_available": True,
    }


def test_get_menu_item_unknown_item_returns_404(client):
    response = client.get("/restaurants/1/menu/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Menu item 999 not found for restaurant 1"


def test_get_menu_item_from_other_restaurant_returns_404(client):
    # Item 4 exists but belongs to restaurant 2
    response = client.get("/restaurants/1/menu/4")

    assert response.status_code == 404


def test_get_menu_item_unknown_restaurant_returns_404(client):
    response = client.get("/restaurants/999/menu/1")

    assert response.status_code == 404
    assert response.json()["detail"] == "Restaurant 999 not found"


# --- POST /restaurants/{restaurant_id}/menu ---


def test_create_menu_item_returns_201_and_persists(client):
    response = client.post("/restaurants/1/menu", json=VALID_ITEM)

    assert response.status_code == 201
    created = response.json()
    assert created == {"id": 6, "restaurant_id": 1, "is_available": True, **VALID_ITEM}

    fetched = client.get("/restaurants/1/menu/6")
    assert fetched.status_code == 200
    assert fetched.json() == created
    assert len(client.get("/restaurants/1/menu").json()) == 4


def test_create_menu_item_applies_defaults(client):
    response = client.post(
        "/restaurants/2/menu",
        json={"name": "Nachos", "price": 3.5, "category": "Sides"},
    )

    assert response.status_code == 201
    assert response.json()["description"] == ""
    assert response.json()["is_available"] is True


def test_create_menu_item_unknown_restaurant_returns_404(client):
    response = client.post("/restaurants/999/menu", json=VALID_ITEM)

    assert response.status_code == 404
    assert len(client.get("/restaurants/1/menu").json()) == 3


@pytest.mark.parametrize(
    "payload",
    [
        {**VALID_ITEM, "price": 0},
        {**VALID_ITEM, "price": -4.5},
        {**VALID_ITEM, "price": "cheap"},
        {**VALID_ITEM, "name": ""},
        {**VALID_ITEM, "name": "   "},
        {**VALID_ITEM, "category": ""},
        {key: value for key, value in VALID_ITEM.items() if key != "name"},
        {key: value for key, value in VALID_ITEM.items() if key != "price"},
        {**VALID_ITEM, "id": 42},
        {**VALID_ITEM, "restaurant_id": 2},
    ],
    ids=[
        "zero-price",
        "negative-price",
        "non-numeric-price",
        "empty-name",
        "blank-name",
        "empty-category",
        "missing-name",
        "missing-price",
        "client-supplied-id",
        "client-supplied-restaurant-id",
    ],
)
def test_create_menu_item_invalid_input_returns_422(client, payload):
    response = client.post("/restaurants/1/menu", json=payload)

    assert response.status_code == 422
    assert len(client.get("/restaurants/1/menu").json()) == 3


# --- PATCH /restaurants/{restaurant_id}/menu/{item_id} ---


def test_update_menu_item_changes_only_given_fields(client):
    response = client.patch("/restaurants/1/menu/3", json={"price": 12.5, "is_available": True})

    assert response.status_code == 200
    updated = response.json()
    assert updated["price"] == 12.5
    assert updated["is_available"] is True
    assert updated["name"] == "Chicken Wings"
    assert updated["restaurant_id"] == 1

    assert client.get("/restaurants/1/menu/3").json() == updated


def test_update_menu_item_unknown_item_returns_404(client):
    response = client.patch("/restaurants/1/menu/999", json={"price": 10})

    assert response.status_code == 404


def test_update_menu_item_from_other_restaurant_returns_404(client):
    response = client.patch("/restaurants/1/menu/4", json={"price": 10})

    assert response.status_code == 404
    assert client.get("/restaurants/2/menu/4").json()["price"] == 6.49


def test_update_menu_item_unknown_restaurant_returns_404(client):
    response = client.patch("/restaurants/999/menu/1", json={"price": 10})

    assert response.status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"price": -1},
        {"name": ""},
        {"name": None},
        {"restaurant_id": 2},
        {"id": 99},
    ],
    ids=["negative-price", "empty-name", "null-name", "change-restaurant", "change-id"],
)
def test_update_menu_item_invalid_input_returns_422(client, payload):
    response = client.patch("/restaurants/1/menu/1", json=payload)

    assert response.status_code == 422
    assert client.get("/restaurants/1/menu/1").json()["name"] == "Pepperoni Pizza"


# --- Data isolation ---


def test_writes_do_not_touch_committed_data(client):
    real_file = BASE_DIR / "data" / "menu_items.json"
    before = real_file.read_text(encoding="utf-8")

    client.post("/restaurants/1/menu", json=VALID_ITEM)
    client.patch("/restaurants/1/menu/1", json={"price": 1.0})

    assert real_file.read_text(encoding="utf-8") == before


# --- Repository ---


def test_repository_get_by_restaurant_id_filters_items(tmp_path):
    repository = MenuItemRepository(tmp_path / "menu_items.json")

    items = repository.get_by_restaurant_id(2)

    assert [item["id"] for item in items] == [4, 5]
    assert repository.get_by_restaurant_id(999) == []


def test_repository_get_by_id(tmp_path):
    repository = MenuItemRepository(tmp_path / "menu_items.json")

    assert repository.get_by_id(2)["name"] == "Caesar Salad"
    assert repository.get_by_id(999) is None


def test_repository_create_assigns_next_id_and_persists(tmp_path):
    repository = MenuItemRepository(tmp_path / "menu_items.json")

    created = repository.create({"restaurant_id": 2, "name": "Soda", "price": 1.99})

    assert created["id"] == 6
    reloaded = MenuItemRepository(tmp_path / "menu_items.json")
    assert reloaded.get_by_id(6) == created


def test_repository_create_uses_max_id_not_count(tmp_path):
    file_path = tmp_path / "gaps.json"
    file_path.write_text(json.dumps([{"id": 1, "restaurant_id": 1}, {"id": 7, "restaurant_id": 1}]))
    repository = MenuItemRepository(file_path)

    assert repository.create({"restaurant_id": 1})["id"] == 8


def test_repository_create_in_empty_file_starts_at_1(tmp_path):
    file_path = tmp_path / "empty.json"
    file_path.write_text("[]")
    repository = MenuItemRepository(file_path)

    assert repository.create({"restaurant_id": 1})["id"] == 1


def test_repository_update_persists_changes(tmp_path):
    repository = MenuItemRepository(tmp_path / "menu_items.json")

    updated = repository.update(1, {"price": 18.0})

    assert updated["price"] == 18.0
    assert updated["name"] == "Pepperoni Pizza"
    assert MenuItemRepository(tmp_path / "menu_items.json").get_by_id(1)["price"] == 18.0


def test_repository_update_missing_item_returns_none(tmp_path):
    repository = MenuItemRepository(tmp_path / "menu_items.json")

    assert repository.update(999, {"price": 1.0}) is None


def test_repository_missing_file_raises_error(tmp_path):
    repository = MenuItemRepository(tmp_path / "does_not_exist.json")

    with pytest.raises(FileNotFoundError):
        repository.get_all()


# --- Duplicate names (409) ---


def test_create_duplicate_name_returns_409(client):
    # Same name as item 1, different case and extra spaces
    response = client.post("/restaurants/1/menu", json={**VALID_ITEM, "name": "  pepperoni PIZZA "})

    assert response.status_code == 409
    assert response.json()["detail"] == "Restaurant 1 already has a menu item named 'pepperoni PIZZA'"
    assert len(client.get("/restaurants/1/menu").json()) == 3


def test_same_name_allowed_at_a_different_restaurant(client):
    response = client.post("/restaurants/2/menu", json={**VALID_ITEM, "name": "Pepperoni Pizza"})

    assert response.status_code == 201


def test_update_to_duplicate_name_returns_409(client):
    response = client.patch("/restaurants/1/menu/2", json={"name": "Chicken Wings"})

    assert response.status_code == 409
    assert client.get("/restaurants/1/menu/2").json()["name"] == "Caesar Salad"


def test_update_keeping_own_name_is_allowed(client):
    response = client.patch("/restaurants/1/menu/2", json={"name": "Caesar Salad", "price": 9.99})

    assert response.status_code == 200
    assert response.json()["price"] == 9.99


# --- Empty update (400) ---


def test_update_with_empty_body_returns_400(client):
    response = client.patch("/restaurants/1/menu/1", json={})

    assert response.status_code == 400
    assert response.json()["detail"] == "Update request must include at least one field"


# --- Repository safety ---


def test_repository_update_never_changes_identifiers(tmp_path):
    repository = MenuItemRepository(tmp_path / "menu_items.json")

    updated = repository.update(1, {"id": 42, "restaurant_id": 2, "price": 1.5})

    assert updated["id"] == 1
    assert updated["restaurant_id"] == 1
    assert updated["price"] == 1.5


def test_repository_save_leaves_no_temp_files(tmp_path):
    repository = MenuItemRepository(tmp_path / "menu_items.json")

    repository.create({"restaurant_id": 1, "name": "Soda", "price": 1.99})
    repository.update(1, {"price": 2.0})

    assert list(tmp_path.glob("*.tmp")) == []
    json.loads((tmp_path / "menu_items.json").read_text(encoding="utf-8"))  # still valid JSON


# --- Persistence and data integrity ---


def test_data_survives_restart(tmp_path):
    """A brand-new service (as after a server restart) sees what the previous one saved."""

    def new_service():
        return MenuService(
            MenuItemRepository(tmp_path / "menu_items.json"),
            RestaurantRepository(tmp_path / "restaurants.json"),
        )

    created = new_service().create_menu_item(1, MenuItemCreate(**VALID_ITEM))

    assert new_service().get_menu_item(1, created["id"]) == created


def test_committed_menu_data_is_valid_and_consistent():
    """Every item in data/menu_items.json is a valid MenuItem, ids are unique,
    names are unique per restaurant, and every restaurant_id points to a real restaurant."""
    items = json.loads((BASE_DIR / "data" / "menu_items.json").read_text(encoding="utf-8"))
    restaurants = json.loads((BASE_DIR / "data" / "restaurants.json").read_text(encoding="utf-8"))
    restaurant_ids = {restaurant["id"] for restaurant in restaurants}

    for item in items:
        MenuItem(**item)
    assert len({item["id"] for item in items}) == len(items)
    assert len({(item["restaurant_id"], item["name"].casefold()) for item in items}) == len(items)
    assert all(item["restaurant_id"] in restaurant_ids for item in items)


# --- API documentation ---


def test_menu_error_responses_are_documented(client):
    paths = client.get("/openapi.json").json()["paths"]
    menu = paths["/restaurants/{restaurant_id}/menu"]
    item = paths["/restaurants/{restaurant_id}/menu/{item_id}"]

    assert "404" in menu["get"]["responses"]
    assert {"201", "404", "409", "422"} <= menu["post"]["responses"].keys()
    assert {"200", "400", "404", "409", "422"} <= item["patch"]["responses"].keys()
