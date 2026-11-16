import json

import pytest

from app.core.config import BASE_DIR
from app.core.security import hash_password, verify_password
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer import Customer, CustomerCreate
from app.services.customer_service import CustomerService, DuplicateEmailError

VALID_CUSTOMER = {
    "name": "Jordan Lee",
    "email": "jordan.lee@example.com",
    "password": "correct-horse-battery",
    "delivery_address": "1200 Academy Way, Kelowna",
}


def stored_customers(tmp_path) -> list[dict]:
    return json.loads((tmp_path / "customers.json").read_text(encoding="utf-8"))


# --- POST /customers: successful registration ---


def test_register_customer_returns_201_and_the_new_customer(client):
    response = client.post("/customers", json=VALID_CUSTOMER)

    assert response.status_code == 201
    assert response.json() == {
        "id": 5,
        "name": "Jordan Lee",
        "email": "jordan.lee@example.com",
        "delivery_address": "1200 Academy Way, Kelowna",
        "role": "customer",
        "is_active": True,
    }


def test_register_customer_is_saved_to_the_file(client, tmp_path):
    client.post("/customers", json=VALID_CUSTOMER)

    customers = stored_customers(tmp_path)
    assert len(customers) == 5
    assert customers[-1]["id"] == 5
    assert customers[-1]["email"] == "jordan.lee@example.com"


def test_register_does_not_change_existing_customers(client, tmp_path):
    before = stored_customers(tmp_path)

    client.post("/customers", json=VALID_CUSTOMER)

    assert stored_customers(tmp_path)[:-1] == before


# --- POST /customers: duplicate emails ---


@pytest.mark.parametrize("email", ["ana.souza@example.com", "Ana.Souza@Example.COM", "  ANA.SOUZA@EXAMPLE.COM  "])
def test_register_duplicate_email_returns_409_ignoring_case(client, tmp_path, email):
    before = stored_customers(tmp_path)

    response = client.post("/customers", json={**VALID_CUSTOMER, "email": email})

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]
    assert stored_customers(tmp_path) == before


def test_register_email_of_deactivated_account_is_still_taken(client):
    response = client.post("/customers", json={**VALID_CUSTOMER, "email": "chloe.martin@example.com"})

    assert response.status_code == 409


# --- POST /customers: invalid bodies ---


@pytest.mark.parametrize(
    "body",
    [
        {k: v for k, v in VALID_CUSTOMER.items() if k != "email"},  # missing email
        {k: v for k, v in VALID_CUSTOMER.items() if k != "password"},  # missing password
        {**VALID_CUSTOMER, "email": "not-an-email"},
        {**VALID_CUSTOMER, "email": "two@@example.com"},
        {**VALID_CUSTOMER, "password": "short"},  # under 8 characters
        {**VALID_CUSTOMER, "name": "   "},  # blank after stripping
        {**VALID_CUSTOMER, "delivery_address": ""},
        {**VALID_CUSTOMER, "name": 123},
        {**VALID_CUSTOMER, "id": 99},  # server-assigned
        {**VALID_CUSTOMER, "role": "manager"},  # cannot self-register as a manager
        {**VALID_CUSTOMER, "is_active": False},
        {**VALID_CUSTOMER, "password_hash": "anything"},
    ],
)
def test_register_invalid_body_returns_422(client, tmp_path, body):
    before = stored_customers(tmp_path)

    response = client.post("/customers", json=body)

    assert response.status_code == 422
    assert stored_customers(tmp_path) == before


def test_register_malformed_json_returns_422(client):
    response = client.post("/customers", content="{not json", headers={"Content-Type": "application/json"})

    assert response.status_code == 422


# --- Passwords ---


def test_password_is_hashed_before_storage(client, tmp_path):
    client.post("/customers", json=VALID_CUSTOMER)

    raw_file = (tmp_path / "customers.json").read_text(encoding="utf-8")
    saved = stored_customers(tmp_path)[-1]
    assert VALID_CUSTOMER["password"] not in raw_file
    assert "password" not in saved
    assert saved["password_hash"].startswith("pbkdf2_sha256$")
    assert verify_password(VALID_CUSTOMER["password"], saved["password_hash"])


def test_password_is_never_returned(client):
    response = client.post("/customers", json=VALID_CUSTOMER)

    assert "password" not in response.json()
    assert "password_hash" not in response.json()
    assert VALID_CUSTOMER["password"] not in response.text


def test_password_spaces_are_kept():
    data = CustomerCreate(**{**VALID_CUSTOMER, "password": "  spaced out  "})

    assert data.password == "  spaced out  "


def test_hash_password_uses_a_fresh_salt_each_time():
    first, second = hash_password("same-password"), hash_password("same-password")

    assert first != second
    assert verify_password("same-password", first)
    assert verify_password("same-password", second)
    assert not verify_password("wrong-password", first)


# --- Service and repository ---


def test_service_register_raises_on_duplicate_email(tmp_path):
    service = CustomerService(CustomerRepository(tmp_path / "customers.json"))

    with pytest.raises(DuplicateEmailError):
        service.register(CustomerCreate(**{**VALID_CUSTOMER, "email": "BEN.CARTER@example.com"}))


def test_repository_create_assigns_next_id(tmp_path):
    repository = CustomerRepository(tmp_path / "customers.json")

    created = repository.create({"name": "X", "email": "x@example.com"})

    assert created["id"] == 5
    assert repository.get_by_email("X@EXAMPLE.COM") == created


def test_repository_get_by_email_returns_none_when_missing(tmp_path):
    repository = CustomerRepository(tmp_path / "customers.json")

    assert repository.get_by_email("nobody@example.com") is None


# --- Committed data and documentation ---


def test_committed_customer_data_is_valid():
    """data/customers.json has valid, uniquely identified customers with hashed passwords:
    at least 2 active customers, 1 deactivated customer and 1 manager."""
    customers = json.loads((BASE_DIR / "data" / "customers.json").read_text(encoding="utf-8"))

    for customer in customers:
        Customer(**customer)
        assert customer["password_hash"].startswith("pbkdf2_sha256$")
        assert "password" not in customer
    assert len({c["id"] for c in customers}) == len(customers)
    assert len({c["email"].casefold() for c in customers}) == len(customers)
    assert sum(c["role"] == "customer" and c["is_active"] for c in customers) >= 2
    assert sum(c["role"] == "customer" and not c["is_active"] for c in customers) >= 1
    assert sum(c["role"] == "manager" for c in customers) >= 1


def test_customer_error_responses_are_documented(client):
    post = client.get("/openapi.json").json()["paths"]["/customers"]["post"]

    assert {"201", "409", "422"} <= post["responses"].keys()
