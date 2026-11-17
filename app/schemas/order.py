from pydantic import BaseModel, Field


class OrderItem(BaseModel):
    """One order line: a snapshot of the menu item's name and price at checkout."""

    menu_item_id: int
    name: str = Field(description="Item name at checkout.")
    unit_price: float = Field(description="Menu price at checkout.")
    quantity: int
    line_total: float = Field(description="`unit_price × quantity`, rounded to 2 decimals.")


class OrderTotals(BaseModel):
    """The lines and totals of an order, calculated by the backend from the current menu."""

    restaurant_id: int
    items: list[OrderItem]
    subtotal: float = Field(description="Sum of the line totals.")
    total: float = Field(description="Amount to pay. Equals the subtotal (no delivery fee or tax yet).")
