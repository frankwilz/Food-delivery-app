# Sprint Planning Milestone 2

**Planning draft prepared November 18, 2026.** This follows the structure of `sprint-planning-m1.md`. It records the repository backlog and current work; it is not a claim that a planning meeting or demo rehearsal has taken place.

## Sprint Information

- **Sprint / Milestone:** Milestone 2 — Integrated System (`m2-integrated-system`).
- **Sprint dates:** To be confirmed by the team. Parent issues record per-person requirements by November 20; verify the official course deadline separately.
- **Planning meeting date:** Not recorded; team confirmation required.
- **Facilitator:** Not recorded; team confirmation required.

### Team Members

Attendance/participation must be confirmed at the actual planning discussion.

- [ ] Frank Williams
- [ ] Olutayo Akere
- [ ] AbdulHaady Oludare
- [ ] Zay Lin Myat

## 1. Sprint Goal

Deliver Customer → Restaurant → Menu → Cart → Checkout → Order as one persisted workflow through the API and frontend. Enforce business rules in services, keep storage in repositories, pass service/repository/API/integration/regression tests in CI, and complete the milestone evidence and demo. Create the final tag only after the last reviewed merge.

## 2. Sprint Backlog

The parent stories are [#28 — Accounts/Auth](https://github.com/frankwilz/Food-delivery-app/issues/28), [#29 — Cart](https://github.com/frankwilz/Food-delivery-app/issues/29), [#30 — Checkout/Orders](https://github.com/frankwilz/Food-delivery-app/issues/30) and [#31 — Integration/Testing/Documentation](https://github.com/frankwilz/Food-delivery-app/issues/31). Track them and their acceptance criteria on the [Project board](https://github.com/users/frankwilz/projects/2); parent ownership includes verification and coordination.

| Task | Priority | Recorded owner / status | Dependencies |
| --- | --- | --- | --- |
| 4.6 / #48: retrieve customer orders | High | Preserved Zay implementation included by the team through merged #88; verify issue/board status. | Authentication and persisted orders. |
| 5.2 / #50: integrate workflow | High | Frank; implementation and evidence merged in #88/#89. Issue closure remains to be reconciled with acceptance criteria. | 2.5, 4.5, 4.6. |
| 5.3 / #51: cross-subsystem rules | High | Assigned-team ownership to confirm; final audit/fix evidence pending. | Customer/cart/checkout services. |
| 5.4 / #52: frontend account/auth | High | Frank; [PR #90](https://github.com/frankwilz/Food-delivery-app/pull/90) open for review. | Register/login/profile API and agreed token handling. |
| 5.5 / #53: frontend ordering | High | Frank; [PR #91](https://github.com/frankwilz/Food-delivery-app/pull/91) open for review. | #90, cart, checkout and order-read APIs. |
| 5.6 / #54: service tests | High | Assigned-team ownership to confirm; verify remaining coverage with its owner. | Customer, cart and checkout services. |
| 5.7 / #55: repository/API tests | High | `tayo-ak`; completion evidence pending. | Repositories, endpoint contracts and auth errors. |
| 5.8 / #56: integration/regression tests | High | `tayo-ak` coordinates; every member still writes their own cross-subsystem test. | #50 and #51. |
| 5.9 / #57: documentation/submission | High | Frank coordinates this draft; every member confirms their provenance and individual evidence. | #50, #51, #53 and #56; final reviewed merges before tag/submission. |

Primary ownership means coordination, not exclusive authorship. Preserve and credit work adapted from retained branches instead of treating it as newly authored code.

## 3. Task Decomposition

### Integrated backend and rules

- Verify #50 against its acceptance criteria using #88/#89 and reconcile the issue/board state.
- Complete the #51 rule-to-service/method-to-test audit, including a hand-edited cart whose restaurant does not match its menu items.
- Confirm service and repository/API coverage for #54/#55 without duplicating already adequate tests.
- Complete #56's demo-scenario, restart, regression and per-member cross-subsystem evidence.

### Frontend account and ordering

- Build registration, sign-in/sign-out and account/profile update flows for #52.
- Send the bearer token on protected requests and display API error messages.
- Build add/update/remove/clear-cart, checkout confirmation and order-history/detail views for #53.
- Display totals from API responses; keep backend rule enforcement authoritative.
- Verify the browser workflow and failure cases, then record the actual checks and PRs.

### Documentation and final preparation

- Update README/API descriptions, error contracts, architecture, data files, rules and tests.
- Complete `docs/milestones/M2.md` and Decision Receipt M2.3 with actual PR, test and review evidence.
- Every member confirms their provenance, architectural improvement, cross-subsystem test and review-driven revision.
- Practise the scenarios in the M2 demo script with every member.
- After final reviewed merges and validation, create the final tag and complete Canvas submission fields.

## 4. Dependencies and Integration

| Dependency | Resolution / current evidence |
| --- | --- |
| Authentication identifies the caller for cart, checkout and order reads | Shared `get_current_customer`; protect requests through bearer-token dependencies and retain 401/403 tests. |
| Checkout reaches customer, menu and cart data consistently | Shared providers in #88; business rules stay in services and storage stays in repositories. |
| Frontend ordering depends on frontend authentication | Agree token/header/error handling in #52 before integrating #53's protected flows. |
| Rule audit and integration tests affect final documentation | Reconcile #51/#56 before claiming final acceptance or creating the tag. |
| Test/demo activity must preserve committed data | Temporary copies of all five files; stable `SECRET_KEY` for restart demos; CI data-diff check. |

### Integration Plan

Prepare small PRs from the `m2-frank-updates` line of work, splitting account UI, ordering UI and documentation as needed. Request reviews from **Abdul138, EuReKaA99 and tayo-ak**. This round requires **at least two teammate approvals** and green checks before merging. Stop with PRs awaiting review rather than self-approving or merging early.

PRs #88/#89 were already merged by Abdul138 with one recorded approval each. Record those facts accurately; they do not establish two approvals for the current round. Each new integration step needs its own relevant tests/browser checks and a clear prerequisite when a PR depends on another.

## 5. Risks and Potential Blockers

| Risk / blocker | Impact | Planned action | Responsibility |
| --- | --- | --- | --- |
| Missing second review | Work cannot meet the current merge agreement. | Request all three teammates and wait for at least two approvals. | PR author and reviewers. |
| #51/#56 evidence incomplete | Final rules, regression and individual requirements may be unmet. | Reconcile their acceptance criteria with the owners before finalization. | Assigned owners; every member for individual evidence. |
| Shared frontend files changed in multiple PRs | Conflicts or dependent behavior may be hard to review. | Keep related changes together or explicitly stack small PRs; verify the combined browser flow. | Frank. |
| JSON files changed during tests/demo | Demo records become inconsistent. | Use isolated data and inspect `git diff -- data/`; keep all five files together. | Everyone. |
| Contribution/review records guessed from assignments | Submission misattributes work or overstates completion. | Link actual commits/PRs/reviews and obtain each member's confirmation. | Everyone. |
| Tag created before final merges | Submitted version omits reviewed work. | Leave tag/SHA/Canvas fields pending until final validation. | Frank coordinates. |

## 6. Definition of Done

For a task to be accepted as done:

- [ ] Its acceptance criteria are satisfied and evidence is linked.
- [ ] Business rules and persistence use the required service/repository layers.
- [ ] Relevant automated checks and browser scenarios pass; committed data is unchanged.
- [ ] Documentation matches the final behavior and error responses.
- [ ] At least two teammate approvals are recorded for PRs in this round and feedback is addressed.
- [ ] The reviewed change is merged into the team's working version.
- [ ] The owner records provenance and any individual-requirement evidence.

These are completion criteria, not attestations that every task already satisfies them.

## 7. Sprint Commitment

| Member | Current responsibilities / evidence to confirm | Confirmed |
| --- | --- | --- |
| Frank Williams | #50, #52, #53 and #57; account/integration parent coordination and the previously assigned M1 cleanup. | ☐ |
| Olutayo Akere | Recorded #55/#56 ownership; confirm additional agreed responsibilities and individual evidence. | ☐ |
| AbdulHaady Oludare | Requested reviewer; confirm his implementation responsibilities and individual evidence. | ☐ |
| Zay Lin Myat | Requested reviewer; confirm his implementation responsibilities, original-work attribution and individual evidence. | ☐ |

## Meeting Notes

- No planning-meeting attendance, facilitator or decisions have been attested in this draft.
- Current implementation evidence: #88/#89 and the source attributions in `docs/PROVENANCE.md`.
- Current frontend review evidence: #90/#91; 27 Node tests and 477 Python tests pass, with the combined browser workflow verified on temporary data. This does not attest team demo practice.
- The Milestone 1 cleanup tracker #24 was closed after Frank confirmed its Canvas PDF had been submitted.
- The present review agreement requests three teammates and requires at least two approvals.
- Record the actual planning discussion, decisions and confirmations here when it happens.
