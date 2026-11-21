# Decision Receipt M2.3: Shared dependency construction

**Updated:** November 20, 2026. **Status:** shared dependency construction is implemented in merged PRs [#88](https://github.com/frankwilz/Food-delivery-app/pull/88) and [#89](https://github.com/frankwilz/Food-delivery-app/pull/89); per-member improvement evidence is recorded below; every missing peer-feedback/revision link remains **PENDING**. Current main snapshot: `a840197` (code, tests and API/reference changes through #107/#101/#103 are merged).

## Problem

Customer, restaurant and menu routes each constructed services independently. Cart routes also exposed repository/service builders that checkout and order routes imported. Tests had to patch data paths in several route modules. A storage-path or construction change could therefore affect one part of the workflow while leaving another part on different dependencies.

## Decision and alternatives

Construct repositories and services in `app/api/dependencies.py` using FastAPI `Depends`. Routes request their service from this module. Repositories obtain file paths from `app/core/config.py` when constructed; business rules stay in services and JSON access stays in repositories.

| Option | Consequence |
| --- | --- |
| Keep builders in each router | Fewer imports in a central file, but repeated construction and path handling can drift. Checkout continues depending on a cart HTTP module. |
| Share ordinary builder functions through one router | Reduces some duplication, but couples subsystems to that router and does not expose the full dependency graph to FastAPI overrides/request caching. |
| **Shared FastAPI providers** | One composition point, explicit service/repository dependencies, request-level reuse and a consistent place to override dependencies or storage paths in tests. |

The selected option reuses FastAPI's existing dependency mechanism and needs no additional framework. Services remain ordinary Python classes that can be tested directly without HTTP.

## Implementation and consequences

- Each of the five repositories has a shared provider.
- Customer, auth, restaurant, menu, cart, checkout and order services declare the repositories/other services they need through providers.
- Every router imports providers instead of constructing repositories or importing builders from another router.
- Tests redirect the five configured paths in one fixture. A separate seeded-demo fixture opts into committed cart/order history; ordinary feature tests start with empty history.
- The trade-off is a central module that imports all subsystems and must be maintained as a new subsystem is added. The providers also describe the runtime object graph, so direct service tests should construct service objects explicitly rather than call provider functions with unresolved `Depends` defaults.

This decision standardizes construction; it does not add JSON transactions, concurrency control or new business rules. Those concerns remain separate from the provider refactor.

## Source, tests and review evidence

Frank Williams adapted the preserved implementation by Zay Lin Myat in commit [`96d7b74`](https://github.com/frankwilz/Food-delivery-app/commit/96d7b74ba17873ca61f63c5d84bcf799989fe114), originally prepared in closed PR #86. Original authorship is credited in the integration commits. The preserved order-retrieval implementation (`94c07ab`, closed PR #85) was included as a prerequisite; Abdul138's #88 review records the team's decision to land it with this work.

| Evidence | What it establishes |
| --- | --- |
| [PR #88](https://github.com/frankwilz/Food-delivery-app/pull/88) | Shared providers and route wiring; the relevant architectural change. |
| [PR #89](https://github.com/frankwilz/Food-delivery-app/pull/89) | Representative data, workflow/restart verification, test isolation and demo documentation. |
| `tests/test_workflow.py::test_full_customer_to_order_workflow` | A fresh account can register, log in, browse, fill/update a cart, check out and retrieve its saved order through the integrated API. |
| `tests/test_integration.py::test_customer_cart_and_order_persist_after_server_restarts` | A new customer, filled cart and saved order survive separate server processes using the same data directory. |
| `tests/test_workflow.py::test_representative_data_has_valid_relationships_and_totals` | Representative records in all five files have valid identifiers, relationships and totals. |
| [Abdul138's #88 review](https://github.com/frankwilz/Food-delivery-app/pull/88#pullrequestreview-5962148609) | Approval after testing the combined work against then-current main: 477 tests passed, both restart checks included, committed data unchanged. |
| [Abdul138's #89 review](https://github.com/frankwilz/Food-delivery-app/pull/89#pullrequestreview-5962151427) | Approval after testing it on top of #88 and main. |

Both PRs were merged by Abdul138. Each has one recorded approval from Abdul138 in the evidence above; this document does not claim a second approval or a feedback-driven revision. The current round requests reviews from other teammates among **Abdul138, EuReKaA99 and tayo-ak**, excluding the PR author, and requires **at least two teammate approvals** before a PR is merged.

## Each member's architectural improvement

The entries below identify implementation and test evidence. Each member must confirm the explanation of their own work. A merge or approval alone does not prove that their substantive PR improved because of peer feedback.

| Member | Improvement, reason and trade-off | Implementation / test evidence |
| --- | --- | --- |
| Frank Williams | Shared frontend HTTP/session client separates token storage/headers from views. It validates the server's profile and rejects late responses after logout or server/account changes. Views must handle superseded requests and subscribe to session changes. | Merged [#90](https://github.com/frankwilz/Food-delivery-app/pull/90), `df1fd7e`, `frontend/api.mjs`, 19 Node HTTP/session tests. Merged #107 reuses this boundary and adds 8 behavior tests. |
| Zay Lin Myat | Central service/repository construction removes duplicate router builders and gives tests one storage configuration boundary. The central composition module imports all subsystems and needs maintenance as they grow. Zay authored preserved source `96d7b74`; Frank adapted it with attribution. Zay also authored the preserved #51 rule-audit source `1b2d1ea`, restored/adapted by Frank with authorship retained as `cf85894` in merged #104. | Merged [#88](https://github.com/frankwilz/Food-delivery-app/pull/88), [original source](https://github.com/frankwilz/Food-delivery-app/commit/96d7b74ba17873ca61f63c5d84bcf799989fe114); workflow/restart and dependency-wiring tests through #88/#89. Abdul's linked reviews validate those PRs; no feedback-driven revision is inferred. |
| AbdulHaady Oludare | Shared `require_role`/`require_manager` dependencies build role checks on the authenticated-customer boundary. Restaurant/menu mutations consistently enforce 401/403 before reaching services. Route declarations must still apply the correct dependency. | Merged [#80](https://github.com/frankwilz/Food-delivery-app/pull/80), `ff8598a`, `app/api/dependencies.py`, `tests/test_authorization.py`. His merged [#94](https://github.com/frankwilz/Food-delivery-app/pull/94) manager UI retains backend enforcement. |
| Olutayo Akere | Per-file shared re-entrant locks and sorted multi-file `transaction(...)` calls serialize read/check/write operations. Same-file writers wait; protection covers one server process and does not make two separate file replacements crash-atomic. | Merged [#95](https://github.com/frankwilz/Food-delivery-app/pull/95), `d52fda6`, `tests/test_concurrency.py` (12 tests). The bug-linked regression additions are merged in replacement [#105](https://github.com/frankwilz/Food-delivery-app/pull/105). Full decision/alternative and contributor-reported lock-disable experiment are retained in [PROVENANCE](PROVENANCE.md). |

### Frank's frontend session boundary

The client in `frontend/api.mjs` owns API-scoped token storage and error handling. It obtains the customer from `/customers/me`, attaches the current bearer token to protected requests and uses a session revision to reject responses from a superseded login, logout or API address. The account module renders forms independently. The merged ordering module reuses that same client and clears protected views when identity changes.

The alternatives were retaining a pasted manager token or duplicating fetch/storage logic in every view. One client avoids drift in authentication behavior; the cost is an explicit lifecycle contract for every protected view. The 19 tests on main exercise headers, error messages, storage isolation, refresh, logout and out-of-order responses. Main now has 27 combined Node tests: the 19 client tests plus 8 ordering behavior tests merged through #107. This is Codex-assisted implementation, not a claim of teammate review before actual evidence exists.

## Per-member peer-review-driven revision register

**Missing member review links remain PENDING.** Populate these fields only with actual reviewer feedback and the substantive revision it caused. The audit found no recorded reviews on #95–#100; merged status alone supplies neither field.

| Member | Substantive PR / feedback link | Resulting revision and explanation | Status |
| --- | --- | --- | --- |
| Frank Williams | **PENDING** | **PENDING** | Missing peer-feedback/revision evidence. |
| Zay Lin Myat | [Abdul138 feedback on #74](https://github.com/frankwilz/Food-delivery-app/pull/74#pullrequestreview-5939365558): refused cart PATCH/DELETE requests must not write data. | [Follow-up #101](https://github.com/frankwilz/Food-delivery-app/pull/101), [`dd09814`](https://github.com/frankwilz/Food-delivery-app/commit/dd09814f4fa3a22ec6c9c360dcf0730cf585934a): implement and test no-write behavior for refused cart operations. | **VERIFIED FEEDBACK → IMPLEMENTED REVISION; #101 MERGED.** |
| AbdulHaady Oludare | **PENDING** | **PENDING** | Missing peer-feedback/revision evidence. |
| Olutayo Akere | **PENDING** | **PENDING** | Missing peer-feedback/revision evidence. |

The [M2 summary](milestones/M2.md) and [PROVENANCE](PROVENANCE.md) record each member's already-authored cross-subsystem test with source attribution. That evidence and the improvement implementations above do not substitute for these missing review-driven revision links.

## Completion conditions

- [ ] Each member confirms their own architectural explanation and implementation/test evidence.
- [ ] Every **PENDING** member review entry has a real feedback link and resulting substantive revision.
- [ ] Completion-round PRs request other teammates from **Abdul138, EuReKaA99 and tayo-ak**, excluding the PR author, obtain **at least two teammate approvals**, address feedback and pass checks before merging. The remaining Frank-authored documentation PR requests all three eligible teammates.
- [x] Code, rule audit/fixes, integration/regression tests and API/reference docs are merged through #101/#103/#104/#105/#106/#107; current main passes 538 Python / 27 Node tests and all three CI checks.
- [ ] This restored milestone receipt/provenance/summary/sprint documentation is reviewed and merged.
- [ ] Final combined verification, `m2-integrated-system` tag/full SHA and final-version submission references are recorded after the last approved merge.

Issue #57 marks demo practice and Canvas submission complete. That checklist state does not establish a currently absent tag or replace the remaining final-version release checks. The course handout is not included in this repository; compare this evidence with the official handout before final acceptance.
