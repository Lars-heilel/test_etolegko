# Task 6 report

## Status

Implemented Task 6 on base `57b7776`.

- Four local mutation use cases, typed API handlers, validated request schemas, and DI.
- Uses the existing repository/catalog ports and function-scoped transaction dependency.
- Campaign-scoped flow lookup; duplicate active/deleted offers return 409 before catalog lookup.
- Domain errors return the brief's top-level `code`/`message` shape (404 missing flow/offer, 409 duplicate, 422 invalid distribution).
- Add alone can read the catalog. Local mutations never invoke a Keitaro write gateway.
- Last-active deletion, deleted zero/unlocked state, locked-share preservation, and all-existing-locked add-at-zero are covered.
- Restore of an already-active offer is now idempotent: a regression test exposed the previous lock/share reset, fixed with a domain guard.

## Verification evidence

Commands run from `apps/api`:

- Initial `uv run pytest tests/presentation/test_offer_mutations.py -q`: 9 failed as expected against missing routes/error contract.
- After initial implementation: 9 passed.
- Added active-locked restore regression: 1 failed, 16 passed; observed 70/locked becoming 100/unlocked before the fix.
- Final `uv run pytest -q`: **145 passed in 4.69s**, including 18 mutation cases.
- `uv run ruff check .`: all checks passed.
- `uv run mypy app`: success, 51 source files.
- `git diff --check`: passed.

Tests use real ASGI handlers, use cases, domain methods and SQLite repository transactions. External HTTP is intercepted with respx. Persistence is checked through fresh sessions; injected failure after a real flush proves rollback. No live requests or database writes were performed.

## Self-review

- Compared implementation to all four routes and response requirements in the brief.
- Checked inward dependency direction and that use cases do not commit or depend on concrete persistence.
- Checked lock/unlock, restore, last deletion, duplicate deleted IDs, wrong campaign, missing offer, invalid payload, upstream failure and post-flush rollback paths.
- Main application gained a domain exception handler because the base had no mapping for the brief's mutation error contract. Existing explicitly handled errors retain their existing envelope.
- No blocking concerns. Concurrent edits still use the existing repository semantics (no new optimistic concurrency/versioning); the existing database unique constraint remains the final duplicate safeguard. Concurrent conflict-to-409 translation is not added by this task.
