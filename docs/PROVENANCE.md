# Provenance

This file records where the work in this repository came from: who wrote each part, which pull request brought it in, which outside sources were used, and where AI tools helped. It covers Milestone 0 (`foundation-gate`), Milestone 1 (`m1-vertical-slice`) and work toward Milestone 2.

**Team:** Abdul & Friends

| Member | Student # | GitHub |
| --- | --- | --- |
| Frank Williams | 23869407 | `frankwilz` |
| Olutayo Akere | 27555010 | `tayo-ak` |
| AbdulHaady Oludare | 81742678 | `Abdul138` |
| Zay Lin Myat | 13187745 | `EuReKaA99` |

The information below comes from the repository's pull requests and git history on GitHub. Each member should check their own rows and complete the **AI assistance** column before submission.

## Milestone 0: Foundation

| PR | Work | Author | Merged by | Main files |
| --- | --- | --- | --- | --- |
| — | Initial project skeleton: FastAPI app, health endpoint, layered restaurant list (route → service → repository → JSON), representative data | AbdulHaady Oludare | — (direct commits) | `app/`, `data/restaurants.json` |
| #1 | Team agreement first version; `Restaurant` schema | AbdulHaady Oludare | Zay Lin Myat | `scrum/team-agreement.md`, `app/schemas/restaurant.py` |
| #2 | `.gitignore`, removed committed `.venv`, renamed `test/` to `tests/`, rewrote `requirements.txt`; restaurant tests with isolated temp data (`tests/conftest.py`) | Zay Lin Myat | Zay Lin Myat | `.gitignore`, `requirements.txt`, `tests/conftest.py`, `tests/test_restaurants.py` |
| #3 | README: setup and run instructions, project details | Frank Williams | Frank Williams | `README.md` |
| #4 | Health endpoint test | Zay Lin Myat (an equivalent test was also written by Olutayo Akere on branch `tayo-test`, not merged) | Zay Lin Myat | `tests/test_health.py` |
| #5 | Team agreement V1 | Zay Lin Myat | Zay Lin Myat | `scrum/team-agreement.md` |
| #6 | README: Milestone 0 test requirements | Frank Williams | AbdulHaady Oludare | `README.md` |

## Milestone 1: First vertical slice

| PR | Work | Author | Merged by | Main files |
| --- | --- | --- | --- | --- |
| #7, #10 | Menu backend: `MenuItem` models, menu data, repository, service and routes (`GET/POST /restaurants/{id}/menu`, `GET/PATCH /restaurants/{id}/menu/{item_id}`) | AbdulHaady Oludare | #7 Zay Lin Myat; #10 AbdulHaady Oludare (to fix a merge mistake, per the PR comment) | `app/schemas/menu_item.py`, `app/repositories/menu_item_repository.py`, `app/services/menu_service.py`, `app/api/routes/menu.py`, `data/menu_items.json`, `tests/test_menu.py` |
| #8 | Alternative menu backend (closed without merging, replaced by #7/#9) | Zay Lin Myat | Not merged | — |
| #9 | Menu validation (409 duplicate name, 400 empty update), atomic file saves, error responses in `/docs`, README menu section and the menu-storage design decision | Zay Lin Myat | Zay Lin Myat | `app/services/menu_service.py`, `app/repositories/menu_item_repository.py`, `app/api/routes/menu.py`, `tests/test_menu.py`, `README.md` |
| #11 | Restaurant CRUD: `GET /restaurants/{id}`, `POST /restaurants`, `PATCH /restaurants/{id}`, search and filters; `RestaurantCreate`/`RestaurantUpdate`, shared `ErrorResponse`, extra sample restaurants | Zay Lin Myat | Frank Williams | `app/api/routes/restaurants.py`, `app/services/restaurant_service.py`, `app/repositories/restaurant_repository.py`, `app/schemas/restaurant.py`, `app/schemas/error.py`, `data/restaurants.json`, `tests/test_restaurants.py`, `README.md` |
| #12 | Testing, CI and integration: GitHub Actions workflow, vertical-slice and real-restart persistence tests, JSON 500 for data-file errors, `/health` response model, README updates | Frank Williams | AbdulHaady Oludare | `.github/workflows/tests.yml`, `tests/test_integration.py`, `app/main.py`, `app/schemas/health.py`, `README.md` |
| [#14](https://github.com/frankwilz/Food-delivery-app/pull/14) | Original restaurant/menu frontend and backend CORS configuration | Olutayo Akere (`tayo-ak`) | Zay Lin Myat (`EuReKaA99`) | `frontend/index.html`, `app/main.py` |

## Milestone 2: Integrated system

The [M2 summary](milestones/M2.md), [Decision Receipt M2.3](decision-receipt-m2.md) and [planning draft](../scrum/sprint-planning-m2.md) separate completed integration evidence from work awaiting review or member confirmation. Assignments alone are not evidence of authorship.

| Work | Contribution and source | Review status |
| --- | --- | --- |
| Frontend file separation ([#27](https://github.com/frankwilz/Food-delivery-app/pull/27)) | AbdulHaady Oludare split the original frontend into HTML, CSS and JavaScript and updated the README. | Merged by Olutayo Akere (`tayo-ak`); this is retained work underlying the new frontend modules. |
| Shared FastAPI repository/service dependencies and route wiring ([PR #88](https://github.com/frankwilz/Food-delivery-app/pull/88)) | Frank Williams prepared the integration against then-current `main`, adapting Zay Lin Myat's original implementation in commit `96d7b74` (closed PR #86). Original authorship is retained with a co-author credit. | Approved and merged by Abdul138. [Review evidence](https://github.com/frankwilz/Food-delivery-app/pull/88#pullrequestreview-5962148609). One recorded approval; no second approval is claimed. |
| Representative carts/orders ([PR #89](https://github.com/frankwilz/Food-delivery-app/pull/89)) | Reused from Zay Lin Myat's preserved `96d7b74` implementation; validated against all five data files. | Approved and merged by Abdul138. [Review evidence](https://github.com/frankwilz/Food-delivery-app/pull/89#pullrequestreview-5962151427). |
| Workflow and restart verification, demo instructions and test isolation (#89) | Frank Williams, with Codex assistance, adapted the preserved workflow examples and added focused behavioral coverage for registration, cart updates, checkout, order retrieval and persistence. | Approved and merged by Abdul138; the review records 477 passing tests and unchanged committed data. |
| Order-retrieval prerequisite included through #88 | Original implementation by Zay Lin Myat in commit `94c07ab` (closed PR #85). Frank included the preserved commit for integration; this is not newly authored 5.2 code. | Abdul138's #88 review records the team's decision to land it here. |
| Frontend account/authentication ([#90](https://github.com/frankwilz/Food-delivery-app/pull/90), issue #52) | Frank Williams, with Codex assistance: account forms, shared HTTP/session client, API-scoped token persistence, stale-response protection, manager controls and 19 frontend tests. | Open for review from Abdul138, EuReKaA99 and tayo-ak; at least two approvals required. |
| Frontend cart/checkout/orders ([#91](https://github.com/frankwilz/Food-delivery-app/pull/91), issue #53) | Frank Williams, with Codex assistance: menu quantity controls, API-priced cart editing/clear, checkout, saved confirmation/history and 8 ordering tests. | Open for review; combined 27 frontend tests and 477 Python tests pass. Browser workflow/errors verified on temporary data; no merge or human feedback revision claimed. |
| API/reference and milestone documentation (#57) | Frank Williams, with Codex assistance, is preparing README/API documentation, the M2 summary, M2.3 receipt, sprint-planning draft and provenance updates. | Pending review; final submission, team practice and individual evidence remain incomplete. |

PRs #88 and #89 were merged by Abdul138 on November 18, 2026. Each has one recorded approval from Abdul138. The current round requests reviews from **Abdul138, EuReKaA99 and tayo-ak** and requires **at least two teammate approvals** before merging. Do not infer a second approval or a feedback-driven revision from a merge alone.

**AI assistance:** OpenAI Codex inspected the preserved branches, adapted dependency wiring, helped write the new frontend, tests and documentation, ran verification, tested browser flows on isolated data and prepared the review PRs. Each member must confirm their own M2 contributions, external sources, AI use and individual-requirement evidence before submission; this document does not supply those confirmations on their behalf.

### Decision evidence: shared dependency construction

Previously checkout and order routes imported repository builders from the cart router, while other routers built separate services. Repository paths had to be patched in several modules during tests. All routes now obtain services from `app/api/dependencies.py`; repositories read their configured paths when constructed and FastAPI shares dependencies within a request. Services retain business rules and repositories retain file access.

The trade-off is a central composition module that imports each subsystem. It keeps construction consistent and lets tests redirect all storage through one configuration module. Evidence is PR #88, `test_full_customer_to_order_workflow`, `test_customer_cart_and_order_persist_after_server_restarts` and the existing feature suite. The merged integration baseline had 477 passing tests, all five data files unchanged by tests, and the register → login → browse → cart → checkout → order-read workflow checked through Swagger UI on temporary data. Abdul138's linked reviews confirm the automated validation. The [M2.3 receipt](decision-receipt-m2.md) records the available evidence and the per-member confirmations still needed.

## Engineering design decision

**Menu items are stored in their own file, `data/menu_items.json`, and linked to restaurants by `restaurant_id`. They are not nested inside `restaurants.json`.**

- **Why:** the restaurant code and the menu code could be built and tested in parallel by different members, with separate repositories and no edits to the same file. Updating one menu item does not rewrite every restaurant. Item ids are unique across all restaurants, so an item can be addressed directly.
- **Trade-off:** JSON does not enforce the link. `MenuService` therefore checks that the restaurant exists before every menu operation, and `test_committed_menu_data_is_valid_and_consistent` checks that every `restaurant_id` in the data points to a real restaurant.
- **Related decisions:** new ids are `max(existing ids) + 1`, and ids are never overwritten, so ids stay stable. Every save writes a temporary file and swaps it in with `os.replace`, so a crash cannot leave a half-written JSON file.

Proposed in PR #7 and documented in PR #9 (see also `README.md`, "Design decision: menu storage").

## Historical refactor receipt: shared JSON repository and centralized error handling

This preserves the earlier pre-M2 refactor record. Its 116-test count and then-unused `ForbiddenError` describe that earlier implementation, not the current system. The M2 decision and current evidence are in [Decision Receipt M2.3](decision-receipt-m2.md).

**Decision:** shared persistence code and shared error handling each live in one place.

- **What changed:**
  - `app/repositories/json_repository.py` adds a `JsonRepository` base class with `load`, an atomic `save` (temporary file + `os.replace`) and `next_id` (`max(existing ids) + 1`). `RestaurantRepository` and `MenuItemRepository` inherit from it and keep only their own lookups and updates.
  - `app/core/errors.py` holds the shared domain errors: `BadRequestError`, `ForbiddenError`, `NotFoundError`, `ConflictError`, plus `RestaurantNotFoundError` and `EmptyUpdateError`, which both services used to define separately. Errors that belong to one feature (`DuplicateRestaurantError`, `MenuItemNotFoundError`, `DuplicateMenuItemError`) stay in their service and subclass a shared base.
  - `app/main.py` maps each base error to a status code (400, 403, 404, 409) in one table and registers one handler for it. Routes no longer catch exceptions; they just call the service.
  - The duplicate `ErrorResponse` re-export was removed from `app/schemas/menu_item.py`. Every module now imports it from `app/schemas/error.py`.
- **Why:** both repositories had the same load, save and id code, and every route repeated the same `try/except` blocks. That made it easy for one copy to drift from the others, for example a new route that forgot to turn an error into a 404. With one base class and one error table, a new feature such as orders gets atomic saves and correct status codes for free.
- **Trade-off:** the route that raises an error no longer shows its status code. To find it, you look up the error's base class in `DOMAIN_ERROR_STATUS` in `main.py`. The `responses=` lists on each route still document the possible errors in `/docs`.
- **Behaviour at that refactor:** status codes, `{"detail": "..."}` bodies and error messages were unchanged, all 116 tests passed without changes, and the generated OpenAPI schema was identical before and after. `ForbiddenError` (403) had no users then; M2 now uses it for deactivated accounts and role checks.

## External sources

| Source | Used for |
| --- | --- |
| [FastAPI documentation](https://fastapi.tiangolo.com/) | Routing, dependencies, `HTTPException`, response models, exception handlers, `TestClient` |
| [Pydantic documentation](https://docs.pydantic.dev/) | Models, `Field` constraints, `ConfigDict(extra="forbid")`, validators |
| [pytest documentation](https://docs.pytest.org/) | Fixtures, `tmp_path`, `monkeypatch`, parametrized tests |
| [GitHub Actions documentation](https://docs.github.com/actions) | `actions/checkout`, `actions/setup-python`, workflow triggers |
| Python standard library documentation | `json`, `os.replace`, `tempfile`, `subprocess` |

_Members: add any other tutorials, Stack Overflow answers, course materials or code you adapted._

## AI assistance

| Member | Tool | What it was used for | How the output was checked |
| --- | --- | --- | --- |
| Frank Williams | Claude Code (Anthropic) | Drafting PR #12: the data-storage error handler, the `/health` response model | Ran the full test suite locally (116 passed)|
| Frank Williams | OpenAI Codex | M2 integration PRs #88/#89: inspecting/reusing preserved work with attribution, dependency wiring, workflow/restart tests and documentation; preparing frontend/account/order views and the remaining milestone documentation. | Integration baseline: 477 tests passed, real-server restart and temporary-data Swagger checks; Abdul138 reviewed #88/#89. Final frontend/documentation checks and peer review remain to be recorded. |
| AbdulHaady Oludare | Claude Code (Anthropic) | Used it to create menu tests and reviewed PR's  | Reviewed by 2 other teammates Frank and Zay|
| Zay Lin Myat | Claude (Anthropic) | Used to draft and review Pull Request #11,Add restaurant get, create, update and search/filter | Run Test locally on local computer|
| Olutayo Akere | _To be completed_ | | |
## Verification

- Historical M1 validation recorded 116 passing tests; this is not the current suite count.
- The merged #88/#89 integration baseline recorded 477 passing tests and unchanged data in the reviews linked above. Rerun and record final counts after the remaining frontend/documentation changes.
- GitHub Actions is configured to test Python 3.11 and 3.13 on pushes and PRs. Inspect the actual [Actions results](https://github.com/frankwilz/Food-delivery-app/actions) for the final commit rather than assuming a pending run has passed.
- Tests use isolated temporary copies of the data files. CI fails if any test modifies `data/`.
- Final tag, full SHA, team demo practice and Canvas submission remain pending in the [M2 summary](milestones/M2.md).
