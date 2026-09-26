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

## Configuration

The default data directory is `data/` at the repository root. Set the `DATA_DIR` environment variable to use a different directory without changing application code:

```bash
DATA_DIR=/absolute/path/to/test-data python -m uvicorn app.main:app --reload
```

The configured directory must contain a file named `restaurants.json`. This setting allows automated tests to use isolated temporary data instead of modifying the committed representative data.

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

**Current repository status:** `test/test_health.py` is empty at the audited commit. Add the required tests before creating the `foundation-gate` submission tag.

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
