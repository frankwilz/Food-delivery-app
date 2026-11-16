from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class LoginRequest(BaseModel):
    """Login body. Only checks that both fields are present; a wrong value is a 401, not a 422."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
        json_schema_extra={"example": {"email": "ana.souza@example.com", "password": "Ana-demo-2026"}},
    )

    email: str = Field(min_length=1, max_length=254, description="The email the account was registered with.")
    # Never stripped: leading or trailing spaces are part of the password the user chose
    password: Annotated[str, StringConstraints(strip_whitespace=False)] = Field(
        min_length=1,
        max_length=128,
        description="The account's plain-text password.",
        json_schema_extra={"format": "password"},
    )


class TokenResponse(BaseModel):
    """A successful login. Send the token back as `Authorization: Bearer <access_token>`."""

    access_token: str = Field(description="Signed JWT that identifies the customer until it expires.")
    token_type: Literal["bearer"] = Field(default="bearer", description="Always `bearer`.")
