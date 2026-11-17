from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class OrderItem(BaseModel):
    """One order line: a snapshot of the menu item's name and price at checkout."""

    menu_item_id: int
    name: str = Field(description="Item name at checkout.")
    unit_price: float = Field(description="Menu price at checkout.")
    quantity: int
    line_total: float = Field(description="`unit_price × quantity`, rounded to 2 decimals.")


class Order(BaseModel):
    """A saved order. Names, prices and the delivery address are snapshots taken at checkout,
    so later menu or profile changes never change an existing order."""

    id: int = Field(description="Stable, server-assigned identifier.")
    customer_id: int
    restaurant_id: int
    items: list[OrderItem]
    subtotal: float = Field(description="Sum of the line totals.")
    total: float = Field(description="Amount paid. Equals the subtotal (no delivery fee or tax yet).")
    delivery_address: str = Field(description="The customer's delivery address at checkout.")
    status: Literal["placed"] = Field(description="Always `placed` for now.")
    created_at: datetime = Field(description="When the order was placed (UTC).")
