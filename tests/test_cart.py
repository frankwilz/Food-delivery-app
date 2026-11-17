"""Tests for the shopping cart."""

import json

import pytest

from app.core.errors import ForbiddenError
from app.core.security import create_access_token
from app.repositories.cart_repository import CartRepository
from app.repositories.customer_repository import CustomerRepository
from app.services.cart_service import CartService
from app.services.customer_service import CustomerService

# From data/customers.json
ANA_ID, BEN_ID, CHLOE_DEACTIVATED_ID = 1, 2, 3


def auth(customer_id: int) -> dict:
    return {"Authorization": f"Bearer {create_access_token(customer_id)}"}


ANA, BEN, CHLOE = auth(ANA_ID), auth(BEN_ID), auth(CHLOE_DEACTIVATED_ID)


def stored_carts(tmp_path) -> list[dict]:
    return json.loads((tmp_path / "carts.json").read_text(encoding="utf-8"))


@pytest.fixture
def service(tmp_path) -> CartService:
    return CartService(
        CartRepository(tmp_path / "carts.json"),
        CustomerService(CustomerRepository(tmp_path / "customers.json")),
    )


# --- 3.2 GET /cart: create/retrieve the active cart ---


def test_get_cart_creates_an_empty_active_cart(client, tmp_path):
    response = client.get("/cart", headers=ANA)

    assert response.status_code == 200
    assert response.json() == {"id": 1, "customer_id": ANA_ID, "restaurant_id": None, "items": [], "status": "active"}
    assert stored_carts(tmp_path) == [
        {"id": 1, "customer_id": ANA_ID, "restaurant_id": None, "items": [], "status": "active"}
    ]


def test_repeated_get_cart_never_creates_a_second_active_cart(client, tmp_path):
    first = client.get("/cart", headers=ANA).json()
    second = client.get("/cart", headers=ANA).json()

    assert first["id"] == second["id"]
    assert len(stored_carts(tmp_path)) == 1


def test_each_customer_gets_their_own_cart(client, tmp_path):
    ana_cart = client.get("/cart", headers=ANA).json()
    ben_cart = client.get("/cart", headers=BEN).json()

    assert ana_cart["id"] != ben_cart["id"]
    assert ben_cart["customer_id"] == BEN_ID
    assert len(stored_carts(tmp_path)) == 2


def test_cart_is_persisted_and_survives_a_new_service(client, service):
    cart_id = client.get("/cart", headers=ANA).json()["id"]

    # A fresh service reading the same file finds the same cart, as after a restart
    assert service.get_cart(ANA_ID)["id"] == cart_id


def test_deactivated_customer_gets_403_and_no_cart(client, tmp_path):
    response = client.get("/cart", headers=CHLOE)

    assert response.status_code == 403
    assert "deactivated" in response.json()["detail"]
    assert stored_carts(tmp_path) == []


def test_get_cart_requires_sign_in(client):
    assert client.get("/cart").status_code == 401


def test_service_get_cart_rejects_deactivated_customer(service):
    with pytest.raises(ForbiddenError):
        service.get_cart(CHLOE_DEACTIVATED_ID)


def test_repository_finds_only_the_active_cart(tmp_path):
    repository = CartRepository(tmp_path / "carts.json")
    repository.create({"customer_id": ANA_ID, "restaurant_id": None, "items": [], "status": "checked_out"})
    active = repository.create({"customer_id": ANA_ID, "restaurant_id": None, "items": [], "status": "active"})

    assert repository.get_active_for_customer(ANA_ID) == active
    assert repository.get_active_for_customer(BEN_ID) is None


def test_get_cart_is_documented(client):
    responses = client.get("/openapi.json").json()["paths"]["/cart"]["get"]["responses"]

    assert {"401", "403"} <= set(responses)
