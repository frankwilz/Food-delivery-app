"""Concurrent requests must not corrupt the JSON data files.

FastAPI runs routes in a thread pool, so these tests start several threads at the same moment
(a `Barrier`) doing the same thing. `slow_saves` makes every save pause briefly, which holds the
race window open: without the locks in `app/repositories/json_repository.py`, every test here
fails reliably (duplicate ids, lost cart quantities, two orders for one cart).
"""

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.core.security import create_access_token
from app.main import app
from app.repositories.cart_repository import CartRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.json_repository import JsonRepository, lock_for, transaction
from app.repositories.menu_item_repository import MenuItemRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.cart import CartItemAdd
from app.schemas.customer import CustomerCreate
from app.services import customer_service as customer_module
from app.services.cart_service import CartService
from app.services.checkout_service import CheckoutService
from app.services.customer_service import CustomerService, DuplicateEmailError
from app.services.menu_service import MenuService

ANA_ID, BEN_ID = 1, 2
PIZZA = 1  # restaurant 1, orderable
THREADS = 8


@pytest.fixture(autouse=True)
def slow_saves(monkeypatch):
    original_save = JsonRepository.save

    def save(self, records):
        time.sleep(0.02)  # long enough that every thread has read the file before the first save lands
        original_save(self, records)

    monkeypatch.setattr(JsonRepository, "save", save)


@pytest.fixture(autouse=True)
def fast_hashing(monkeypatch):
    # PBKDF2 is deliberately slow; it is not what these tests are about
    monkeypatch.setattr(customer_module, "hash_password", lambda password: f"test-hash:{password}")


def run_together(task, count=THREADS):
    """Run `task(i)` in `count` threads released at the same moment. Returns each result or raised error."""
    barrier = threading.Barrier(count)

    def worker(i):
        barrier.wait()
        try:
            return task(i)
        except Exception as error:  # collected so the test can count successes and failures
            return error

    with ThreadPoolExecutor(max_workers=count) as pool:
        return list(pool.map(worker, range(count)))


def read(file_path):
    return json.loads(file_path.read_text(encoding="utf-8"))


def customer_service():
    return CustomerService(CustomerRepository(config.CUSTOMERS_FILE))


def cart_service():
    menu = MenuService(MenuItemRepository(config.MENU_ITEMS_FILE), RestaurantRepository(config.RESTAURANTS_FILE))
    return CartService(CartRepository(config.CARTS_FILE), menu, customer_service())


def checkout_service():
    menu = MenuService(MenuItemRepository(config.MENU_ITEMS_FILE), RestaurantRepository(config.RESTAURANTS_FILE))
    return CheckoutService(
        customer_service(),
        CartRepository(config.CARTS_FILE),
        RestaurantRepository(config.RESTAURANTS_FILE),
        cart_service(),
        menu,
        OrderRepository(config.ORDERS_FILE),
    )


def new_customer(i, email=None):
    return CustomerCreate(
        name=f"Customer {i}",
        email=email or f"customer{i}@example.com",
        delivery_address="1 Test Street",
        password="a-long-password",
    )


# --- The locks themselves ---


def test_every_repository_for_a_file_shares_one_lock():
    assert CartRepository(config.CARTS_FILE).lock is CartRepository(config.CARTS_FILE).lock
    assert lock_for(config.CARTS_FILE) is not lock_for(config.ORDERS_FILE)


def test_transaction_holds_the_lock_and_releases_it_afterwards():
    carts = CartRepository(config.CARTS_FILE)
    acquired_elsewhere = []

    def try_from_another_thread():
        got_it = carts.lock.acquire(blocking=False)
        if got_it:
            carts.lock.release()
        acquired_elsewhere.append(got_it)

    with transaction(carts):
        thread = threading.Thread(target=try_from_another_thread)
        thread.start()
        thread.join()
    assert acquired_elsewhere == [False]

    thread = threading.Thread(target=try_from_another_thread)
    thread.start()
    thread.join()
    assert acquired_elsewhere == [False, True]


def test_transaction_is_reentrant():
    carts = CartRepository(config.CARTS_FILE)
    orders = OrderRepository(config.ORDERS_FILE)
    with transaction(carts, orders), transaction(carts):
        carts.create({"customer_id": ANA_ID, "restaurant_id": None, "items": [], "status": "active"})
    assert len(read(config.CARTS_FILE)) == 1


# --- Repositories ---


def test_concurrent_creates_get_unique_ids_and_none_are_lost():
    before = read(config.RESTAURANTS_FILE)
    repository = RestaurantRepository(config.RESTAURANTS_FILE)

    results = run_together(
        lambda i: repository.create(
            {"name": f"Place {i}", "cuisine": "Test", "address": f"{i} Road", "rating": 0, "is_open": True}
        )
    )

    saved = read(config.RESTAURANTS_FILE)
    assert len(saved) == len(before) + THREADS
    ids = [restaurant["id"] for restaurant in saved]
    assert len(ids) == len(set(ids))
    assert sorted(result["id"] for result in results) == ids[-THREADS:]


def test_concurrent_updates_to_different_records_are_all_kept():
    repository = MenuItemRepository(config.MENU_ITEMS_FILE)
    item_ids = [item["id"] for item in read(config.MENU_ITEMS_FILE)][:THREADS]

    run_together(lambda i: repository.update(item_ids[i], {"price": 1000 + i}), count=len(item_ids))

    prices = {item["id"]: item["price"] for item in read(config.MENU_ITEMS_FILE)}
    assert [prices[item_id] for item_id in item_ids] == [1000 + i for i in range(len(item_ids))]


# --- Services: a check followed by a write ---


def test_concurrent_registrations_all_succeed_with_unique_ids():
    before = len(read(config.CUSTOMERS_FILE))

    results = run_together(lambda i: customer_service().register(new_customer(i)))

    assert not [r for r in results if isinstance(r, Exception)]
    saved = read(config.CUSTOMERS_FILE)
    assert len(saved) == before + THREADS
    assert len({customer["id"] for customer in saved}) == len(saved)


def test_concurrent_registrations_with_the_same_email_create_one_account():
    results = run_together(lambda i: customer_service().register(new_customer(i, email="same@example.com")))

    assert sum(isinstance(r, dict) for r in results) == 1
    assert sum(isinstance(r, DuplicateEmailError) for r in results) == THREADS - 1
    assert sum(c["email"] == "same@example.com" for c in read(config.CUSTOMERS_FILE)) == 1


def test_concurrent_first_cart_requests_create_one_active_cart():
    run_together(lambda i: cart_service().get_cart(ANA_ID))

    carts = read(config.CARTS_FILE)
    assert len([c for c in carts if c["customer_id"] == ANA_ID and c["status"] == "active"]) == 1


def test_concurrent_adds_to_the_same_cart_keep_every_quantity():
    results = run_together(lambda i: cart_service().add_item(ANA_ID, CartItemAdd(menu_item_id=PIZZA, quantity=1)))

    assert not [r for r in results if isinstance(r, Exception)]
    (cart,) = read(config.CARTS_FILE)
    assert cart["items"] == [{"menu_item_id": PIZZA, "quantity": THREADS}]


def test_concurrent_checkouts_of_one_cart_create_one_order():
    cart_service().add_item(ANA_ID, CartItemAdd(menu_item_id=PIZZA, quantity=2))

    results = run_together(lambda i: checkout_service().checkout(ANA_ID))

    orders = read(config.ORDERS_FILE)
    assert len(orders) == 1
    assert sum(isinstance(r, dict) for r in results) == 1
    # The others waited, then found the cart already checked out, so there was nothing left to order
    assert all(isinstance(r, Exception) for r in results if not isinstance(r, dict))
    assert [c["status"] for c in read(config.CARTS_FILE)] == ["checked_out"]


def test_checkouts_by_different_customers_at_once_all_succeed():
    for customer_id in (ANA_ID, BEN_ID):
        cart_service().add_item(customer_id, CartItemAdd(menu_item_id=PIZZA, quantity=1))

    results = run_together(lambda i: checkout_service().checkout((ANA_ID, BEN_ID)[i]), count=2)

    assert all(isinstance(r, dict) for r in results)
    orders = read(config.ORDERS_FILE)
    assert sorted(order["customer_id"] for order in orders) == [ANA_ID, BEN_ID]
    assert len({order["id"] for order in orders}) == 2


# --- Through the HTTP API ---


def test_double_clicked_place_order_over_http_creates_one_order():
    headers = {"Authorization": f"Bearer {create_access_token(ANA_ID)}"}
    client = TestClient(app, headers=headers)
    assert client.post("/cart/items", json={"menu_item_id": PIZZA, "quantity": 1}).status_code == 200

    responses = run_together(lambda i: TestClient(app, headers=headers).post("/checkout"), count=4)

    codes = sorted(response.status_code for response in responses)
    assert codes.count(201) == 1
    assert all(code == 400 for code in codes if code != 201)  # "The cart is empty"
    assert len(read(config.ORDERS_FILE)) == 1
