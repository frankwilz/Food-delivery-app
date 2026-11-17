"""The one place money is calculated. The cart and checkout both call `price_lines`.

Amounts are calculated with `Decimal` and rounded half-up to 2 decimals, so 0.1 + 0.2 is
exactly 0.30 and the same cart always gives the same total. They are returned as floats
because that is how prices are stored in data/menu_items.json and sent as JSON.

Decision: `total` equals `subtotal` for Milestone 2. There is no delivery fee or tax yet; if
one is added, it goes in `price_lines` so the cart and checkout stay in agreement.
"""

from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def to_money(amount: Decimal) -> float:
    return float(amount.quantize(CENT, rounding=ROUND_HALF_UP))


def price_lines(lines: list[tuple[dict, int]]) -> dict:
    """Price `(menu item, quantity)` pairs using each item's current menu price.

    Returns `{"items": [...], "subtotal": float, "total": float}`. Each item line has the
    `menu_item_id`, `name`, `unit_price`, `quantity` and `line_total`.
    """
    priced = []
    subtotal = Decimal("0")
    for item, quantity in lines:
        # str() first, so 16.99 becomes Decimal("16.99") rather than its binary approximation
        unit_price = Decimal(str(item["price"]))
        line_total = (unit_price * quantity).quantize(CENT, rounding=ROUND_HALF_UP)
        subtotal += line_total
        priced.append(
            {
                "menu_item_id": item["id"],
                "name": item["name"],
                "unit_price": to_money(unit_price),
                "quantity": quantity,
                "line_total": to_money(line_total),
            }
        )
    total = subtotal  # no delivery fee or tax in Milestone 2 (see module docstring)
    return {"items": priced, "subtotal": to_money(subtotal), "total": to_money(total)}
