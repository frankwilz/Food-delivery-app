"""Cross-subsystem test: Customer -> Menu -> Cart -> Checkout -> Order, with menu price changes.

A price change before checkout must reach the cart total and the order (checkout recalculates from the
current menu). A price change after checkout must not change the saved order (it keeps a snapshot).
"""

ANA = {"email": "ana.souza@example.com", "password": "Ana-demo-2026"}
MANAGER = {"email": "dev.patel@example.com", "password": "Dev-demo-2026"}
RESTAURANT_ID = 1
PIZZA, SALAD = 1, 2  # Pepperoni Pizza 16.99 and Caesar Salad 9.49 at restaurant 1


def sign_in(client, account: dict) -> dict:
    response = client.post("/auth/login", json=account)
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_price_changes_before_and_after_checkout(client):
    customer = sign_in(client, ANA)
    manager = sign_in(client, MANAGER)

    # Customer: the signed-in account, whose address the order will keep
    address = client.get("/customers/me", headers=customer).json()["delivery_address"]

    # Menu: both items are on the menu and can be ordered
    menu = {item["id"]: item for item in client.get(f"/restaurants/{RESTAURANT_ID}/menu").json()}
    assert menu[PIZZA]["is_available"] and menu[SALAD]["is_available"]

    # Cart: add both items, then change a quantity
    client.post("/cart/items", json={"menu_item_id": PIZZA, "quantity": 1}, headers=customer)
    client.post("/cart/items", json={"menu_item_id": SALAD, "quantity": 1}, headers=customer)
    cart = client.patch(f"/cart/items/{PIZZA}", json={"quantity": 2}, headers=customer).json()
    assert cart["total"] == 43.47  # 2 x 16.99 + 9.49

    # Menu change before checkout: the cart is repriced from the current menu
    assert client.patch(
        f"/restaurants/{RESTAURANT_ID}/menu/{PIZZA}", json={"price": 18.5}, headers=manager
    ).status_code == 200
    assert client.get("/cart", headers=customer).json()["total"] == 46.49  # 2 x 18.50 + 9.49

    # Checkout: the order uses the new price, never the price from when the item was added
    response = client.post("/checkout", headers=customer)
    assert response.status_code == 201
    order = response.json()
    assert [(line["menu_item_id"], line["unit_price"], line["quantity"]) for line in order["items"]] == [
        (PIZZA, 18.5, 2),
        (SALAD, 9.49, 1),
    ]
    assert order["total"] == 46.49
    assert order["delivery_address"] == address
    assert order["status"] == "placed"

    # The cart was closed only after the order was saved: the customer now has a new, empty cart
    assert client.get("/cart", headers=customer).json()["items"] == []

    # Menu change after checkout: the saved order keeps its snapshot
    changed = client.patch(
        f"/restaurants/{RESTAURANT_ID}/menu/{PIZZA}", json={"price": 25, "name": "Deluxe Pizza"}, headers=manager
    )
    assert changed.status_code == 200
    current_menu = client.get(f"/restaurants/{RESTAURANT_ID}/menu/{PIZZA}")
    assert current_menu.status_code == 200
    assert current_menu.json()["price"] == 25
    assert current_menu.json()["name"] == "Deluxe Pizza"
    saved = client.get(f"/orders/{order['id']}", headers=customer).json()
    assert saved == order
    assert saved["items"][0]["name"] == "Pepperoni Pizza"
    assert client.get("/orders", headers=customer).json()[0]["id"] == order["id"]
