from fastapi import APIRouter, Depends

from app.core.config import RESTAURANTS_FILE
from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.restaurant import Restaurant
from app.services.restaurant_service import RestaurantService

router = APIRouter()


def get_restaurant_service() -> RestaurantService:
    repository = RestaurantRepository(RESTAURANTS_FILE)
    return RestaurantService(repository)


@router.get("/restaurants", response_model=list[Restaurant])
def list_restaurants(service: RestaurantService = Depends(get_restaurant_service)):
    return service.list_restaurants()