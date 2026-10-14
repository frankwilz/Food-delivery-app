import json

import pytest

from app.core.config import BASE_DIR
from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.restaurant import Restaurant, RestaurantCreate, RestaurantUpdate
from app.services.restaurant_service import (
    DuplicateRestaurantError,
    EmptyUpdateError,
    RestaurantNotFoundError,
    RestaurantService,
)

# Test data (copied to a temp folder by conftest.py):
#   1 Boston Pizza       Pizza     123 Kelowna Road    3.3 open
#   2 Taco Bell          Mexican   456 Okanagan Drive  2.9 open
#   3 Okanagan Sushi     Japanese  789 Bernard Avenue  4.6 closed
#   4 Lakeside Pizzeria  Pizza     12 Water Street     4.1 open

NEW_RESTAURANT = {
    "name": "Kelowna Curry House",
    "cuisine": "Indian",
    "address": "55 Pandosy Street",
    "rating": 4.4,
    "is_open": True,
}


def ids(response):
    return [restaurant["id"] for restaurant in response.json()]


# --- GET /restaurants ---


def test_list_restaurants_returns_200_and_data(client):
    response = client.get("/restaurants")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 4
    assert data[0]["id"] == 1
    assert data[0]["name"] == "Boston Pizza"


# --- Search / filter ---


def test_search_matches_name_case_insensitive(client):
    assert ids(client.get("/restaurants", params={"search": "PIZZ"})) == [1, 4]


def test_search_matches_cuisine(client):
    assert ids(client.get("/restaurants", params={"search": "japan"})) == [3]


def test_filter_by_cuisine_is_exact_and_case_insensitive(client):
    assert ids(client.get("/restaurants", params={"cuisine": "pizza"})) == [1, 4]
    assert ids(client.get("/restaurants", params={"cuisine": "Pizz"})) == []


def test_filter_by_is_open(client):
    assert ids(client.get("/restaurants", params={"is_open": "false"})) == [3]
    assert ids(client.get("/restaurants", params={"is_open": "true"})) == [1, 2, 4]


def test_filter_by_min_rating(client):
    assert ids(client.get("/restaurants", params={"min_rating": 4})) == [3, 4]


def test_filters_combine(client):
    response = client.get("/restaurants", params={"cuisine": "Pizza", "min_rating": 4, "is_open": "true"})

    assert ids(response) == [4]


def test_search_with_no_matches_returns_empty_list(client):
    response = client.get("/restaurants", params={"search": "burger"})

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize(
    "params",
    [{"min_rating": 6}, {"min_rating": -1}, {"min_rating": "high"}, {"is_open": "maybe"}],
    ids=["rating-above-5", "negative-rating", "non-numeric-rating", "non-boolean-is-open"],
)
def test_invalid_filter_returns_422(client, params):
    assert client.get("/restaurants", params=params).status_code == 422


# --- GET /restaurants/{restaurant_id} ---


def test_get_restaurant_returns_details(client):
    response = client.get("/restaurants/2")

    assert response.status_code == 200
    assert response.json() == {
        "id": 2,
        "name": "Taco Bell",
        "cuisine": "Mexican",
        "address": "456 Okanagan Drive",
        "rating": 2.9,
        "is_open": True,
    }


def test_get_unknown_restaurant_returns_404(client):
    response = client.get("/restaurants/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Restaurant 999 not found"}


def test_get_restaurant_non_integer_id_returns_422(client):
    assert client.get("/restaurants/abc").status_code == 422


# --- POST /restaurants ---


def test_create_restaurant_returns_201_with_new_id(client):
    response = client.post("/restaurants", json=NEW_RESTAURANT)

    assert response.status_code == 201
    assert response.json() == {"id": 5, **NEW_RESTAURANT}  # highest id (4) + 1


def test_created_restaurant_is_persisted(client):
    created = client.post("/restaurants", json=NEW_RESTAURANT).json()

    assert client.get(f"/restaurants/{created['id']}").json() == created
    assert len(client.get("/restaurants").json()) == 5


def test_create_restaurant_applies_defaults(client):
    response = client.post(
        "/restaurants", json={"name": "New Place", "cuisine": "Thai", "address": "1 Main Street"}
    )

    assert response.status_code == 201
    assert response.json()["rating"] == 0.0
    assert response.json()["is_open"] is True


def test_create_restaurant_trims_whitespace(client):
    response = client.post("/restaurants", json={**NEW_RESTAURANT, "name": "  Kelowna Curry House  "})

    assert response.json()["name"] == "Kelowna Curry House"


@pytest.mark.parametrize(
    "payload",
    [
        {**NEW_RESTAURANT, "name": ""},
        {**NEW_RESTAURANT, "name": "   "},
        {**NEW_RESTAURANT, "cuisine": ""},
        {**NEW_RESTAURANT, "rating": 5.5},
        {**NEW_RESTAURANT, "rating": -1},
        {**NEW_RESTAURANT, "rating": "great"},
        {key: value for key, value in NEW_RESTAURANT.items() if key != "address"},
        {**NEW_RESTAURANT, "id": 50},
        {**NEW_RESTAURANT, "owner": "someone"},
    ],
    ids=[
        "empty-name",
        "blank-name",
        "empty-cuisine",
        "rating-above-5",
        "negative-rating",
        "non-numeric-rating",
        "missing-address",
        "client-supplied-id",
        "unknown-field",
    ],
)
def test_create_restaurant_invalid_input_returns_422(client, payload):
    response = client.post("/restaurants", json=payload)

    assert response.status_code == 422
    assert len(client.get("/restaurants").json()) == 4  # nothing was saved


def test_create_duplicate_restaurant_returns_409(client):
    response = client.post(
        "/restaurants",
        json={**NEW_RESTAURANT, "name": "boston pizza", "address": "123 KELOWNA ROAD"},
    )

    assert response.status_code == 409
    assert len(client.get("/restaurants").json()) == 4


def test_same_name_at_different_address_is_allowed(client):
    response = client.post("/restaurants", json={**NEW_RESTAURANT, "name": "Boston Pizza"})

    assert response.status_code == 201


# --- PATCH /restaurants/{restaurant_id} ---


def test_update_restaurant_changes_only_given_fields(client):
    response = client.patch("/restaurants/1", json={"address": "99 Harvey Avenue", "is_open": False})

    assert response.status_code == 200
    updated = response.json()
    assert updated == {
        "id": 1,
        "name": "Boston Pizza",
        "cuisine": "Pizza",
        "address": "99 Harvey Avenue",
        "rating": 3.3,
        "is_open": False,
    }
    assert client.get("/restaurants/1").json() == updated  # persisted


def test_update_unknown_restaurant_returns_404(client):
    assert client.patch("/restaurants/999", json={"is_open": False}).status_code == 404


def test_update_with_empty_body_returns_400(client):
    response = client.patch("/restaurants/1", json={})

    assert response.status_code == 400
    assert response.json() == {"detail": "Update request must include at least one field"}


@pytest.mark.parametrize(
    "payload",
    [{"name": ""}, {"name": None}, {"rating": 9}, {"id": 99}, {"owner": "x"}],
    ids=["empty-name", "null-name", "rating-above-5", "change-id", "unknown-field"],
)
def test_update_invalid_input_returns_422(client, payload):
    response = client.patch("/restaurants/1", json=payload)

    assert response.status_code == 422
    assert client.get("/restaurants/1").json()["name"] == "Boston Pizza"


def test_update_into_duplicate_returns_409(client):
    # Moving Lakeside Pizzeria to... the same name and address as Boston Pizza
    response = client.patch("/restaurants/4", json={"name": "Boston Pizza", "address": "123 Kelowna Road"})

    assert response.status_code == 409
    assert client.get("/restaurants/4").json()["name"] == "Lakeside Pizzeria"


def test_update_keeping_own_name_and_address_is_allowed(client):
    response = client.patch("/restaurants/1", json={"name": "Boston Pizza", "rating": 3.5})

    assert response.status_code == 200
    assert response.json()["rating"] == 3.5


# --- Works together with menus ---


def test_new_restaurant_can_get_a_menu(client):
    restaurant = client.post("/restaurants", json=NEW_RESTAURANT).json()

    assert client.get(f"/restaurants/{restaurant['id']}/menu").json() == []
    item = client.post(
        f"/restaurants/{restaurant['id']}/menu",
        json={"name": "Butter Chicken", "price": 17.5, "category": "Mains"},
    )
    assert item.status_code == 201
    assert item.json()["restaurant_id"] == restaurant["id"]


# --- Repository ---


def test_repository_reads_all_restaurants(tmp_path):
    repository = RestaurantRepository(tmp_path / "restaurants.json")

    restaurants = repository.get_all()

    assert len(restaurants) == 4
    assert restaurants[1]["cuisine"] == "Mexican"


def test_repository_missing_file_raises_error(tmp_path):
    repository = RestaurantRepository(tmp_path / "does_not_exist.json")

    with pytest.raises(FileNotFoundError):
        repository.get_all()


def test_repository_get_by_id(tmp_path):
    repository = RestaurantRepository(tmp_path / "restaurants.json")

    assert repository.get_by_id(3)["name"] == "Okanagan Sushi"
    assert repository.get_by_id(999) is None


def test_repository_create_assigns_next_id_and_persists(tmp_path):
    repository = RestaurantRepository(tmp_path / "restaurants.json")

    created = repository.create(dict(NEW_RESTAURANT))

    assert created["id"] == 5
    assert RestaurantRepository(tmp_path / "restaurants.json").get_by_id(5) == created


def test_repository_create_uses_max_id_not_count(tmp_path):
    file_path = tmp_path / "gaps.json"
    file_path.write_text(json.dumps([{"id": 2}, {"id": 9}]))

    assert RestaurantRepository(file_path).create({"name": "X"})["id"] == 10


def test_repository_create_in_empty_file_starts_at_1(tmp_path):
    file_path = tmp_path / "empty.json"
    file_path.write_text("[]")

    assert RestaurantRepository(file_path).create({"name": "X"})["id"] == 1


def test_repository_update_never_changes_id(tmp_path):
    repository = RestaurantRepository(tmp_path / "restaurants.json")

    updated = repository.update(1, {"id": 42, "rating": 4.0})

    assert updated["id"] == 1
    assert updated["rating"] == 4.0
    assert repository.get_by_id(42) is None


def test_repository_update_missing_returns_none(tmp_path):
    assert RestaurantRepository(tmp_path / "restaurants.json").update(999, {"rating": 1.0}) is None


def test_repository_save_leaves_no_temp_files(tmp_path):
    repository = RestaurantRepository(tmp_path / "restaurants.json")

    repository.create(dict(NEW_RESTAURANT))
    repository.update(1, {"is_open": False})

    assert list(tmp_path.glob("*.tmp")) == []
    json.loads((tmp_path / "restaurants.json").read_text(encoding="utf-8"))  # still valid JSON


# --- Service ---


@pytest.fixture
def service(tmp_path):
    return RestaurantService(RestaurantRepository(tmp_path / "restaurants.json"))


def test_service_get_unknown_raises(service):
    with pytest.raises(RestaurantNotFoundError):
        service.get_restaurant(999)


def test_service_rejects_duplicate(service):
    with pytest.raises(DuplicateRestaurantError):
        service.create_restaurant(
            RestaurantCreate(name="Taco Bell", cuisine="Mexican", address="456 okanagan drive")
        )


def test_service_rejects_empty_update(service):
    with pytest.raises(EmptyUpdateError):
        service.update_restaurant(1, RestaurantUpdate())


# --- Persistence and data integrity ---


def test_data_survives_restart(tmp_path):
    """A brand-new service (as after a server restart) sees what the previous one saved."""
    path = tmp_path / "restaurants.json"
    created = RestaurantService(RestaurantRepository(path)).create_restaurant(RestaurantCreate(**NEW_RESTAURANT))
    RestaurantService(RestaurantRepository(path)).update_restaurant(1, RestaurantUpdate(is_open=False))

    restarted = RestaurantService(RestaurantRepository(path))
    assert restarted.get_restaurant(created["id"]) == created
    assert restarted.get_restaurant(1)["is_open"] is False


def test_committed_restaurant_data_is_valid():
    """Every restaurant in data/restaurants.json is a valid Restaurant and ids are unique."""
    restaurants = json.loads((BASE_DIR / "data" / "restaurants.json").read_text(encoding="utf-8"))

    for restaurant in restaurants:
        Restaurant(**restaurant)
    assert len({restaurant["id"] for restaurant in restaurants}) == len(restaurants)


def test_writes_do_not_touch_committed_data(client):
    real_file = BASE_DIR / "data" / "restaurants.json"
    before = real_file.read_text(encoding="utf-8")

    client.post("/restaurants", json=NEW_RESTAURANT)
    client.patch("/restaurants/1", json={"is_open": False})

    assert real_file.read_text(encoding="utf-8") == before


# --- API documentation ---


def test_restaurant_endpoints_are_documented(client):
    paths = client.get("/openapi.json").json()["paths"]
    collection = paths["/restaurants"]
    single = paths["/restaurants/{restaurant_id}"]

    assert {"get", "post"} <= collection.keys()
    assert {"get", "patch"} <= single.keys()
    assert {"search", "cuisine", "is_open", "min_rating"} <= {p["name"] for p in collection["get"]["parameters"]}
    assert {"201", "409", "422"} <= collection["post"]["responses"].keys()
    assert "404" in single["get"]["responses"]
    assert {"200", "400", "404", "409", "422"} <= single["patch"]["responses"].keys()
    assert all(op["description"] for op in [collection["get"], collection["post"], single["get"], single["patch"]])
