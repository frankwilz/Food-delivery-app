import json

import pytest

from app.repositories.cart_repository import CartRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.order_repository import OrderRepository


def customer(n: int) -> dict:
    return {
        "name": f"Customer {n}",
        "email": f"customer{n}@example.com",
        "password_hash": "pbkdf2_sha256$1$00$00",
        "delivery_address": f"{n} Test Street",
        "role": "customer",
        "is_active": True,
    }


def cart(n: int) -> dict:
    return {"customer_id": n, "restaurant_id": 1, "items": [{"menu_item_id": 1, "quantity": n}], "status": "active"}


def order(n: int) -> dict:
    return {
        "customer_id": n,
        "cart_id": n,
        "restaurant_id": 1,
        "items": [{"menu_item_id": 1, "name": "Pizza", "unit_price": 10.0, "quantity": n, "line_total": 10.0 * n}],
        "subtotal": 10.0 * n,
        "total": 10.0 * n,
        "delivery_address": "1 Test Street",
        "status": "placed",
        "created_at": f"2026-11-0{n}T12:00:00+00:00",
    }


REPOSITORIES = [
    pytest.param(CustomerRepository, customer, id="customers"),
    pytest.param(CartRepository, cart, id="carts"),
    pytest.param(OrderRepository, order, id="orders"),
]


@pytest.fixture
def data_file(tmp_path):
    (tmp_path / "repository").mkdir()
    path = tmp_path / "repository" / "records.json"
    path.write_text("[]\n", encoding="utf-8")
    return path


def stored(path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(("repository_class", "make"), REPOSITORIES)
def test_create_saves_the_record_to_the_file(repository_class, make, data_file):
    created = repository_class(data_file).create(make(1))

    assert created == {"id": 1, **make(1)}
    assert stored(data_file) == [created]


@pytest.mark.parametrize(("repository_class", "make"), REPOSITORIES)
def test_ids_start_at_1_and_count_up(repository_class, make, data_file):
    repository = repository_class(data_file)

    assert [repository.create(make(n))["id"] for n in (1, 2, 3)] == [1, 2, 3]


@pytest.mark.parametrize(("repository_class", "make"), REPOSITORIES)
def test_records_and_ids_are_stable_after_reload(repository_class, make, data_file):
    created = [repository_class(data_file).create(make(n)) for n in (1, 2, 3)]

    reloaded = repository_class(data_file)

    assert reloaded.get_all() == created
    for record in created:
        assert reloaded.get_by_id(record["id"]) == record


@pytest.mark.parametrize(("repository_class", "make"), REPOSITORIES)
def test_new_id_follows_the_highest_id_after_reload(repository_class, make, data_file):
    data_file.write_text(json.dumps([{"id": 1, **make(1)}, {"id": 7, **make(2)}]), encoding="utf-8")

    assert repository_class(data_file).create(make(3))["id"] == 8


@pytest.mark.parametrize(("repository_class", "make"), REPOSITORIES)
def test_get_by_id_returns_none_for_an_unknown_id(repository_class, make, data_file):
    repository = repository_class(data_file)
    repository.create(make(1))

    assert repository.get_by_id(999) is None


@pytest.mark.parametrize(("repository_class", "make"), REPOSITORIES)
def test_saving_leaves_only_the_data_file(repository_class, make, data_file):
    repository = repository_class(data_file)
    for n in (1, 2):
        repository.create(make(n))

    assert [path.name for path in data_file.parent.iterdir()] == [data_file.name]


@pytest.mark.parametrize(("repository_class", "make"), REPOSITORIES)
def test_saved_file_is_a_valid_json_list(repository_class, make, data_file):
    repository_class(data_file).create(make(1))

    text = data_file.read_text(encoding="utf-8")
    assert isinstance(json.loads(text), list)
    assert text.endswith("\n")


@pytest.mark.parametrize(("repository_class", "make"), REPOSITORIES)
def test_a_missing_file_raises_instead_of_returning_empty(repository_class, make, tmp_path):
    with pytest.raises(FileNotFoundError):
        repository_class(tmp_path / "missing.json").get_all()


@pytest.mark.parametrize(("repository_class", "make"), REPOSITORIES)
def test_each_repository_only_touches_its_own_file(repository_class, make, tmp_path):
    mine, other = tmp_path / "mine.json", tmp_path / "other.json"
    for path in (mine, other):
        path.write_text("[]\n", encoding="utf-8")

    repository_class(mine).create(make(1))

    assert stored(other) == []


def test_customer_update_persists_and_never_changes_the_id(data_file):
    repository = CustomerRepository(data_file)
    repository.create(customer(1))

    repository.update(1, {"id": 99, "delivery_address": "2 Moved Street"})

    reloaded = CustomerRepository(data_file).get_by_id(1)
    assert reloaded["delivery_address"] == "2 Moved Street"
    assert CustomerRepository(data_file).get_by_id(99) is None


def test_customer_get_by_email_ignores_case_and_spaces(data_file):
    repository = CustomerRepository(data_file)
    created = repository.create(customer(1))

    assert repository.get_by_email("  CUSTOMER1@Example.com ") == created
    assert repository.get_by_email("nobody@example.com") is None


def test_cart_update_persists_and_never_changes_id_or_owner(data_file):
    repository = CartRepository(data_file)
    repository.create(cart(1))

    repository.update(1, {"id": 50, "customer_id": 2, "items": [], "restaurant_id": None})

    reloaded = CartRepository(data_file).get_by_id(1)
    assert (reloaded["customer_id"], reloaded["items"], reloaded["restaurant_id"]) == (1, [], None)


def test_cart_update_of_an_unknown_cart_returns_none_and_writes_nothing(data_file):
    repository = CartRepository(data_file)
    repository.create(cart(1))
    before = data_file.read_text(encoding="utf-8")

    assert repository.update(999, {"items": []}) is None
    assert data_file.read_text(encoding="utf-8") == before


def test_active_cart_lookup_ignores_checked_out_carts_after_reload(data_file):
    repository = CartRepository(data_file)
    repository.create({**cart(1), "status": "checked_out"})
    active = repository.create(cart(1))

    assert CartRepository(data_file).get_active_for_customer(1) == active


def test_orders_are_append_only():
    assert not hasattr(OrderRepository, "update")
    assert not hasattr(OrderRepository, "delete")


def test_order_lookups_by_customer_and_cart_after_reload(data_file):
    repository = OrderRepository(data_file)
    first, second, third = (repository.create(order(n)) for n in (1, 2, 1))

    reloaded = OrderRepository(data_file)

    assert reloaded.get_by_customer(1) == [first, third]
    assert reloaded.get_by_customer(3) == []
    assert reloaded.get_by_cart_id(2) == second
    assert reloaded.get_by_cart_id(999) is None


def test_creating_an_order_keeps_earlier_orders_unchanged(data_file):
    repository = OrderRepository(data_file)
    first = repository.create(order(1))

    repository.create(order(2))

    assert OrderRepository(data_file).get_by_id(1) == first
