"""Restaurant imports use fictional rows and isolated files, never the external dataset."""

import csv
import json
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import pytest

from app import import_restaurants as importer
from app.core import config
from app.repositories.restaurant_repository import RestaurantRepository
from app.services.restaurant_service import RestaurantService

SOURCE_COLUMNS = ("loc_name", "address", "cuisines", "review_rating")


def source_row(**changes):
    return {
        "loc_name": "Maple Supper",
        "address": "8 Fictional Lane",
        "cuisines": "Italian | Pizza",
        "review_rating": "4.6",
        **changes,
    }


def distinct_rows(count):
    return [source_row(loc_name=f"Fictional Restaurant {index}", address=f"{index} Fictional Way") for index in range(count)]


@pytest.fixture
def service(isolated_data):
    return RestaurantService(RestaurantRepository(config.RESTAURANTS_FILE))


def data_snapshot(data_dir):
    return {path.name: path.read_bytes() for path in data_dir.glob("*.json")}


def write_csv(path, rows, columns=SOURCE_COLUMNS):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def test_import_maps_fields_preserves_existing_and_is_visible_without_a_menu(service, client, tmp_path):
    existing = service.list_restaurants()
    before = data_snapshot(tmp_path)
    result = importer.import_restaurants(
        [source_row(loc_name="  Maple Supper  ", address="  8 Fictional Lane  ", cuisines=" |  Italian | Pizza")],
        service,
    )

    assert (result.added, result.duplicates, result.invalid) == (1, 0, 0)
    expected = {
        "id": max(restaurant["id"] for restaurant in existing) + 1,
        "name": "Maple Supper",
        "address": "8 Fictional Lane",
        "cuisine": "Italian",
        "rating": 4.6,
        "is_open": False,
    }
    assert service.list_restaurants() == [*existing, expected]
    response = client.get(f"/restaurants/{expected['id']}")
    assert response.status_code == 200 and response.json() == expected
    listed = client.get("/restaurants", params={"search": "maple supper"})
    assert listed.status_code == 200 and listed.json() == [expected]
    menu = client.get(f"/restaurants/{expected['id']}/menu")
    assert menu.status_code == 200 and menu.json() == []
    after = data_snapshot(tmp_path)
    assert {name: content for name, content in after.items() if name != "restaurants.json"} == {
        name: content for name, content in before.items() if name != "restaurants.json"
    }


def test_import_skips_invalid_rows_and_deduplicates_existing_and_batch_records(service):
    existing = service.list_restaurants()
    duplicate = source_row(loc_name=existing[0]["name"].upper(), address=f"  {existing[0]['address'].upper()}  ")
    invalid = [
        source_row(loc_name=" "),
        source_row(address=""),
        source_row(cuisines=" | | "),
        *[source_row(review_rating=value) for value in ("not-rated", "NaN", "inf", "-inf", "-0.1", "5.1")],
    ]
    first = source_row(loc_name="Straße Kitchen", address="12 Fictional Road")
    repeated = source_row(loc_name=" STRASSE KITCHEN ", address=" 12 FICTIONAL ROAD ")
    other_branch = source_row(loc_name="Straße Kitchen", address="14 Fictional Road", review_rating="")

    result = importer.import_restaurants([duplicate, first, repeated, *invalid, other_branch], service)

    assert (result.added, result.duplicates, result.invalid) == (2, 2, len(invalid))
    saved = service.list_restaurants()
    assert saved[:len(existing)] == existing
    next_id = max(restaurant["id"] for restaurant in existing) + 1
    assert [restaurant["id"] for restaurant in saved[len(existing):]] == [next_id, next_id + 1]
    assert saved[-1]["rating"] == 0.0
    assert all(restaurant["is_open"] is False for restaurant in saved[len(existing):])
    reloaded = RestaurantRepository(config.RESTAURANTS_FILE).get_all()
    assert reloaded == saved


def test_repeating_a_bounded_import_does_not_append_the_next_source_rows(service, tmp_path):
    rows = distinct_rows(3)
    first = importer.import_restaurants(rows, service, limit=2)
    before = data_snapshot(tmp_path)
    saved = service.list_restaurants()

    repeated = importer.import_restaurants(
        rows, RestaurantService(RestaurantRepository(config.RESTAURANTS_FILE)), limit=2
    )

    assert first.added == 2
    assert (repeated.added, repeated.duplicates, repeated.invalid) == (0, 2, 0)
    assert service.list_restaurants() == saved
    assert data_snapshot(tmp_path) == before

    expanded = importer.import_restaurants(rows, service, limit=3)
    assert (expanded.added, expanded.duplicates, expanded.invalid) == (1, 2, 0)
    assert service.list_restaurants()[:-1] == saved
    assert service.list_restaurants()[-1]["id"] == max(restaurant["id"] for restaurant in saved) + 1


def test_dry_run_counts_candidates_and_batch_duplicates_without_changing_files(service, tmp_path):
    before = data_snapshot(tmp_path)
    rows = [source_row(), source_row(loc_name="MAPLE SUPPER", address="8 FICTIONAL LANE")]

    result = importer.import_restaurants(rows, service, dry_run=True)

    assert (result.added, result.duplicates, result.invalid) == (1, 1, 0)
    assert data_snapshot(tmp_path) == before


def test_limit_bounds_distinct_valid_source_records_including_existing_restaurants(service):
    existing = service.list_restaurants()
    duplicate = source_row(loc_name=existing[0]["name"], address=existing[0]["address"])
    candidates = distinct_rows(2)
    result = importer.import_restaurants(
        [candidates[0], candidates[0], source_row(review_rating="bad"), duplicate, candidates[1]], service, limit=2
    )

    assert (result.added, result.duplicates, result.invalid) == (1, 2, 1)
    saved = service.list_restaurants()
    assert len(saved) == len(existing) + 1
    assert saved[:len(existing)] == existing
    assert saved[-1]["name"] == candidates[0]["loc_name"]


def test_default_limit_imports_one_hundred_restaurants(service):
    existing = service.list_restaurants()

    result = importer.import_restaurants(distinct_rows(101), service)

    assert result.added == 100
    assert len(service.list_restaurants()) == len(existing) + 100


@pytest.mark.parametrize("category", ["Convenience", "Grocery", "Florist", "Personal Care", "Pet Stores", "Liquor Store"])
def test_retail_businesses_do_not_consume_the_restaurant_limit(service, category):
    before = service.list_restaurants()
    result = importer.import_restaurants(
        [source_row(cuisines=f"Snacks | {category.upper()}"), source_row(loc_name="Fictional Cafe")],
        service,
        limit=1,
    )

    assert result.excluded == 1 and result.added == 1
    assert service.list_restaurants()[:-1] == before
    assert service.list_restaurants()[-1]["name"] == "Fictional Cafe"


def test_restaurants_with_alcohol_or_ownership_tags_keep_their_food_cuisine(service):
    result = importer.import_restaurants([source_row(cuisines="Alcohol | Black Owned | Tacos | Ramen")], service)

    assert result.added == 1 and result.excluded == 0
    assert service.list_restaurants()[-1]["cuisine"] == "Tacos"


def test_cli_imports_local_csv_into_requested_directory_without_loading_kaggle(tmp_path, monkeypatch):
    data_dir = tmp_path / "local-import"
    data_dir.mkdir()
    restaurants_file = data_dir / "restaurants.json"
    restaurants_file.write_text("[]\n", encoding="utf-8")
    local_csv = tmp_path / "fictional.csv"
    write_csv(local_csv, distinct_rows(3))
    remote_loader = Mock(side_effect=AssertionError("Local CSV import must not contact Kaggle"))
    monkeypatch.setattr(importer, "load_kaggle_rows", remote_loader)

    importer.main(["--csv", str(local_csv), "--data-dir", str(data_dir), "--limit", "2"])

    saved = json.loads(restaurants_file.read_text(encoding="utf-8"))
    assert [restaurant["id"] for restaurant in saved] == [1, 2]
    assert [restaurant["name"] for restaurant in saved] == ["Fictional Restaurant 0", "Fictional Restaurant 1"]
    assert all(restaurant["is_open"] is False for restaurant in saved)
    remote_loader.assert_not_called()


def test_cli_default_limit_is_one_hundred_and_dry_run_uses_configured_directory(tmp_path, monkeypatch):
    before = data_snapshot(tmp_path)
    local_csv = tmp_path / "fictional.csv"
    write_csv(local_csv, distinct_rows(101))
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)

    importer.main(["--csv", str(local_csv), "--dry-run"])
    assert data_snapshot(tmp_path) == before
    importer.main(["--csv", str(local_csv)])

    saved = json.loads(config.RESTAURANTS_FILE.read_text(encoding="utf-8"))
    previous_count = len(json.loads(before["restaurants.json"]))
    assert len(saved) == previous_count + 100
    imported = data_snapshot(tmp_path)
    importer.main(["--csv", str(local_csv)])
    assert data_snapshot(tmp_path) == imported


def test_cli_rejects_wrong_csv_columns_without_changing_data(tmp_path):
    before = data_snapshot(tmp_path)
    local_csv = tmp_path / "wrong-schema.csv"
    row = source_row()
    del row["review_rating"]
    write_csv(local_csv, [row], columns=("loc_name", "address", "cuisines"))

    with pytest.raises(SystemExit) as error:
        importer.main(["--csv", str(local_csv), "--data-dir", str(tmp_path)])

    assert error.value.code == 1
    assert data_snapshot(tmp_path) == before


def test_cli_reports_csv_parse_errors_without_changing_data(tmp_path, capsys):
    before = data_snapshot(tmp_path)
    local_csv = tmp_path / "oversized-field.csv"
    write_csv(local_csv, [source_row(loc_name="x" * (csv.field_size_limit() + 1))])

    with pytest.raises(SystemExit) as error:
        importer.main(["--csv", str(local_csv), "--data-dir", str(tmp_path)])

    assert error.value.code == 1
    assert "Import failed:" in capsys.readouterr().err
    assert data_snapshot(tmp_path) == before


@pytest.mark.parametrize("limit", ["0", "-1"])
def test_cli_rejects_nonpositive_limits_before_loading_rows(limit, monkeypatch):
    remote_loader = Mock(side_effect=AssertionError("Invalid arguments must not load a dataset"))
    monkeypatch.setattr(importer, "load_kaggle_rows", remote_loader)

    with pytest.raises(SystemExit) as error:
        importer.main(["--limit", limit])

    assert error.value.code == 2
    remote_loader.assert_not_called()


class FakeFrame:
    def __init__(self, records, columns=SOURCE_COLUMNS):
        self.records = records
        self.columns = list(columns)

    def to_dict(self, orient="dict"):
        assert orient == "records"
        return self.records


def fake_kagglehub(monkeypatch, frame):
    module = ModuleType("kagglehub")
    module.KaggleDatasetAdapter = SimpleNamespace(PANDAS=object())
    module.dataset_load = Mock(return_value=frame)
    monkeypatch.setitem(sys.modules, "kagglehub", module)
    return module


def test_kaggle_loader_uses_the_pinned_dataset_and_fixed_csv_with_string_fields(monkeypatch):
    records = [source_row()]
    kagglehub = fake_kagglehub(monkeypatch, FakeFrame(records))

    loaded = importer.load_kaggle_rows()

    assert loaded == records
    kagglehub.dataset_load.assert_called_once()
    args, kwargs = kagglehub.dataset_load.call_args
    assert args == (
        kagglehub.KaggleDatasetAdapter.PANDAS,
        "polartech/doordash-restaurant-data/versions/1",
        "doordash.csv",
    )
    assert kwargs["pandas_kwargs"]["dtype"] is str
    assert kwargs["pandas_kwargs"]["keep_default_na"] is False
    if "usecols" in kwargs["pandas_kwargs"]:
        assert set(kwargs["pandas_kwargs"]["usecols"]) == set(SOURCE_COLUMNS)


@pytest.mark.parametrize("missing_column", SOURCE_COLUMNS)
def test_kaggle_loader_rejects_an_unexpected_source_schema(monkeypatch, missing_column):
    columns = [column for column in SOURCE_COLUMNS if column != missing_column]
    records = [{column: value for column, value in source_row().items() if column != missing_column}]
    fake_kagglehub(monkeypatch, FakeFrame(records, columns))

    with pytest.raises(ValueError):
        importer.load_kaggle_rows()
