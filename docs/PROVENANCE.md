# Provenance

This file records where the work in this repository came from: who wrote each part, which pull request brought it in, which outside sources were used, and where AI tools helped. It covers Milestone 0 (`foundation-gate`) and Milestone 1 (`m1-vertical-slice`).

**Team:** Abdul & Friends

| Member | Student # | GitHub |
| --- | --- | --- |
| Frank Williams | 23869407 | `frankwilz` |
| Olutayo Akere | 27555010 | — |
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
| — | Frontend: restaurant list, details, menu view, create/update form | _To be completed_ | — | _To be completed_ |

## Engineering design decision

**Menu items are stored in their own file, `data/menu_items.json`, and linked to restaurants by `restaurant_id`. They are not nested inside `restaurants.json`.**

- **Why:** the restaurant code and the menu code could be built and tested in parallel by different members, with separate repositories and no edits to the same file. Updating one menu item does not rewrite every restaurant. Item ids are unique across all restaurants, so an item can be addressed directly.
- **Trade-off:** JSON does not enforce the link. `MenuService` therefore checks that the restaurant exists before every menu operation, and `test_committed_menu_data_is_valid_and_consistent` checks that every `restaurant_id` in the data points to a real restaurant.
- **Related decisions:** new ids are `max(existing ids) + 1`, and ids are never overwritten, so ids stay stable. Every save writes a temporary file and swaps it in with `os.replace`, so a crash cannot leave a half-written JSON file.

Proposed in PR #7 and documented in PR #9 (see also `README.md`, "Design decision: menu storage").

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
| AbdulHaady Oludare | _To be completed_ | | |
| Zay Lin Myat | _To be completed_ | | |
| Olutayo Akere | _To be completed_ | | |
## Verification

- `python -m pytest -q` passes locally: 116 tests.
- GitHub Actions passes on Python 3.11 and 3.13 for every push and pull request: https://github.com/frankwilz/Food-delivery-app/actions
- Tests use isolated temporary copies of the data files. CI fails if any test modifies `data/`.
