# Task 13 report

Base: `6d5bf55`. Scope: campaign editor actions only.

## Implemented
- Per-flow accessible picker with local trimmed, case-insensitive search; excludes existing active and deleted IDs in that flow.
- Add, delete (including last active offer), restore, lock/unlock and explicit Save use backend responses as the complete rotation replacement.
- All rotation-changing controls, including refresh and Save, are disabled during any rotation request. Picker cannot dismiss or submit again during add.
- Failures preserve rotation and picker search, with API errors visible inside the dialog and editor. Catalog loading, retry and empty results are handled.
- Existing keyed route isolation and manual-only refresh retained. Active 0% offers remain visible and actionable. Only Save calls the remote-save endpoint.

## Verification
- TDD: editor tests initially failed (9 failures) on missing actions/picker/Save.
- Focused editor suite: 17 passed.
- Full frontend suite: 46 tests across 6 files passed.
- `pnpm lint`: passed; three existing Fast Refresh export warnings in shared button/form/badge.
- `pnpm fsd:lint`: passed, no problems.
- `pnpm typecheck`: passed after correcting the generic type of a deferred test promise.
- `pnpm build`: passed; bundle-size warning (>500 kB).
- `git diff --check`: passed.

## Self-review
Reviewed the spec's FR-020–029, mutation endpoint arguments, response replacement, pending-state coverage, error preservation, dialog labeling and page-local FSD boundaries. Tests cover per-flow filtering, active/deleted exclusions, last deletion, restore, both lock directions, active zero, Save response, every mutation failure, catalog retry, pending conflicts and late mutation responses after navigation. No outstanding task-13 issues found. No backend or shared UI changes.

## Review fixes
- Explicitly disabled catalog refetch on reconnect and window focus; opening the picker and manual retry remain the fetching triggers.
- New editor operations (including picker open) reset previous failed mutation states. Current failures remain visible until another operation starts; rotation is never cleared. Pending guards and keyed route isolation remain intact.
- Added behavioral regressions for reconnect after catalog failure followed by manual retry, switching from failed deletion to pending/failed Save, and reopening after add failure.
- Red: all three new regressions failed before the fixes (17 existing tests passed).
- Green: full frontend suite passed, 49 tests / 6 files, including route isolation and pending/failure coverage. Typecheck and diff check passed; lint passed with the same three existing shared-component Fast Refresh warnings.
