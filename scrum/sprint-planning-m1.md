# Sprint Planning Milestone 1

## Sprint Information

- **Sprint / Milestone:** Milestone 1 — First Vertical Slice (tag `m1-vertical-slice`)
- **Sprint dates:** _YYYY-MM-DD_ to 2026-10-16
- **Planning meeting date:** _YYYY-MM-DD_
- **Facilitator:** _Name_

### Team Members

- [ ] Frank Williams
- [ ] Olutayo Akere
- [ ] AbdulHaady Oludare
- [ ] Zay Lin Myat

---

## 1. Sprint Goal

> What should the team have working by the end of this sprint?

**Sprint Goal:**

Deliver the first complete vertical slice of the backend: a customer can list, search and filter restaurants, open a restaurant's details, and view its menu and menu items, and a restaurant manager can create and update restaurants and menu items. Every endpoint follows route → service → repository → JSON, is documented in `/docs`, and is covered by automated tests that run in GitHub Actions. A basic frontend calls the API to show the same flow.

---

## 2. Sprint Backlog

Select the user stories that the team commits to working on during this sprint.

| User Story | Description | Priority | Primary Owner | Dependencies |
|---|---|---|---|---|
| #_ US1 Restaurant management | As a restaurant manager, I can view, create and update restaurants, so the list stays accurate | High | Zay Lin Myat | JSON storage design decision |
| #_ US2 Restaurant search | As a customer, I can search and filter restaurants by name, cuisine, open status and rating, so I can find somewhere to order from | High | Zay Lin Myat | US1 |
| #_ US3 Menu browsing and management | As a customer, I can view a restaurant's menu and individual items; as a manager, I can add and update menu items | High | AbdulHaady Oludare | US1, storage design decision |
| #_ US4 Frontend | As a customer, I can use a web page to see restaurants, select one, see its details and menu, and create or update a restaurant | High | Olutayo Akere | US1, US2, US3 endpoints |
| #_ US5 CI, integration and persistence | As a team, every push and PR is tested automatically, the full flow is tested end to end, and data survives a restart | High | Frank Williams | US1, US3 |
| #_ US6 Documentation and submission | README, `docs/PROVENANCE.md`, scrum notes and the `m1-vertical-slice` tag are complete | Medium | Frank Williams | All stories |

> **Important:** Primary ownership means that the student is responsible for coordinating the work. It does not mean that the student works alone or that other team members cannot contribute.

---

## 3. Task Decomposition

Break larger user stories into smaller tasks that can be implemented, reviewed, and tested.

### User Story #_ — US1 Restaurant management

- [x] `GET /restaurants/{id}` with 404 for unknown ids (PR #11)
- [x] `POST /restaurants` with server-assigned id (`max + 1`) and 409 for duplicate name + address (PR #11)
- [x] `PATCH /restaurants/{id}` with 400 for an empty body and 404/409/422 (PR #11)
- [x] `RestaurantCreate` / `RestaurantUpdate` request models; `Restaurant` response model; shared `ErrorResponse` (PR #11)
- [x] Repository `get_by_id`, `create`, `update` with atomic saves (PR #11)
- [x] Tests (PR #11)
- [x] Documentation / API updates: route descriptions, README endpoint table (PR #11)

### User Story #_ — US2 Restaurant search

- [x] `search`, `cuisine`, `is_open`, `min_rating` query parameters on `GET /restaurants`, combinable (PR #11)
- [x] Filtering logic in `RestaurantService`, not in the route (PR #11)
- [x] Extra sample restaurants for demos (PR #11)
- [x] Tests, including 422 for invalid filter values (PR #11)
- [x] Documentation / API updates (PR #11)

### User Story #_ — US3 Menu browsing and management

- [x] `MenuItem`, `MenuItemCreate`, `MenuItemUpdate` models (PR #7/#10)
- [x] `data/menu_items.json` linked to restaurants by `restaurant_id` (PR #7/#10)
- [x] Menu repository, service and routes: `GET/POST /restaurants/{id}/menu`, `GET/PATCH /restaurants/{id}/menu/{item_id}` (PR #7/#10)
- [x] 409 duplicate item name, 400 empty update, atomic saves (PR #9)
- [x] Tests (PR #7/#9/#10)
- [x] Documentation / API updates, including the menu-storage design decision (PR #9)

### User Story #_ — US4 Frontend

- [x] Restaurant list page that fetches `GET /restaurants`, with search box and cuisine chips (PR #14)
- [x] Select a restaurant to show its details (`GET /restaurants/{id}`) and menu grouped by category (`GET /restaurants/{id}/menu`) (PR #14)
- [x] Create restaurant form (`POST /restaurants`) showing API errors such as 409 (PR #14)
- [x] CORS in `app/main.py` so the page on port 5500 can call the API (PR #14)
- [x] Test the main user workflow: list → search → details → menu → create, unknown restaurant (404) and duplicate (409), checked in Chrome against the running API
- [x] README: how to run the frontend and showcase the vertical slice

### User Story #_ — US5 CI, integration and persistence

- [x] GitHub Actions workflow running pytest on every push and PR, Python 3.11 and 3.13 (PR #12)
- [x] Vertical-slice integration test through every layer (PR #12)
- [x] Restart test: real `uvicorn` with `DATA_DIR`, write, restart, read back (PR #12)
- [x] JSON 500 for data-file errors; `/health` response model (PR #12)
- [x] Tests (PR #12)
- [x] Documentation / API updates: README tests and error-handling sections (PR #12)

### User Story #_ — US6 Documentation and submission

- [x] `docs/PROVENANCE.md` (PR #13); README provenance section removed (PR #15)
- [x] Sprint planning notes under `scrum/`
- [ ] Each member completes their provenance rows (Zay: PR #16)
- [ ] GitHub Issues and Project board created and linked
- [ ] Tag `m1-vertical-slice`; Canvas PDF with repo, board, tag URL, SHA and agreed contribution %

---

## 4. Dependencies and Integration

Identify work that depends on another team member, subsystem, or component.

| Dependency | Related User Stories | Who is Responsible? | Planned Resolution |
|---|---|---|---|
| JSON storage design (one file or two) affects both restaurant and menu code | US1, US3 | Zay Lin Myat, AbdulHaady Oludare | Two files linked by `restaurant_id`, decided before coding and documented in the README and `docs/PROVENANCE.md` |
| Menu endpoints need restaurants to exist | US3 | AbdulHaady Oludare | `MenuService` checks the restaurant exists before every menu operation (404 otherwise) |
| Frontend needs working endpoints and cross-origin access | US4 | Olutayo Akere | Built against the merged endpoints documented in `/docs`; CORS allows the page served on port 5500 (PR #14) |
| Integration tests need restaurant and menu features merged | US5 | Frank Williams | Written after PRs #10 and #11 were merged into `main` |

### Integration Plan

Each story is built on its own feature branch and merged into `main` through a pull request reviewed by another member. GitHub Actions runs the full test suite on every push and PR, so a broken merge is visible immediately. Restaurant and menu backends were developed in parallel against separate JSON files, then integrated through `tests/test_integration.py`, which runs the full flow (create restaurant → search → update → add menu item → update item) and a real server restart. The frontend (`frontend/index.html`, PR #14) connects to the merged API on `main` and was checked end to end in a browser: list → search → details → menu → create.

---

## 5. Risks and Potential Blockers

Identify anything that could prevent the team from achieving the sprint goal.

| Risk / Blocker | Impact | Planned Action | Owner |
|---|---|---|---|
| Frontend blocked waiting for endpoints | Frontend not ready for the demo | Start against the documented API shape; backend list/detail endpoints first | Olutayo Akere |
| Restaurant and menu work editing the same files | Merge conflicts | Separate JSON files, repositories and services | Zay Lin Myat, AbdulHaady Oludare |
| Tests modifying committed data | Demo data corrupted | `conftest.py` copies data to a temp folder for every test; CI fails if `data/` changes | Frank Williams |
| Collaboration evidence missing (issues, reviews, board) | Lost marks on GitHub collaboration | Create issues with acceptance criteria and labels, a Project board, and request teammate reviews on every PR | Everyone |
| Late merges after tagging | Assessed version missing work | Tag `m1-vertical-slice` only after the final merge; re-tag before the deadline if needed | Frank Williams |

---

## 6. Definition of Done

For work to be considered **DONE**, the team agrees that it must satisfy the following:

- [ ] Requirements/acceptance criteria are satisfied.
- [ ] Business logic is implemented in the appropriate service layer.
- [ ] Persistence is handled through the repository layer.
- [ ] Appropriate unit tests are included.
- [ ] Appropriate integration/API tests are included.
- [ ] Tests pass.
- [ ] Code has been reviewed by at least one teammate.
- [ ] Review feedback has been addressed.
- [ ] Documentation has been updated where necessary.
- [ ] The change is integrated into the team's working version.
- [ ] No known critical defects remain.

---

## 7. Sprint Commitment

Before ending the meeting, each team member should confirm their understanding of the sprint plan.

| Team Member | Initial Responsibilities | Confirmed |
|---|---|---|
| Zay Lin Myat | Restaurant backend: get, create, update, search/filter, tests (US1, US2) | ☐ |
| AbdulHaady Oludare | Menu backend: models, data, repository, service, endpoints, tests (US3) | ☐ |
| Olutayo Akere | Frontend (US4) | ☐ |
| Frank Williams | Testing, CI and integration; README, provenance and submission (US5, US6) | ☐ |

---

## Meeting Notes

- Storage decision: menu items are kept in `data/menu_items.json`, linked by `restaurant_id`, instead of being nested in `restaurants.json`. This lets restaurant and menu work proceed in parallel. The trade-off and its safeguards are in `docs/PROVENANCE.md`.
- ID strategy: new ids are `max(existing ids) + 1` and are never overwritten.
- Error contract: every error returns `{"detail": "..."}`; 400 empty update, 404 unknown id, 409 duplicate, 422 invalid input, 500 data-file error.
- _Add any other decisions or questions from the meeting._
