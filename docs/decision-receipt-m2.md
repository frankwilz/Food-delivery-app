# Decision Receipt M2.3: Shared dependency construction

**Prepared:** November 18, 2026. **Status:** implemented in merged PRs [#88](https://github.com/frankwilz/Food-delivery-app/pull/88) and [#89](https://github.com/frankwilz/Food-delivery-app/pull/89); individual team evidence and review-driven improvement records are still being completed.

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

Both PRs were merged by Abdul138. Each has one recorded approval from Abdul138 in the evidence above; this document does not claim a second approval or a feedback-driven revision. The current round requests reviews from **Abdul138, EuReKaA99 and tayo-ak** and requires **at least two teammate approvals** before a PR is merged.

## Each member's architectural improvement

### Frontend session boundary in PR #90

Frank's new frontend architecture separates HTTP/session behavior (`frontend/api.mjs`) from account rendering and restaurant/order views. One client attaches the current bearer token, formats API errors and owns API-scoped token storage. It obtains profiles from the server and uses a session revision to reject late responses after logout, a new login or an API-address change. The ordering module reuses this client and replaces protected views when the session changes.

This avoids separate token/header logic in each screen. The trade-off is that views must subscribe to session changes and handle a request superseded by another session. Alternatives were retaining the manual manager-token field or giving each view its own fetch/storage code. Neither would provide one consistent account boundary. Evidence: [PR #90](https://github.com/frankwilz/Food-delivery-app/pull/90), [PR #91](https://github.com/frankwilz/Food-delivery-app/pull/91), 19 HTTP/session tests and 8 ordering behavior tests. These are new implementations with Codex assistance; no teammate feedback-driven revision is claimed before actual review.

This table is an evidence register, not an attribution based on planned ownership. Each member must confirm their own contribution and the associated PR/tests/review feedback.

| Member | Improvement and available evidence | Remaining confirmation |
| --- | --- | --- |
| Frank Williams | New shared frontend HTTP/session boundary in #90, reused by ordering in #91 and covered by 27 frontend tests; adapted shared backend composition in #88 and integration tests in #89 retain Zay's source credit. | Obtain teammate reviews, address substantive feedback and link the resulting revision; confirm the individual requirement with the team. |
| Zay Lin Myat | Original author of the preserved integration/order-reading work credited above. | Select and explain his own qualifying M2 improvement; link his PR, tests and actual review discussion. |
| AbdulHaady Oludare | Authored frontend file separation in [#27](https://github.com/frankwilz/Food-delivery-app/pull/27); review/merge evidence for #88/#89 is recorded above. | Confirm the qualifying M2 improvement and link its tests/review discussion; review of someone else's PR does not substitute for his own implementation. |
| Olutayo Akere | Testing ownership is recorded in #55/#56. An assignment is not evidence of a completed architectural change. | Provide his qualifying improvement, PR, tests and review discussion. |

## Completion conditions

- [ ] Every member has confirmed their improvement and its PR/test evidence.
- [ ] Each member's substantive PR improved through peer-review feedback is linked, with the feedback and resulting change identified.
- [ ] The current frontend/documentation PRs have at least two teammate approvals and green checks before merging.
- [ ] The receipt and [M2 summary](milestones/M2.md) match the final merged system before tagging/submission.

The course handout is not included in this repository. This receipt follows issue #57 and the per-person requirements recorded in the parent issues; the team should verify the final submission against the official handout.
