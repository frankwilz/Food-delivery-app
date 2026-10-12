# Food Delivery App
Food Delivery App is a team project that currently provides the Milestone 0 backend foundation. The repository contains a FastAPI application, a layered restaurant-list operation, JSON persistence, Pydantic response models, and a team agreement. The backend exposes health, restaurant, and interactive API-documentation endpoints.

**Team name:** Abdul & Friends

## Requirements

- Python 3.11 or newer
- `pip`
- Git

## Setup

Clone the repository and enter the project directory:

```bash
git clone https://github.com/frankwilz/Food-delivery-app.git
cd Food-delivery-app
```

Create and activate a virtual environment.

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

Install the project dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run the Application

Start the development server from the repository root:

```bash
python -m uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000` by default. Stop the server with `Ctrl+C`.

## API Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Confirms that the API is running. |
| `GET` | `/restaurants` | Returns all representative restaurants. |
| `GET` | `/restaurants/{restaurant_id}/menu` | Returns all menu items for a restaurant (404 if the restaurant does not exist). |
| `GET` | `/restaurants/{restaurant_id}/menu/{item_id}` | Returns one menu item (404 if missing or owned by another restaurant). |
| `POST` | `/restaurants/{restaurant_id}/menu` | Adds a menu item; the server assigns the id (201; 404; 409 duplicate name; 422 invalid body). |
| `PATCH` | `/restaurants/{restaurant_id}/menu/{item_id}` | Partially updates a menu item (200; 400 empty body; 404; 409 duplicate name; 422). |
| `GET` | `/docs` | Opens FastAPI's interactive Swagger UI. |
| `GET` | `/openapi.json` | Returns the generated OpenAPI schema. |

Example health request:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

Example restaurant request:

```bash
curl http://127.0.0.1:8000/restaurants
```

The restaurant endpoint returns objects with the following Pydantic fields: `id`, `name`, `cuisine`, `address`, `rating`, and `is_open`.

## Architecture

The restaurant-list request follows the required layered path:

```text
GET /restaurants
  -> FastAPI route in app/api/routes/restaurants.py
  -> RestaurantService in app/services/restaurant_service.py
  -> RestaurantRepository in app/repositories/restaurant_repository.py
  -> data/restaurants.json
```

Each layer has one responsibility:

- **Route:** Handles the HTTP endpoint, dependency creation, and response model.
- **Service:** Coordinates the restaurant-list operation.
- **Repository:** Reads restaurant records from the configured JSON file.
- **Persistence:** Stores representative restaurant data in `data/restaurants.json`.
- **Schema:** Defines the API response contract in `app/schemas/restaurant.py`.

The route does not read the JSON file directly.

## Menu Functionality

Menu requests follow the same layered path as restaurants:

```text
GET/POST/PATCH /restaurants/{restaurant_id}/menu[/{item_id}]
  -> FastAPI routes in app/api/routes/menu.py
  -> MenuService in app/services/menu_service.py
  -> MenuItemRepository in app/repositories/menu_item_repository.py
  -> data/menu_items.json
```

- **Schemas** (`app/schemas/menu_item.py`): `MenuItem` (response), `MenuItemCreate` (POST body, no `id`/`restaurant_id`), `MenuItemUpdate` (PATCH body, every field optional), `ErrorResponse` (error body).
- **Fields:** `id`, `restaurant_id`, `name`, `description`, `price` (> 0), `category`, `is_available`.
- **Service rules:** the restaurant must exist; an item is only reachable through the restaurant that owns it; item names are unique within a restaurant (case-insensitive, 409); a PATCH with no fields is rejected (400).
- **Repository:** the only code that reads or writes `data/menu_items.json`. New ids are `max(existing ids) + 1`, and `id`/`restaurant_id` are never overwritten. Each save writes a temporary file and swaps it in with `os.replace`, so a crash cannot leave a half-written file.

Example: add a menu item.

```bash
curl -X POST http://127.0.0.1:8000/restaurants/1/menu \
  -H "Content-Type: application/json" \
  -d '{"name": "Garlic Bread", "price": 5.99, "category": "Appetizers"}'
```

### Design decision: menu storage

Menu items are stored in their **own file** (`data/menu_items.json`) and linked to restaurants by `restaurant_id`, instead of being nested inside each restaurant in `restaurants.json`.

- **Why:** restaurant and menu code can be built and tested independently (separate repositories, no edits to the same file); updating one menu item does not rewrite every restaurant; item ids are unique across all restaurants, so an item can be addressed directly.
- **Trade-off:** JSON does not enforce the link, so the service checks that the restaurant exists before every menu operation, and `test_committed_menu_data_is_valid_and_consistent` checks that every `restaurant_id` in the data points to a real restaurant.

## Configuration

The default data directory is `data/` at the repository root. Set the `DATA_DIR` environment variable to use a different directory without changing application code:

```bash
DATA_DIR=/absolute/path/to/test-data python -m uvicorn app.main:app --reload
```

The configured directory must contain `restaurants.json` and `menu_items.json`. This setting allows automated tests to use isolated temporary data instead of modifying the committed representative data.

## Representative Data

Representative restaurant data is stored in:

```text
data/restaurants.json
```

The committed file contains two restaurant records with stable integer identifiers.

## Tests

Run the test suite from the repository root:

```bash
python -m pytest -q
```

Milestone 0 requires tests for the health endpoint, restaurant-list endpoint, repository behavior, and at least one invalid or failure case. Tests should use temporary data, set `DATA_DIR` when needed, and never modify `data/restaurants.json`.

## Repository Structure

```text
Food-delivery-app/
├── app/
│   ├── api/routes/restaurants.py
│   ├── core/config.py
│   ├── repositories/restaurant_repository.py
│   ├── schemas/restaurant.py
│   ├── services/restaurant_service.py
│   └── main.py
├── data/
│   └── restaurants.json
├── scrum/
│   └── team-agreement.md
├── test/
│   └── test_health.py
├── README.md
└── requirements.txt
```

## Milestone 0 Submission Check

1. Implement and pass the required pytest cases.
2. Confirm that the application starts with the documented command.
3. Confirm that `/health`, `/restaurants`, and `/docs` work in a clean environment.
4. Review and approve the current version of `scrum/team-agreement.md`.
5. Commit all final files and push them to GitHub.
6. Create and push the required `foundation-gate` tag.
7. Record the tag URL and its full commit SHA in the submission PDF.
