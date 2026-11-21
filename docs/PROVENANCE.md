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
| #14 | Frontend: restaurant list, details, menu view, create/update form; CORS for the frontend's origin (US4, #22) | Olutayo Akere | Zay Lin Myat | `frontend/index.html`, `app/main.py` |

## Milestone 2: Evidence snapshot — November 20, 2026

This register describes current `main` at [`a840197`](https://github.com/frankwilz/Food-delivery-app/commit/a840197ae8a736a36883d7b56c0903a19637ca3f) and separately identifies work awaiting review. Closed pull requests and preserved branch files are not counted as merged work. See [M2 summary](milestones/M2.md), [Decision Receipt M2.3](decision-receipt-m2.md) and [sprint notes](../scrum/sprint-planning-m2.md).

| Work | Contribution and source | Landed / review evidence |
| --- | --- | --- |
| Order retrieval and shared dependency construction | Zay Lin Myat authored preserved commits `94c07ab` (#85) and `96d7b74` (#86). Frank Williams adapted the implementation to the integrated branch with original-source/co-author credit. | Included in merged [#88](https://github.com/frankwilz/Food-delivery-app/pull/88). The original #85/#86 were closed; their source was preserved in the landed integration. Abdul138's [#88 review](https://github.com/frankwilz/Food-delivery-app/pull/88#pullrequestreview-5962148609) records an approval. |
| Representative data, full workflow, restart verification and isolation | Frank Williams adapted preserved workflow examples with Codex assistance; Zay's original integration/data source remains credited. | Merged [#89](https://github.com/frankwilz/Food-delivery-app/pull/89), approved by Abdul138 in [this review](https://github.com/frankwilz/Food-delivery-app/pull/89#pullrequestreview-5962151427). |
| Frontend accounts and shared HTTP/session client | Frank Williams, with Codex assistance: register, sign in/out, account updates, API-scoped session storage, server-validated profiles and late-response guards. | Merged [#90](https://github.com/frankwilz/Food-delivery-app/pull/90), commit `df1fd7e`; 19 HTTP/session tests are on main. |
| Manager menu controls | AbdulHaady Oludare: manager-only menu creation and restaurant-button placement, building on his frontend file separation in #27 and backend role enforcement in #80. | Merged [#94](https://github.com/frankwilz/Food-delivery-app/pull/94), commits `c83d09b` and `80cde94`. Ordering restoration retains this UI. |
| Concurrent JSON operations | Olutayo Akere: one re-entrant lock per data file and consistent multi-file transaction locking, plus 12 concurrency tests. | Merged [#95](https://github.com/frankwilz/Food-delivery-app/pull/95), commit `d52fda6`, merged by Zay Lin Myat. No recorded review comments on #95 establish a feedback-driven revision. |
| Frontend polish | Olutayo Akere: unavailable-item indicators, removal of manual restaurant rating and redirect of signed-in users away from authentication forms. | Merged [#99](https://github.com/frankwilz/Food-delivery-app/pull/99), commit `e2fedca`; retained in ordering restoration. |
| Tayo's contribution/AI record | Olutayo Akere authored his provenance rows and concurrency decision evidence. | Merged [#100](https://github.com/frankwilz/Food-delivery-app/pull/100), commit `19f35f9`; retained and reconciled here. |
| Stored-data rule audit and repair | Zay Lin Myat authored preserved source [`1b2d1ea`](https://github.com/frankwilz/Food-delivery-app/commit/1b2d1eac4c913daa2f6f0cde3aaf1dc741f710aa). Frank Williams restored/adapted it against current main, retaining Zay's authorship in `cf85894`. Zay also independently prepared parallel [#102](https://github.com/frankwilz/Food-delivery-app/pull/102), credited separately. | Merged [#104](https://github.com/frankwilz/Food-delivery-app/pull/104), `cf85894`, current main `a840197`. Zay's preserved #51 source actually landed; the separate #102 commits are not claimed as merged. |
| Cart peer-review follow-up | Zay implements Abdul's verified #74 feedback that refused cart PATCH/DELETE requests must not write data. | [#101](https://github.com/frankwilz/Food-delivery-app/pull/101), `dd09814`, follows [this review](https://github.com/frankwilz/Food-delivery-app/pull/74#pullrequestreview-5939365558); **merged into current main**. |
| Additional Zay cross-subsystem scenario | Zay authored `test_price_changes_before_and_after_checkout`: menu prices → cart repricing → checkout → fixed order snapshot, original source `b839f18`. | Merged [#103](https://github.com/frankwilz/Food-delivery-app/pull/103). Zay's original `b839f18` is preserved; Frank strengthened the final menu-mutation assertion in `639a40a` with Codex assistance. |
| Frontend ordering | Frank Williams, with Codex assistance: menu quantities, API-priced cart edits, checkout, confirmation and private order views; 8 ordering tests. | Original [#91](https://github.com/frankwilz/Food-delivery-app/pull/91) did not land on the earlier main. Restored against current main and merged in [#107](https://github.com/frankwilz/Food-delivery-app/pull/107), source `e5d84d2`/`2ca4f43`; 27 combined Node tests pass. |
| API and milestone documentation | Frank Williams, with Codex assistance, prepared endpoint descriptions, milestone summary, decision receipt and sprint notes. | Original #92/#93 did not land on the earlier main. API/reference restoration is merged in [#106](https://github.com/frankwilz/Food-delivery-app/pull/106), `165fd9a`. This provenance/milestone/receipt/sprint restoration remains a review draft awaiting its own approved merge. |

PRs #88/#89 have one recorded Abdul138 approval each. They are historical evidence, not evidence of two approvals or a substantive feedback-driven revision. This completion round requests other teammates from **Abdul138, EuReKaA99 and tayo-ak**, excluding the PR author, and requires **at least two teammate approvals**, addressed feedback and green CI before merge. Closed #96 was replaced by merged Frank-authored #105, retaining Tayo's history. Frank-authored completion PRs request all three eligible teammates; this does not assert that every historical merge obtained two approvals. No such approvals are claimed here. The review audit found no recorded reviews for #95–#100; merge events alone do not demonstrate peer-review feedback.

### Olutayo Akere: retained testing work and status

| PR / branch | Authored work | Current evidence boundary |
| --- | --- | --- |
| [#97](https://github.com/frankwilz/Food-delivery-app/pull/97), `tayo-5.6-service-tests` | `tests/test_services.py`: direct customer, cart and checkout service tests. | Closed without merge. Existing feature tests on main already contain direct service coverage; these additional files are not on main. |
| [#98](https://github.com/frankwilz/Food-delivery-app/pull/98), `tayo-5.7-repo-api-tests` | `tests/test_repositories.py` and `tests/test_api_status_codes.py`: isolated persistence and API/status tests. | Closed without merge. Existing main tests provide repository and API evidence; this branch's additional files are not on main. |
| [#96](https://github.com/frankwilz/Food-delivery-app/pull/96), `tayo-5.8-integration-tests` | Demo scenarios, Tayo's full cross-subsystem test, named regressions for #95, restart relationships and a stricter CI data check. | Closed without merge; GitHub would not reopen the recreated head. Merged replacement [#105](https://github.com/frankwilz/Food-delivery-app/pull/105) retains Tayo's original history and refreshed tests (`aa77849`); those files are now on main. |

Tayo's branch-specific full-flow test is `test_new_restaurant_menu_changes_flow_through_cart_into_a_fixed_order` in `tests/test_demo_scenarios.py` (Auth → Restaurants → Menu → Customers → Cart → Checkout → Orders), originally committed in `b86dbeb`. It is now part of main through #105, alongside his already-merged concurrent-checkout test. His already-merged cross-subsystem test is recorded next.

### Each member's cross-subsystem test on main

The authors below were verified by `git blame` at ancestor main `4ae2824`; these tests remain part of current main. Attribution is to the authored test, not issue assignment or the person who later merged it.

| Member | Authored test and scope | Source commit |
| --- | --- | --- |
| Frank Williams | [`tests/test_workflow.py::test_full_customer_to_order_workflow`](https://github.com/frankwilz/Food-delivery-app/blob/4ae2824c8c958d504fa6ccd9988644d2f2667255/tests/test_workflow.py#L104): register/login → browse → cart → checkout → order retrieval. The integration work retains Zay's preserved-source attribution. | `4d1907f` |
| AbdulHaady Oludare | [`tests/test_checkout.py::test_price_change_after_adding_is_used_at_checkout`](https://github.com/frankwilz/Food-delivery-app/blob/4ae2824c8c958d504fa6ccd9988644d2f2667255/tests/test_checkout.py#L272): menu price change → existing cart → checkout. | `a81e51c` |
| Zay Lin Myat | [`tests/test_checkout.py::test_order_snapshot_does_not_change_with_the_menu_or_profile`](https://github.com/frankwilz/Food-delivery-app/blob/4ae2824c8c958d504fa6ccd9988644d2f2667255/tests/test_checkout.py#L462): menu/profile changes leave saved order snapshots unchanged. | `c3bc4dc` |
| Olutayo Akere | [`tests/test_concurrency.py::test_double_clicked_place_order_over_http_creates_one_order`](https://github.com/frankwilz/Food-delivery-app/blob/4ae2824c8c958d504fa6ccd9988644d2f2667255/tests/test_concurrency.py#L238): cart → concurrent checkout → one stored order. | `d52fda6` |

Frank, Abdul and Tayo's substantive peer-feedback/revision links remain **PENDING**. Zay's verified Abdul feedback on #74 is addressed in merged follow-up #101 (`dd09814`). See the per-member register in the [Decision Receipt](decision-receipt-m2.md). Authored tests, approvals and merge events do not replace that evidence.

### Decision Receipt: per-file locks for concurrent requests (Olutayo Akere)

**Decision:** every JSON data file has one lock, and every check followed by a write runs while holding it.

- **Before:** FastAPI runs routes in a thread pool. Two requests could read the same old JSON file, then overwrite each other's update. This could lose quantities, duplicate IDs/emails or turn a double-clicked checkout into two orders.
- **After:** `app/repositories/json_repository.py` supplies one shared re-entrant lock per file. Repository `create`/`update` operations hold it throughout read-modify-write. Services use `transaction(...)` for checks plus writes; checkout locks carts and orders together. Locks are acquired in sorted file-path order to avoid deadlock.
- **Alternative considered:** SQLite transactions. Tayo rejected this for the milestone's required JSON storage; repositories would permit a later migration.
- **Benefit and cost:** requests in one server process cannot interleave these protected operations; changes to the same file wait for each other. Multiple worker processes need file-system locks or a database. Checkout's two file writes are still not one crash-atomic storage transaction.
- **Landed evidence:** [#95](https://github.com/frankwilz/Food-delivery-app/pull/95), `d52fda6`, and the 12 tests in `tests/test_concurrency.py`, including `test_concurrent_checkouts_of_one_cart_create_one_order`.
- **Contributor-reported experiment:** Tayo's #100 provenance reports that disabling the locks makes 10 of 12 concurrency tests and both branch regression tests fail. This preserves his report; the regression files are now merged through replacement #105 and their runtime negative-control check is recorded below.
- **Peer-review-driven revision:** **PENDING**; #95 was merged by Zay, but no feedback/revision link is recorded.

## Engineering design decision

**Menu items are stored in their own file, `data/menu_items.json`, and linked to restaurants by `restaurant_id`. They are not nested inside `restaurants.json`.**

- **Why:** the restaurant code and the menu code could be built and tested in parallel by different members, with separate repositories and no edits to the same file. Updating one menu item does not rewrite every restaurant. Item ids are unique across all restaurants, so an item can be addressed directly.
- **Trade-off:** JSON does not enforce the link. `MenuService` therefore checks that the restaurant exists before every menu operation, and `test_committed_menu_data_is_valid_and_consistent` checks that every `restaurant_id` in the data points to a real restaurant.
- **Related decisions:** new ids are `max(existing ids) + 1`, and ids are never overwritten, so ids stay stable. Every save writes a temporary file and swaps it in with `os.replace`, so a crash cannot leave a half-written JSON file.

Proposed in PR #7 and documented in PR #9 (see also `README.md`, "Design decision: menu storage").

## Earlier decision: shared JSON repository and centralized error handling

**Decision:** shared persistence code and shared error handling each live in one place.

- **What changed:**
  - `app/repositories/json_repository.py` adds a `JsonRepository` base class with `load`, an atomic `save` (temporary file + `os.replace`) and `next_id` (`max(existing ids) + 1`). `RestaurantRepository` and `MenuItemRepository` inherit from it and keep only their own lookups and updates.
  - `app/core/errors.py` holds the shared domain errors: `BadRequestError`, `ForbiddenError`, `NotFoundError`, `ConflictError`, plus `RestaurantNotFoundError` and `EmptyUpdateError`, which both services used to define separately. Errors that belong to one feature (`DuplicateRestaurantError`, `MenuItemNotFoundError`, `DuplicateMenuItemError`) stay in their service and subclass a shared base.
  - `app/main.py` maps each base error to a status code (400, 403, 404, 409) in one table and registers one handler for it. Routes no longer catch exceptions; they just call the service.
  - The duplicate `ErrorResponse` re-export was removed from `app/schemas/menu_item.py`. Every module now imports it from `app/schemas/error.py`.
- **Why:** both repositories had the same load, save and id code, and every route repeated the same `try/except` blocks. That made it easy for one copy to drift from the others, for example a new route that forgot to turn an error into a 404. With one base class and one error table, a new feature such as orders gets atomic saves and correct status codes for free.
- **Trade-off:** the route that raises an error no longer shows its status code. To find it, you look up the error's base class in `DOMAIN_ERROR_STATUS` in `main.py`. The `responses=` lists on each route still document the possible errors in `/docs`.
- **Historical validation at the time of that refactor:** behaviour was unchanged. Status codes, `{"detail": "..."}` bodies and error messages are the same, all 116 tests pass without changes, and the generated OpenAPI schema is identical before and after. `ForbiddenError` (403) was reserved for permission checks at that stage; M2 authentication and role checks now use it.

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
| AbdulHaady Oludare | Claude Code (Anthropic) | Used it to create menu tests and reviewed PR's  | Reviewed by 2 other teammates Frank and Zay|
| Zay Lin Myat | Claude (Anthropic) | Used to draft and review Pull Request #11,Add restaurant get, create, update and search/filter | Run Test locally on local computer|
| Olutayo Akere | Claude Code (Anthropic) | Suggested design improvements; implemented the per-file locks in PR #95 and their tests; wrote the 5.6–5.8 tests and frontend fixes on the branches listed under "Olutayo Akere: Milestone 2" | Ran the full test suite locally; disabled the locks to confirm the concurrency and regression tests fail without them; checked the frontend changes in a browser on a copy of the data. These are contributor-reported checks; teammate feedback/revision links remain PENDING. |
| Frank Williams | OpenAI Codex | Adapted preserved integration work with source credit; implemented account/session and ordering UI/tests; restored missing milestone documentation and audited issue/PR evidence | Historical integration checks: 477 Python tests. Current main a840197: 538 Python / 27 Node tests and fresh browser workflow verified with unchanged committed data. The remaining documentation review/merge, three missing member feedback links and final release references remain required. |

## Verification and release evidence

- Current main [`a840197`](https://github.com/frankwilz/Food-delivery-app/commit/a840197ae8a736a36883d7b56c0903a19637ca3f): **538 Python / 27 Node tests passed**, including both real-server restart checks; all five committed JSON data files stayed unchanged. This includes merged #101/#103/#104/#105/#106/#107. It is the current code snapshot, not the final post-documentation release tag.
- The two regression tests linked to #95 also failed as expected in the runtime experiment with locks disabled, establishing that they exercise the actual duplicate-order/lost-quantity bugs.
- Fresh browser verification on the combined code covered manager menu creation (new restaurant rating starts at zero), unavailable-item indicators, customer registration, cart refresh/update/remove, mixed-restaurant 409, checkout/order total 50.97, order-history refresh, signed-in auth-page redirects, account view and logout. Temporary data was used; this verifies behavior, not unrecorded team attendance.
- [GitHub Actions](https://github.com/frankwilz/Food-delivery-app/actions) is configured for Python 3.11/3.13, Node 22 and unchanged committed data. All three checks on current main are green. Confirm the remaining documentation PR checks and relevant final checks on the last merged commit before tagging.
- The checklist on [issue #57](https://github.com/frankwilz/Food-delivery-app/issues/57) marks demo practice and Canvas submission complete. This records the issue's state; no submission receipt or team rehearsal was independently inspected here.
- The remaining milestone-documentation PR still needs **at least two eligible teammate approvals**, addressed feedback, green checks and merge. Frank, Abdul and Tayo's peer-feedback/revision links remain **PENDING**; Zay's verified #74 → merged #101 pair is recorded in the receipt.
- `m2-integrated-system` and its full final SHA remain **PENDING**. Create the tag after the documentation merge and final verification, then confirm/update Canvas to reference that exact final tag/SHA. #57 is not technically closed by this review draft.
