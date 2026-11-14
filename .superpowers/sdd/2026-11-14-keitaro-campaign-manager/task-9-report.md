# Task 9 report

Implemented against base `43e3d14`.

## Delivered

- Campaign transport with all ten methods and seven exported snake_case DTO types, checked against the implemented backend schemas and handlers.
- Error-message helper preserving backend messages (including partial failures), unavailable-service fallback, and safe handling of malformed payloads.
- Russian-localized, sorted country options from `world-countries`.
- Vite-safe Sonner export and root-layout toaster.
- Shared Select, Dialog, Command, Popover, Table, Form, Checkbox primitives plus generated InputGroup/Textarea dependencies; all exported from the UI public API.
- Per-render QueryClient and memory-router test renderer with retries disabled. A wildcard fallback avoids duplicate concrete routes and preserves edit-route parameters.

## Installation and self-review

- Replaced only the worktree's `node_modules` symlink using `unlink`, then installed locally; original checkout target was not deleted or modified.
- Inspected existing `components.json` (Vite, radix-nova, Tailwind v4, Lucide).
- Moved CLI output from literal `@/shared/ui` to `src/shared/ui` using patches, preserving existing Button/Input/Label and other primitives.
- Current radix-nova registry omitted Form; installed the shadcn new-york Form registry item for the requested React Hook Form API.
- Removed generated `next-themes` dependency; Sonner is a direct Vite-safe re-export.
- Reviewed generated sources and corrected CommandDialog's title/description placement inside portaled content, PopoverTitle's heading element, FormItem gap styling, and class-name helper imports.
- Shared code contains transport/config/UI infrastructure only; providers/testing remain in app. No live API writes or agents used.

## Verification

- RED: focused error-helper test failed because its implementation module did not exist.
- GREEN: `pnpm test` — 2 files, 14 tests passed.
- `pnpm typecheck` — passed.
- `pnpm lint` — exit 0; three Fast Refresh warnings for mixed component/helper exports: pre-existing `badge.tsx` and `button.tsx`, plus generated `form.tsx` (`useFormField`).
- `pnpm fsd:lint` — no problems found.
- `pnpm build` — passed.
- `git diff --check` — passed.

No unresolved implementation blockers. Package installation reported peer-dependency warnings; frontend checks and build succeeded.

## Review follow-up: assigned-country contract and generator paths

- Replaced the brief's unfiltered country mapping with `world-countries`' `officially-assigned` status filter. All 249 backend-accepted ISO codes, including territories, remain; user-assigned `XK` is excluded.
- Added a cross-language contract test that sends every offered code to the actual Python `CountryCode` validator and compares the complete offered set with the backend's accepted set. It does not copy the backend allowlist or repeat the frontend metadata filter. The test uses local `python3` and only Python standard-library code; no API service or Python third-party dependencies are needed.
- RED: the contract test failed with rejected code `["XK"]` before the filter. GREEN: all 15 tests across 3 files pass.
- Added the existing `@/* -> ./src/*` mapping to root `tsconfig.json`, where shadcn discovers aliases. `shadcn info --json` now resolves UI to `src/shared/ui` and recognizes installed components. `shadcn add select --dry-run` targets `src/shared/ui/select.tsx`, not literal `@/shared/ui`; no component overwrite was performed.
- Updated the generator's utils alias and all Task 9 UI helper imports to the `@/shared/lib` public API.
- Exact peer warning from `pnpm peers check`: **`tsconfck@3.1.6` requires peer `typescript@^5.0.0`; installed `typescript@7.0.2`**. This is the only reported mismatch (the diagnostic exits 1). No dependency versions or lockfile were changed for this follow-up.
- Initial typecheck identified missing Node type references in the new subprocess-based test; added a test-file Node type reference and reran the complete frontend checks.
- Final checks: `pnpm test`, `pnpm typecheck`, `pnpm lint`, `pnpm fsd:lint`, and `pnpm build` all exit 0. Lint retains the same three documented Fast Refresh warnings. Production bundle size is unchanged. No live writes or agents used.
