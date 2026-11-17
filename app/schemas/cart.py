from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Largest quantity of a single item a cart may hold. Stops typos like 1000 pizzas.
MAX_QUANTITY = 99

# strict=True rejects 2.0, "2" and true, so a quantity must be a JSON whole number
Quantity = Field(strict=True, ge=1, le=MAX_QUANTITY, description=f"Whole number from 1 to {MAX_QUANTITY}.")


class CartItem(BaseModel):
    """One stored cart line. Only the id and quantity are stored, never a price."""

    menu_item_id: int
    quantity: int


class Cart(BaseModel):
    """A cart as stored in data/carts.json."""

    id: int
    customer_id: int
    restaurant_id: int | None = Field(description="Restaurant of the items in the cart; null while it is empty.")
    items: list[CartItem]
    status: Literal["active", "checked_out"]


class CartItemAdd(BaseModel):
    """Body of `POST /cart/items`."""

    model_config = ConfigDict(extra="forbid", json_schema_extra={"example": {"menu_item_id": 1, "quantity": 2}})

    menu_item_id: int = Field(strict=True, ge=1, description="Id of the menu item to add.")
    quantity: int = Quantity


class CartItemUpdate(BaseModel):
    """Body of `PATCH /cart/items/{menu_item_id}`."""

    model_config = ConfigDict(extra="forbid", json_schema_extra={"example": {"quantity": 3}})

    quantity: int = Quantity


class CartLine(BaseModel):
    """A cart line priced from the current menu."""

    menu_item_id: int
    name: str
    unit_price: float = Field(description="Current menu price.")
    quantity: int
    line_total: float = Field(description="`unit_price × quantity`, rounded to 2 decimals.")
    is_orderable: bool = Field(
        description="False if the item has since become unavailable or been removed from the menu. "
        "Such an item stays in the cart but checkout will refuse it."
    )


class CartResponse(BaseModel):
    """A cart with prices calculated by the backend from the current menu."""

    id: int
    customer_id: int
    restaurant_id: int | None
    status: Literal["active", "checked_out"]
    items: list[CartLine]
    subtotal: float = Field(description="Sum of the line totals.")
    total: float = Field(description="Amount to pay. For now this equals the subtotal (no delivery fee or tax).")
