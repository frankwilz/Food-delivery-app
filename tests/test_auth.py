import os
import subprocess
import sys
from datetime import timedelta

import jwt
import pytest

from app.core import security
from app.core.config import BASE_DIR
from app.core.security import create_access_token, decode_access_token
from app.repositories.customer_repository import CustomerRepository

ANA_ID = 1  # Ana Souza in data/customers.json


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


# --- Repository ---


def test_repository_get_by_id(tmp_path):
    repository = CustomerRepository(tmp_path / "customers.json")

    assert repository.get_by_id(2)["email"] == "ben.carter@example.com"
    assert repository.get_by_id(999) is None
