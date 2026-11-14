# Task 8 implementation and self-review report

Base: `91a0293`. Implemented Task 8 only, plus the requested test/report cleanup.

## Changes and review

- Centralized existing domain, validation and Keitaro handling in presentation/errors.py; routes and DI now let those handlers translate errors. Application errors use top-level code/message.
- Preserved creation campaign_id/failed_step/confirmed_flows and save failed_stream_id/confirmed_stream_ids, their sanitized messages and HTTP 502 status. Existing partial-write integration tests now assert the flat envelope.
- Validation remains 422, missing campaign/flow/offer 404, duplicate 409. Raw Keitaro response failures map to 502; unavailable errors (including exhausted 5xx retries) map to 503. Upstream strings/bodies are never returned.
- Added typed pure-ASGI request-ID middleware: one bounded ASCII token is accepted, missing/unsafe/duplicate values get UUID hex; request state and response header agree. CORS exposes the header; middleware also covers preflight responses. No shared per-request mutable state.
- Spec is authoritative: country failures remain VALIDATION_ERROR; InvalidCountryCodeError is already used by CreateCampaignUseCase, so it is retained. Campaign/flow/offer missing errors intentionally share CAMPAIGN_NOT_FOUND. No new error codes or endpoints introduced.
- Added real transaction regression coverage for refresh failure after flush: deletion of an old stream and insertion of a new stream both roll back. Existing local mutation rollback coverage remains.
- Removed duplicate mutation-test assertion and corrected Task 7 retry wording: PUT inherits client retries, creation POST does not retry.
- Updated README endpoints, local/remote persistence behavior, partial outcomes, retries, error contract, request IDs and backend checks; removed stale backend status claims.
- Reviewed layer boundaries and diff: no domain/use-case behavior changes, schema changes, new dependencies, agents, live Keitaro calls/writes or secret access.

## Verification evidence

- RED: new error tests: 15 failed for missing request IDs, missing handlers/status mapping and nested validation envelope (the copied brief's shorter flow message also differed from the existing implementation).
- RED: updated creation/save/read contract tests: 58 failed, 12 passed; failures were missing top-level fields.
- Initial full-check attempt stopped during import after an incorrect removal of the already-used country exception; restored it. Ruff also found two missing import separators, corrected. Mypy initially caught the same missing exception.
- First collected full suite: 171 passed, two failures: `test_missing_flow_returns_machine_code` expected the brief's shorter message, and `test_failed_catalog_lookup_does_not_mutate` still expected 502 for exhausted upstream 5xx. Kept the existing campaign-qualified message and corrected the status expectation to the brief's unavailable mapping, 503.
- Final `uv run pytest -q`: **173 passed** (7.17s).
- `uv run ruff check .`: passed.
- Final `uv run ruff format --check .`: passed, 69 files.
- `uv run mypy app`: passed, 54 source files.
- `git diff --check`: passed before report creation.
- Repeated checks only to resolve the failures above; rollback/duplicate-ID/preflight tests characterize retained behavior rather than claim separate red-green production changes.

## Boundaries

Remote multi-write operations remain non-atomic. Error-envelope standardization is an intentional contract change from nested detail; consumers should use the documented top-level fields. Standard framework routing errors and unexpected uncaught exceptions retain framework behavior; the request-ID guarantee here covers successful and handled-error responses (including CORS preflight), not an outer server-generated 500. No blocking concerns found for Task 8.
