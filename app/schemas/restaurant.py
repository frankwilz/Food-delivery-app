from pydantic import BaseModel, ConfigDict, Field, field_validator


class RestaurantId(BaseModel):
    id: int = Field(description="Stable, server-assigned identifier.")


class RestaurantBase(BaseModel):
    """Fields shared by every restaurant model."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100, description="Restaurant name.")
    cuisine: str = Field(min_length=1, max_length=50, description="Type of food, e.g. Pizza, Mexican.")
    address: str = Field(min_length=1, max_length=200, description="Street address.")
    rating: float = Field(default=0.0, ge=0, le=5, description="Average rating from 0 to 5.")
    is_open: bool = Field(default=True, description="Whether the restaurant is currently accepting orders.")


class Restaurant(RestaurantBase, RestaurantId):
    """Response model: a restaurant as stored and returned by the API.

    (RestaurantId is listed last so `id` appears first in responses.)
    """


class RestaurantCreate(RestaurantBase):
    """Request body for creating a restaurant. The id is assigned by the server, so it may not be sent."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "name": "Lakeside Pizzeria",
                "cuisine": "Pizza",
                "address": "12 Water Street",
                "rating": 4.2,
                "is_open": True,
            }
        },
    )


class RestaurantUpdate(BaseModel):
    """Request body for a partial update: only the fields provided are changed."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
        json_schema_extra={"example": {"address": "99 Harvey Avenue", "is_open": False}},
    )

    name: str | None = Field(default=None, min_length=1, max_length=100)
    cuisine: str | None = Field(default=None, min_length=1, max_length=50)
    address: str | None = Field(default=None, min_length=1, max_length=200)
    rating: float | None = Field(default=None, ge=0, le=5)
    is_open: bool | None = None

    @field_validator("*")
    @classmethod
    def reject_explicit_null(cls, value):
        # Fields may be omitted, but sending null would erase required data
        if value is None:
            raise ValueError("field cannot be null")
        return value
