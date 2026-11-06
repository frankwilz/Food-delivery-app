from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

# Deliberately simple: one "@", no spaces, and a dot in the domain
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class CustomerBase(BaseModel):
    """Profile fields shared by every customer model."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100, description="Full name.")
    email: str = Field(
        max_length=254,
        pattern=EMAIL_PATTERN,
        description="Login email. Unique across all customers, ignoring case.",
    )
    delivery_address: str = Field(min_length=1, max_length=200, description="Where orders are delivered.")


class Customer(CustomerBase):
    """Response model. It has no password fields, so a password hash can never be returned."""

    id: int = Field(description="Stable, server-assigned identifier.")
    role: Literal["customer", "manager"] = Field(description="`customer` or `manager`.")
    is_active: bool = Field(description="False once the account has been deactivated.")


class CustomerCreate(CustomerBase):
    """Registration body. The server sets `id`, `role` (always `customer`) and `is_active`, so they may not be sent."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "name": "Jordan Lee",
                "email": "jordan.lee@example.com",
                "password": "correct-horse-battery",
                "delivery_address": "1200 Academy Way, Kelowna",
            }
        },
    )

    # Never stripped: leading or trailing spaces are part of the password the user chose
    password: Annotated[str, StringConstraints(strip_whitespace=False)] = Field(
        min_length=8,
        max_length=128,
        description="Plain-text password, 8 to 128 characters. Only a salted hash is stored.",
        json_schema_extra={"format": "password"},
    )


class CustomerUpdate(BaseModel):
    """Partial profile update: only the fields provided are changed."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, max_length=254, pattern=EMAIL_PATTERN)
    delivery_address: str | None = Field(default=None, min_length=1, max_length=200)

    @field_validator("*")
    @classmethod
    def reject_explicit_null(cls, value):
        # Fields may be omitted, but sending null would erase required data
        if value is None:
            raise ValueError("field cannot be null")
        return value
