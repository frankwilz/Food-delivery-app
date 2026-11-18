import shutil

import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.core.config import BASE_DIR
from app.core.security import create_access_token
from app.main import app

REAL_DATA = BASE_DIR / "data"
MANAGER_ID = 4  # Dev Patel, the manager in data/customers.json


DATA_FILES = {
    "RESTAURANTS_FILE": "restaurants.json",
    "MENU_ITEMS_FILE": "menu_items.json",
    "CUSTOMERS_FILE": "customers.json",
    "CARTS_FILE": "carts.json",
    "ORDERS_FILE": "orders.json",
}


@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    # Every test works on its own copy of the data files. The shared dependencies in
    # app/api/dependencies.py read the paths from app.core.config, so this is the only place to change them.
    for setting, file_name in DATA_FILES.items():
        shutil.copy(REAL_DATA / file_name, tmp_path / file_name)
        monkeypatch.setattr(config, setting, tmp_path / file_name)
    # Most feature tests start before the customer's first cart/order. The workflow
    # demo test explicitly opts into the representative history instead.
    for file_name in ("carts.json", "orders.json"):
        (tmp_path / file_name).write_text("[]\n", encoding="utf-8")


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def manager_client():
    """A client that sends the manager's token on every request, for restaurant and menu changes."""
    return TestClient(app, headers={"Authorization": f"Bearer {create_access_token(MANAGER_ID)}"})
