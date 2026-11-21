import json
from decimal import Decimal

import pytest

from app.core import config
from app.core.errors import ForbiddenError, NotFoundError
from app.core.security import verify_password
from app.repositories.cart_repository import CartRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.menu_item_repository import MenuItemRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.cart import CartItemAdd
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.services.cart_service import CartService, DifferentRestaurantError, ItemNotInCartError
from app.services.checkout_service import CheckoutService, EmptyCartError, RestaurantClosedError
from app.services.customer_service import CustomerNotFoundError, CustomerService, DuplicateEmailError
from app.services.menu_service import MenuItemUnavailableError, MenuService

ANA_ID, BEN_ID, CHLOE_DEACTIVATED_ID = 1, 2, 3
PIZZA, SALAD = 1, 2
CRUNCHWRAP = 4


@pytest.fixture
def customers() -> CustomerService:
    return CustomerService(CustomerRepository(config.CUSTOMERS_FILE))


@pytest.fixture
def menu() -> MenuService:
    return MenuService(MenuItemRepository(config.MENU_ITEMS_FILE), RestaurantRepository(config.RESTAURANTS_FILE))


@pytest.fixture
def carts(customers, menu) -> CartService:
    return CartService(CartRepository(config.CARTS_FILE), menu, customers)


@pytest.fixture
def checkout(customers, menu, carts) -> CheckoutService:
    return CheckoutService(
        customers,
        CartRepository(config.CARTS_FILE),
        RestaurantRepository(config.RESTAURANTS_FILE),
        carts,
        menu,
        OrderRepository(config.ORDERS_FILE),
    )


def read(file_path) -> list[dict]:
    return json.loads(file_path.read_text(encoding="utf-8"))


def data_files() -> dict[str, str]:
    files = (config.CUSTOMERS_FILE, config.CARTS_FILE, config.ORDERS_FILE, config.MENU_ITEMS_FILE)
    return {path.name: path.read_text(encoding="utf-8") for path in files}


def new_customer(**changes) -> CustomerCreate:
    fields = {
        "name": "Sam Rivera",
        "email": "sam.rivera@example.com",
        "delivery_address": "500 Service Street",
        "password": "a-long-password",
        **changes,
    }
    return CustomerCreate(**fields)


def add(carts: CartService, item_id: int, quantity: int = 1, customer_id: int = ANA_ID) -> dict:
    return carts.add_item(customer_id, CartItemAdd(menu_item_id=item_id, quantity=quantity))


def test_register_saves_a_customer_with_a_hashed_password(customers):
    customer = customers.register(new_customer())

    assert customer["role"] == "customer" and customer["is_active"] is True
    assert "password" not in customer
    assert verify_password("a-long-password", customer["password_hash"])
    assert read(config.CUSTOMERS_FILE)[-1] == customer


def test_register_gives_each_customer_a_new_id(customers):
    first = customers.register(new_customer(email="one@example.com"))
    second = customers.register(new_customer(email="two@example.com"))

    assert second["id"] == first["id"] + 1


def test_register_rejects_an_email_that_differs_only_in_case(customers):
    with pytest.raises(DuplicateEmailError):
        customers.register(new_customer(email="ANA.SOUZA@example.com"))


def test_update_profile_then_get_active_customer_sees_the_change(customers):
    customers.update_profile(ANA_ID, CustomerUpdate(delivery_address="77 New Road"))

    assert customers.get_active_customer(ANA_ID)["delivery_address"] == "77 New Road"


def test_deactivated_customer_cannot_update_their_profile(customers):
    with pytest.raises(ForbiddenError):
        customers.update_profile(CHLOE_DEACTIVATED_ID, CustomerUpdate(name="New Name"))


def test_deactivate_then_get_active_customer_is_refused(customers):
    customers.deactivate(BEN_ID)

    with pytest.raises(ForbiddenError):
        customers.get_active_customer(BEN_ID)


def test_get_active_customer_unknown_id(customers):
    with pytest.raises(CustomerNotFoundError):
        customers.get_active_customer(999)


def test_add_update_and_remove_items(carts):
    add(carts, PIZZA)
    add(carts, SALAD, 2)
    cart = carts.update_quantity(ANA_ID, PIZZA, 3)

    assert [(line["menu_item_id"], line["quantity"]) for line in cart["items"]] == [(PIZZA, 3), (SALAD, 2)]

    cart = carts.remove_item(ANA_ID, SALAD)
    assert [(line["menu_item_id"], line["quantity"]) for line in cart["items"]] == [(PIZZA, 3)]


def test_clear_for_customer_empties_only_that_customers_cart(carts):
    add(carts, PIZZA, customer_id=ANA_ID)
    add(carts, SALAD, customer_id=BEN_ID)

    cleared = carts.clear_for_customer(ANA_ID)

    assert cleared["items"] == [] and cleared["restaurant_id"] is None
    assert [line["menu_item_id"] for line in carts.get_cart(BEN_ID)["items"]] == [SALAD]


@pytest.mark.parametrize(
    "operation",
    [
        lambda carts: carts.get_cart(CHLOE_DEACTIVATED_ID),
        lambda carts: add(carts, PIZZA, customer_id=CHLOE_DEACTIVATED_ID),
        lambda carts: carts.update_quantity(CHLOE_DEACTIVATED_ID, PIZZA, 2),
        lambda carts: carts.remove_item(CHLOE_DEACTIVATED_ID, PIZZA),
        lambda carts: carts.clear_for_customer(CHLOE_DEACTIVATED_ID),
    ],
    ids=["get", "add", "update", "remove", "clear"],
)
def test_every_cart_operation_refuses_a_deactivated_customer(carts, operation):
    with pytest.raises(ForbiddenError):
        operation(carts)
    assert read(config.CARTS_FILE) == []


def test_cart_operations_for_an_unknown_customer_raise_not_found(carts):
    with pytest.raises(NotFoundError):
        add(carts, PIZZA, customer_id=999)


def test_update_quantity_of_an_item_not_in_the_cart(carts):
    add(carts, PIZZA)

    with pytest.raises(ItemNotInCartError):
        carts.update_quantity(ANA_ID, SALAD, 2)


def test_priced_cart_uses_current_menu_prices(carts):
    add(carts, PIZZA, 2)
    add(carts, SALAD, 1)

    cart = carts.get_cart(ANA_ID)

    assert [line["line_total"] for line in cart["items"]] == [33.98, 9.49]
    assert cart["subtotal"] == cart["total"] == 43.47


def test_priced_cart_follows_a_later_price_change(carts, menu):
    add(carts, PIZZA, 2)
    menu.menu_repository.update(PIZZA, {"price": 20.00})

    cart = carts.get_cart(ANA_ID)

    assert cart["items"][0]["unit_price"] == 20.00
    assert cart["total"] == 40.00


def test_priced_total_is_the_exact_decimal_sum_of_its_lines(carts):
    add(carts, PIZZA, 3)
    add(carts, SALAD, 7)

    cart = carts.get_cart(ANA_ID)

    assert Decimal(str(cart["total"])) == sum(Decimal(str(line["line_total"])) for line in cart["items"])


def test_priced_cart_marks_an_item_that_became_unavailable(carts, menu):
    add(carts, PIZZA)
    add(carts, SALAD)
    menu.menu_repository.update(SALAD, {"is_available": False})

    lines = {line["menu_item_id"]: line["is_orderable"] for line in carts.get_cart(ANA_ID)["items"]}

    assert lines == {PIZZA: True, SALAD: False}


def test_cart_restaurant_follows_its_items(carts):
    assert carts.get_cart(ANA_ID)["restaurant_id"] is None
    assert add(carts, PIZZA)["restaurant_id"] == 1
    assert add(carts, SALAD)["restaurant_id"] == 1
    assert carts.remove_item(ANA_ID, PIZZA)["restaurant_id"] == 1
    assert carts.remove_item(ANA_ID, SALAD)["restaurant_id"] is None
    assert add(carts, CRUNCHWRAP)["restaurant_id"] == 2


def test_a_refused_change_leaves_the_stored_cart_unchanged(carts):
    add(carts, PIZZA)
    before = read(config.CARTS_FILE)

    with pytest.raises(DifferentRestaurantError):
        add(carts, CRUNCHWRAP)
    with pytest.raises(MenuItemUnavailableError):
        add(carts, 3)

    assert read(config.CARTS_FILE) == before


def test_a_customer_never_has_more_than_one_active_cart(carts):
    for _ in range(3):
        carts.get_cart(ANA_ID)
        add(carts, PIZZA)
        carts.clear_for_customer(ANA_ID)

    active = [c for c in read(config.CARTS_FILE) if c["customer_id"] == ANA_ID and c["status"] == "active"]
    assert len(active) == 1


def test_stored_cart_holds_only_ids_and_quantities(carts):
    add(carts, PIZZA, 2)

    (stored,) = read(config.CARTS_FILE)
    assert stored["items"] == [{"menu_item_id": PIZZA, "quantity": 2}]


def test_checkout_with_no_cart_is_refused_and_creates_nothing(checkout):
    with pytest.raises(EmptyCartError):
        checkout.checkout(ANA_ID)

    assert read(config.CARTS_FILE) == [] and read(config.ORDERS_FILE) == []


def test_checkout_of_an_emptied_cart_is_refused(carts, checkout):
    add(carts, PIZZA)
    carts.clear_for_customer(ANA_ID)

    with pytest.raises(EmptyCartError):
        checkout.checkout(ANA_ID)


def test_checkout_from_a_restaurant_that_has_since_closed_writes_nothing(carts, checkout):
    add(carts, PIZZA)
    RestaurantRepository(config.RESTAURANTS_FILE).update(1, {"is_open": False})
    before = data_files()

    with pytest.raises(RestaurantClosedError):
        checkout.checkout(ANA_ID)

    assert data_files() == before


def test_checkout_of_an_item_made_unavailable_writes_nothing(carts, menu, checkout):
    add(carts, PIZZA)
    menu.menu_repository.update(PIZZA, {"is_available": False})
    before = data_files()

    with pytest.raises(MenuItemUnavailableError):
        checkout.checkout(ANA_ID)

    assert data_files() == before


def test_deactivated_customer_cannot_check_out(customers, carts, checkout):
    add(carts, PIZZA, customer_id=BEN_ID)
    customers.deactivate(BEN_ID)

    with pytest.raises(ForbiddenError):
        checkout.checkout(BEN_ID)
    assert read(config.ORDERS_FILE) == []


def test_checkout_creates_an_order_matching_the_priced_cart(carts, checkout):
    add(carts, PIZZA, 2)
    add(carts, SALAD, 1)
    cart = carts.get_cart(ANA_ID)

    order = checkout.checkout(ANA_ID)

    assert (order["customer_id"], order["cart_id"], order["restaurant_id"]) == (ANA_ID, cart["id"], 1)
    assert (order["subtotal"], order["total"]) == (cart["subtotal"], cart["total"])
    assert [(line["menu_item_id"], line["quantity"], line["line_total"]) for line in order["items"]] == [
        (line["menu_item_id"], line["quantity"], line["line_total"]) for line in cart["items"]
    ]
    assert order["delivery_address"] == "1155 Bernard Avenue, Kelowna"
    assert read(config.ORDERS_FILE) == [order]


def test_checkout_closes_the_cart_and_the_next_cart_is_new(carts, checkout):
    add(carts, PIZZA)
    order = checkout.checkout(ANA_ID)

    closed = CartRepository(config.CARTS_FILE).get_by_id(order["cart_id"])
    assert closed["status"] == "checked_out"
    assert closed["items"] == [{"menu_item_id": PIZZA, "quantity": 1}]

    fresh = carts.get_cart(ANA_ID)
    assert fresh["id"] != order["cart_id"] and fresh["items"] == []


def test_a_second_checkout_without_new_items_is_refused(carts, checkout):
    add(carts, PIZZA)
    checkout.checkout(ANA_ID)

    with pytest.raises(EmptyCartError):
        checkout.checkout(ANA_ID)
    assert len(read(config.ORDERS_FILE)) == 1


def test_each_checkout_gets_a_new_order_id(carts, checkout):
    add(carts, PIZZA, customer_id=ANA_ID)
    first = checkout.checkout(ANA_ID)
    add(carts, CRUNCHWRAP, customer_id=BEN_ID)
    second = checkout.checkout(BEN_ID)

    assert second["id"] == first["id"] + 1
    assert (first["restaurant_id"], second["restaurant_id"]) == (1, 2)


def test_order_keeps_its_prices_after_the_menu_changes(carts, menu, checkout):
    add(carts, PIZZA, 2)
    order = checkout.checkout(ANA_ID)

    menu.menu_repository.update(PIZZA, {"price": 99.99, "name": "Renamed Pizza"})

    stored = OrderRepository(config.ORDERS_FILE).get_by_id(order["id"])
    assert stored["items"][0]["name"] == "Pepperoni Pizza"
    assert stored["items"][0]["unit_price"] == 16.99
    assert stored["total"] == 33.98
