from pydantic import BaseModel, ConfigDict, Field


class MenuItemBase(BaseModel):
    """Fields shared by every menu-item model."""

    name: str = Field(..., min_length=1, max_length=100, description="Display name of the dish.")
    description: str = Field("", max_length=500, description="Short description shown to customers.")
    price: float = Field(..., gt=0, description="Price in dollars. Must be greater than zero.")
    category: str = Field("Main", min_length=1, max_length=50, description="Menu section, e.g. Appetizer, Main, Drink.")
    is_available: bool = Field(True, description="Whether the item can currently be ordered.")


class MenuItemCreate(MenuItemBase):
    """Request body for adding a menu item.

    `id` and `restaurant_id` are not accepted from the client: the id is assigned by
    the server and the restaurant comes from the URL path.
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "name": "Garlic Bread",
                "description": "Toasted baguette with garlic butter",
                "price": 6.49,
                "category": "Appetizer",
                "is_available": True,
            }
        },
    )


class MenuItemUpdate(BaseModel):
    """Request body for a partial update. Only the fields sent are changed."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": {"price": 7.99, "is_available": False}},
    )

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    price: float | None = Field(None, gt=0)
    category: str | None = Field(None, min_length=1, max_length=50)
    is_available: bool | None = None


class MenuItemIds(BaseModel):
    id: int = Field(..., description="Stable, server-assigned identifier (unique across all restaurants).")
    restaurant_id: int = Field(..., description="Id of the restaurant this item belongs to.")


class MenuItem(MenuItemBase, MenuItemIds):
    """Response model: a menu item as stored and returned by the API.

    (Inherits MenuItemIds last so `id` and `restaurant_id` appear first in responses.)
    """


class ErrorResponse(BaseModel):
    """Shape of error bodies returned by the menu endpoints (matches FastAPI's HTTPException)."""

    detail: str
