import pytest

from app.repositories.restaurant_repository import RestaurantRepository


def test_list_restaurants_returns_200_and_data(client):
    response = client.get("/restaurants")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["id"] == 1
    assert data[0]["name"] == "Boston Pizza"


def test_repository_reads_all_restaurants(tmp_path):
    repository = RestaurantRepository(tmp_path / "restaurants.json")

    restaurants = repository.get_all()

    assert len(restaurants) == 2
    assert restaurants[1]["cuisine"] == "Mexican"


def test_repository_missing_file_raises_error(tmp_path):
    repository = RestaurantRepository(tmp_path / "does_not_exist.json")

    with pytest.raises(FileNotFoundError):
        repository.get_all()