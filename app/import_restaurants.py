"""One-time restaurant catalog import; never runs during API startup or requests."""

import argparse
import csv
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from app.core import config
from app.demo_menus import seed_demo_menus
from app.repositories.menu_item_repository import MenuItemRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.restaurant import RestaurantCreate
from app.services.menu_service import MenuService
from app.services.restaurant_service import DuplicateRestaurantError, RestaurantService

DATASET_HANDLE = "polartech/doordash-restaurant-data/versions/1"
DATASET_FILE = "doordash.csv"
REQUIRED_COLUMNS = {"loc_name", "address", "cuisines", "review_rating"}
# DoorDash also lists retail businesses. Keep those out of the restaurant catalog.
EXCLUDED_CATEGORIES = {"convenience", "grocery", "florist", "personal care", "pet stores", "liquor store"}
NON_CUISINE_TAGS = {"alcohol", "black owned", "delivery"}


@dataclass
class ImportResult:
    added: int = 0
    duplicates: int = 0
    invalid: int = 0
    excluded: int = 0
    menu_items_added: int = 0
    restaurants_seeded: int = 0
    restaurants_opened: int = 0
    menus_skipped: int = 0


def load_kaggle_rows() -> list[dict]:
    """Download the pinned public dataset with the optional Pandas adapter."""
    try:
        import kagglehub
        from kagglehub import KaggleDatasetAdapter
    except ImportError as exc:
        raise RuntimeError("Install the importer with: pip install -r requirements-import.txt") from exc

    frame = kagglehub.dataset_load(
        KaggleDatasetAdapter.PANDAS,
        DATASET_HANDLE,
        DATASET_FILE,
        pandas_kwargs={"dtype": str, "keep_default_na": False},
    )
    _check_columns(frame.columns)
    return frame.to_dict(orient="records")


def _check_columns(columns: Iterable[str]) -> None:
    missing = REQUIRED_COLUMNS.difference(columns)
    if missing:
        raise ValueError("Dataset is missing required columns: " + ", ".join(sorted(missing)))


def load_csv_rows(path: Path) -> list[dict]:
    """Support an already downloaded CSV without requiring Kaggle or Pandas."""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        _check_columns(reader.fieldnames or [])
        return list(reader)


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def import_restaurants(
    rows: Iterable[Mapping],
    service: RestaurantService,
    *,
    limit: int = 100,
    dry_run: bool = False,
    demo_menus: bool = False,
    menu_service: MenuService | None = None,
) -> ImportResult:
    """Import the first ``limit`` valid unique source restaurants, append-only.

    Use the ordinary creation service for duplicate enforcement, stable IDs and
    atomic saves. Stop the API before importing: JSON locks cover one process.
    A dry run counts additions without writing anything. The bounded selection
    includes already imported entries, so repeating a run does not add the next
    batch. Increase the limit explicitly to expand the selection.
    """
    if limit < 1:
        raise ValueError("limit must be a positive integer")
    if demo_menus and menu_service is None:
        raise ValueError("menu_service is required when demo_menus=True")
    result = ImportResult()
    existing = service.list_restaurants()
    by_identity = {
        (r["name"].strip().casefold(), r["address"].strip().casefold()): r
        for r in existing
    }
    next_id = max((r["id"] for r in existing), default=0) + 1
    selected: set[tuple[str, str]] = set()
    selected_restaurants: list[dict] = []
    for row in rows:
        if len(selected) >= limit:
            break
        categories = [part.strip() for part in _text(row.get("cuisines")).split("|") if part.strip()]
        if any(category.casefold() in EXCLUDED_CATEGORIES for category in categories):
            result.excluded += 1
            continue
        try:
            cuisine = next((part for part in categories if part.casefold() not in NON_CUISINE_TAGS), "")
            data = RestaurantCreate(
                name=_text(row.get("loc_name")),
                address=_text(row.get("address")),
                cuisine=cuisine,
                rating=_text(row.get("review_rating")) or 0.0,
                # The 2022 source has no live availability or menus for our app.
                is_open=False,
            )
        except ValidationError:
            result.invalid += 1
            continue
        key = (data.name.casefold(), data.address.casefold())
        if key in selected:
            result.duplicates += 1
            continue
        selected.add(key)
        if key in by_identity:
            result.duplicates += 1
            selected_restaurants.append(by_identity[key])
            continue
        if dry_run:
            restaurant = {"id": next_id, **data.model_dump()}
            next_id += 1
        else:
            try:
                restaurant = service.create_restaurant(data)
            except DuplicateRestaurantError:
                result.duplicates += 1
                # Another creator won the duplicate check; bind to the same domain identity.
                matching = next(
                    r for r in service.list_restaurants()
                    if (r["name"].strip().casefold(), r["address"].strip().casefold()) == key
                )
                by_identity[key] = matching
                selected_restaurants.append(matching)
                continue
        by_identity[key] = restaurant
        selected_restaurants.append(restaurant)
        result.added += 1
    if demo_menus:
        seeded = seed_demo_menus(selected_restaurants, service, menu_service, dry_run=dry_run)
        result.menu_items_added = seeded.items_added
        result.restaurants_seeded = seeded.restaurants_seeded
        result.restaurants_opened = seeded.restaurants_opened
        result.menus_skipped = seeded.skipped
    return result


def _positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, help="Use a downloaded doordash.csv instead of Kaggle")
    parser.add_argument("--data-dir", type=Path, default=config.DATA_DIR, help="Existing app data directory")
    parser.add_argument("--limit", type=_positive_int, default=100, help="First N valid unique source restaurants (default: 100)")
    parser.add_argument("--dry-run", action="store_true", help="Preview counts without saving")
    parser.add_argument("--demo-menus", action="store_true", help="Add fictional sample menus to selected empty restaurants and open them")
    args = parser.parse_args(argv)
    target = args.data_dir / "restaurants.json"
    if not target.is_file():
        parser.error(f"{target} does not exist; copy the app's data directory first")
    menu_target = args.data_dir / "menu_items.json"
    if args.demo_menus and not menu_target.is_file():
        parser.error(f"{menu_target} does not exist; copy the app's data directory first")
    try:
        rows = load_csv_rows(args.csv) if args.csv else load_kaggle_rows()
        service = RestaurantService(RestaurantRepository(target))
        menu_service = MenuService(MenuItemRepository(menu_target), service.repository) if args.demo_menus else None
        result = import_restaurants(
            rows, service, limit=args.limit, dry_run=args.dry_run,
            demo_menus=args.demo_menus, menu_service=menu_service,
        )
    except (OSError, ValueError, RuntimeError, csv.Error) as exc:
        parser.exit(1, f"Import failed: {exc}\n")
    verb = "Would add" if args.dry_run else "Added"
    print(
        f"{verb} {result.added} restaurants; skipped {result.duplicates} duplicates, "
        f"{result.invalid} invalid rows and {result.excluded} retail rows."
    )
    print(f"Restaurant data: {target.resolve()}")
    if args.demo_menus:
        print(
            f"{'Would add' if args.dry_run else 'Added'} {result.menu_items_added} fictional demo menu items "
            f"for {result.restaurants_seeded} restaurants; "
            f"{'would open' if args.dry_run else 'opened'} {result.restaurants_opened}; "
            f"skipped {result.menus_skipped} protected or existing menus."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
