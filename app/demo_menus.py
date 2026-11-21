"""Fictional sample menus for an explicitly selected offline restaurant import.

These dishes and prices are project demo content, not menus supplied by Kaggle,
DoorDash or the named restaurants. Existing menus are never replaced.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from app.repositories.json_repository import transaction
from app.schemas.menu_item import MenuItemCreate
from app.schemas.restaurant import RestaurantUpdate
from app.services.menu_service import MenuService
from app.services.restaurant_service import RestaurantService


@dataclass
class DemoMenuResult:
    items_added: int = 0
    restaurants_seeded: int = 0
    restaurants_opened: int = 0
    skipped: int = 0


# The immutable domain identities of the project's four original examples.
# Do not derive this from the working restaurants.json: the default import target
# is that same mutable file and may already contain the external catalog.
PROJECT_EXAMPLE_IDENTITIES = frozenset({
    ("boston pizza", "123 kelowna road"),
    ("taco bell", "456 okanagan drive"),
    ("okanagan sushi", "789 bernard avenue"),
    ("lakeside pizzeria", "12 water street"),
})


# Each selection has one main, one side and one drink, all with fictional dollar prices.
# The first matching cuisine wins; the fallback also gives unfamiliar cuisines a usable demo.
RECIPES = (
    (("pizza", "italian"), (("Margherita pizza", 12.0, "Mains"), ("Garden salad", 4.5, "Sides"), ("Sparkling water", 2.5, "Drinks"))),
    (("mexican", "taco", "burrito", "tex-mex"), (("Vegetable burrito", 11.0, "Mains"), ("Chips and salsa", 4.0, "Sides"), ("Limeade", 3.0, "Drinks"))),
    (("indian", "pakistani", "curry"), (("Chickpea curry with rice", 13.0, "Mains"), ("Garlic naan", 3.5, "Sides"), ("Mango lassi", 4.0, "Drinks"))),
    (("japanese", "sushi", "ramen"), (("Vegetable sushi roll", 10.0, "Mains"), ("Edamame", 4.0, "Sides"), ("Green tea", 2.5, "Drinks"))),
    (("chinese", "asian", "wok"), (("Vegetable fried rice", 11.5, "Mains"), ("Spring rolls", 4.0, "Sides"), ("Jasmine tea", 2.5, "Drinks"))),
    (("thai", "vietnamese", "noodle"), (("Tofu noodle bowl", 12.0, "Mains"), ("Cucumber salad", 4.0, "Sides"), ("Iced lemon tea", 3.0, "Drinks"))),
    (("korean",), (("Vegetable rice bowl", 12.5, "Mains"), ("Kimchi side", 3.5, "Sides"), ("Barley tea", 2.5, "Drinks"))),
    (("mediterranean", "greek", "middle eastern", "falafel"), (("Falafel pita", 10.5, "Mains"), ("Hummus and pita", 4.5, "Sides"), ("Mint lemonade", 3.0, "Drinks"))),
    (("seafood", "fish"), (("Fish sandwich", 12.0, "Mains"), ("Coleslaw", 3.5, "Sides"), ("Lemonade", 3.0, "Drinks"))),
    (("salad", "vegan", "vegetarian", "healthy"), (("Roasted vegetable bowl", 11.0, "Mains"), ("Seasonal fruit", 4.0, "Sides"), ("Citrus iced tea", 3.0, "Drinks"))),
    (("breakfast", "brunch", "cafe", "coffee", "bakery", "dessert", "donut"), (("Breakfast sandwich", 8.5, "Mains"), ("Blueberry muffin", 3.5, "Sides"), ("Iced coffee", 3.0, "Drinks"))),
    (("chicken", "wings"), (("Grilled chicken wrap", 10.5, "Mains"), ("Potato wedges", 4.0, "Sides"), ("Iced tea", 2.5, "Drinks"))),
)
FALLBACK = (("House sandwich", 9.5, "Mains"), ("Side salad", 4.0, "Sides"), ("Lemonade", 2.5, "Drinks"))


def demo_menu_items(cuisine: str) -> tuple[MenuItemCreate, ...]:
    """Validate three original sample dishes before any menu record is written."""
    wanted = cuisine.casefold()
    recipe = next((items for tags, items in RECIPES if any(tag in wanted for tag in tags)), FALLBACK)
    return tuple(
        MenuItemCreate(
            name=f"Demo {name}",
            description="Demo menu: Fictional sample dish and price, not the restaurant's real menu.",
            price=price,
            category=category,
            is_available=True,
        )
        for name, price, category in recipe
    )


def _identity(restaurant: Mapping) -> tuple[str, str]:
    return restaurant["name"].strip().casefold(), restaurant["address"].strip().casefold()


def seed_demo_menus(
    restaurants: Iterable[Mapping],
    restaurant_service: RestaurantService,
    menu_service: MenuService,
    *,
    dry_run: bool = False,
) -> DemoMenuResult:
    """Seed only the supplied selection's empty menus, then open those restaurants.

    The caller binds the bounded source identities to current restaurant records;
    this function never sweeps all restaurants or guesses provenance from IDs.
    Committed seed identities and any existing menu (even inactive) are protected.
    Dry runs also accept planned, not-yet-saved restaurant records from the importer.
    """
    result = DemoMenuResult()
    seen = set()
    for supplied in restaurants:
        restaurant_id = supplied["id"]
        if restaurant_id in seen or _identity(supplied) in PROJECT_EXAMPLE_IDENTITIES:
            result.skipped += 1
            continue
        seen.add(restaurant_id)
        with transaction(restaurant_service.repository, menu_service.menu_repository):
            restaurant = supplied if dry_run else restaurant_service.get_restaurant(restaurant_id)
            # Repository reads support planned dry-run IDs that do not exist yet.
            existing = menu_service.menu_repository.get_by_restaurant_id(restaurant_id)
            if existing:
                result.skipped += 1
                continue
            items = demo_menu_items(restaurant["cuisine"])
            if not dry_run:
                # An operator may have opened an empty import manually. Keep it closed
                # during seeding too, so a failed menu save cannot leave it accepting orders.
                if restaurant["is_open"]:
                    restaurant_service.update_restaurant(restaurant_id, RestaurantUpdate(is_open=False))
                for item in items:
                    menu_service.create_menu_item(restaurant_id, item)
                # Never open a restaurant before all three menu saves succeed.
                # Existing menus are skipped above, so a later manual closure stays closed on reruns.
                restaurant_service.update_restaurant(restaurant_id, RestaurantUpdate(is_open=True))
            result.items_added += len(items)
            result.restaurants_seeded += 1
            result.restaurants_opened += int(not restaurant["is_open"])
    return result
