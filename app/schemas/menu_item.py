from pydantic import BaseModel, ConfigDict, Field, field_validator


class MenuItemBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    price: float = Field(gt=0)
    category: str = Field(min_length=1, max_length=50)
    is_available: bool = Field(default=True, description="False while the item is temporarily out of stock.")


class MenuItem(MenuItemBase):
    id: int
    restaurant_id: int
    is_active: bool = Field(
        default=True,
        description="False once the item has been removed from the menu. Records are kept, never erased.",
    )


class MenuItemCreate(MenuItemBase):
    # id and restaurant_id come from the server/URL and a new item always starts active,
    # so clients may not send id, restaurant_id or is_active
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class MenuItemUpdate(BaseModel):
    """Partial update: only the fields provided by the client are changed."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    price: float | None = Field(default=None, gt=0)
    category: str | None = Field(default=None, min_length=1, max_length=50)
    is_available: bool | None = None
    is_active: bool | None = Field(default=None, description="Send `true` to put a removed item back on the menu.")

    @field_validator("*")
    @classmethod
    def reject_explicit_null(cls, value):
        # Fields may be omitted, but sending null would erase required data
        if value is None:
            raise ValueError("field cannot be null")
        return value
