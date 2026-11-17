import shutil

import pytest
from fastapi.testclient import TestClient

from app.api import dependencies
from app.api.routes import cart as cart_route
from app.api.routes import customers as customers_route
from app.api.routes import menu as menu_route
from app.api.routes import restaurants as restaurants_route
from app.core.config import BASE_DIR
from app.core.security import create_access_token
from app.main import app

REAL_DATA = BASE_DIR / "data"
MANAGER_ID = 4  # Dev Patel, the manager in data/customers.json


@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    shutil.copy(REAL_DATA / "restaurants.json", tmp_path / "restaurants.json")
    shutil.copy(REAL_DATA / "menu_items.json", tmp_path / "menu_items.json")
    monkeypatch.setattr(restaurants_route, "RESTAURANTS_FILE", tmp_path / "restaurants.json")
    # The menu routes import both file constants by name, so patch both there too
    monkeypatch.setattr(menu_route, "RESTAURANTS_FILE", tmp_path / "restaurants.json")
    monkeypatch.setattr(menu_route, "MENU_ITEMS_FILE", tmp_path / "menu_items.json")
    shutil.copy(REAL_DATA / "customers.json", tmp_path / "customers.json")
    monkeypatch.setattr(customers_route, "CUSTOMERS_FILE", tmp_path / "customers.json")
    # Login and get_current_customer read the customers file through the shared dependencies
    monkeypatch.setattr(dependencies, "CUSTOMERS_FILE", tmp_path / "customers.json")
    # The cart route builds every service the cart and checkout need, so patch all five files there
    shutil.copy(REAL_DATA / "carts.json", tmp_path / "carts.json")
    monkeypatch.setattr(cart_route, "CARTS_FILE", tmp_path / "carts.json")
    monkeypatch.setattr(cart_route, "CUSTOMERS_FILE", tmp_path / "customers.json")
    monkeypatch.setattr(cart_route, "MENU_ITEMS_FILE", tmp_path / "menu_items.json")
    monkeypatch.setattr(cart_route, "RESTAURANTS_FILE", tmp_path / "restaurants.json")
    shutil.copy(REAL_DATA / "orders.json", tmp_path / "orders.json")
    monkeypatch.setattr(cart_route, "ORDERS_FILE", tmp_path / "orders.json")


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def manager_client():
    """A client that sends the manager's token on every request, for restaurant and menu changes."""
    return TestClient(app, headers={"Authorization": f"Bearer {create_access_token(MANAGER_ID)}"})