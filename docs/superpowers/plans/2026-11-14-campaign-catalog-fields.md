# Campaign catalog fields implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require campaign group and traffic source while allowing creation without a domain.

**Architecture:** Reuse the existing form-options endpoint and Keitaro gateway. Load catalogs alongside offers, validate selections in the form, and enforce required IDs at the backend boundary and use case.

**Tech Stack:** React, TanStack Query, React Hook Form, Zod, FastAPI, Pydantic.

**Spec:** User-approved chat requirements: domain optional; group and source required; document the actual domain-creation permission failure.

## Global Constraints

- Preserve existing name, country, offer and two-stream creation behavior.
- No automatic creation of remote resources during implementation or tests.
- Source creation is performed in Keitaro; this change selects existing sources through the API.
- Domain absence must not block submission when required catalogs and selections are available.
- Document the observed 403 as a limitation of the supplied credentials, not a limitation of Keitaro API generally.

## Review Focus

- Empty domains allow submission; omit domain_id when unselected.
- Empty groups or sources block submission with a specific explanation and refresh action.
- Failed catalog requests are distinguishable from empty catalogs and can be retried.
- Missing, null, zero and malformed required IDs are rejected before upstream writes.
- Stale selections absent from a refreshed catalog fail form validation.

### Task 1: Backend contract

**Files:**
- Modify: `apps/api/app/presentation/api/keitaro/schemas.py`
- Modify: `apps/api/app/usecase/keitaro/create_campaign_usecase.py`
- Modify: `apps/api/app/presentation/api/keitaro/handlers/campaigns.py`
- Test: `apps/api/tests/presentation/test_create_campaign.py`
- Update existing use-case tests and callers found by searching `CreateCampaignUseCase`.

**Interfaces:** CreateCampaignRequest requires positive strict integer group_id and traffic_source_id; domain_id remains optional. Use-case execute signature becomes `(name: str, country_code: str, offer_id: int, group_id: int, traffic_source_id: int, domain_id: int | None = None) -> CampaignSummary`; handler passes catalog IDs by keyword.

- [ ] Add/update tests for successful creation with and without domain, mandatory group/source validation, and no upstream writes for invalid inputs.
- [ ] Run `make test-api`; confirm new assertions fail on current behavior.
- [ ] Implement required IDs in schemas/use case, adjust callers, preserve string serialization of group_id to Keitaro.
- [ ] Run `make test-api`; require all tests passing.

### Task 2: Form catalogs and documentation

**Files:**
- Modify: `apps/web/src/pages/campaign-create/api/use-campaign-form.ts`
- Modify: `apps/web/src/pages/campaign-create/model/campaign-create-schema.ts`
- Modify: `apps/web/src/pages/campaign-create/ui/campaign-create-page.tsx`
- Modify: `apps/web/src/shared/api/campaigns.ts`
- Test: `apps/web/src/pages/campaign-create/ui/campaign-create-page.test.tsx`
- Modify: `README.md`

**Interfaces:** useCampaignForm returns offers and formOptions query results. campaignCreateCatalogSchema consumes offers and FormOptions. CreateCampaignPayload requires group_id and traffic_source_id, retains optional domain_id.

- [ ] Add tests covering selected IDs in payload, omitted domain, empty required catalogs, catalog errors/retry, and stale catalog selections.
- [ ] Run `make test-web`; confirm the new behavior assertions fail.
- [ ] Load form options and add labeled group/source/domain selects using existing form styling. Start with explicit selection placeholders; domain has a no-domain option. Validate required selections and catalog membership. Convert empty optional selection to undefined, never zero or NaN.
- [ ] Block submission on unloaded/failed catalogs or empty required catalogs. Permit empty domains. Refresh both catalogs and offers with existing retry/refresh controls.
- [ ] Explain empty domains in the form without assuming every empty response is caused by permission denial.
- [ ] Update README usage and record: supplied API credentials received HTTP 403 on POST /admin_api/v1/domains with “You have no permission to access this page - Domains”; GET /domains returned an empty list. Domain is temporarily optional, so the original domain requirement is not fully satisfied. Group and source remain required; create a source in Keitaro and refresh the form if none exist.
- [ ] Run `make test-web`, `make lint`, and `make typecheck`; require all checks passing.
- [ ] Review diff for credentials, unrelated changes and consistency with the requirements.

## Self-review

Backend and frontend contracts agree on required group/source and optional domain. Tests cover the five review conditions above. Source creation inside this application is outside this change; the currently empty remote source catalog will need an entry before actual campaign creation succeeds.
