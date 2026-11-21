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

The frontend is a single page that calls the REST API with `fetch`. `index.js` handles browsing/navigation, `api.mjs` handles HTTP/session state, `account.mjs` renders account forms, and `shopping.mjs` renders ordering views. It has no build step or third-party JavaScript dependencies.

1. Start the backend as shown above, on port `8000`.
2. In a **second terminal**, serve the frontend from the repository root on port `5500`:

   ```bash
   python -m http.server 5500 --directory frontend
   ```

3. Open **http://127.0.0.1:5500** in a browser.

The page must be served on port `5500`, either from `localhost` or `127.0.0.1`. The backend only accepts cross-origin requests from those two origins (`CORSMiddleware` in `app/main.py`). Opening `index.html` directly from the file system, or serving it on another port, fails with "Could not load restaurants". VS Code's Live Server extension also uses port 5500 by default. If the API runs somewhere else, change the **API address** field at the bottom of the page.

### Customer workflow in the browser

1. Click **Register**, enter your details and delivery address, and create an account. Registration signs you in automatically. Existing accounts use **Sign in**; the demo credentials are listed under [Representative Data](#representative-data).
2. Your name appears in the header. Click it to update your name, email or delivery address. The **Add restaurant** button appears only for a signed-in manager.
3. Open a restaurant, choose a quantity and click **Add to cart**. Unavailable menu items are marked. A mixed-restaurant API error is displayed beside the item without replacing your existing cart.
4. Open **Cart** to update quantities, remove items or clear the cart. Item prices, line totals, subtotal and total come from API responses.
5. Check the delivery address and click **Place order**. The confirmation shows the saved items, prices, total, address and status. **My orders** opens your order history and saved details.
6. Refresh to restore your session and retrieve the saved data. **Sign out** removes the token from this browser tab; changing the API address also signs you out. Expired or deactivated sessions show the API's error and require signing in again.

Only the token is retained in `sessionStorage`, keyed by API address; profiles are fetched from `/customers/me`. Passwords are not persisted. The backend enforces ownership and roles on every protected request. Use a temporary `DATA_DIR` for browser demos as shown below.

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
| Create a restaurant | Sign in as `dev.patel@example.com` using its demo password, click **Add restaurant**, fill in the form and click **Create restaurant**. Customers do not see the manager button; the backend also rejects unauthorized mutations. | `POST /restaurants` |
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
| `GET` | `/cart` | Returns or creates the signed-in customer's active cart, priced from the current menu. |
| `POST` | `/cart/items` | Adds a menu item and quantity to the signed-in customer's cart. |
| `PATCH` | `/cart/items/{menu_item_id}` | Changes a cart item's quantity. |
| `DELETE` | `/cart/items/{menu_item_id}` | Removes one cart item. |
| `DELETE` | `/cart` | Empties the active cart. |
| `POST` | `/checkout` | Saves an order with item/price/address snapshots, then closes the cart (201). |
| `GET` | `/orders` | Lists only the signed-in customer's orders, newest first. |
| `GET` | `/orders/{order_id}` | Returns an owned order; missing and other customers' orders both return 404. |
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

### Concurrent requests

FastAPI runs the routes in a thread pool, so two requests can change the same data file at once. Every change is a read → modify → write of the whole file, so without protection the second save would silently overwrite the first. That could lose a cart quantity, give two records the same id, create two accounts with one email, or turn a double-clicked **Place order** into two orders.

`app/repositories/json_repository.py` prevents this with one re-entrant lock per data file:

- **Repositories** hold their file's lock for the whole of each `create` and `update`.
- **Services** wrap each check followed by a write in `transaction(...)`, so the check is still true when the write happens. Examples are duplicate email/name checks, cart changes, and checkout. Checkout locks the carts and orders files together, so a cart becomes exactly one order.
- `transaction` takes its locks in a fixed order (sorted by file path), so two transactions over the same files cannot deadlock.

`tests/test_concurrency.py` starts several threads at the same moment and checks that nothing is lost or duplicated. These locks cover one server process, which is how the app runs. Several worker processes (`uvicorn --workers N`) would need file-system locks or a database.

### Customer-to-order integration (5.2)

`app/api/dependencies.py` builds every repository and service through FastAPI's `Depends` functions. Routes request services from that module. Checkout receives the customer and menu services, cart service/repository, restaurant repository and order repository; it never opens another subsystem's JSON file. Shared dependencies are reused within a request, and file paths come from `app.core.config` when repositories are built.

To demonstrate the complete API workflow in `/docs`, use a temporary copy of all five data files:

```bash
cp -r data /tmp/m2-demo-data
DATA_DIR=/tmp/m2-demo-data SECRET_KEY=local-demo-key python -m uvicorn app.main:app
```

Use a fresh temporary directory for each demo. The key above is only for the local demo; keep the same `DATA_DIR` and key when restarting.

| Step | In `/docs` | Expected result |
| --- | --- | --- |
| Register | `POST /customers` with `{"name":"Jordan Lee","email":"jordan.lee@example.com","password":"Jordan-demo-2026","delivery_address":"1200 Academy Way, Kelowna"}` | 201 and a customer id; no password in the response. |
| Sign in | `POST /auth/login` with the same email and password, then paste `access_token` into **Authorize** | Protected requests use this account. |
| Browse | `GET /restaurants?is_open=true`, then `GET /restaurants/1/menu` | Restaurant 1 and its current menu. |
| Add to cart | `POST /cart/items` with `{"menu_item_id":1,"quantity":2}` | The backend returns total 33.98. |
| Restart with the same command | Stop and restart the server, then `GET /customers/me` and `GET /cart` | The account and filled cart survive; the token still works. |
| Check out | `POST /checkout` | 201 with a saved order; keep its id. |
| View the order | `GET /orders` and `GET /orders/{order_id}` | The created order, including item, price and address snapshots. |
| Restart again | Restart with the same command, then repeat the order requests and `GET /cart` | The order survives; the active cart is new and empty. |

The full API demo uses the order-retrieval implementation from 4.6 (#48). The web frontend workflow is covered separately by 5.4 and 5.5.

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

## Business Rules

Cross-subsystem rules are enforced by backend services, request schemas and shared authentication dependencies, never only in the frontend. Each row names the code that enforces the rule and a test that proves it. `tests/test_business_rules.py` checks that every test named here exists.

| Rule | Where it is enforced | Proved by |
| --- | --- | --- |
| A deactivated customer can't create or modify a cart | `get_current_customer` in `app/api/dependencies.py`, and `CartService.get_or_create_active_cart` through `CustomerService.get_active_customer` | `tests/test_cart.py::test_deactivated_customer_gets_403_and_no_cart`, `tests/test_cart.py::test_deactivated_customer_cannot_add_items`, `tests/test_cart.py::test_service_get_cart_rejects_deactivated_customer` |
| At most one active cart per customer | `CartService.get_or_create_active_cart` checks and creates under the cart repository transaction lock, so concurrent first requests cannot create duplicate active carts | `tests/test_cart.py::test_repeated_get_cart_never_creates_a_second_active_cart`, `tests/test_concurrency.py::test_concurrent_first_cart_requests_create_one_active_cart` |
| Cart items come from only one restaurant | `CartService.add_item` (`DifferentRestaurantError`), and again at checkout in `CheckoutService.prepare` | `tests/test_cart.py::test_item_from_a_different_restaurant_returns_409_and_changes_nothing`, `tests/test_checkout.py::test_cart_mixing_restaurants_cannot_be_checked_out` |
| Unavailable, deactivated or nonexistent items can't be added | `CartService.add_item` through `MenuService.get_orderable_item` | `tests/test_cart.py::test_unavailable_item_returns_409`, `tests/test_cart.py::test_deactivated_item_returns_409`, `tests/test_cart.py::test_unknown_item_returns_404` |
| Quantities are valid | `CartItemAdd` and `CartItemUpdate` in `app/schemas/cart.py` (whole number, 1 to 99), `CartService.add_item` (combined total), `CheckoutService.prepare` (stored quantities) | `tests/test_cart.py::test_add_invalid_quantity_returns_422`, `tests/test_cart.py::test_update_invalid_quantity_returns_422_and_changes_nothing`, `tests/test_cart.py::test_add_beyond_the_maximum_combined_quantity_returns_400`, `tests/test_checkout.py::test_invalid_stored_quantity_returns_400` |
| The backend calculates totals | `price_lines` in `app/services/pricing.py`, used by `CartService.priced` and `CheckoutService.calculate_totals`; the cart stores only ids and quantities | `tests/test_cart.py::test_totals_for_several_items_and_quantities`, `tests/test_cart.py::test_prices_are_never_stored_in_the_cart`, `tests/test_checkout.py::test_any_price_or_total_sent_by_the_client_is_ignored`, `tests/test_checkout.py::test_checkout_uses_the_shared_pricing_function` |
| Checkout revalidates menu availability and prices | `CheckoutService.revalidate_items` through `MenuService.get_orderable_item`, then `calculate_totals` with the current menu items | `tests/test_checkout.py::test_item_made_unavailable_after_adding_returns_409_naming_it`, `tests/test_checkout.py::test_item_deactivated_after_adding_returns_409_naming_it`, `tests/test_checkout.py::test_price_changed_between_adding_and_checkout_uses_the_new_price` |
| Checkout requires a valid customer | `get_current_customer`, and `CheckoutService.prepare` through `CustomerService.get_active_customer` | `tests/test_checkout.py::test_checkout_requires_sign_in`, `tests/test_checkout.py::test_deactivated_customer_gets_403` |
| Orders are only created from a valid cart | `CheckoutService.prepare`: the customer's own active, non-empty cart, an existing and open restaurant, valid quantities and orderable items; nothing is written if a check fails | `tests/test_checkout.py::test_empty_cart_returns_400`, `tests/test_checkout.py::test_missing_restaurant_returns_404`, `tests/test_checkout.py::test_closed_restaurant_returns_409`, `tests/test_checkout.py::test_another_customers_cart_is_not_used`, `tests/test_checkout.py::test_failed_checkout_does_not_create_an_order` |
| The cart is not cleared until the order is saved | `CheckoutService.checkout` holds cart/order transaction locks and calls `OrderRepository.create` first and `CartService.mark_checked_out` after; each order records its `cart_id`, so a cart becomes at most one order | `tests/test_checkout.py::test_cart_is_closed_only_after_the_order_is_saved`, `tests/test_checkout.py::test_order_save_failure_leaves_the_cart_unchanged`, `tests/test_checkout.py::test_checking_out_twice_creates_only_one_order`, `tests/test_checkout.py::test_order_saved_but_cart_not_closed_is_not_ordered_twice` |
| Relationships stay valid after restarts | Repositories assign stable ids (`max + 1`) and save atomically; API removals keep referenced records, and orders keep snapshots of names, prices and the address | `tests/test_integration.py::test_customer_cart_and_order_persist_after_server_restarts`, `tests/test_workflow.py::test_representative_data_has_valid_relationships_and_totals`, `tests/test_orders.py::test_menu_price_change_after_checkout_does_not_change_the_order` |

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

The configured directory must contain all five files: `restaurants.json`, `menu_items.json`, `customers.json`, `carts.json` and `orders.json`. This setting allows automated tests to use isolated temporary data instead of modifying the committed representative data.

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

`data/carts.json` and `data/orders.json` complete the linked demo data. Ben has a historical order and an active restaurant-2 cart totaling 15.27; logging in as Ben allows an immediate checkout demo. Chloe's past order is retained after account deactivation. Ana has no carts or orders, so she can demonstrate a fresh workflow. Every customer, restaurant, menu-item and cart reference points to an existing record; order totals reflect saved snapshots rather than current menu prices.

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
| `tests/test_workflow.py` | Five-file data consistency, the seeded checkout demo, and a new customer's registration → login → browsing → cart → checkout → order retrieval. |
| `tests/test_integration.py` | Restaurant/menu integration, error handling, API documentation, and real `uvicorn` restart tests, including a registered customer, filled cart and saved order across two restarts with the same `DATA_DIR`. |

**Isolated test data:** `tests/conftest.py` copies all five JSON files into a fresh temporary folder before **every** test and sets their paths in `app.core.config`. Feature tests start with empty carts/orders; the seeded workflow test explicitly restores the representative history in its temporary directory. Tests can create and update freely without changing the committed data or affecting each other. Restart tests use separate copies through `DATA_DIR`.

**Continuous integration:** `.github/workflows/tests.yml` runs `pytest` with GitHub Actions on Python 3.11 and 3.13 for every pull request and every push to `main`. It then checks that `data/` was not modified. A pull request should only be merged when this check is green.

## Repository Structure

```text
Food-delivery-app/
├── .github/workflows/tests.yml     # CI: runs pytest on every push and PR
├── app/
│   ├── api/
│   │   ├── dependencies.py         # get_current_customer (Bearer token -> customer)
│   │   └── routes/
│   │       ├── auth.py
│   │       ├── customers.py
│   │       ├── menu.py
│   │       └── restaurants.py
│   ├── core/
│   │   ├── config.py               # DATA_DIR, data file paths, token settings
│   │   ├── errors.py               # shared domain errors (401, 404, 409, ...)
│   │   └── security.py             # salted password hashing, login tokens
│   ├── repositories/
│   │   ├── customer_repository.py
│   │   ├── json_repository.py      # JsonRepository base: load, atomic save, next_id
│   │   ├── menu_item_repository.py
│   │   └── restaurant_repository.py
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── customer.py
│   │   ├── error.py
│   │   ├── health.py
│   │   ├── menu_item.py
│   │   └── restaurant.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── customer_service.py
│   │   ├── menu_service.py
│   │   └── restaurant_service.py
│   └── main.py                     # app, /health, error handlers, CORS
├── data/
│   ├── customers.json
│   ├── menu_items.json
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
│   ├── test_customers.py
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
