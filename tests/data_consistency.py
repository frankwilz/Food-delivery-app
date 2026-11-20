"""Checks that a folder of the five JSON data files is valid and consistent.

Shared by the committed-data test (test_workflow.py) and the restart test (test_integration.py),
so the data a real server leaves behind meets the same rules as the committed demo data.
Originally written inline in test_workflow.py (5.2, #50); moved here for 5.8 (#56).
"""

import json
from decimal import Decimal
from pathlib import Path

from app.schemas.cart import MAX_QUANTITY, Cart
from app.schemas.customer import Customer
from app.schemas.menu_item import MenuItem
from app.schemas.order import Order
from app.schemas.restaurant import Restaurant

SCHEMAS = {
    "restaurants": Restaurant,
    "menu_items": MenuItem,
    "customers": Customer,
    "carts": Cart,
    "orders": Order,
}


def load_and_check(data_dir: Path) -> dict[str, dict[int, dict]]:
    """Assert every record and relationship in `data_dir` is valid; return the records by file and id."""
    data = {}
    for name, schema in SCHEMAS.items():
        records = json.loads((data_dir / f"{name}.json").read_text(encoding="utf-8"))
        assert len({record["id"] for record in records}) == len(records), f"{name}: repeated id"
        for record in records:
            schema.model_validate(record)
        data[name] = {record["id"]: record for record in records}

    for item in data["menu_items"].values():
        assert item["restaurant_id"] in data["restaurants"]

    active_customers = []
    for cart in data["carts"].values():
        assert cart["customer_id"] in data["customers"]
        if cart["status"] == "active":
            active_customers.append(cart["customer_id"])
        assert cart["restaurant_id"] in data["restaurants"] if cart["items"] else cart["restaurant_id"] is None
        for line in cart["items"]:
            assert set(line) == {"menu_item_id", "quantity"}  # Prices belong to the menu or order snapshot.
            assert type(line["quantity"]) is int and 1 <= line["quantity"] <= MAX_QUANTITY
            assert data["menu_items"][line["menu_item_id"]]["restaurant_id"] == cart["restaurant_id"]
    assert len(active_customers) == len(set(active_customers)), "a customer has two active carts"

    ordered_carts = []
    for order in data["orders"].values():
        assert order["customer_id"] in data["customers"]
        assert order["restaurant_id"] in data["restaurants"]
        cart = data["carts"][order["cart_id"]]
        ordered_carts.append(cart["id"])
        assert cart["status"] == "checked_out"
        assert (cart["customer_id"], cart["restaurant_id"]) == (order["customer_id"], order["restaurant_id"])
        assert [(line["menu_item_id"], line["quantity"]) for line in order["items"]] == [
            (line["menu_item_id"], line["quantity"]) for line in cart["items"]
        ]
        for line in order["items"]:
            assert data["menu_items"][line["menu_item_id"]]["restaurant_id"] == order["restaurant_id"]
            assert Decimal(str(line["unit_price"])) * line["quantity"] == Decimal(str(line["line_total"]))
        total = sum(Decimal(str(line["line_total"])) for line in order["items"])
        assert total == Decimal(str(order["subtotal"])) == Decimal(str(order["total"]))
    assert len(ordered_carts) == len(set(ordered_carts)), "a cart became two orders"

    return data
