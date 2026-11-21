"""Original sample menus for fictional import rows, using isolated app data."""

import csv
from unittest.mock import Mock

import pytest

from app import import_restaurants as importer
from app.core import config
from app.repositories.menu_item_repository import MenuItemRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.menu_item import MenuItem, MenuItemCreate
from app.schemas.restaurant import RestaurantCreate, RestaurantUpdate
from app.services.menu_service import MenuService
from app.services.restaurant_service import RestaurantService


def source_row(index=0, **changes):
    return {
        "loc_name": f"Fictional Imported Restaurant {index}",
        "address": f"{index} Fictional Import Way",
        "cuisines": "Pizza",
        "review_rating": "4.2",
        **changes,
    }


@pytest.fixture
def services(isolated_data):
    restaurants = RestaurantRepository(config.RESTAURANTS_FILE)
    return RestaurantService(restaurants), MenuService(MenuItemRepository(config.MENU_ITEMS_FILE), restaurants)


def seed(rows, services, **options):
    restaurants, menus = services
    return importer.import_restaurants(rows, restaurants, demo_menus=True, menu_service=menus, **options)


def snapshot(data_dir):
    return {path.name: path.read_bytes() for path in data_dir.glob("*.json")}


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("loc_name", "address", "cuisines", "review_rating"))
        writer.writeheader()
        writer.writerows(rows)


def assert_sample_menu(items):
    assert len(items) == 3
    assert len({item["name"] for item in items}) == 3
    for item in items:
        MenuItem.model_validate(item)
        assert item["name"].startswith("Demo ")
        assert item["description"].startswith("Demo menu:")
        assert "sample" in item["description"].casefold()
        assert "not" in item["description"].casefold() and "real menu" in item["description"].casefold()
        assert item["price"] > 0 and item["is_available"] and item["is_active"]


def test_three_cuisine_based_sample_items_are_created_before_restaurants_open(services, monkeypatch):
    restaurants, menus = services
    created_while_closed = []
    create = menus.create_menu_item

    def checked_create(restaurant_id, item):
        assert restaurants.get_restaurant(restaurant_id)["is_open"] is False
        created = create(restaurant_id, item)
        created_while_closed.append(created)
        return created

    monkeypatch.setattr(menus, "create_menu_item", checked_create)
    rows = [source_row(index, cuisines=cuisine) for index, cuisine in enumerate(("Pizza", "Mexican", "Indian"))]

    result = seed(rows, services)

    assert (result.added, result.menu_items_added, result.restaurants_seeded, result.restaurants_opened) == (3, 9, 3, 3)
    imported = restaurants.list_restaurants(search="Fictional Imported")
    names_by_cuisine = []
    for restaurant in imported:
        assert restaurant["is_open"] is True
        items = menus.list_menu_items(restaurant["id"])
        assert_sample_menu(items)
        names_by_cuisine.append(frozenset(item["name"] for item in items))
    assert len(set(names_by_cuisine)) == 3
    assert len(created_while_closed) == 9
    reloaded_restaurants = RestaurantRepository(config.RESTAURANTS_FILE)
    reloaded_items = MenuItemRepository(config.MENU_ITEMS_FILE)
    for restaurant in imported:
        assert reloaded_restaurants.get_by_id(restaurant["id"]) == restaurant
        assert reloaded_items.get_by_restaurant_id(restaurant["id"]) == menus.list_menu_items(restaurant["id"])


@pytest.mark.parametrize("already_open", [False, True], ids=["closed-import", "previously-open-empty-import"])
def test_failed_menu_creation_does_not_open_the_imported_restaurant(services, monkeypatch, already_open):
    restaurants, menus = services
    row = source_row()
    if already_open:
        assert importer.import_restaurants([row], restaurants).added == 1
        restaurant = restaurants.list_restaurants(search=row["loc_name"])[0]
        restaurants.update_restaurant(restaurant["id"], RestaurantUpdate(is_open=True))
    create = menus.create_menu_item
    calls = 0

    def fail_second_item(restaurant_id, item):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated menu save failure")
        return create(restaurant_id, item)

    monkeypatch.setattr(menus, "create_menu_item", fail_second_item)

    with pytest.raises(OSError, match="simulated menu save failure"):
        seed([row], services)

    restaurant = restaurants.list_restaurants(search="Fictional Imported")[0]
    assert restaurant["is_open"] is False


def test_committed_seed_restaurants_existing_items_and_off_source_custom_restaurants_are_preserved(services, tmp_path):
    restaurants, menus = services
    original_restaurants = restaurants.list_restaurants()
    original_items = menus.menu_repository.get_all()
    custom = restaurants.create_restaurant(
        RestaurantCreate(name="Private Test Cafe", address="7 User Created Way", cuisine="Cafe", is_open=False)
    )
    before = snapshot(tmp_path)
    seed_rows = [
        source_row(loc_name=restaurant["name"], address=restaurant["address"], cuisines=restaurant["cuisine"])
        for restaurant in original_restaurants
    ]

    result = seed([*seed_rows, source_row()], services)

    assert (result.added, result.menu_items_added, result.restaurants_seeded) == (1, 3, 1)
    for restaurant in original_restaurants:
        assert restaurants.get_restaurant(restaurant["id"]) == restaurant
    assert menus.menu_repository.get_all()[:len(original_items)] == original_items
    assert restaurants.get_restaurant(custom["id"]) == custom
    assert menus.list_menu_items(custom["id"]) == []
    after = snapshot(tmp_path)
    for name in ("customers.json", "carts.json", "orders.json"):
        assert after[name] == before[name]


@pytest.mark.parametrize("inactive", [False, True], ids=["active-menu", "inactive-menu"])
def test_existing_manager_menu_is_never_overwritten_or_opened(services, tmp_path, inactive):
    restaurants, menus = services
    row = source_row()
    assert importer.import_restaurants([row], restaurants).added == 1
    restaurant = restaurants.list_restaurants(search=row["loc_name"])[0]
    item = menus.create_menu_item(
        restaurant["id"], MenuItemCreate(name="Manager Special", price=12.25, category="Mains")
    )
    if inactive:
        menus.deactivate_menu_item(restaurant["id"], item["id"])
    before = snapshot(tmp_path)

    result = seed([row], services)

    assert (result.added, result.menu_items_added, result.restaurants_opened) == (0, 0, 0)
    assert restaurants.get_restaurant(restaurant["id"])["is_open"] is False
    assert snapshot(tmp_path) == before


def test_repeated_seeding_is_a_noop_and_does_not_reopen_a_manager_closed_restaurant(services, tmp_path):
    restaurants, menus = services
    row = source_row()
    assert seed([row], services).menu_items_added == 3
    restaurant = restaurants.list_restaurants(search=row["loc_name"])[0]
    restaurants.update_restaurant(restaurant["id"], RestaurantUpdate(is_open=False))
    before = snapshot(tmp_path)

    repeated = seed([row], services)

    assert (repeated.added, repeated.menu_items_added, repeated.restaurants_seeded, repeated.restaurants_opened) == (0, 0, 0, 0)
    assert restaurants.get_restaurant(restaurant["id"])["is_open"] is False
    assert len(menus.list_menu_items(restaurant["id"])) == 3
    assert snapshot(tmp_path) == before


def test_prior_one_hundred_imports_get_sample_menus_without_importing_the_next_source_record(services, tmp_path):
    restaurants, menus = services
    rows = [source_row(index) for index in range(101)]
    assert importer.import_restaurants(rows, restaurants).added == 100

    result = seed(rows, services)

    assert (result.added, result.menu_items_added, result.restaurants_seeded, result.restaurants_opened) == (0, 300, 100, 100)
    imported = restaurants.list_restaurants(search="Fictional Imported")
    assert len(imported) == 100
    assert all(restaurant["name"] != rows[100]["loc_name"] for restaurant in imported)
    for restaurant in imported:
        assert restaurant["is_open"] is True
        assert_sample_menu(menus.list_menu_items(restaurant["id"]))
    before = snapshot(tmp_path)
    assert seed(rows, services).menu_items_added == 0
    assert snapshot(tmp_path) == before


def test_seeding_uses_the_same_bounded_source_selection_as_the_restaurant_import(services):
    restaurants, menus = services
    rows = [source_row(index) for index in range(3)]
    assert importer.import_restaurants(rows, restaurants, limit=3).added == 3

    result = seed(rows, services, limit=2)

    assert (result.added, result.menu_items_added, result.restaurants_opened) == (0, 6, 2)
    for index, row in enumerate(rows):
        restaurant = restaurants.list_restaurants(search=row["loc_name"])[0]
        assert restaurant["is_open"] is (index < 2)
        assert len(menus.list_menu_items(restaurant["id"])) == (3 if index < 2 else 0)


@pytest.mark.parametrize("already_imported", [False, True], ids=["fresh-import", "prior-import"])
def test_dry_run_previews_restaurants_menus_and_opening_without_changing_any_data(services, tmp_path, already_imported):
    restaurants, _ = services
    rows = [source_row(index) for index in range(2)]
    if already_imported:
        assert importer.import_restaurants(rows, restaurants).added == 2
    before = snapshot(tmp_path)

    result = seed(rows, services, dry_run=True)

    assert result.added == (0 if already_imported else 2)
    assert (result.menu_items_added, result.restaurants_seeded, result.restaurants_opened) == (6, 2, 2)
    assert snapshot(tmp_path) == before


def test_fresh_csv_cli_creates_sample_menus_and_dry_run_only_previews_them(tmp_path, monkeypatch, capsys):
    rows = [source_row(index) for index in range(3)]
    path = tmp_path / "fictional-restaurants.csv"
    write_csv(path, rows)
    remote = Mock(side_effect=AssertionError("Local CSV must not load Kaggle"))
    monkeypatch.setattr(importer, "load_kaggle_rows", remote)
    args = ["--csv", str(path), "--data-dir", str(tmp_path), "--limit", "2", "--demo-menus"]
    before = snapshot(tmp_path)

    assert importer.main([*args, "--dry-run"]) == 0
    preview = capsys.readouterr().out.casefold()
    assert "would" in preview and "menu" in preview
    assert snapshot(tmp_path) == before
    assert importer.main(args) == 0

    restaurants = RestaurantRepository(config.RESTAURANTS_FILE)
    items = MenuItemRepository(config.MENU_ITEMS_FILE)
    imported = [restaurant for restaurant in restaurants.get_all() if restaurant["name"].startswith("Fictional Imported")]
    assert len(imported) == 2
    for restaurant in imported:
        assert restaurant["is_open"] is True
        assert_sample_menu(items.get_by_restaurant_id(restaurant["id"]))
    remote.assert_not_called()


@pytest.mark.parametrize("already_imported", [False, True], ids=["fresh-default-data", "prior-default-import"])
def test_default_project_data_target_does_not_treat_imported_restaurants_as_original_seeds(tmp_path, monkeypatch, already_imported):
    project_dir = tmp_path / "default-project"
    data_dir = project_dir / "data"
    data_dir.mkdir(parents=True)
    for name, content in snapshot(tmp_path).items():
        (data_dir / name).write_bytes(content)
    monkeypatch.setattr(config, "BASE_DIR", project_dir)
    monkeypatch.setattr(config, "DATA_DIR", data_dir)
    row = source_row()
    path = tmp_path / "default-import.csv"
    write_csv(path, [row])
    restaurants = RestaurantService(RestaurantRepository(data_dir / "restaurants.json"))
    if already_imported:
        assert importer.import_restaurants([row], restaurants).added == 1

    assert importer.main(["--csv", str(path), "--demo-menus"]) == 0

    restaurant = restaurants.list_restaurants(search=row["loc_name"])[0]
    assert restaurant["is_open"] is True
    assert_sample_menu(MenuItemRepository(data_dir / "menu_items.json").get_by_restaurant_id(restaurant["id"]))


def test_imported_sample_menu_supports_real_customer_cart_checkout_and_order_reads(services, client):
    restaurants, _ = services
    row = source_row(cuisines="Indian")
    assert seed([row], services).menu_items_added == 3
    restaurant = restaurants.list_restaurants(search=row["loc_name"])[0]
    menu = client.get(f"/restaurants/{restaurant['id']}/menu")
    assert menu.status_code == 200
    assert_sample_menu(menu.json())
    item = menu.json()[0]
    account = {
        "name": "Sample Menu Customer",
        "email": "sample-menu@example.com",
        "password": "sample-menu-password",
        "delivery_address": "5 Fictional Customer Way",
    }
    registered = client.post("/customers", json=account)
    assert registered.status_code == 201
    login = client.post("/auth/login", json={"email": account["email"], "password": account["password"]})
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    added = client.post("/cart/items", json={"menu_item_id": item["id"], "quantity": 2}, headers=headers)
    assert added.status_code == 200
    expected_total = round(item["price"] * 2, 2)
    assert added.json()["restaurant_id"] == restaurant["id"]
    assert added.json()["total"] == expected_total
    checkout = client.post("/checkout", headers=headers)
    assert checkout.status_code == 201
    order = checkout.json()
    assert (order["customer_id"], order["restaurant_id"], order["total"]) == (
        registered.json()["id"], restaurant["id"], expected_total
    )
    assert order["items"][0]["name"] == item["name"]
    assert order["delivery_address"] == account["delivery_address"]
    retrieved = client.get(f"/orders/{order['id']}", headers=headers)
    assert retrieved.status_code == 200 and retrieved.json() == order
    history = client.get("/orders", headers=headers)
    assert history.status_code == 200 and history.json() == [order]
    assert client.get("/cart", headers=headers).json()["items"] == []
