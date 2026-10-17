# Food Delivery App

[![Tests](https://github.com/frankwilz/Food-delivery-app/actions/workflows/tests.yml/badge.svg)](https://github.com/frankwilz/Food-delivery-app/actions/workflows/tests.yml)

Food Delivery App is a team project. Milestone 1 delivers the first vertical slice: a customer can list, search and filter restaurants, open a restaurant's details and browse its menu, and a restaurant manager can create and update restaurants and menu items. It consists of a FastAPI backend (route → service → repository → JSON), Pydantic request and response models, automated tests that run in GitHub Actions, and a basic web frontend that calls the API.

**Team name:** Abdul & Friends

**Project board:** https://github.com/users/frankwilz/projects/2 (user stories #19–#24)

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

## Run the Frontend

The frontend is a single page, `frontend/index.html`, that calls the REST API with `fetch`. It has no build step and no extra dependencies.

1. Start the backend as shown above, on port `8000`.
2. In a **second terminal**, serve the frontend from the repository root on port `5500`:

   ```bash
   python -m http.server 5500 --directory frontend
   ```

3. Open **http://127.0.0.1:5500** in a browser.

The page must be served on port `5500`, either from `localhost` or `127.0.0.1`. The backend only accepts cross-origin requests from those two origins (`CORSMiddleware` in `app/main.py`). Opening `index.html` directly from the file system, or serving it on another port, fails with "Could not load restaurants". VS Code's Live Server extension also uses port 5500 by default. If the API runs somewhere else, change the **API address** field at the bottom of the page.

### Showcase the vertical slice

To demo without changing the committed data, run the backend on a temporary copy of `data/`:

```bash
cp -r data /tmp/demo-data
DATA_DIR=/tmp/demo-data python -m uvicorn app.main:app --reload
```

Then walk through **Restaurant List → Search / Filter → Restaurant Details → Menu → Menu Items** in the browser:

| Step | In the frontend | API call |
| --- | --- | --- |
| Restaurant list | The home page shows every restaurant as a card | `GET /restaurants` |
| Search / filter | Type in the search box (name, cuisine or address), or click a cuisine chip | Filters the loaded list in the browser |
| Restaurant details | Click a card | `GET /restaurants/{id}` |
| Menu and menu items | The details page lists the menu, grouped by category, with prices | `GET /restaurants/{id}/menu` |
| Create a restaurant | Click **Add restaurant**, fill in the form and click **Create restaurant** | `POST /restaurants` |
| Unknown restaurant | Go to `http://127.0.0.1:5500/#/restaurant/999` | `GET /restaurants/999` → 404, shown as "That restaurant doesn't exist" |
| Validation error | Create a restaurant with the same name and address as an existing one | `POST /restaurants` → 409, shown in the form |

After creating a restaurant, stop the backend (`Ctrl+C`) and start it again with the same `DATA_DIR`. The new restaurant is still there, because it was saved to `restaurants.json`. The API side of search and filter (`?search=`, `?cuisine=`, `?is_open=`, `?min_rating=`) can be shown in `/docs`.

## API Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Confirms that the API is running. |
| `GET` | `/restaurants` | Lists restaurants. Optional filters: `search`, `cuisine`, `is_open`, `min_rating` (422 for invalid values). |
| `GET` | `/restaurants/{restaurant_id}` | Returns one restaurant's details (404 if it does not exist). |
| `POST` | `/restaurants` | Creates a restaurant; the server assigns the id (201; 409 duplicate name + address; 422 invalid body). |
| `PATCH` | `/restaurants/{restaurant_id}` | Partially updates a restaurant (200; 400 empty body; 404; 409 duplicate; 422). |
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

Example restaurant requests:

```bash
curl http://127.0.0.1:8000/restaurants
curl "http://127.0.0.1:8000/restaurants?search=pizza&min_rating=4"
curl http://127.0.0.1:8000/restaurants/2
curl -X POST http://127.0.0.1:8000/restaurants \
  -H "Content-Type: application/json" \
  -d '{"name": "Kelowna Curry House", "cuisine": "Indian", "address": "55 Pandosy Street", "rating": 4.4}'
curl -X PATCH http://127.0.0.1:8000/restaurants/2 \
  -H "Content-Type: application/json" \
  -d '{"is_open": false}'
```

Restaurant endpoints return the `Restaurant` Pydantic model: `id`, `name`, `cuisine`, `address`, `rating` (0 to 5), and `is_open`.

### Search and filter

`GET /restaurants` accepts optional query parameters, which can be combined (all must match):

| Parameter | Meaning |
| --- | --- |
| `search` | Name **or** cuisine contains this text (case-insensitive), e.g. `?search=pizz`. |
| `cuisine` | Cuisine is exactly this value (case-insensitive), e.g. `?cuisine=Mexican`. |
| `is_open` | `true` or `false`. |
| `min_rating` | Rating is at least this value (0 to 5). |

No matches returns `200` with an empty list.

## Architecture

Restaurant requests follow the required layered path:

```text
GET/POST /restaurants, GET/PATCH /restaurants/{restaurant_id}
  -> FastAPI route in app/api/routes/restaurants.py
  -> RestaurantService in app/services/restaurant_service.py
  -> RestaurantRepository in app/repositories/restaurant_repository.py
  -> data/restaurants.json
```

Each layer has one responsibility:

- **Route:** Handles the HTTP endpoint, dependency creation, and response model.
- **Service:** Holds the business rules: search/filter logic, 404 for unknown ids, no duplicate restaurant (same name **and** address, case-insensitive, so chains at different addresses are allowed), and no empty updates.
- **Repository:** The only code that reads or writes the JSON file: `get_all`, `get_by_id`, `create`, `update`. New ids are `max(existing ids) + 1` and the id is never overwritten, so ids stay stable and menu items keep pointing at the right restaurant. Each save writes a temporary file and swaps it in with `os.replace`, so a crash cannot leave a half-written file.
- **Persistence:** Stores restaurant data in `data/restaurants.json`.
- **Schema:** `app/schemas/restaurant.py` defines `Restaurant` (response), `RestaurantCreate` (POST body, no `id`) and `RestaurantUpdate` (PATCH body, every field optional, `null` rejected). Errors use the shared `ErrorResponse` model in `app/schemas/error.py`.

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

## Error Handling

Every error response is JSON with the shared `ErrorResponse` shape, `{"detail": "..."}`, and every error status is listed in `/docs`.

| Status | When |
| --- | --- |
| `400` | A `PATCH` body contains no fields. |
| `404` | The restaurant or menu item does not exist, or the menu item belongs to another restaurant. |
| `409` | A create or update would duplicate a restaurant (name + address) or a menu item name at the same restaurant. |
| `422` | Invalid input: a wrong type, a value out of range, a missing required field, an unknown or server-assigned field (`id`, `restaurant_id`), `null` in a `PATCH`, or malformed JSON. For `422` responses, `detail` is FastAPI's list of validation errors. |
| `500` | A data file is missing, unreadable or corrupt. The client receives `{"detail": "Data storage error"}`, and the full error is written to the server log. |

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

The committed file contains four restaurant records with stable integer identifiers (two Pizza, one Mexican, one Japanese; one closed), so search and filters can be demonstrated.

## Tests

Run the test suite from the repository root:

```bash
python -m pytest -q
```

| File | Covers |
| --- | --- |
| `tests/test_health.py` | `GET /health`. |
| `tests/test_restaurants.py` | Restaurant endpoints, search and filters, validation, the repository and service, and committed data integrity. |
| `tests/test_menu.py` | Menu endpoints, validation, duplicate names, the repository, and committed data integrity. |
| `tests/test_integration.py` | The complete vertical slice (restaurant + menu through every layer to the JSON files), error handling (`404`/`405`/`422`/JSON `500`), API documentation, and **persistence across a real restart**: the test starts `uvicorn` with `DATA_DIR` set to a temporary folder, writes data, stops the server, starts it again and reads the data back. |

**Isolated test data:** `tests/conftest.py` copies `data/restaurants.json` and `data/menu_items.json` into a fresh temporary folder before **every** test and points the routes at those copies. Tests can create and update freely without changing the committed data or affecting each other. Several tests check that the files in `data/` are unchanged afterwards.

**Continuous integration:** `.github/workflows/tests.yml` runs `pytest` with GitHub Actions on Python 3.11 and 3.13 for every pull request and every push to `main`. It then checks that `data/` was not modified. A pull request should only be merged when this check is green.

## Repository Structure

```text
Food-delivery-app/
├── .github/workflows/tests.yml     # CI: runs pytest on every push and PR
├── app/
│   ├── api/routes/
│   │   ├── menu.py
│   │   └── restaurants.py
│   ├── core/config.py              # DATA_DIR and data file paths
│   ├── repositories/
│   │   ├── menu_item_repository.py
│   │   └── restaurant_repository.py
│   ├── schemas/
│   │   ├── error.py
│   │   ├── health.py
│   │   ├── menu_item.py
│   │   └── restaurant.py
│   ├── services/
│   │   ├── menu_service.py
│   │   └── restaurant_service.py
│   └── main.py                     # app, /health, storage-error handler, CORS
├── data/
│   ├── menu_items.json
│   └── restaurants.json
├── docs/
│   └── PROVENANCE.md
├── frontend/
│   └── index.html                  # restaurant list, details, menu, create form
├── scrum/
│   ├── sprint-planning-m1.md
│   └── team-agreement.md
├── tests/
│   ├── conftest.py                 # isolated temporary data for every test
│   ├── test_health.py
│   ├── test_integration.py
│   ├── test_menu.py
│   └── test_restaurants.py
├── README.md
└── requirements.txt
```

## Milestone 1 Submission Check

1. `python -m pytest -q` passes locally, and the GitHub Actions check is green on `main`.
2. The backend and frontend start with the documented commands, and the vertical slice works in the browser.
3. `/docs` lists every endpoint with a description, parameters, request and response models, and error responses.
4. `docs/PROVENANCE.md` and the scrum notes in `scrum/` are complete.
5. Every feature has a GitHub Issue with acceptance criteria and labels, and is on the Project board.
6. All work is merged into `main` through reviewed pull requests.
7. Create and push the `m1-vertical-slice` tag on the final commit.
8. Record the repository, Project board and tag URLs, the full commit SHA and the agreed contribution percentages in the submission PDF.
