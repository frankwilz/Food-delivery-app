# Sprint Planning Milestone 2

**Updated November 20, 2026.** This follows the course-template structure used by `sprint-planning-m1.md` and reconciles the backlog with current main `a840197`. It restores the preserved planning draft and records current evidence; meeting attendance, facilitator and unrecorded decisions still require team confirmation.

## Sprint Information

- **Sprint / milestone:** Milestone 2 — Integrated System (`m2-integrated-system`).
- **Sprint dates:** Confirm against the official course schedule. Parent issues list individual requirements by November 20; this is not an independent deadline verification.
- **Planning meeting date:** Not recorded.
- **Facilitator:** Not recorded.
- **Evidence snapshot:** Main `a840197ae8a736a36883d7b56c0903a19637ca3f`, November 20, 2026.

### Team Members

Confirm actual planning-meeting participation separately from implementation credit.

- [ ] Frank Williams
- [ ] Olutayo Akere
- [ ] AbdulHaady Oludare
- [ ] Zay Lin Myat

## 1. Sprint Goal

Deliver Customer → Restaurant → Menu → Cart → Checkout → Order as one persisted API/browser workflow. Enforce rules in services, keep storage in repositories, pass the service/repository/API/integration/regression checks, and complete the milestone evidence. Create the final tag after the last approved merge and final verification.

## 2. Sprint Backlog

Track parent stories [#28](https://github.com/frankwilz/Food-delivery-app/issues/28), [#29](https://github.com/frankwilz/Food-delivery-app/issues/29), [#30](https://github.com/frankwilz/Food-delivery-app/issues/30) and [#31](https://github.com/frankwilz/Food-delivery-app/issues/31) on the [Project board](https://github.com/users/frankwilz/projects/2). Parent ownership includes coordination and acceptance checks, not duplicate implementation credit.

| Task | Priority | Implementation / completion evidence | Remaining dependency |
| --- | --- | --- | --- |
| 4.6 / #48: retrieve orders | High | Zay's preserved order-retrieval implementation landed through #88. API ownership/snapshot tests are on main. | Reconcile issue/board state against evidence. |
| 5.2 / #50: integrate workflow | High | Frank adapted Zay's integration source; #88/#89 are merged, with full-flow and restart tests. | Preserve attribution and final combined checks. |
| 5.3 / #51: rules | High | Merged [#104](https://github.com/frankwilz/Food-delivery-app/pull/104), `cf85894`, repairs stored-data relationship edge cases and adds the rule-to-method-to-test README table. | Preserve the merged repair in final combined validation. |
| 5.4 / #52: account frontend | High | Frank's #90 is merged; 19 HTTP/session tests and account forms are on main. | Preserve #94 manager UI and #99 polish during ordering integration. |
| 5.5 / #53: ordering frontend | High | Restored in merged [#107](https://github.com/frankwilz/Food-delivery-app/pull/107), source `e5d84d2`/`2ca4f43`, retaining #94/#99. Current main passes 27 Node tests and fresh browser ordering checks. | Preserve this verified behavior through the final documentation merge. |
| 5.6 / #54: service tests | High | Existing customer/cart/checkout files already contain direct service tests. Tayo's additional #97 was closed without merge. | Reconcile acceptance from existing coverage; do not count unmerged files. |
| 5.7 / #55: repository/API tests | High | Main has direct isolated repository save/read tests, API success/error tests and OpenAPI/status assertions. Tayo's extra #98 was closed without merge. | Reconcile issue acceptance with source evidence rather than PR status alone. |
| 5.8 / #56: integration/regression | High | Merged [#105](https://github.com/frankwilz/Food-delivery-app/pull/105) retains Tayo's scenarios, named regressions, restart relationships and stricter data check. Every member has a cross-subsystem test; merged #103 adds Zay's price-flow scenario. | Current combined main validation: 538 Python / 27 Node, both restarts and unchanged data. |
| 5.9 / #57: docs/submission | High | Frank coordinates restored API/milestone docs with all members' credited evidence. Issue checklist marks demo practice and Canvas submission complete. | Documentation review/merge, missing member feedback links, final tag/SHA and final-version submission confirmation. |

Primary ownership means coordination. [PROVENANCE](../docs/PROVENANCE.md) records original authors, adapted source and AI assistance. No assignment, merge event or closed branch is used as a substitute for completed contribution evidence.

## 3. Task Decomposition

### Integrated backend and verification

- Preserve the merged #104 stored-cart consistency repairs and rule-to-service/method-to-test table during integration.
- Use existing direct service/repository/API tests as #54/#55 evidence; add tests only for actual gaps.
- Preserve Tayo's authorship and the bug-linked regression docstrings merged through replacement #105.
- Verify all demo scenarios, five-file relationships, real server restarts and unchanged committed data.

### Frontend and API documentation

- Preserve merged #107 ordering on top of #90/#94/#99, including account/session handling, manager menu forms and unavailable-item indicators.
- Keep displayed totals from API responses and backend business rules authoritative.
- Verify cart add/update/remove/clear, checkout, confirmation/history, authorization and API error messages in the browser.
- Restore API path descriptions and the README endpoint/error/architecture/test records to match the actual system.

### Individual and final evidence

- Preserve each member's already-authored cross-subsystem test and record their architectural improvement/trade-offs.
- Leave every missing substantive peer-feedback link and resulting revision **PENDING** until the member supplies real evidence.
- Record #57's demo/Canvas checkboxes as issue-checklist evidence, without inventing attendance or a submission receipt.
- After approved final merges, rerun the combined checks, create the tag/full SHA and verify the final-version Canvas references.

## 4. Dependencies and Integration

| Dependency | Resolution / current evidence |
| --- | --- |
| Protected cart/checkout/order APIs need caller identity | Shared `get_current_customer`, bearer tokens, active-state checks and 401/403 tests. |
| Checkout needs consistent customer/menu/cart data | Shared providers in #88; service rules and repository storage boundaries. |
| Concurrent writes must not lose/duplicate records | Tayo's merged #95 uses shared per-file locks and sorted multi-file transactions in one server process. |
| Ordering must preserve others' frontend changes | Merged #107 retains Abdul's #94 manager UI and Tayo's #99 polish; fresh browser checks verify them. |
| Final documentation depends on actual final code/tests | Code/tests/reference changes #101/#103/#104/#105/#106/#107 are merged; reconcile the remaining milestone files with current main. |
| Test/demo activity must preserve committed records | Temporary copies of all five files; stable `SECRET_KEY` for restart demos; CI data checks. |

### Integration Plan

The independent main-based restorations #104/#105/#106/#107 and Zay's #101/#103 were merged by teammates during preparation. Current main now contains all code/tests/reference work and has passed combined automated/browser checks. The previous #91–#93 stack was not on the earlier main; the remaining four milestone evidence files still need their own focused documentation PR and approved merge before final tagging.

Request reviews from other teammates among **Abdul138, EuReKaA99 and tayo-ak**, excluding the PR author. Closed #96 was replaced by merged Frank-authored #105, retaining Tayo's history. Frank-authored completion PRs request all three eligible teammates; this does not assert that every historical merge obtained two approvals. This completion round requires **at least two teammate approvals**, addressed feedback and green CI before each merge. Stop with reviewable PRs awaiting human review. Historical #88/#89 each record one Abdul approval; #95–#100 have no recorded reviews in the audit. Those historical merges do not meet this round's approval requirement or supply missing feedback-driven revisions.

## 5. Risks and Potential Blockers

| Risk | Impact | Action / responsibility |
| --- | --- | --- |
| Missing member review links | Individual course evidence remains incomplete. | Each member supplies actual feedback and the resulting revision; keep all missing entries PENDING. |
| Pending documentation approval/merge | Main has the code, tests and API/reference work; milestone evidence files still need their reviewed merge. | PR authors request eligible non-author teammates; wait for at least two approvals and passing checks. |
| Shared frontend work overwritten | Manager or polish behavior may regress. | Retain the now-merged #107 behavior and the verified #94/#99 manager/polish features. |
| Branch work described as merged | Contribution and test claims become inaccurate. | Distinguish main, preserved source, restored branch and final merge evidence. |
| Concurrent or interrupted JSON writes | Multiple processes or a crash can exceed current storage guarantees. | Keep the documented single-process limitation; preserve checkout recovery behavior. |
| Early tag or outdated submission | Hand-in omits final fixes. | Frank creates the tag after the final approved merge and confirms the exact submitted SHA. |

## 6. Definition of Done

- [ ] Task acceptance criteria have linked implementation/test evidence.
- [ ] Rules/persistence follow the required service/repository layers.
- [ ] Relevant automated/browser checks pass with all five committed data files unchanged.
- [ ] Documentation matches final behavior and API errors.
- [ ] Completion-round PR has at least two teammate approvals, addressed feedback and green CI.
- [ ] The reviewed change is merged into main.
- [ ] Provenance, architectural improvement and cross-subsystem evidence are recorded; missing individual feedback/revision evidence is resolved.

These are completion criteria, not attestations that every task already meets them.

## 7. Sprint Commitment

| Member | Recorded contribution / current responsibility | Evidence still needed |
| --- | --- | --- |
| Frank Williams | Integration adaptation #88/#89, account UI #90, restored ordering and final documentation coordination. | Actual peer-feedback/revision link; approved final merges and release references. |
| Olutayo Akere | Concurrency #95, polish #99, provenance #100; retained #96–#98 testing work and merged replacement #105. | Actual peer-feedback/revision link. |
| AbdulHaady Oludare | Role enforcement #80, menu/checkout work, frontend separation/manager UI #27/#94; reviews of #88/#89. | Actual peer-feedback/revision link and confirmation of his improvement explanation. |
| Zay Lin Myat | Preserved integration/order reading, order snapshots, #103 price flow and merged #101 addressing Abdul's verified #74 feedback. | Confirm his credited improvement explanation; the #74 → #101 feedback/revision pair is recorded. |

## Meeting Notes and Verification

- No planning-meeting attendance, facilitator or unrecorded decisions are asserted by this restored draft.
- Git-blame evidence confirms each member authored a cross-subsystem test already on main; exact tests/commits are in [M2](../docs/milestones/M2.md) and [PROVENANCE](../docs/PROVENANCE.md).
- Current main `a840197` is byte-identical to the validated combined code: **538 Python / 27 Node tests passed**, both real-server restart checks passed, all five committed data files unchanged and all three main CI checks green.
- Fresh browser checks passed manager creation/zero restaurant rating, unavailable menu indicators, registration, cart refresh/update/remove, mixed-restaurant 409, checkout/order total 50.97, history refresh, auth-page redirects, account and logout. The test order retained delivery address `12 Final Demo Lane`.
- The #57 checklist marks demo practice and Canvas submission complete. This document records those checkboxes; it does not independently verify the rehearsal or submission receipt.
- The M1 cleanup tracker #24 was closed after Frank directly confirmed the M1 PDF submission. That fact is separate from M2 release evidence.
- `m2-integrated-system`, its full final SHA, the final post-documentation release check and final-version hand-in confirmation remain pending.
- Record actual planning discussion/attendance and decisions when the team confirms them.
