import shutil

import pytest
from fastapi.testclient import TestClient

from app.api.routes import restaurants as restaurants_route
from app.core.config import BASE_DIR
from app.main import app

REAL_DATA = BASE_DIR / "data"


@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    shutil.copy(REAL_DATA / "restaurants.json", tmp_path / "restaurants.json")
    monkeypatch.setattr(restaurants_route, "RESTAURANTS_FILE", tmp_path / "restaurants.json")


@pytest.fixture
def client():
    return TestClient(app)