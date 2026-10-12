from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.core import config
from app.repositories.menu_repository import MenuRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.menu_item import ErrorResponse, MenuItem, MenuItemCreate, MenuItemUpdate
from app.services.menu_service import (
    DuplicateMenuItemError,
    EmptyUpdateError,
    MenuItemNotFoundError,
    MenuService,
    RestaurantNotFoundError,
)

router = APIRouter(prefix="/restaurants/{restaurant_id}/menu", tags=["menu"])


def get_menu_service() -> MenuService:
    # Read paths from config at request time so tests can point them at temp files.
    return MenuService(
        MenuRepository(config.MENU_ITEMS_FILE),
        RestaurantRepository(config.RESTAURANTS_FILE),
    )


RestaurantId = Path(..., ge=1, description="Id of the restaurant.")
ItemId = Path(..., ge=1, description="Id of the menu item.")

NOT_FOUND = {status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Restaurant or menu item not found."}}
CONFLICT = {status.HTTP_409_CONFLICT: {"model": ErrorResponse, "description": "Restaurant already has an item with this name."}}
BAD_REQUEST = {status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Update body contained no fields."}}


@router.get(
    "",
    response_model=list[MenuItem],
    summary="View a restaurant's menu",
    description="Returns every menu item that belongs to the given restaurant. "
    "Returns an empty list if the restaurant exists but has no items yet.",
    responses=NOT_FOUND,
)
def list_menu(restaurant_id: int = RestaurantId, service: MenuService = Depends(get_menu_service)):
    try:
        return service.list_menu(restaurant_id)
    except RestaurantNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/{item_id}",
    response_model=MenuItem,
    summary="Get one menu item",
    description="Returns a single menu item. Responds 404 if the restaurant does not exist, "
    "the item does not exist, or the item belongs to a different restaurant.",
    responses=NOT_FOUND,
)
def get_menu_item(
    restaurant_id: int = RestaurantId,
    item_id: int = ItemId,
    service: MenuService = Depends(get_menu_service),
):
    try:
        return service.get_menu_item(restaurant_id, item_id)
    except (RestaurantNotFoundError, MenuItemNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "",
    response_model=MenuItem,
    status_code=status.HTTP_201_CREATED,
    summary="Add a menu item",
    description="Adds a new item to the restaurant's menu. The server assigns the id "
    "(highest existing id + 1). Item names must be unique within a restaurant (case-insensitive).",
    responses={**NOT_FOUND, **CONFLICT},
)
def add_menu_item(
    item: MenuItemCreate,
    restaurant_id: int = RestaurantId,
    service: MenuService = Depends(get_menu_service),
):
    try:
        return service.add_menu_item(restaurant_id, item)
    except RestaurantNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DuplicateMenuItemError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.patch(
    "/{item_id}",
    response_model=MenuItem,
    summary="Update a menu item",
    description="Partially updates a menu item: only the fields included in the body are changed. "
    "The item's id and restaurant cannot be changed.",
    responses={**BAD_REQUEST, **NOT_FOUND, **CONFLICT},
)
def update_menu_item(
    changes: MenuItemUpdate,
    restaurant_id: int = RestaurantId,
    item_id: int = ItemId,
    service: MenuService = Depends(get_menu_service),
):
    try:
        return service.update_menu_item(restaurant_id, item_id, changes)
    except EmptyUpdateError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except (RestaurantNotFoundError, MenuItemNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DuplicateMenuItemError as e:
        raise HTTPException(status_code=409, detail=str(e))
