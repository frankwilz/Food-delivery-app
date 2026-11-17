"""Tests for 2.5 (#36), part 1: customer deactivation, and deactivated customers locked out."""

import json

import pytest

from app.core.errors import ForbiddenError
from app.core.security import create_access_token
from app.repositories.customer_repository import CustomerRepository
from app.services.auth_service import AuthService, InvalidCredentialsError
from app.services.customer_service import (
    CustomerDeactivatedError,
    CustomerNotFoundError,
    CustomerService,
    ensure_active,
)

# Demo accounts from data/customers.json (the passwords are listed in the README)
ANA = {"email": "ana.souza@example.com", "password": "Ana-demo-2026"}
CHLOE = {"email": "chloe.martin@example.com", "password": "Chloe-demo-2026"}  # deactivated
ANA_ID, BEN_ID, CHLOE_ID = 1, 2, 3


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def login(client, credentials: dict) -> str:
    return client.post("/auth/login", json=credentials).json()["access_token"]


def stored_customer(tmp_path, customer_id: int) -> dict:
    customers = json.loads((tmp_path / "customers.json").read_text(encoding="utf-8"))
    return next(c for c in customers if c["id"] == customer_id)


@pytest.fixture
def repository(tmp_path) -> CustomerRepository:
    return CustomerRepository(tmp_path / "customers.json")


# --- POST /customers/me/deactivate ---


def test_deactivate_returns_the_account_with_is_active_false(client, tmp_path):
    token = login(client, ANA)

    response = client.post("/customers/me/deactivate", headers=bearer(token))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == ANA_ID
    assert body["is_active"] is False
    assert "password_hash" not in body
    assert stored_customer(tmp_path, ANA_ID)["is_active"] is False


def test_deactivate_keeps_the_rest_of_the_record(client, tmp_path):
    before = stored_customer(tmp_path, ANA_ID)

    client.post("/customers/me/deactivate", headers=bearer(login(client, ANA)))

    assert stored_customer(tmp_path, ANA_ID) == {**before, "is_active": False}


def test_deactivate_only_changes_the_signed_in_customer(client, tmp_path):
    client.post("/customers/me/deactivate", headers=bearer(login(client, ANA)))

    assert stored_customer(tmp_path, BEN_ID)["is_active"] is True


def test_deactivate_requires_sign_in(client, tmp_path):
    response = client.post("/customers/me/deactivate")

    assert response.status_code == 401
    assert stored_customer(tmp_path, ANA_ID)["is_active"] is True


def test_deactivated_customer_cannot_deactivate_again(client):
    response = client.post("/customers/me/deactivate", headers=bearer(create_access_token(CHLOE_ID)))

    assert response.status_code == 403


def test_deactivated_email_stays_taken(client):
    client.post("/customers/me/deactivate", headers=bearer(login(client, ANA)))

    response = client.post(
        "/customers",
        json={"name": "Someone Else", "email": ANA["email"], "password": "long-enough-1", "delivery_address": "1 St"},
    )

    assert response.status_code == 409


# --- a deactivated customer cannot log in ---


def test_deactivated_customer_login_returns_403(client):
    response = client.post("/auth/login", json=CHLOE)

    assert response.status_code == 403
    assert response.json() == {"detail": "Customer 3 has been deactivated"}


def test_deactivated_customer_with_wrong_password_still_gets_401(client):
    # The account's status is only revealed to someone who knows the password
    response = client.post("/auth/login", json={**CHLOE, "password": "wrong-password"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect email or password"}


def test_login_fails_after_deactivating(client):
    client.post("/customers/me/deactivate", headers=bearer(login(client, ANA)))

    assert client.post("/auth/login", json=ANA).status_code == 403


# --- existing tokens stop working ---


def test_token_issued_before_deactivation_is_refused(client):
    token = login(client, ANA)
    assert client.get("/customers/me", headers=bearer(token)).status_code == 200

    client.post("/customers/me/deactivate", headers=bearer(token))
    response = client.get("/customers/me", headers=bearer(token))

    assert response.status_code == 403
    assert response.json() == {"detail": "Customer 1 has been deactivated"}


@pytest.mark.parametrize(
    "method, path",
    [("get", "/customers/me"), ("get", "/cart"), ("delete", "/cart"), ("post", "/checkout")],
)
def test_deactivated_customer_token_is_refused_on_protected_endpoints(client, method, path):
    response = getattr(client, method)(path, headers=bearer(create_access_token(CHLOE_ID)))

    assert response.status_code == 403


def test_deactivated_customer_cannot_add_to_cart_after_deactivating(client, tmp_path):
    token = login(client, ANA)
    client.post("/customers/me/deactivate", headers=bearer(token))

    response = client.post("/cart/items", json={"menu_item_id": 1, "quantity": 1}, headers=bearer(token))

    assert response.status_code == 403
    carts = json.loads((tmp_path / "carts.json").read_text(encoding="utf-8"))
    assert [cart for cart in carts if cart["customer_id"] == ANA_ID] == []


def test_deactivation_responses_are_documented(client):
    paths = client.get("/openapi.json").json()["paths"]

    assert {"401", "403"} <= set(paths["/customers/me/deactivate"]["post"]["responses"])
    assert "403" in paths["/customers/me"]["get"]["responses"]
    assert "403" in paths["/auth/login"]["post"]["responses"]


# --- service and repository ---


def test_service_deactivate_sets_is_active_false(repository):
    service = CustomerService(repository)

    customer = service.deactivate(ANA_ID)

    assert customer["is_active"] is False
    assert repository.get_by_id(ANA_ID)["is_active"] is False
    with pytest.raises(CustomerDeactivatedError):
        service.get_active_customer(ANA_ID)


def test_service_deactivate_unknown_customer_raises_not_found(repository):
    with pytest.raises(CustomerNotFoundError):
        CustomerService(repository).deactivate(99)


def test_auth_service_refuses_deactivated_customer(repository):
    service = AuthService(repository)
    token = create_access_token(CHLOE_ID)

    with pytest.raises(ForbiddenError):
        service.login(CHLOE["email"], CHLOE["password"])
    with pytest.raises(InvalidCredentialsError):
        service.login(CHLOE["email"], "wrong-password")
    with pytest.raises(CustomerDeactivatedError):
        service.get_customer_for_token(token)


def test_ensure_active():
    assert ensure_active({"id": 1, "is_active": True}) == {"id": 1, "is_active": True}
    with pytest.raises(CustomerDeactivatedError, match="Customer 7 has been deactivated"):
        ensure_active({"id": 7, "is_active": False})


def test_repository_update_never_changes_the_id(repository):
    updated = repository.update(ANA_ID, {"id": 99, "is_active": False})

    assert updated["id"] == ANA_ID
    assert repository.get_by_id(99) is None
    assert repository.get_by_id(ANA_ID)["is_active"] is False


def test_repository_update_unknown_customer_returns_none(repository):
    assert repository.update(99, {"is_active": False}) is None
