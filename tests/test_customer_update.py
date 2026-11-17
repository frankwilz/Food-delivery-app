"""Tests for 2.4 (#35): PATCH /customers/me updates name, email and delivery address."""

import json

import pytest

from app.core.errors import BadRequestError
from app.core.security import create_access_token, verify_password
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer import CustomerUpdate
from app.services.customer_service import (
    CustomerDeactivatedError,
    CustomerService,
    DuplicateEmailError,
)

ANA_ID, BEN_ID, CHLOE_DEACTIVATED_ID = 1, 2, 3
ANA_PASSWORD = "Ana-demo-2026"
BEN_EMAIL = "ben.carter@example.com"


def bearer(customer_id: int) -> dict:
    return {"Authorization": f"Bearer {create_access_token(customer_id)}"}


ANA = bearer(ANA_ID)


def stored_customers(tmp_path) -> list[dict]:
    return json.loads((tmp_path / "customers.json").read_text(encoding="utf-8"))


def stored_customer(tmp_path, customer_id: int) -> dict:
    return next(c for c in stored_customers(tmp_path) if c["id"] == customer_id)


def customers_text(tmp_path) -> str:
    return (tmp_path / "customers.json").read_text(encoding="utf-8")


@pytest.fixture
def service(tmp_path) -> CustomerService:
    return CustomerService(CustomerRepository(tmp_path / "customers.json"))


# --- success ---


def test_update_all_three_fields(client, tmp_path):
    changes = {"name": "Ana Lima", "email": "ana.lima@example.com", "delivery_address": "3333 University Way, Kelowna"}

    response = client.patch("/customers/me", json=changes, headers=ANA)

    assert response.status_code == 200
    body = response.json()
    assert {key: body[key] for key in changes} == changes
    assert body["id"] == ANA_ID
    assert body["role"] == "customer"
    assert body["is_active"] is True
    assert "password_hash" not in body
    assert {key: stored_customer(tmp_path, ANA_ID)[key] for key in changes} == changes


@pytest.mark.parametrize(
    "changes",
    [{"name": "Ana Lima"}, {"email": "ana.lima@example.com"}, {"delivery_address": "780 Glenmore Road, Kelowna"}],
)
def test_update_one_field_leaves_the_others_unchanged(client, tmp_path, changes):
    before = stored_customer(tmp_path, ANA_ID)

    response = client.patch("/customers/me", json=changes, headers=ANA)

    assert response.status_code == 200
    assert stored_customer(tmp_path, ANA_ID) == {**before, **changes}


def test_update_only_changes_the_signed_in_customer(client, tmp_path):
    others_before = [c for c in stored_customers(tmp_path) if c["id"] != ANA_ID]

    client.patch("/customers/me", json={"name": "Ana Lima"}, headers=ANA)

    assert [c for c in stored_customers(tmp_path) if c["id"] != ANA_ID] == others_before


def test_values_are_trimmed(client):
    response = client.patch("/customers/me", json={"name": "  Ana Lima  "}, headers=ANA)

    assert response.json()["name"] == "Ana Lima"


def test_get_customers_me_shows_the_update(client):
    client.patch("/customers/me", json={"delivery_address": "1 New Street, Kelowna"}, headers=ANA)

    assert client.get("/customers/me", headers=ANA).json()["delivery_address"] == "1 New Street, Kelowna"


def test_can_log_in_with_the_new_email_and_the_same_password(client):
    client.patch("/customers/me", json={"email": "ana.lima@example.com"}, headers=ANA)

    assert client.post("/auth/login", json={"email": "ana.lima@example.com", "password": ANA_PASSWORD}).status_code == 200
    assert client.post("/auth/login", json={"email": "ana.souza@example.com", "password": ANA_PASSWORD}).status_code == 401


def test_changing_only_the_case_of_your_own_email_is_allowed(client):
    response = client.patch("/customers/me", json={"email": "Ana.Souza@Example.com"}, headers=ANA)

    assert response.status_code == 200
    assert response.json()["email"] == "Ana.Souza@Example.com"


def test_sending_the_same_values_succeeds(client, tmp_path):
    before = stored_customer(tmp_path, ANA_ID)

    response = client.patch("/customers/me", json={"name": before["name"], "email": before["email"]}, headers=ANA)

    assert response.status_code == 200
    assert stored_customer(tmp_path, ANA_ID) == before


# --- errors ---


def test_empty_body_returns_400(client, tmp_path):
    before = customers_text(tmp_path)

    response = client.patch("/customers/me", json={}, headers=ANA)

    assert response.status_code == 400
    assert response.json() == {"detail": "Update request must include at least one field"}
    assert customers_text(tmp_path) == before


@pytest.mark.parametrize("email", [BEN_EMAIL, "BEN.CARTER@example.com", "chloe.martin@example.com"])
def test_duplicate_email_returns_409(client, tmp_path, email):
    # Ben is active, Chloe is deactivated: both emails stay taken
    before = customers_text(tmp_path)

    response = client.patch("/customers/me", json={"email": email}, headers=ANA)

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]
    assert customers_text(tmp_path) == before


@pytest.mark.parametrize(
    "body",
    [
        {"name": ""},
        {"name": "   "},
        {"name": "x" * 101},
        {"email": "not-an-email"},
        {"email": "two@@example.com"},
        {"delivery_address": ""},
        {"delivery_address": "x" * 201},
        {"name": 123},
        {"name": None},
        {"email": None},
        {"delivery_address": None},
    ],
)
def test_invalid_values_or_null_return_422(client, tmp_path, body):
    before = customers_text(tmp_path)

    response = client.patch("/customers/me", json=body, headers=ANA)

    assert response.status_code == 422
    assert customers_text(tmp_path) == before


@pytest.mark.parametrize(
    "body",
    [
        {"id": 99},
        {"role": "manager"},
        {"is_active": False},
        {"password": "a-new-password"},
        {"password_hash": "pbkdf2_sha256$1$00$00"},
        {"name": "Ana Lima", "role": "manager"},
    ],
)
def test_protected_fields_cannot_be_changed(client, tmp_path, body):
    before = customers_text(tmp_path)

    response = client.patch("/customers/me", json=body, headers=ANA)

    assert response.status_code == 422
    assert customers_text(tmp_path) == before
    # The account is unchanged, including the password
    assert stored_customer(tmp_path, ANA_ID)["role"] == "customer"
    assert verify_password(ANA_PASSWORD, stored_customer(tmp_path, ANA_ID)["password_hash"])


def test_update_requires_sign_in(client, tmp_path):
    before = customers_text(tmp_path)

    assert client.patch("/customers/me", json={"name": "Someone"}).status_code == 401
    assert customers_text(tmp_path) == before


def test_deactivated_customer_gets_403(client, tmp_path):
    before = customers_text(tmp_path)

    response = client.patch("/customers/me", json={"name": "Chloe M"}, headers=bearer(CHLOE_DEACTIVATED_ID))

    assert response.status_code == 403
    assert customers_text(tmp_path) == before


def test_update_responses_are_documented(client):
    responses = client.get("/openapi.json").json()["paths"]["/customers/me"]["patch"]["responses"]

    assert {"200", "400", "401", "403", "409", "422"} <= set(responses)


# --- service ---


def test_service_update_profile(service):
    updated = service.update_profile(ANA_ID, CustomerUpdate(delivery_address="1 New Street, Kelowna"))

    assert updated["delivery_address"] == "1 New Street, Kelowna"
    assert service.repository.get_by_id(ANA_ID)["delivery_address"] == "1 New Street, Kelowna"


def test_service_update_profile_errors(service):
    with pytest.raises(BadRequestError):
        service.update_profile(ANA_ID, CustomerUpdate())
    with pytest.raises(DuplicateEmailError):
        service.update_profile(ANA_ID, CustomerUpdate(email=BEN_EMAIL))
    with pytest.raises(CustomerDeactivatedError):
        service.update_profile(CHLOE_DEACTIVATED_ID, CustomerUpdate(name="Chloe M"))


def test_customer_update_model_has_only_the_editable_fields():
    assert set(CustomerUpdate.model_fields) == {"name", "email", "delivery_address"}
