"""Tests for 2.5 (#36), part 2: roles, and customers limited to their own data."""

import json

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient

from app.api.dependencies import require_role
from app.core.security import create_access_token
from app.main import app

ANA_ID, BEN_ID, CHLOE_DEACTIVATED_ID, MANAGER_ID = 1, 2, 3, 4


def auth(customer_id: int) -> dict:
    return {"Authorization": f"Bearer {create_access_token(customer_id)}"}


ANA, BEN, CHLOE, MANAGER = auth(ANA_ID), auth(BEN_ID), auth(CHLOE_DEACTIVATED_ID), auth(MANAGER_ID)

NEW_RESTAURANT = {"name": "Kelowna Curry House", "cuisine": "Indian", "address": "55 Pandosy Street"}
NEW_ITEM = {"name": "Garlic Bread", "price": 5.99, "category": "Appetizers"}

# Every endpoint that changes restaurants or menus, with a valid body
MANAGER_ENDPOINTS = [
    ("post", "/restaurants", NEW_RESTAURANT),
    ("patch", "/restaurants/1", {"is_open": False}),
    ("post", "/restaurants/1/menu", NEW_ITEM),
    ("patch", "/restaurants/1/menu/1", {"price": 20}),
    ("delete", "/restaurants/1/menu/1", None),
]

# Every endpoint that needs a signed-in customer, one or more per router
SIGNED_IN_ENDPOINTS = [
    ("get", "/customers/me", None),
    ("post", "/customers/me/deactivate", None),
    ("get", "/cart", None),
    ("post", "/cart/items", {"menu_item_id": 1, "quantity": 1}),
    ("patch", "/cart/items/1", {"quantity": 2}),
    ("delete", "/cart/items/1", None),
    ("delete", "/cart", None),
    ("post", "/checkout", None),
]


def call(client, method: str, path: str, body: dict | None, headers: dict | None = None):
    kwargs = {"headers": headers}
    if body is not None:
        kwargs["json"] = body
    return getattr(client, method)(path, **kwargs)


def data_files(tmp_path) -> dict[str, str]:
    return {path.name: path.read_text(encoding="utf-8") for path in sorted(tmp_path.glob("*.json"))}


# --- restaurant and menu changes: managers only ---


@pytest.mark.parametrize("method, path, body", MANAGER_ENDPOINTS)
def test_manager_endpoints_return_401_without_a_token(client, tmp_path, method, path, body):
    before = data_files(tmp_path)

    response = call(client, method, path, body)

    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}
    assert data_files(tmp_path) == before


@pytest.mark.parametrize("method, path, body", MANAGER_ENDPOINTS)
def test_manager_endpoints_return_403_for_a_customer(client, tmp_path, method, path, body):
    before = data_files(tmp_path)

    response = call(client, method, path, body, ANA)

    assert response.status_code == 403
    assert response.json() == {"detail": "Only a manager can do this"}
    assert data_files(tmp_path) == before


@pytest.mark.parametrize("method, path, body", MANAGER_ENDPOINTS)
def test_manager_endpoints_succeed_for_a_manager(client, method, path, body):
    response = call(client, method, path, body, MANAGER)

    assert response.status_code in (200, 201)


def test_invalid_token_on_a_manager_endpoint_returns_401(client):
    response = client.post("/restaurants", json=NEW_RESTAURANT, headers={"Authorization": "Bearer not-a-token"})

    assert response.status_code == 401


def test_a_deactivated_manager_is_refused(client, tmp_path):
    customers_file = tmp_path / "customers.json"
    customers = json.loads(customers_file.read_text(encoding="utf-8"))
    next(c for c in customers if c["id"] == MANAGER_ID)["is_active"] = False
    customers_file.write_text(json.dumps(customers), encoding="utf-8")

    response = client.post("/restaurants", json=NEW_RESTAURANT, headers=MANAGER)

    assert response.status_code == 403
    assert response.json() == {"detail": "Customer 4 has been deactivated"}


def test_auth_is_checked_before_the_body(client):
    # An unauthenticated caller learns nothing about what a valid body looks like
    assert client.post("/restaurants", json={}).status_code == 401
    assert client.post("/restaurants", json={}, headers=ANA).status_code == 403


@pytest.mark.parametrize(
    "path",
    ["/restaurants", "/restaurants/1", "/restaurants/1/menu", "/restaurants/1/menu/1", "/restaurants?search=pizza"],
)
def test_reading_restaurants_and_menus_stays_public(client, path):
    assert client.get(path).status_code == 200


def test_registration_and_login_stay_public(client):
    register = client.post(
        "/customers",
        json={"name": "Jordan Lee", "email": "jordan@example.com", "password": "long-enough-1", "delivery_address": "1 St"},
    )
    login = client.post("/auth/login", json={"email": "ana.souza@example.com", "password": "Ana-demo-2026"})

    assert register.status_code == 201
    assert login.status_code == 200


# --- customer endpoints: signed in, active ---


@pytest.mark.parametrize("method, path, body", SIGNED_IN_ENDPOINTS)
def test_customer_endpoints_return_401_without_a_token(client, tmp_path, method, path, body):
    before = data_files(tmp_path)

    assert call(client, method, path, body).status_code == 401
    assert data_files(tmp_path) == before


@pytest.mark.parametrize("method, path, body", SIGNED_IN_ENDPOINTS)
def test_customer_endpoints_return_403_for_a_deactivated_customer(client, tmp_path, method, path, body):
    before = data_files(tmp_path)

    assert call(client, method, path, body, CHLOE).status_code == 403
    assert data_files(tmp_path) == before


# --- customers only see their own data ---


def test_customers_me_returns_only_the_callers_account(client):
    assert client.get("/customers/me", headers=ANA).json()["id"] == ANA_ID
    assert client.get("/customers/me", headers=BEN).json()["id"] == BEN_ID


def test_a_customer_cannot_see_or_change_another_customers_cart(client):
    client.post("/cart/items", json={"menu_item_id": 1, "quantity": 2}, headers=ANA)

    # Ben's requests only ever reach Ben's own cart
    assert client.get("/cart", headers=BEN).json()["items"] == []
    assert client.patch("/cart/items/1", json={"quantity": 5}, headers=BEN).status_code == 404
    assert client.delete("/cart/items/1", headers=BEN).status_code == 404
    client.delete("/cart", headers=BEN)
    assert client.post("/checkout", headers=BEN).status_code == 400

    ana_cart = client.get("/cart", headers=ANA).json()
    assert [(line["menu_item_id"], line["quantity"]) for line in ana_cart["items"]] == [(1, 2)]


def test_customer_endpoints_take_no_customer_id_from_the_client(client):
    # The customer always comes from the token; no customer endpoint accepts an id in the path or query
    paths = client.get("/openapi.json").json()["paths"]
    for path, operations in paths.items():
        if path.startswith(("/customers/me", "/cart", "/checkout")):
            for operation in operations.values():
                names = {p["name"] for p in operation.get("parameters", [])}
                assert not names & {"customer_id", "id"}, path


# --- require_role ---


@pytest.fixture
def role_client():
    router = APIRouter()

    @router.get("/test-only/manager")
    def manager_only(account: dict = Depends(require_role("manager"))):
        return {"id": account["id"]}

    routes_before = list(app.router.routes)
    app.include_router(router)
    yield TestClient(app)
    app.router.routes[:] = routes_before


def test_require_role_returns_the_account(role_client):
    assert role_client.get("/test-only/manager", headers=MANAGER).json() == {"id": MANAGER_ID}


def test_require_role_refuses_other_roles_and_missing_tokens(role_client):
    assert role_client.get("/test-only/manager", headers=ANA).status_code == 403
    assert role_client.get("/test-only/manager").status_code == 401


def test_role_errors_are_documented(client):
    paths = client.get("/openapi.json").json()["paths"]
    for method, path, _ in MANAGER_ENDPOINTS:
        template = path.replace("/restaurants/1/menu/1", "/restaurants/{restaurant_id}/menu/{item_id}")
        template = template.replace("/restaurants/1/menu", "/restaurants/{restaurant_id}/menu")
        template = template.replace("/restaurants/1", "/restaurants/{restaurant_id}")
        assert {"401", "403"} <= set(paths[template][method]["responses"]), (method, template)
