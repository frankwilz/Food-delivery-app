import json
import os
import subprocess
import sys
from datetime import timedelta

import jwt
import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_customer
from app.core import security
from app.core.config import BASE_DIR
from app.core.security import create_access_token, decode_access_token
from app.main import app
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer import Customer
from app.services.auth_service import AuthService, InvalidCredentialsError, InvalidTokenError

# Demo accounts from data/customers.json (the passwords are listed in the README)
ANA = {"email": "ana.souza@example.com", "password": "Ana-demo-2026"}
ANA_ID = 1


def customers_file_text(tmp_path) -> str:
    return (tmp_path / "customers.json").read_text(encoding="utf-8")


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# --- POST /auth/login ---


def test_login_returns_a_bearer_token_for_the_customer(client):
    response = client.post("/auth/login", json=ANA)

    assert response.status_code == 200
    body = response.json()
    assert body.keys() == {"access_token", "token_type"}
    assert body["token_type"] == "bearer"
    assert decode_access_token(body["access_token"]) == ANA_ID


@pytest.mark.parametrize("email", ["Ana.Souza@Example.COM", "  ana.souza@example.com  "])
def test_login_email_ignores_case_and_surrounding_spaces(client, email):
    response = client.post("/auth/login", json={**ANA, "email": email})

    assert response.status_code == 200
    assert decode_access_token(response.json()["access_token"]) == ANA_ID


def test_login_wrong_password_returns_401(client):
    response = client.post("/auth/login", json={**ANA, "password": "not-the-password"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect email or password"}
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_login_unknown_email_returns_the_same_401(client):
    response = client.post("/auth/login", json={"email": "nobody@example.com", "password": "Ana-demo-2026"})

    # Same status and message as a wrong password, so the response does not reveal which emails exist
    assert response.status_code == 401
    assert response.json() == {"detail": "Incorrect email or password"}


def test_login_password_spaces_are_not_stripped(client):
    response = client.post("/auth/login", json={**ANA, "password": " Ana-demo-2026 "})

    assert response.status_code == 401


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"email": "ana.souza@example.com"},
        {"password": "Ana-demo-2026"},
        {"email": "", "password": "Ana-demo-2026"},
        {"email": "ana.souza@example.com", "password": ""},
        {"email": "ana.souza@example.com", "password": 12345678},
        {**ANA, "role": "manager"},
    ],
)
def test_login_invalid_body_returns_422(client, body):
    assert client.post("/auth/login", json=body).status_code == 422


def test_login_does_not_change_the_customers_file(client, tmp_path):
    before = customers_file_text(tmp_path)

    client.post("/auth/login", json=ANA)
    client.post("/auth/login", json={**ANA, "password": "not-the-password"})

    assert customers_file_text(tmp_path) == before


def test_login_responses_are_documented(client):
    post = client.get("/openapi.json").json()["paths"]["/auth/login"]["post"]

    assert {"200", "401", "422"} <= post["responses"].keys()


# --- Tokens ---


def test_token_round_trip_returns_the_customer_id():
    assert decode_access_token(create_access_token(42)) == 42


def test_token_carries_an_expiry_and_no_personal_data():
    payload = jwt.decode(create_access_token(ANA_ID), options={"verify_signature": False})

    assert payload.keys() == {"sub", "iat", "exp"}
    assert payload["exp"] - payload["iat"] == security.ACCESS_TOKEN_EXPIRE_MINUTES * 60


def test_expired_token_is_rejected():
    assert decode_access_token(create_access_token(ANA_ID, expires_in=timedelta(seconds=-1))) is None


def test_tampered_token_is_rejected():
    header, payload, signature = create_access_token(ANA_ID).split(".")
    other_payload = create_access_token(2).split(".")[1]

    # Swapping in another customer's payload breaks the signature
    assert decode_access_token(f"{header}.{other_payload}.{signature}") is None


def test_token_signed_with_another_key_is_rejected():
    forged = jwt.encode({"sub": "1", "exp": 4102444800}, "some-other-secret-key-of-32-bytes!!", algorithm="HS256")

    assert decode_access_token(forged) is None


def test_unsigned_token_is_rejected():
    unsigned = jwt.encode({"sub": "1", "exp": 4102444800}, key=None, algorithm="none")

    assert decode_access_token(unsigned) is None


@pytest.mark.parametrize("token", ["", "not-a-token", "a.b.c"])
def test_malformed_token_is_rejected(token):
    assert decode_access_token(token) is None


def test_token_without_expiry_or_subject_is_rejected():
    no_expiry = jwt.encode({"sub": "1"}, security.SECRET_KEY, algorithm="HS256")
    no_subject = jwt.encode({"exp": 4102444800}, security.SECRET_KEY, algorithm="HS256")
    bad_subject = jwt.encode({"sub": "ana", "exp": 4102444800}, security.SECRET_KEY, algorithm="HS256")

    assert decode_access_token(no_expiry) is None
    assert decode_access_token(no_subject) is None
    assert decode_access_token(bad_subject) is None


def test_secret_key_is_read_from_the_environment():
    # Config is resolved at import time, so read it in a fresh interpreter
    def secret_key(env: dict) -> str:
        result = subprocess.run(
            [sys.executable, "-c", "from app.core.config import SECRET_KEY; print(SECRET_KEY)"],
            cwd=BASE_DIR,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    without_variable = {key: value for key, value in os.environ.items() if key != "SECRET_KEY"}

    assert secret_key({**without_variable, "SECRET_KEY": "from-the-environment"}) == "from-the-environment"
    # With no variable set there is no built-in default: each start generates its own random key
    first, second = secret_key(without_variable), secret_key(without_variable)
    assert len(first) == 64
    assert first != second


# --- get_current_customer ---


@pytest.fixture
def whoami_client():
    """A client for the real app with one extra route that needs a signed-in customer.

    No endpoint uses get_current_customer yet, so this route exists only for these tests
    and is removed again afterwards.
    """
    router = APIRouter()

    @router.get("/test-only/whoami", response_model=Customer)
    def whoami(customer: dict = Depends(get_current_customer)):
        return customer

    routes_before = list(app.router.routes)
    app.include_router(router)
    yield TestClient(app)
    app.router.routes[:] = routes_before


def test_valid_token_identifies_the_customer(client, whoami_client):
    token = client.post("/auth/login", json=ANA).json()["access_token"]

    response = whoami_client.get("/test-only/whoami", headers=bearer(token))

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "name": "Ana Souza",
        "email": "ana.souza@example.com",
        "delivery_address": "1155 Bernard Avenue, Kelowna",
        "role": "customer",
        "is_active": True,
    }


def test_missing_token_returns_401(whoami_client):
    response = whoami_client.get("/test-only/whoami")

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_non_bearer_authorization_header_returns_401(whoami_client):
    response = whoami_client.get("/test-only/whoami", headers={"Authorization": "Basic YW5hOnBhc3N3b3Jk"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.parametrize("token", ["not-a-token", "a.b.c"])
def test_invalid_token_returns_401(whoami_client, token):
    response = whoami_client.get("/test-only/whoami", headers=bearer(token))

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_expired_token_returns_401(whoami_client):
    expired = create_access_token(ANA_ID, expires_in=timedelta(seconds=-1))

    response = whoami_client.get("/test-only/whoami", headers=bearer(expired))

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}


def test_token_for_a_customer_that_no_longer_exists_returns_401(whoami_client):
    response = whoami_client.get("/test-only/whoami", headers=bearer(create_access_token(999)))

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}


def test_test_only_route_is_removed_after_use(client):
    assert client.get("/test-only/whoami").status_code == 404


# --- Service and repository ---


def test_service_login_raises_on_wrong_password(tmp_path):
    service = AuthService(CustomerRepository(tmp_path / "customers.json"))

    with pytest.raises(InvalidCredentialsError):
        service.login(ANA["email"], "not-the-password")


def test_service_login_raises_on_unknown_email(tmp_path):
    service = AuthService(CustomerRepository(tmp_path / "customers.json"))

    with pytest.raises(InvalidCredentialsError):
        service.login("nobody@example.com", ANA["password"])


def test_service_returns_the_customer_for_a_valid_token(tmp_path):
    service = AuthService(CustomerRepository(tmp_path / "customers.json"))

    customer = service.get_customer_for_token(service.login(**ANA))

    assert customer["id"] == ANA_ID
    assert customer["email"] == "ana.souza@example.com"


def test_service_raises_on_invalid_token(tmp_path):
    service = AuthService(CustomerRepository(tmp_path / "customers.json"))

    with pytest.raises(InvalidTokenError):
        service.get_customer_for_token("not-a-token")


def test_repository_get_by_id(tmp_path):
    repository = CustomerRepository(tmp_path / "customers.json")

    assert repository.get_by_id(2)["email"] == "ben.carter@example.com"
    assert repository.get_by_id(999) is None


def test_committed_demo_passwords_can_log_in(client):
    """The demo passwords listed in the README match the hashes in data/customers.json."""
    committed = json.loads((BASE_DIR / "data" / "customers.json").read_text(encoding="utf-8"))
    demo_passwords = {
        "ana.souza@example.com": "Ana-demo-2026",
        "ben.carter@example.com": "Ben-demo-2026",
        "dev.patel@example.com": "Dev-demo-2026",
    }

    for email, password in demo_passwords.items():
        response = client.post("/auth/login", json={"email": email, "password": password})
        customer_id = next(c["id"] for c in committed if c["email"] == email)
        assert response.status_code == 200
        assert decode_access_token(response.json()["access_token"]) == customer_id
