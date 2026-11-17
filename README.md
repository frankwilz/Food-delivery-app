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

The frontend is a single page that calls the REST API with `fetch`, split into `frontend/index.html` (markup), `frontend/styles.css` (styles) and `frontend/index.js` (behavior). It has no build step and no extra dependencies.

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
| Create a restaurant | Log in as the manager in `/docs` (`POST /auth/login` with `dev.patel@example.com`), paste the `access_token` into **Manager token** at the bottom of the page, then click **Add restaurant**, fill in the form and click **Create restaurant**. Without a manager token the form shows the 401 or 403 error. | `POST /restaurants` |
| Unknown restaurant | Go to `http://127.0.0.1:5500/#/restaurant/999` | `GET /restaurants/999` → 404, shown as "That restaurant doesn't exist" |
| Validation error | Create a restaurant with the same name and address as an existing one | `POST /restaurants` → 409, shown in the form |

After creating a restaurant, stop the backend (`Ctrl+C`) and start it again with the same `DATA_DIR`. The new restaurant is still there, because it was saved to `restaurants.json`. The API side of search and filter (`?search=`, `?cuisine=`, `?is_open=`, `?min_rating=`) can be shown in `/docs`.

## API Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Confirms that the API is running. |
| `GET` | `/restaurants` | Lists restaurants. Optional filters: `search`, `cuisine`, `is_open`, `min_rating` (422 for invalid values). |
| `GET` | `/restaurants/{restaurant_id}` | Returns one restaurant's details (404 if it does not exist). |
| `POST` | `/restaurants` | **Manager only.** Creates a restaurant; the server assigns the id (201; 401; 403 not a manager; 409 duplicate name + address; 422 invalid body). |
| `PATCH` | `/restaurants/{restaurant_id}` | **Manager only.** Partially updates a restaurant (200; 400 empty body; 401; 403; 404; 409 duplicate; 422). |
| `GET` | `/restaurants/{restaurant_id}/menu` | Returns a restaurant's menu items. Deactivated items are hidden unless `include_inactive=true` is sent (404 if the restaurant does not exist). |
| `GET` | `/restaurants/{restaurant_id}/menu/{item_id}` | Returns one menu item (404 if missing or owned by another restaurant). |
| `POST` | `/restaurants/{restaurant_id}/menu` | **Manager only.** Adds a menu item; the server assigns the id (201; 401; 403; 404; 409 duplicate name; 422 invalid body). |
| `PATCH` | `/restaurants/{restaurant_id}/menu/{item_id}` | **Manager only.** Partially updates a menu item, including `is_available` and `is_active` (200; 400 empty body; 401; 403; 404; 409 duplicate name; 422). |
| `DELETE` | `/restaurants/{restaurant_id}/menu/{item_id}` | **Manager only.** Deactivates a menu item (soft delete: sets `is_active` to `false` and keeps the record) and returns it (200; 401; 403; 404). |
| `POST` | `/customers` | Registers a customer account; the server assigns the id, sets `role` to `customer` and stores only a salted password hash (201; 409 duplicate email, case-insensitive; 422 invalid body). |
| `GET` | `/customers/me` | Returns the signed-in customer (200; 401 missing, invalid or expired token; 403 deactivated). Requires `Authorization: Bearer <token>`. |
| `PATCH` | `/customers/me` | Changes the signed-in customer's `name`, `email` and/or `delivery_address` (200; 400 empty body; 401; 403 deactivated; 409 duplicate email, case-insensitive; 422 invalid value, `null`, or a field that can't be changed here such as `id`, `role`, `is_active` or `password`). |
| `POST` | `/customers/me/deactivate` | Deactivates the signed-in customer's account and returns it with `is_active: false` (200; 401; 403 already deactivated). The record is kept, so the email stays taken. |
| `POST` | `/auth/login` | Checks an email and password and returns a signed token (200; 401 wrong email or password; 403 deactivated account with the correct password; 422 invalid body). |
| `GET` | `/cart` | Returns the signed-in customer's active cart, creating an empty one the first time, priced from the current menu (200; 401; 403 deactivated). |
| `POST` | `/cart/items` | Adds a menu item and quantity to the cart; adding it again increases the quantity (200; 400 total quantity above 99; 401; 403; 404 unknown item; 409 another restaurant, unavailable or removed item; 422 invalid quantity). |
| `PATCH` | `/cart/items/{menu_item_id}` | Sets an item's quantity (200; 401; 403; 404 not in the cart; 422 invalid quantity). |
| `DELETE` | `/cart/items/{menu_item_id}` | Removes one item; an emptied cart is no longer tied to a restaurant (200; 401; 403; 404 not in the cart). |
| `DELETE` | `/cart` | Empties the cart (200; 401; 403). |
| `POST` | `/checkout` | Places an order from the active cart and returns it (201; 400 empty cart or invalid quantity; 401; 403; 404 restaurant or item gone; 409 restaurant closed, item unavailable or removed, or cart already checked out). |
| `GET` | `/orders` | Lists the signed-in customer's orders, newest first (200; 401; 403). |
| `GET` | `/orders/{order_id}` | Returns one of the signed-in customer's orders (200; 401; 403; 404 missing or another customer's). |
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
# Creating and updating need a manager's token (log in as dev.patel@example.com, see Authentication)
curl -X POST http://127.0.0.1:8000/restaurants \
  -H "Authorization: Bearer <manager token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Kelowna Curry House", "cuisine": "Indian", "address": "55 Pandosy Street", "rating": 4.4}'
curl -X PATCH http://127.0.0.1:8000/restaurants/2 \
  -H "Authorization: Bearer <manager token>" \
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
GET/POST/PATCH/DELETE /restaurants/{restaurant_id}/menu[/{item_id}]
  -> FastAPI routes in app/api/routes/menu.py
  -> MenuService in app/services/menu_service.py
  -> MenuItemRepository in app/repositories/menu_item_repository.py
  -> data/menu_items.json
```

- **Schemas** (`app/schemas/menu_item.py`): `MenuItem` (response), `MenuItemCreate` (POST body, no `id`/`restaurant_id`), `MenuItemUpdate` (PATCH body, every field optional). Errors use the shared `ErrorResponse` in `app/schemas/error.py`.
- **Fields:** `id`, `restaurant_id`, `name`, `description`, `price` (> 0), `category`, `is_available`, `is_active`.
- **Service rules:** the restaurant must exist; an item is only reachable through the restaurant that owns it; item names are unique within a restaurant (case-insensitive, 409); a PATCH with no fields is rejected (400).
- **Availability and deactivation:** an item has two separate flags.
  - `is_available: false` means temporarily out of stock. The item stays on the menu, marked as unavailable. Set it with `PATCH`.
  - `is_active: false` means removed from the menu. `DELETE` sets it (a soft delete, so the record and its id are kept for carts and orders that refer to it), and `PATCH` with `is_active: true` puts the item back. Deactivated items are hidden from the menu list unless `include_inactive=true` is sent, can still be fetched by id, and keep their name reserved. New items always start active.
- **One rule for ordering:** `MenuService.get_orderable_item(item_id)` returns the item only if it exists, is active and is available. Otherwise it raises a clear error: not found (404), or `MenuItemDeactivatedError` / `MenuItemUnavailableError` (both 409, both subclasses of `MenuItemNotOrderableError`). The cart and checkout call this method instead of checking the flags themselves.
- **Repository:** the only code that reads or writes `data/menu_items.json`. New ids are `max(existing ids) + 1`, and `id`/`restaurant_id` are never overwritten. Each save writes a temporary file and swaps it in with `os.replace`, so a crash cannot leave a half-written file.

Example: add a menu item (managers only).

```bash
curl -X POST http://127.0.0.1:8000/restaurants/1/menu \
  -H "Authorization: Bearer <manager token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Garlic Bread", "price": 5.99, "category": "Appetizers"}'
```

### Design decision: menu storage

Menu items are stored in their **own file** (`data/menu_items.json`) and linked to restaurants by `restaurant_id`, instead of being nested inside each restaurant in `restaurants.json`.

- **Why:** restaurant and menu code can be built and tested independently (separate repositories, no edits to the same file); updating one menu item does not rewrite every restaurant; item ids are unique across all restaurants, so an item can be addressed directly.
- **Trade-off:** JSON does not enforce the link, so the service checks that the restaurant exists before every menu operation, and `test_committed_menu_data_is_valid_and_consistent` checks that every `restaurant_id` in the data points to a real restaurant.

## Authentication

A customer logs in with their email and password and receives a token:

```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "ana.souza@example.com", "password": "Ana-demo-2026"}'
```

```json
{"access_token": "<token>", "token_type": "bearer"}
```

The token is sent on later requests in the `Authorization: Bearer <token>` header. In `/docs`, click **Authorize**, paste the token and every protected endpoint is then called with it. For example, to read the signed-in customer:

```bash
curl http://127.0.0.1:8000/customers/me -H "Authorization: Bearer <token>"
```

```text
POST /auth/login
  -> FastAPI route in app/api/routes/auth.py
  -> AuthService in app/services/auth_service.py
  -> CustomerRepository in app/repositories/customer_repository.py
  -> data/customers.json
```

- **Token:** a JWT signed with HS256 (`app/core/security.py`, using PyJWT). It holds only the customer id and an expiry time (60 minutes by default), never the email, role or password.
- **Signing key:** read from the `SECRET_KEY` environment variable and never hard-coded (see [Configuration](#configuration)).
- **Protecting an endpoint:** add `customer: dict = Depends(get_current_customer)` from `app/api/dependencies.py`. It reads the header, checks the token and loads the customer. It responds with `401` if the token is missing, invalid or expired, and `403` if the account has been deactivated.
- **Active customers:** whether an account is active is decided in one function, `ensure_active` in `app/services/customer_service.py`. `CustomerService.get_active_customer(customer_id)` uses it and also raises 404 for a missing account; the cart and checkout call it instead of checking `is_active` themselves. `AuthService` uses it at login and on every token check.
- **Updating an account:** `PATCH /customers/me` goes through `CustomerService.update_profile`. The body model, `CustomerUpdate`, only has `name`, `email` and `delivery_address` and forbids any other field, so `id`, `role`, `is_active` and the password hash can never be changed through it.
- **Deactivation:** `POST /customers/me/deactivate` sets `is_active` to `false` and keeps the record. After that, login returns `403`, but only when the password is correct, so a wrong password never reveals an account's status. Because the customer record is read on every request, tokens issued before deactivation stop working immediately with `403`, even though they have not expired.
- **Wrong email or wrong password:** both return the same `401` and message, so the response does not reveal which emails have accounts.

### Authorization (who may call what)

| Endpoints | Who | Without a valid token | Wrong account |
| --- | --- | --- | --- |
| `GET /health`, `GET /restaurants...`, `GET .../menu...`, `POST /customers`, `POST /auth/login` | Anyone | — | — |
| `POST`/`PATCH /restaurants...`, `POST`/`PATCH`/`DELETE .../menu...` | A signed-in, active **manager** | `401` | `403` for a customer or a deactivated account |
| `/customers/me...`, `/cart...`, `/checkout`, `/orders...` | A signed-in, active account, acting on **its own** data only | `401` | `403` if deactivated |

- **Where it is enforced:** in FastAPI dependencies in `app/api/dependencies.py`. `get_current_customer` checks the token and that the account is active. `require_role("manager")` builds on it and also checks the role; manager-only routes declare `dependencies=[Depends(require_manager)]`. Both run before the route body, so a refused request never reaches a service and writes nothing.
- **Own data only:** customer endpoints never take a customer id from the client. The id always comes from the token (`customer["id"]`), and services look up only that customer's records, so there is no way to name another customer's cart or account.
- **Demo:** log in as `dev.patel@example.com` (password in [Representative Data](#representative-data)) to get a manager token for the restaurant and menu forms in `/docs`.

## Customer-to-Order Workflow

The full flow goes through every subsystem: **register → log in → browse → add to cart → check out → view the order**.

```text
POST /checkout
  -> FastAPI route in app/api/routes/checkout.py
  -> CheckoutService in app/services/checkout_service.py
       CustomerService.get_active_customer   (the customer is active)
       CartRepository.get_active_for_customer (the cart exists and is not empty)
       RestaurantRepository.get_by_id         (the restaurant exists and is open)
       MenuService.get_orderable_item         (every item can still be ordered, at its current price)
       price_lines                            (the same pricing as the cart)
       OrderRepository.create                 (the order is saved...)
       CartService.mark_checked_out           (...and only then is the cart closed)
  -> data/customers.json, carts.json, restaurants.json, menu_items.json, orders.json
```

**How services get their dependencies:** every repository and service is built in one place, `app/api/dependencies.py`. Each repository is made from its data file path in a `get_..._repository` function, and each service from the repositories and services it needs in a `get_..._service` function, chained with FastAPI's `Depends`. Routes only ask for a service, for example `service: CheckoutService = Depends(get_checkout_service)`. No route or service opens a data file or builds another subsystem's objects; only repositories read and write JSON. `tests/test_workflow.py` checks this.

**Try it in `/docs`** (on a copy of the data, see [Showcase the vertical slice](#showcase-the-vertical-slice)):

1. `POST /customers` to register, then `POST /auth/login` with the same email and password. Click **Authorize** and paste the `access_token`.
2. `GET /restaurants` and `GET /restaurants/1/menu` to browse.
3. `POST /cart/items` with `{"menu_item_id": 1, "quantity": 2}`, then `GET /cart` to see the backend's totals.
4. `POST /checkout` returns `201` with the order. `GET /cart` now returns a new, empty cart.
5. `GET /orders` and `GET /orders/{order_id}` show the order.
6. Stop the server and start it again with the same `DATA_DIR`. The account, the order and the empty cart are all still there.

To skip registering, log in as `ben.carter@example.com`, who already has a cart ready to check out and a past order.

## Business Rules

Every cross-subsystem rule is enforced in the backend service layer (or in a shared FastAPI dependency that runs before the service), never only in the frontend. Each row names the code that enforces the rule and a test that proves it. `tests/test_business_rules.py` checks that every test named here exists.

| Rule | Where it is enforced | Proved by |
| --- | --- | --- |
| A deactivated customer can't create or modify a cart | `get_current_customer` in `app/api/dependencies.py`, and `CartService.get_or_create_active_cart` through `CustomerService.get_active_customer` | `tests/test_cart.py::test_deactivated_customer_gets_403_and_no_cart`, `tests/test_cart.py::test_deactivated_customer_cannot_add_items`, `tests/test_cart.py::test_service_get_cart_rejects_deactivated_customer` |
| At most one active cart per customer | `CartService.get_or_create_active_cart` creates a cart only when `CartRepository.get_active_for_customer` finds none | `tests/test_cart.py::test_repeated_get_cart_never_creates_a_second_active_cart`, `tests/test_workflow.py::test_each_customer_has_at_most_one_active_cart` |
| Cart items come from only one restaurant | `CartService.add_item` (`DifferentRestaurantError`), and again at checkout in `CheckoutService.prepare` | `tests/test_cart.py::test_item_from_a_different_restaurant_returns_409_and_changes_nothing`, `tests/test_checkout.py::test_cart_mixing_restaurants_cannot_be_checked_out` |
| Unavailable, deactivated or nonexistent items can't be added | `CartService.add_item` through `MenuService.get_orderable_item` | `tests/test_cart.py::test_unavailable_item_returns_409`, `tests/test_cart.py::test_deactivated_item_returns_409`, `tests/test_cart.py::test_unknown_item_returns_404` |
| Quantities are valid | `CartItemAdd` and `CartItemUpdate` in `app/schemas/cart.py` (whole number, 1 to 99), `CartService.add_item` (combined total), `CheckoutService.prepare` (stored quantities) | `tests/test_cart.py::test_add_invalid_quantity_returns_422`, `tests/test_cart.py::test_update_invalid_quantity_returns_422_and_changes_nothing`, `tests/test_cart.py::test_add_beyond_the_maximum_combined_quantity_returns_400`, `tests/test_checkout.py::test_invalid_stored_quantity_returns_400` |
| The backend calculates totals | `price_lines` in `app/services/pricing.py`, used by `CartService.priced` and `CheckoutService.calculate_totals`; the cart stores only ids and quantities | `tests/test_cart.py::test_totals_for_several_items_and_quantities`, `tests/test_cart.py::test_prices_are_never_stored_in_the_cart`, `tests/test_checkout.py::test_any_price_or_total_sent_by_the_client_is_ignored`, `tests/test_checkout.py::test_checkout_uses_the_shared_pricing_function` |
| Checkout revalidates menu availability and prices | `CheckoutService.revalidate_items` through `MenuService.get_orderable_item`, then `calculate_totals` with the current menu items | `tests/test_checkout.py::test_item_made_unavailable_after_adding_returns_409_naming_it`, `tests/test_checkout.py::test_item_deactivated_after_adding_returns_409_naming_it`, `tests/test_checkout.py::test_price_changed_between_adding_and_checkout_uses_the_new_price` |
| Checkout requires a valid customer | `get_current_customer`, and `CheckoutService.prepare` through `CustomerService.get_active_customer` | `tests/test_checkout.py::test_checkout_requires_sign_in`, `tests/test_checkout.py::test_deactivated_customer_gets_403` |
| Orders are only created from a valid cart | `CheckoutService.prepare`: the customer's own active, non-empty cart, an existing and open restaurant, valid quantities and orderable items; nothing is written if a check fails | `tests/test_checkout.py::test_empty_cart_returns_400`, `tests/test_checkout.py::test_missing_restaurant_returns_404`, `tests/test_checkout.py::test_closed_restaurant_returns_409`, `tests/test_checkout.py::test_another_customers_cart_is_not_used`, `tests/test_checkout.py::test_failed_checkout_does_not_create_an_order` |
| The cart is not cleared until the order is saved | `CheckoutService.checkout` calls `OrderRepository.create` first and `CartService.mark_checked_out` after; each order records its `cart_id`, so a cart becomes at most one order | `tests/test_checkout.py::test_cart_is_closed_only_after_the_order_is_saved`, `tests/test_checkout.py::test_order_save_failure_leaves_the_cart_unchanged`, `tests/test_checkout.py::test_checking_out_twice_creates_only_one_order`, `tests/test_checkout.py::test_order_saved_but_cart_not_closed_is_not_ordered_twice` |
| Relationships stay valid after restarts | Repositories keep ids stable (`max + 1`, never reused) and save atomically; orders keep snapshots of names, prices and the address | `tests/test_integration.py::test_cart_and_order_persist_after_server_restarts`, `tests/test_workflow.py::test_carts_point_to_real_customers_restaurants_and_menu_items`, `tests/test_workflow.py::test_orders_point_to_real_records`, `tests/test_orders.py::test_menu_price_change_after_checkout_does_not_change_the_order` |

**Gap found and fixed (5.3):** the one-restaurant rule was only checked when an item was added. If `carts.json` was changed outside the API, checkout would accept a cart that mixed restaurants and save an order with another restaurant's item. `CheckoutService.prepare` now rechecks every item's restaurant with the same `DifferentRestaurantError` and refuses with `409`.

## Error Handling

Every error response is JSON with the shared `ErrorResponse` shape, `{"detail": "..."}`, and every error status is listed in `/docs`.

| Status | When |
| --- | --- |
| `400` | A `PATCH` body contains no fields. |
| `401` | The login email or password is wrong, or a protected endpoint was called with a missing, invalid or expired token. The response includes a `WWW-Authenticate: Bearer` header. |
| `403` | The account has been deactivated (at login with the correct password, and on every protected endpoint, including with a token issued before deactivation), or a customer called a manager-only endpoint. |
| `404` | The restaurant or menu item does not exist, or the menu item belongs to another restaurant. |
| `409` | A create or update would duplicate a restaurant (name + address), a menu item name at the same restaurant, or a customer email (case-insensitive). |
| `422` | Invalid input: a wrong type, a value out of range, a missing required field, an unknown or server-assigned field (`id`, `restaurant_id`), `null` in a `PATCH`, or malformed JSON. For `422` responses, `detail` is FastAPI's list of validation errors. |
| `500` | A data file is missing, unreadable or corrupt. The client receives `{"detail": "Data storage error"}`, and the full error is written to the server log. |

## Configuration

The default data directory is `data/` at the repository root. Set the `DATA_DIR` environment variable to use a different directory without changing application code:

```bash
DATA_DIR=/absolute/path/to/test-data python -m uvicorn app.main:app --reload
```

The configured directory must contain all five data files: `restaurants.json`, `menu_items.json`, `customers.json`, `carts.json` and `orders.json`. This setting allows automated tests to use isolated temporary data instead of modifying the committed representative data.

Login tokens are configured with two more environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | A random key generated at startup | Signs login tokens. Without it, every token stops working when the server restarts (including each `--reload`), so set it to keep users signed in. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | How long a login token stays valid. |

```bash
SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')" python -m uvicorn app.main:app --reload
```

## Representative Data

Representative restaurant data is stored in:

```text
data/restaurants.json
```

The committed file contains four restaurant records with stable integer identifiers (two Pizza, one Mexican, one Japanese; one closed), so search and filters can be demonstrated.

`data/customers.json` contains four accounts: two active customers, one deactivated customer and one manager. Passwords are stored only as salted PBKDF2-SHA256 hashes (`app/core/security.py`). The demo passwords are:

| Email | Password | Role | Active |
| --- | --- | --- | --- |
| `ana.souza@example.com` | `Ana-demo-2026` | customer | yes |
| `ben.carter@example.com` | `Ben-demo-2026` | customer | yes |
| `chloe.martin@example.com` | `Chloe-demo-2026` | customer | no |
| `dev.patel@example.com` | `Dev-demo-2026` | manager | yes |

`data/carts.json` and `data/orders.json` fit the other files:

- **Ben** has an active cart at Taco Bell (restaurant 2) ready to check out, and one past order from Boston Pizza (order 1, from his closed cart 1).
- **Chloe**, now deactivated, has one past order (order 2). Her account is kept, so the order keeps its owner.
- **Ana** has no cart and no orders, to show the flow from the start.

Every `customer_id`, `restaurant_id`, `menu_item_id` and `cart_id` points to a real record, each cart holds items from its own restaurant only, and each order's totals add up. `tests/test_workflow.py` checks all of this.

## Tests

Run the test suite from the repository root:

```bash
python -m pytest -q
```

| File | Covers |
| --- | --- |
| `tests/test_health.py` | `GET /health`. |
| `tests/test_restaurants.py` | Restaurant endpoints, search and filters, validation, the repository and service, and committed data integrity. |
| `tests/test_menu.py` | Menu endpoints, validation, duplicate names, availability, deactivation (soft delete), `get_orderable_item`, the repository, and committed data integrity. |
| `tests/test_customers.py` | Customer registration, duplicate emails (case-insensitive), validation, password hashing, the repository and service, and committed data integrity. |
| `tests/test_auth.py` | Login (valid, wrong password, unknown email, invalid body), tokens (expired, tampered, forged, malformed), `get_current_customer` (missing, invalid and expired tokens), and the `SECRET_KEY` setting. |
| `tests/test_cart.py` | The cart: one active cart per customer, adding, updating, removing and clearing items, the one-restaurant rule, quantities, and totals from the current menu. |
| `tests/test_checkout.py` | Checkout: every check before anything is written, revalidating items and prices, the order total, saving the order with snapshots, and closing the cart only after the order is saved. |
| `tests/test_orders.py` | `GET /orders` (newest first, own orders only) and `GET /orders/{order_id}` (404 for a missing or another customer's order), and snapshots that never change. |
| `tests/test_business_rules.py` | That every cross-subsystem rule is in the README's Business Rules table, and that every test the table names exists. |
| `tests/test_workflow.py` | The full customer-to-order flow through the API, the consistency of the representative data in all five files, and that routes and services never touch data files directly. |
| `tests/test_integration.py` | The complete vertical slice (restaurant + menu through every layer to the JSON files), error handling (`404`/`405`/`422`/JSON `500`), API documentation, and **persistence across a real restart**: the tests start `uvicorn` with `DATA_DIR` set to a temporary folder, write data, stop the server, start it again and read the data back. One of them fills a cart, restarts, checks out, restarts again and checks the order, its cart and the new empty cart. |

**Isolated test data:** `tests/conftest.py` copies all five data files into a fresh temporary folder before **every** test and points `app.core.config` at those copies, which every shared dependency reads. The cart, checkout and order tests start with empty `carts.json` and `orders.json` (the `no_carts_or_orders` fixture). Tests can create and update freely without changing the committed data or affecting each other. Several tests check that the files in `data/` are unchanged afterwards.

**Continuous integration:** `.github/workflows/tests.yml` runs `pytest` with GitHub Actions on Python 3.11 and 3.13 for every pull request and every push to `main`. It then checks that `data/` was not modified. A pull request should only be merged when this check is green.

## Repository Structure

```text
Food-delivery-app/
├── .github/workflows/tests.yml     # CI: runs pytest on every push and PR
├── app/
│   ├── api/
│   │   ├── dependencies.py         # builds every repository and service; get_current_customer, require_role
│   │   └── routes/
│   │       ├── auth.py
│   │       ├── cart.py
│   │       ├── checkout.py
│   │       ├── customers.py
│   │       ├── menu.py
│   │       ├── orders.py
│   │       └── restaurants.py
│   ├── core/
│   │   ├── config.py               # DATA_DIR, data file paths, token settings
│   │   ├── errors.py               # shared domain errors (401, 404, 409, ...)
│   │   └── security.py             # salted password hashing, login tokens
│   ├── repositories/
│   │   ├── cart_repository.py
│   │   ├── customer_repository.py
│   │   ├── json_repository.py      # JsonRepository base: load, atomic save, next_id
│   │   ├── menu_item_repository.py
│   │   ├── order_repository.py
│   │   └── restaurant_repository.py
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── cart.py
│   │   ├── customer.py
│   │   ├── error.py
│   │   ├── health.py
│   │   ├── menu_item.py
│   │   ├── order.py
│   │   └── restaurant.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── cart_service.py
│   │   ├── checkout_service.py
│   │   ├── customer_service.py
│   │   ├── menu_service.py
│   │   ├── order_service.py
│   │   ├── pricing.py              # price_lines: the one place money is calculated
│   │   └── restaurant_service.py
│   └── main.py                     # app, /health, error handlers, CORS
├── data/
│   ├── carts.json
│   ├── customers.json
│   ├── menu_items.json
│   ├── orders.json
│   └── restaurants.json
├── docs/
│   └── PROVENANCE.md
├── frontend/
│   ├── index.html                  # page markup
│   ├── index.js                    # restaurant list, details, menu, create form
│   └── styles.css                  # page styles
├── scrum/
│   ├── sprint-planning-m1.md
│   └── team-agreement.md
├── tests/
│   ├── conftest.py                 # isolated temporary data for every test
│   ├── test_auth.py
│   ├── test_authorization.py
│   ├── test_business_rules.py
│   ├── test_cart.py
│   ├── test_checkout.py
│   ├── test_customer_update.py
│   ├── test_customers.py
│   ├── test_deactivation.py
│   ├── test_health.py
│   ├── test_integration.py
│   ├── test_menu.py
│   ├── test_orders.py
│   ├── test_restaurants.py
│   └── test_workflow.py
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
