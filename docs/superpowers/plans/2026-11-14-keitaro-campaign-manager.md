# Keitaro Campaign Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Adrobot test assignment: create Keitaro campaigns with two flows and edit offers/shares in existing campaigns through a FastAPI + React application.

**Architecture:** Backend follows `python-fastapi-ddd-skill`: pure domain entities/value objects, repository interfaces, one use case per action, SQLAlchemy infrastructure, FastAPI presentation. Frontend follows `feature-sliced-design` with `app`, `pages`, and `shared`; page-specific state and query hooks stay in pages, transport types and the fetch client stay in `shared/api`. Keitaro is the source of truth for campaigns, flows, offers, domains, groups and traffic sources. One local PostgreSQL table stores what Keitaro cannot represent: locked shares and soft-deleted offers.

**Tech Stack:** Python 3.12, uv, FastAPI, Pydantic v2, SQLAlchemy 2 async, asyncpg, Alembic, httpx, pytest, respx, ruff, mypy. Vite, React 19, TypeScript strict, React Router 7, TanStack Query 5, shadcn/ui, Tailwind 4, react-hook-form, zod, vitest, Steiger.

**Spec:** `specs/001-keitaro-campaign-manager/spec.md`

## Global Constraints

- Load and follow these skills before writing code, per `specs/001-keitaro-campaign-manager/spec.md` §7.4:
  - backend architecture: `python-fastapi-ddd-skill` (single source of truth)
  - backend practices: `fastapi`, `fastapi-patterns`, `sqlalchemy-alembic-expert-best-practices-code-review`
  - frontend structure: `feature-sliced-design` (single source of truth)
  - frontend practices: `shadcn`, `react-router`, `vercel-react-best-practices`
  - process: `test-driven-development`, `verification-before-completion`
- No business logic before its task's failing test exists.
- API prefix is `/api/v1`; JSON is snake_case; timestamps are ISO-8601 UTC.
- Machine-readable error codes: `VALIDATION_ERROR`, `KEITARO_UNAVAILABLE`, `CAMPAIGN_NOT_FOUND`, `VERSION_CONFLICT`, `OFFER_ALREADY_EXISTS`, `LAST_OFFER`.
- Secrets only in `.env`; `.env.example` is committed.
- Google redirect URL is the code constant `https://www.google.com`; it is never an environment variable.
- Campaign list and offer search are local: `GET /campaigns` accepts only `offset`/`limit`, `GET /offers` accepts no query parameters.
- Keitaro Admin API auth header is `Api-Key`. Base path is `/admin_api/v1`.
- Share is an integer percentage, per flow. Deleted offers always have `share = 0`.
- Locked offers never change share. Recalculation applies only to active, unlocked offers in the same flow.
- When every active offer in a flow is locked, a newly added offer gets `0` and stays active.
- Refresh is manual only. Do not auto-poll or auto-refresh flows.
- A flow whose Keitaro `offers` array is empty is skipped during refresh; its contents are not parsed or stored.
- Keep the existing env names: `DATABASE_URL`, `KEITARO_BASE_URL`, `KEITARO_API_KEY`, `CORS_ORIGINS`, `VITE_API_BASE_URL`.

## File Structure

### Backend

```text
apps/api/app/
  domain/keitaro/
    entities/campaign_offer.py          # CampaignOffer entity
    entities/flow_offers.py             # FlowOffers aggregate: add/delete/restore/lock/rebalance
    value_objects/identifiers.py        # CampaignId, StreamId, OfferId
    value_objects/offer_share.py        # OfferShare, OfferState
    value_objects/country.py            # CountryCode
    services/share_distribution.py      # integer share split
    snapshots.py                        # KeitaroFlowSnapshot, KeitaroOfferSnapshot, CatalogItem, CampaignSummary
    repositories.py                     # repository/gateway protocols
    exceptions.py                       # domain errors
  infrastructure/
    keitaro/client.py                   # httpx client, retries, Api-Key
    keitaro/errors.py                   # infrastructure errors
    keitaro/campaigns.py                # campaigns + catalog gateway
    keitaro/flows.py                    # flows gateway
    persistence/models.py               # SQLAlchemy model
    persistence/campaign_offer_repository.py
    di/injection.py                     # FastAPI dependencies
  usecase/keitaro/
    list_campaigns_usecase.py
    list_offers_usecase.py
    get_form_options_usecase.py
    create_campaign_usecase.py
    refresh_campaign_offers_usecase.py
    add_offer_usecase.py
    delete_offer_usecase.py
    restore_offer_usecase.py
    set_offer_lock_usecase.py
    save_campaign_offers_usecase.py
  presentation/api/keitaro/
    handlers/campaigns.py
    handlers/offers.py
    schemas.py
    dependencies.py
    responses.py
  presentation/errors.py
```

### Frontend

```text
apps/web/src/
  app/layouts/root-layout.tsx            # add Toaster
  app/router/router.tsx                  # existing routes
  app/testing/render-with-providers.tsx  # test-only router/query wrapper
  shared/api/campaigns.ts                # all campaign/offer transport functions + types
  shared/lib/get-api-error-message.ts
  shared/config/countries.ts             # country options from world-countries
  shared/ui/*                            # generated shadcn components
  pages/campaigns-list/
    api/use-campaigns.ts
    ui/campaigns-list-page.tsx
    ui/campaigns-list-page.test.tsx
  pages/campaign-create/
    api/use-campaign-form.ts
    model/campaign-create-schema.ts
    ui/campaign-create-page.tsx
    ui/campaign-create-page.test.tsx
  pages/campaign-edit/
    api/use-campaign-offers.ts
    ui/campaign-edit-page.tsx
    ui/flow-offers-card.tsx
    ui/offer-picker-dialog.tsx
    ui/campaign-edit-page.test.tsx
```

---

## Task 0: Commit the Existing Scaffold

**Files:**
- Modify: none

**Interfaces:**
- Consumes: existing scaffold.
- Produces: clean baseline commit.

- [ ] **Step 1: Verify the baseline**

Run:

```bash
cd apps/api && uv run pytest -q
cd ../web && pnpm test && pnpm typecheck && pnpm fsd:lint
```

Expected: backend `1 passed`; frontend tests pass; typecheck and Steiger exit 0.

- [ ] **Step 2: Commit the scaffold**

```bash
git add .env.example .gitignore Makefile README.md apps infra specs .specify docs
git commit -m "chore: scaffold keitaro campaign manager"
```

Expected: `.env` is not staged because it is ignored.

---

## Task 1: Domain Offer Rotation

**Files:**
- Create: `apps/api/app/domain/keitaro/value_objects/identifiers.py`
- Create: `apps/api/app/domain/keitaro/value_objects/offer_share.py`
- Create: `apps/api/app/domain/keitaro/value_objects/country.py`
- Create: `apps/api/app/domain/keitaro/entities/campaign_offer.py`
- Create: `apps/api/app/domain/keitaro/entities/flow_offers.py`
- Create: `apps/api/app/domain/keitaro/services/share_distribution.py`
- Create: `apps/api/app/domain/keitaro/exceptions.py`
- Create: `apps/api/app/domain/keitaro/__init__.py`
- Test: `apps/api/tests/domain/test_flow_offers.py`
- Test: `apps/api/tests/domain/test_share_distribution.py`

**Interfaces:**
- Consumes: stdlib only.
- Produces:
  - `CampaignId(value: int)`, `StreamId(value: int)`, `OfferId(value: int)`
  - `OfferShare(value: int)` — validates `0 <= value <= 100`
  - `OfferState(str, Enum)` — `ACTIVE = "active"`, `DELETED = "deleted"`
  - `FlowOffers.empty(stream_id: StreamId, name: str) -> FlowOffers`
  - `FlowOffers.rehydrate(stream_id, name, offers: list[CampaignOffer]) -> FlowOffers`
  - `FlowOffers.add_offer(offer_id: OfferId, name: str) -> None`
  - `FlowOffers.delete_offer(offer_id: OfferId) -> None`
  - `FlowOffers.restore_offer(offer_id: OfferId) -> None`
  - `FlowOffers.set_locked(offer_id: OfferId, locked: bool) -> None`
  - `FlowOffers.active_offers() -> list[CampaignOffer]`
  - `distribute(total: int, count: int) -> list[int]`

- [ ] **Step 1: Write the failing tests**

Create `apps/api/tests/domain/test_flow_offers.py`:

```python
import pytest

from app.domain.keitaro.entities.campaign_offer import CampaignOffer
from app.domain.keitaro.entities.flow_offers import FlowOffers
from app.domain.keitaro.exceptions import OfferAlreadyExistsError, OfferNotFoundError
from app.domain.keitaro.value_objects.identifiers import OfferId, StreamId
from app.domain.keitaro.value_objects.offer_share import OfferShare, OfferState


def offer(offer_id: int, share: int, state: OfferState = OfferState.ACTIVE, locked: bool = False):
    return CampaignOffer(
        offer_id=OfferId(offer_id),
        name=f"Offer {offer_id}",
        share=OfferShare(share),
        state=state,
        locked=locked,
    )


def shares(flow: FlowOffers) -> dict[int, int]:
    return {item.offer_id.value: item.share.value for item in flow.offers}


def test_add_fourth_offer_splits_25_percent() -> None:
    flow = FlowOffers.empty(StreamId(10), "Main")
    for offer_id in (1, 2, 3):
        flow.add_offer(OfferId(offer_id), f"Offer {offer_id}")

    flow.add_offer(OfferId(4), "Offer 4")

    assert shares(flow) == {1: 25, 2: 25, 3: 25, 4: 25}


def test_locked_offer_keeps_share_and_others_split_remainder() -> None:
    flow = FlowOffers.rehydrate(
        StreamId(10),
        "Main",
        [offer(1, 50, locked=True), offer(2, 50)],
    )

    flow.add_offer(OfferId(3), "Offer 3")

    assert shares(flow) == {1: 50, 2: 25, 3: 25}


def test_delete_sets_zero_and_redistributes_to_active() -> None:
    flow = FlowOffers.rehydrate(
        StreamId(10),
        "Main",
        [offer(1, 50), offer(2, 50)],
    )

    flow.delete_offer(OfferId(1))

    assert shares(flow) == {1: 0, 2: 100}
    assert flow.offers[0].state is OfferState.DELETED


def test_restore_joins_active_flow_equally() -> None:
    flow = FlowOffers.rehydrate(
        StreamId(10),
        "Main",
        [offer(1, 0, state=OfferState.DELETED), offer(2, 100)],
    )

    flow.restore_offer(OfferId(1))

    assert shares(flow) == {1: 50, 2: 50}


def test_all_active_locked_new_offer_gets_zero() -> None:
    flow = FlowOffers.rehydrate(
        StreamId(10),
        "Main",
        [offer(1, 60, locked=True), offer(2, 40, locked=True)],
    )

    flow.add_offer(OfferId(3), "Offer 3")

    assert shares(flow) == {1: 60, 2: 40, 3: 0}


def test_duplicate_offer_is_rejected() -> None:
    flow = FlowOffers.empty(StreamId(10), "Main")
    flow.add_offer(OfferId(1), "Offer 1")

    with pytest.raises(OfferAlreadyExistsError):
        flow.add_offer(OfferId(1), "Offer 1")


def test_missing_offer_is_rejected() -> None:
    flow = FlowOffers.empty(StreamId(10), "Main")

    with pytest.raises(OfferNotFoundError):
        flow.delete_offer(OfferId(99))


def test_lock_rebalances_unlocked_offers() -> None:
    flow = FlowOffers.rehydrate(
        StreamId(10),
        "Main",
        [offer(1, 50), offer(2, 50)],
    )

    flow.set_locked(OfferId(1), True)

    assert shares(flow) == {1: 50, 2: 50}
```

Create `apps/api/tests/domain/test_share_distribution.py`:

```python
from app.domain.keitaro.services.share_distribution import distribute


def test_even_split() -> None:
    assert distribute(100, 4) == [25, 25, 25, 25]


def test_remainder_goes_to_first_offers() -> None:
    assert distribute(100, 3) == [34, 33, 33]


def test_zero_count_returns_empty_list() -> None:
    assert distribute(100, 0) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd apps/api && uv run pytest tests/domain -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'app.domain.keitaro'`.

- [ ] **Step 3: Write the value objects and exceptions**

`apps/api/app/domain/keitaro/value_objects/identifiers.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class CampaignId:
    value: int

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError("Campaign id must be positive")


@dataclass(frozen=True)
class StreamId:
    value: int

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError("Stream id must be positive")


@dataclass(frozen=True)
class OfferId:
    value: int

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise ValueError("Offer id must be positive")
```

`apps/api/app/domain/keitaro/value_objects/offer_share.py`:

```python
from dataclasses import dataclass
from enum import Enum


class OfferState(str, Enum):
    ACTIVE = "active"
    DELETED = "deleted"


@dataclass(frozen=True)
class OfferShare:
    value: int

    def __post_init__(self) -> None:
        if self.value < 0 or self.value > 100:
            raise ValueError("Offer share must be between 0 and 100")
```

`apps/api/app/domain/keitaro/value_objects/country.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class CountryCode:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().upper()
        if len(normalized) != 2 or not normalized.isalpha():
            raise ValueError("Country code must be ISO-3166 alpha-2")
        object.__setattr__(self, "value", normalized)
```

`apps/api/app/domain/keitaro/exceptions.py`:

```python
class DomainError(Exception):
    code = "VALIDATION_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidCountryCodeError(DomainError):
    pass


class CampaignNotFoundError(DomainError):
    code = "CAMPAIGN_NOT_FOUND"


class FlowNotFoundError(DomainError):
    code = "CAMPAIGN_NOT_FOUND"


class OfferNotFoundError(DomainError):
    code = "CAMPAIGN_NOT_FOUND"


class OfferAlreadyExistsError(DomainError):
    code = "OFFER_ALREADY_EXISTS"


class ShareTotalError(DomainError):
    pass
```

- [ ] **Step 4: Write the entity, aggregate and distribution service**

`apps/api/app/domain/keitaro/entities/campaign_offer.py`:

```python
from dataclasses import dataclass

from app.domain.keitaro.value_objects.identifiers import OfferId
from app.domain.keitaro.value_objects.offer_share import OfferShare, OfferState


@dataclass
class CampaignOffer:
    offer_id: OfferId
    name: str
    share: OfferShare
    state: OfferState = OfferState.ACTIVE
    locked: bool = False

    @property
    def is_active(self) -> bool:
        return self.state is OfferState.ACTIVE
```

`apps/api/app/domain/keitaro/services/share_distribution.py`:

```python
def distribute(total: int, count: int) -> list[int]:
    if count <= 0:
        return []
    base, remainder = divmod(max(total, 0), count)
    return [base + (1 if index < remainder else 0) for index in range(count)]
```

`apps/api/app/domain/keitaro/entities/flow_offers.py`:

```python
from dataclasses import dataclass, field

from app.domain.keitaro.entities.campaign_offer import CampaignOffer
from app.domain.keitaro.exceptions import (
    OfferAlreadyExistsError,
    OfferNotFoundError,
    ShareTotalError,
)
from app.domain.keitaro.services.share_distribution import distribute
from app.domain.keitaro.value_objects.identifiers import OfferId, StreamId
from app.domain.keitaro.value_objects.offer_share import OfferShare, OfferState


@dataclass
class FlowOffers:
    stream_id: StreamId
    name: str
    offers: list[CampaignOffer] = field(default_factory=list)

    @classmethod
    def empty(cls, stream_id: StreamId, name: str) -> "FlowOffers":
        return cls(stream_id=stream_id, name=name)

    @classmethod
    def rehydrate(
        cls,
        stream_id: StreamId,
        name: str,
        offers: list[CampaignOffer],
    ) -> "FlowOffers":
        flow = cls(stream_id=stream_id, name=name, offers=offers)
        ids = [item.offer_id.value for item in offers]
        if len(ids) != len(set(ids)):
            raise OfferAlreadyExistsError("Flow contains duplicate offers")
        return flow

    def _find(self, offer_id: OfferId) -> CampaignOffer:
        for item in self.offers:
            if item.offer_id == offer_id:
                return item
        raise OfferNotFoundError(f"Offer {offer_id.value} is not in the flow")

    def add_offer(self, offer_id: OfferId, name: str) -> None:
        if any(item.offer_id == offer_id for item in self.offers):
            raise OfferAlreadyExistsError(f"Offer {offer_id.value} already exists in the flow")
        self.offers.append(
            CampaignOffer(
                offer_id=offer_id,
                name=name,
                share=OfferShare(0),
                state=OfferState.ACTIVE,
                locked=False,
            )
        )
        self._rebalance()

    def delete_offer(self, offer_id: OfferId) -> None:
        item = self._find(offer_id)
        item.state = OfferState.DELETED
        item.locked = False
        item.share = OfferShare(0)
        self._rebalance()

    def restore_offer(self, offer_id: OfferId) -> None:
        item = self._find(offer_id)
        item.state = OfferState.ACTIVE
        item.locked = False
        item.share = OfferShare(0)
        self._rebalance()

    def set_locked(self, offer_id: OfferId, locked: bool) -> None:
        item = self._find(offer_id)
        if item.state is OfferState.DELETED:
            raise OfferNotFoundError(f"Offer {offer_id.value} is deleted")
        item.locked = locked
        self._rebalance()

    def active_offers(self) -> list[CampaignOffer]:
        return [item for item in self.offers if item.is_active]

    def _rebalance(self) -> None:
        for item in self.offers:
            if not item.is_active:
                item.share = OfferShare(0)

        active = self.active_offers()
        if not active:
            return

        fixed = sum(item.share.value for item in active if item.locked)
        if fixed > 100:
            raise ShareTotalError("Locked shares exceed 100 percent")

        unlocked = [item for item in active if not item.locked]
        for share, item in zip(distribute(100 - fixed, len(unlocked)), unlocked, strict=True):
            item.share = OfferShare(share)
```

- [ ] **Step 5: Run domain tests**

Run: `cd apps/api && uv run pytest tests/domain -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/domain apps/api/tests/domain
git commit -m "feat(api): add offer rotation domain model"
```

---

## Task 2: Persistence Model and Repository

**Files:**
- Create: `apps/api/app/infrastructure/persistence/__init__.py`
- Create: `apps/api/app/infrastructure/persistence/models.py`
- Create: `apps/api/app/infrastructure/persistence/campaign_offer_repository.py`
- Create: `apps/api/app/domain/keitaro/snapshots.py`
- Modify: `apps/api/app/domain/keitaro/repositories.py` (create)
- Modify: `apps/api/tests/conftest.py`
- Test: `apps/api/tests/infrastructure/test_campaign_offer_repository.py`
- Create migration: `apps/api/alembic/versions/<generated>_add_campaign_offer_states.py`

**Interfaces:**
- Consumes: Task 1 entities.
- Produces:
  - `Base` metadata includes `campaign_offer_states`.
  - `CampaignOfferRepository` protocol with `list_by_campaign`, `save`, `sync_from_keitaro`.
  - `SqlAlchemyCampaignOfferRepository(session: AsyncSession)`.
  - `KeitaroFlowSnapshot(stream_id, name, offers)`, `KeitaroOfferSnapshot(offer_id, share)`.
  - `CatalogItem(id, name)`, `CampaignSummary(id, name, state, alias)`.
  - `CampaignOfferRepository.list_by_campaign(campaign_id: CampaignId) -> list[FlowOffers]`
  - `CampaignOfferRepository.save(campaign_id: CampaignId, flow: FlowOffers) -> None`
  - `CampaignOfferRepository.sync_from_keitaro(campaign_id, flows, seen_stream_ids, offer_names) -> None`

- [ ] **Step 1: Write the failing repository test**

Create `apps/api/tests/infrastructure/test_campaign_offer_repository.py`:

```python
from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.domain.keitaro.entities.campaign_offer import CampaignOffer
from app.domain.keitaro.entities.flow_offers import FlowOffers
from app.domain.keitaro.snapshots import KeitaroFlowSnapshot, KeitaroOfferSnapshot
from app.domain.keitaro.value_objects.identifiers import CampaignId, OfferId, StreamId
from app.domain.keitaro.value_objects.offer_share import OfferShare, OfferState
from app.infrastructure.database import Base
from app.infrastructure.persistence.campaign_offer_repository import (
    SqlAlchemyCampaignOfferRepository,
)


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db_session:
        yield db_session
    await engine.dispose()


async def test_save_and_load_flow(session: AsyncSession) -> None:
    repository = SqlAlchemyCampaignOfferRepository(session)
    flow = FlowOffers.rehydrate(
        StreamId(7),
        "Main",
        [
            CampaignOffer(OfferId(1), "One", OfferShare(70), OfferState.ACTIVE, True),
            CampaignOffer(OfferId(2), "Two", OfferShare(0), OfferState.DELETED, False),
        ],
    )

    await repository.save(CampaignId(3), flow)
    await session.commit()

    loaded = await repository.list_by_campaign(CampaignId(3))
    assert len(loaded) == 1
    assert loaded[0].name == "Main"
    assert [(item.offer_id.value, item.share.value, item.state.value, item.locked) for item in loaded[0].offers] == [
        (1, 70, "active", True),
        (2, 0, "deleted", False),
    ]


async def test_sync_marks_missing_offer_deleted(session: AsyncSession) -> None:
    repository = SqlAlchemyCampaignOfferRepository(session)
    await repository.save(
        CampaignId(3),
        FlowOffers.rehydrate(StreamId(7), "Main", [CampaignOffer(OfferId(1), "One", OfferShare(100))]),
    )
    await session.commit()

    await repository.sync_from_keitaro(
        CampaignId(3),
        [KeitaroFlowSnapshot(7, "Main", [KeitaroOfferSnapshot(2, 100)])],
        [7],
        {2: "Two"},
    )
    await session.commit()

    loaded = await repository.list_by_campaign(CampaignId(3))
    assert {item.offer_id.value: (item.share.value, item.state.value) for item in loaded[0].offers} == {
        1: (0, "deleted"),
        2: (100, "active"),
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && uv run pytest tests/infrastructure/test_campaign_offer_repository.py -q`

Expected: FAIL with `ModuleNotFoundError` for `snapshots` / repository.

- [ ] **Step 3: Add snapshots, protocol and SQLAlchemy model**

`apps/api/app/domain/keitaro/snapshots.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogItem:
    id: int
    name: str


@dataclass(frozen=True)
class CampaignSummary:
    id: int
    name: str
    state: str
    alias: str


@dataclass(frozen=True)
class KeitaroOfferSnapshot:
    offer_id: int
    share: int


@dataclass(frozen=True)
class KeitaroFlowSnapshot:
    stream_id: int
    name: str
    offers: list[KeitaroOfferSnapshot]
```

`apps/api/app/domain/keitaro/repositories.py`:

```python
from typing import Any, Protocol

from app.domain.keitaro.entities.flow_offers import FlowOffers
from app.domain.keitaro.snapshots import (
    CampaignSummary,
    CatalogItem,
    KeitaroFlowSnapshot,
)
from app.domain.keitaro.value_objects.identifiers import CampaignId


class CampaignOfferRepository(Protocol):
    async def list_by_campaign(self, campaign_id: CampaignId) -> list[FlowOffers]: ...

    async def save(self, campaign_id: CampaignId, flow: FlowOffers) -> None: ...

    async def sync_from_keitaro(
        self,
        campaign_id: CampaignId,
        flows: list[KeitaroFlowSnapshot],
        seen_stream_ids: list[int],
        offer_names: dict[int, str],
    ) -> None: ...


class CampaignGateway(Protocol):
    async def list_campaigns(self) -> list[CampaignSummary]: ...

    async def create_campaign(self, payload: dict[str, Any]) -> dict[str, Any]: ...


class CatalogGateway(Protocol):
    async def list_domains(self) -> list[CatalogItem]: ...

    async def list_groups(self) -> list[CatalogItem]: ...

    async def list_traffic_sources(self) -> list[CatalogItem]: ...

    async def list_offers(self) -> list[CatalogItem]: ...

    async def get_offer(self, offer_id: int) -> CatalogItem: ...


class FlowGateway(Protocol):
    async def list_flows(self, campaign_id: int) -> list[KeitaroFlowSnapshot]: ...

    async def create_google_flow(self, campaign_id: int, country_code: str) -> None: ...

    async def create_offer_flow(self, campaign_id: int, offer_id: int) -> None: ...

    async def update_offers(self, stream_id: int, offers: list[tuple[int, int]]) -> None: ...
```

`apps/api/app/infrastructure/persistence/models.py`:

```python
from sqlalchemy import Boolean, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class CampaignOfferModel(Base):
    __tablename__ = "campaign_offer_states"
    __table_args__ = (
        UniqueConstraint("campaign_id", "stream_id", "offer_id", name="uq_campaign_stream_offer"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_id: Mapped[int] = mapped_column(Integer, index=True)
    stream_id: Mapped[int] = mapped_column(Integer, index=True)
    stream_name: Mapped[str] = mapped_column(String(255))
    offer_id: Mapped[int] = mapped_column(Integer)
    offer_name: Mapped[str] = mapped_column(String(255))
    share: Mapped[int] = mapped_column(Integer, default=0)
    state: Mapped[str] = mapped_column(String(16), default="active")
    locked: Mapped[bool] = mapped_column(Boolean, default=False)
```

- [ ] **Step 4: Implement the repository**

`apps/api/app/infrastructure/persistence/campaign_offer_repository.py`:

```python
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.keitaro.entities.campaign_offer import CampaignOffer
from app.domain.keitaro.entities.flow_offers import FlowOffers
from app.domain.keitaro.snapshots import KeitaroFlowSnapshot
from app.domain.keitaro.value_objects.identifiers import CampaignId, OfferId, StreamId
from app.domain.keitaro.value_objects.offer_share import OfferShare, OfferState
from app.infrastructure.persistence.models import CampaignOfferModel


class SqlAlchemyCampaignOfferRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_campaign(self, campaign_id: CampaignId) -> list[FlowOffers]:
        result = await self._session.scalars(
            select(CampaignOfferModel)
            .where(CampaignOfferModel.campaign_id == campaign_id.value)
            .order_by(CampaignOfferModel.stream_id, CampaignOfferModel.id)
        )
        grouped: dict[int, FlowOffers] = {}
        for row in result:
            flow = grouped.setdefault(
                row.stream_id,
                FlowOffers.empty(StreamId(row.stream_id), row.stream_name),
            )
            flow.offers.append(
                CampaignOffer(
                    offer_id=OfferId(row.offer_id),
                    name=row.offer_name,
                    share=OfferShare(row.share),
                    state=OfferState(row.state),
                    locked=row.locked,
                )
            )
        return list(grouped.values())

    async def save(self, campaign_id: CampaignId, flow: FlowOffers) -> None:
        existing = {
            row.offer_id: row
            for row in await self._session.scalars(
                select(CampaignOfferModel).where(
                    CampaignOfferModel.campaign_id == campaign_id.value,
                    CampaignOfferModel.stream_id == flow.stream_id.value,
                )
            )
        }
        keep: set[int] = set()
        for item in flow.offers:
            keep.add(item.offer_id.value)
            row = existing.get(item.offer_id.value)
            if row is None:
                row = CampaignOfferModel(
                    campaign_id=campaign_id.value,
                    stream_id=flow.stream_id.value,
                    offer_id=item.offer_id.value,
                )
                self._session.add(row)
            row.stream_name = flow.name
            row.offer_name = item.name
            row.share = item.share.value
            row.state = item.state.value
            row.locked = item.locked
        stale = set(existing) - keep
        if stale:
            await self._session.execute(
                delete(CampaignOfferModel).where(
                    CampaignOfferModel.campaign_id == campaign_id.value,
                    CampaignOfferModel.stream_id == flow.stream_id.value,
                    CampaignOfferModel.offer_id.in_(stale),
                )
            )

    async def sync_from_keitaro(
        self,
        campaign_id: CampaignId,
        flows: list[KeitaroFlowSnapshot],
        seen_stream_ids: list[int],
        offer_names: dict[int, str],
    ) -> None:
        rows = list(
            await self._session.scalars(
                select(CampaignOfferModel).where(
                    CampaignOfferModel.campaign_id == campaign_id.value
                )
            )
        )
        by_key = {(row.stream_id, row.offer_id): row for row in rows}
        seen_keys: set[tuple[int, int]] = set()
        for flow in flows:
            for item in flow.offers:
                key = (flow.stream_id, item.offer_id)
                seen_keys.add(key)
                row = by_key.get(key)
                if row is None:
                    row = CampaignOfferModel(
                        campaign_id=campaign_id.value,
                        stream_id=flow.stream_id,
                        offer_id=item.offer_id,
                        locked=False,
                    )
                    self._session.add(row)
                row.stream_name = flow.name
                row.offer_name = offer_names.get(item.offer_id, f"Offer {item.offer_id}")
                row.share = item.share
                row.state = OfferState.ACTIVE.value
        for row in rows:
            if (row.stream_id, row.offer_id) not in seen_keys:
                row.share = 0
                row.state = OfferState.DELETED.value
                row.locked = False
```

- [ ] **Step 5: Add test DB fixtures and run tests**

Modify `apps/api/tests/conftest.py` to import `Base` and `models` so metadata is registered, and add:

```python
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.infrastructure.database import Base


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()
```

Run: `cd apps/api && uv run pytest tests/infrastructure -q`

Expected: PASS.

- [ ] **Step 6: Generate and apply the migration**

Modify `apps/api/alembic/env.py` so autogenerate sees the model:

```python
from app.infrastructure.database import Base
from app.infrastructure.persistence import models  # noqa: F401
```

Run:

```bash
cd apps/api
uv run alembic revision --autogenerate -m "add campaign offer states"
uv run alembic upgrade head
```

Expected: a revision creates `campaign_offer_states`; `alembic current` shows the new head.

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/domain/keitaro/snapshots.py apps/api/app/domain/keitaro/repositories.py \
  apps/api/app/infrastructure/persistence apps/api/alembic/versions apps/api/tests
git commit -m "feat(api): persist offer state in postgres"
```

---

## Task 3: Keitaro HTTP Client and Gateways

**Files:**
- Create: `apps/api/app/infrastructure/keitaro/__init__.py`
- Create: `apps/api/app/infrastructure/keitaro/errors.py`
- Create: `apps/api/app/infrastructure/keitaro/client.py`
- Create: `apps/api/app/infrastructure/keitaro/campaigns.py`
- Create: `apps/api/app/infrastructure/keitaro/flows.py`
- Create: `apps/api/app/domain/keitaro/constants.py`
- Test: `apps/api/tests/infrastructure/test_keitaro_client.py`
- Test: `apps/api/tests/infrastructure/test_keitaro_gateways.py`

**Interfaces:**
- Consumes: `CatalogItem`, `CampaignSummary`, `KeitaroFlowSnapshot`, `KeitaroOfferSnapshot`.
- Produces:
  - `KeitaroClient(base_url, api_key, timeout=10.0)` async context manager
  - `KeitaroClient.get(path, params=None) -> object`
  - `KeitaroClient.post(path, json) -> object`
  - `KeitaroClient.put(path, json) -> object`
  - `KeitaroCampaignGateway(client)` with `list_campaigns`, `create_campaign`, `list_domains`, `list_groups`, `list_traffic_sources`, `list_offers`, `get_offer`
  - `KeitaroFlowGateway(client)` with `list_flows`, `create_google_flow`, `create_offer_flow`, `update_offers`
  - `GOOGLE_REDIRECT_URL`, `COUNTRY_FILTER_NAME`, `REDIRECT_ACTION_TYPE`, `OFFERS_ACTION_TYPE`, `OFFER_FLOW_SCHEMA`

- [ ] **Step 1: Write failing client tests**

Create `apps/api/tests/infrastructure/test_keitaro_client.py`:

```python
import httpx
import pytest
import respx

from app.infrastructure.keitaro.client import KeitaroClient
from app.infrastructure.keitaro.errors import KeitaroResponseError, KeitaroUnavailableError


@respx.mock
async def test_client_sends_api_key() -> None:
    route = respx.get("https://tracker.example.com/admin_api/v1/campaigns").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "One"}])
    )
    async with KeitaroClient("https://tracker.example.com", "secret") as client:
        result = await client.get("/campaigns")

    assert result == [{"id": 1, "name": "One"}]
    assert route.calls[0].request.headers["Api-Key"] == "secret"


@respx.mock
async def test_client_retries_get_on_5xx() -> None:
    respx.get("https://tracker.example.com/admin_api/v1/campaigns").mock(
        side_effect=[
            httpx.Response(500),
            httpx.Response(200, json=[]),
        ]
    )
    async with KeitaroClient("https://tracker.example.com", "secret") as client:
        assert await client.get("/campaigns") == []


@respx.mock
async def test_client_does_not_retry_post() -> None:
    route = respx.post("https://tracker.example.com/admin_api/v1/campaigns").mock(
        return_value=httpx.Response(500)
    )
    async with KeitaroClient("https://tracker.example.com", "secret") as client:
        with pytest.raises(KeitaroUnavailableError):
            await client.post("/campaigns", json={})
    assert route.call_count == 1


@respx.mock
async def test_client_surfaces_keitaro_error_body() -> None:
    respx.get("https://tracker.example.com/admin_api/v1/campaigns").mock(
        return_value=httpx.Response(400, json={"message": "Bad request"})
    )
    async with KeitaroClient("https://tracker.example.com", "secret") as client:
        with pytest.raises(KeitaroResponseError, match="Bad request"):
            await client.get("/campaigns")
```

- [ ] **Step 2: Run to verify failure**

Run: `cd apps/api && uv run pytest tests/infrastructure/test_keitaro_client.py -q`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement errors and client**

`apps/api/app/infrastructure/keitaro/errors.py`:

```python
class KeitaroError(Exception):
    pass


class KeitaroUnavailableError(KeitaroError):
    pass


class KeitaroResponseError(KeitaroError):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
```

`apps/api/app/infrastructure/keitaro/client.py`:

```python
import asyncio
from types import TracebackType
from typing import Any, Self

import httpx

from app.infrastructure.keitaro.errors import (
    KeitaroResponseError,
    KeitaroUnavailableError,
)


class KeitaroClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 10.0) -> None:
        if not base_url or not api_key:
            raise KeitaroUnavailableError("Keitaro URL and API key are not configured")
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Api-Key": api_key, "Accept": "application/json"},
            timeout=timeout,
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        attempts = 3 if method in {"GET", "PUT"} else 1
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                response = await self._client.request(method, f"/admin_api/v1{path}", **kwargs)
            except httpx.HTTPError as error:
                last_error = error
                if attempt + 1 == attempts:
                    break
                await asyncio.sleep(0.2 * (2**attempt))
                continue

            if response.status_code >= 500:
                last_error = KeitaroUnavailableError(
                    f"Keitaro returned {response.status_code}"
                )
                if attempt + 1 == attempts:
                    break
                await asyncio.sleep(0.2 * (2**attempt))
                continue
            if response.status_code >= 400:
                message = response.text
                try:
                    payload = response.json()
                    message = payload.get("message") or payload.get("error") or message
                except ValueError:
                    pass
                raise KeitaroResponseError(response.status_code, str(message))
            return response.json()

        raise KeitaroUnavailableError(str(last_error or "Keitaro is unavailable"))

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return await self._request("GET", path, params=params)

    async def post(self, path: str, json: Any) -> Any:
        return await self._request("POST", path, json=json)

    async def put(self, path: str, json: Any) -> Any:
        return await self._request("PUT", path, json=json)
```

- [ ] **Step 4: Add constants and gateways**

`apps/api/app/domain/keitaro/constants.py`:

```python
GOOGLE_REDIRECT_URL = "https://www.google.com"
COUNTRY_FILTER_NAME = "country"
REDIRECT_ACTION_TYPE = "http"
OFFERS_ACTION_TYPE = "http"
OFFER_FLOW_SCHEMA = "landings"
```

These values were verified against the live Keitaro instance on 2026-11-14: redirect streams use `schema="redirect"` plus `action_type="http"` and `action_payload=<url>`; offer streams use `schema="landings"` plus `action_type="http"` and `action_payload=""`. `action_options` is `null` and must not be sent.

`apps/api/app/infrastructure/keitaro/campaigns.py`:

```python
from typing import Any

from app.domain.keitaro.snapshots import CampaignSummary, CatalogItem
from app.infrastructure.keitaro.client import KeitaroClient

PAGE_SIZE = 100


class KeitaroCampaignGateway:
    def __init__(self, client: KeitaroClient) -> None:
        self._client = client

    async def list_campaigns(self) -> list[CampaignSummary]:
        campaigns: list[CampaignSummary] = []
        offset = 0
        while True:
            payload = await self._client.get(
                "/campaigns", params={"offset": offset, "limit": PAGE_SIZE}
            )
            page = list(payload)
            campaigns.extend(
                CampaignSummary(
                    id=item["id"],
                    name=item["name"],
                    state=item.get("state", "active"),
                    alias=item.get("alias", ""),
                )
                for item in page
            )
            if len(page) < PAGE_SIZE:
                return campaigns
            offset += PAGE_SIZE

    async def create_campaign(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._client.post("/campaigns", json=payload)

    async def list_domains(self) -> list[CatalogItem]:
        return [
            CatalogItem(id=item["id"], name=item["name"])
            for item in await self._client.get("/domains")
        ]

    async def list_groups(self) -> list[CatalogItem]:
        return [
            CatalogItem(id=item["id"], name=item["name"])
            for item in await self._client.get("/groups", params={"type": "campaigns"})
        ]

    async def list_traffic_sources(self) -> list[CatalogItem]:
        return [
            CatalogItem(id=item["id"], name=item["name"])
            for item in await self._client.get("/traffic_sources")
        ]

    async def list_offers(self) -> list[CatalogItem]:
        return [
            CatalogItem(id=item["id"], name=item["name"])
            for item in await self._client.get("/offers")
        ]

    async def get_offer(self, offer_id: int) -> CatalogItem:
        item = await self._client.get(f"/offers/{offer_id}")
        return CatalogItem(id=item["id"], name=item["name"])
```

`apps/api/app/infrastructure/keitaro/flows.py`:

```python
from typing import Any

from app.domain.keitaro.constants import (
    COUNTRY_FILTER_NAME,
    GOOGLE_REDIRECT_URL,
    OFFER_FLOW_SCHEMA,
    OFFERS_ACTION_TYPE,
    REDIRECT_ACTION_TYPE,
)
from app.domain.keitaro.snapshots import KeitaroFlowSnapshot, KeitaroOfferSnapshot
from app.infrastructure.keitaro.client import KeitaroClient

READ_ONLY_STREAM_FIELDS = {"id", "updated_at", "created_at"}


class KeitaroFlowGateway:
    def __init__(self, client: KeitaroClient) -> None:
        self._client = client

    async def list_flows(self, campaign_id: int) -> list[KeitaroFlowSnapshot]:
        payload = await self._client.get(f"/campaigns/{campaign_id}/streams")
        return [
            KeitaroFlowSnapshot(
                stream_id=item["id"],
                name=item.get("name", f"Flow {item['id']}"),
                offers=[
                    KeitaroOfferSnapshot(
                        offer_id=offer["offer_id"],
                        share=int(offer.get("share", 0)),
                    )
                    for offer in item.get("offers", [])
                ],
            )
            for item in payload
        ]

    async def create_google_flow(self, campaign_id: int, country_code: str) -> None:
        await self._client.post(
            "/streams",
            json={
                "campaign_id": campaign_id,
                "type": "regular",
                "name": "Google",
                "position": 1,
                "weight": 50,
                "state": "active",
                "schema": "redirect",
                "action_type": REDIRECT_ACTION_TYPE,
                "action_payload": GOOGLE_REDIRECT_URL,
                "filters": [
                    {
                        "name": COUNTRY_FILTER_NAME,
                        "mode": "accept",
                        "payload": [country_code],
                    }
                ],
            },
        )

    async def create_offer_flow(self, campaign_id: int, offer_id: int) -> None:
        await self._client.post(
            "/streams",
            json={
                "campaign_id": campaign_id,
                "type": "regular",
                "name": "Offer",
                "position": 2,
                "weight": 50,
                "state": "active",
                "schema": OFFER_FLOW_SCHEMA,
                "action_type": OFFERS_ACTION_TYPE,
                "action_payload": "",
                "offers": [{"offer_id": offer_id, "share": 100, "state": "active"}],
            },
        )

    async def update_offers(self, stream_id: int, offers: list[tuple[int, int]]) -> None:
        stream: dict[str, Any] = await self._client.get(f"/streams/{stream_id}")
        payload = {
            key: value
            for key, value in stream.items()
            if key not in READ_ONLY_STREAM_FIELDS
        }
        payload["offers"] = [
            {"offer_id": offer_id, "share": share, "state": "active"}
            for offer_id, share in offers
        ]
        await self._client.put(f"/streams/{stream_id}", json=payload)
```

- [ ] **Step 5: Add gateway tests**

Create `apps/api/tests/infrastructure/test_keitaro_gateways.py`:

```python
import httpx
import respx

from app.infrastructure.keitaro.campaigns import KeitaroCampaignGateway
from app.infrastructure.keitaro.client import KeitaroClient
from app.infrastructure.keitaro.flows import KeitaroFlowGateway


@respx.mock
async def test_campaign_gateway_paginates() -> None:
    first = [{"id": index, "name": str(index), "state": "active", "alias": ""} for index in range(100)]
    second = [{"id": 100, "name": "last", "state": "active", "alias": ""}]
    respx.get("https://tracker.example.com/admin_api/v1/campaigns", params={"offset": 0, "limit": 100}).mock(
        return_value=httpx.Response(200, json=first)
    )
    respx.get("https://tracker.example.com/admin_api/v1/campaigns", params={"offset": 100, "limit": 100}).mock(
        return_value=httpx.Response(200, json=second)
    )
    async with KeitaroClient("https://tracker.example.com", "secret") as client:
        result = await KeitaroCampaignGateway(client).list_campaigns()
    assert len(result) == 101


@respx.mock
async def test_update_offers_preserves_filters_and_omits_deleted() -> None:
    stream = {
        "id": 5,
        "campaign_id": 3,
        "type": "regular",
        "name": "Main",
        "schema": "landings",
        "action_type": "http",
        "updated_at": "2026-01-01T00:00:00Z",
        "filters": [{"name": "country", "mode": "accept", "payload": "US"}],
        "offers": [{"offer_id": 1, "share": 100}],
    }
    respx.get("https://tracker.example.com/admin_api/v1/streams/5").mock(
        return_value=httpx.Response(200, json=stream)
    )
    put_route = respx.put("https://tracker.example.com/admin_api/v1/streams/5").mock(
        return_value=httpx.Response(200, json=stream)
    )
    async with KeitaroClient("https://tracker.example.com", "secret") as client:
        await KeitaroFlowGateway(client).update_offers(5, [(1, 100)])
    body = put_route.calls[0].request.read().decode()
    assert "filters" in body
    assert '"offer_id":1' in body
```

- [ ] **Step 6: Run tests**

Run: `cd apps/api && uv run pytest tests/infrastructure -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/domain/keitaro/constants.py apps/api/app/infrastructure/keitaro apps/api/tests/infrastructure
git commit -m "feat(api): add keitaro http gateways"
```

---

## Task 4: Read Use Cases and API Endpoints

**Files:**
- Create: `apps/api/app/usecase/keitaro/list_campaigns_usecase.py`
- Create: `apps/api/app/usecase/keitaro/list_offers_usecase.py`
- Create: `apps/api/app/usecase/keitaro/get_form_options_usecase.py`
- Create: `apps/api/app/usecase/keitaro/refresh_campaign_offers_usecase.py`
- Create: `apps/api/app/presentation/api/keitaro/schemas.py`
- Create: `apps/api/app/presentation/api/keitaro/responses.py`
- Create: `apps/api/app/presentation/api/keitaro/dependencies.py`
- Create: `apps/api/app/presentation/api/keitaro/handlers/campaigns.py`
- Create: `apps/api/app/presentation/api/keitaro/handlers/offers.py`
- Modify: `apps/api/app/presentation/api/router.py`
- Test: `apps/api/tests/presentation/test_read_api.py`

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces endpoints:
  - `GET /api/v1/campaigns -> list[CampaignSummaryResponse]`
  - `GET /api/v1/campaigns/form-options -> FormOptionsResponse`
  - `GET /api/v1/offers -> list[CatalogItemResponse]`
  - `GET /api/v1/campaigns/{campaign_id}/offers -> OfferRotationResponse`
- Produces schemas: `CampaignSummaryResponse`, `CatalogItemResponse`, `FormOptionsResponse`, `OfferResponse`, `FlowOffersResponse`, `OfferRotationResponse`.

- [ ] **Step 1: Make the API test client use sqlite**

Modify `apps/api/tests/conftest.py` so the app dependency returns the same sqlite session factory:

```python
import os
from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

os.environ.setdefault("KEITARO_BASE_URL", "https://tracker.example.com")
os.environ.setdefault("KEITARO_API_KEY", "secret")

from app.infrastructure.database import Base, get_session  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest_asyncio.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncClient]:
    app = create_app()

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
```

Keep the existing `db_session` fixture below it.

- [ ] **Step 3: Write the failing API test**

Create `apps/api/tests/presentation/test_read_api.py`:

```python
import httpx
import respx
from httpx import AsyncClient

from app.infrastructure.config import get_settings


@respx.mock
async def test_read_endpoints(client: AsyncClient, monkeypatch) -> None:
    monkeypatch.setenv("KEITARO_BASE_URL", "https://tracker.example.com")
    monkeypatch.setenv("KEITARO_API_KEY", "secret")
    get_settings.cache_clear()

    respx.get("https://tracker.example.com/admin_api/v1/campaigns", params={"offset": 0, "limit": 100}).mock(
        return_value=httpx.Response(200, json=[{"id": 4, "name": "Campa", "state": "active", "alias": "campa"}])
    )
    respx.get("https://tracker.example.com/admin_api/v1/offers").mock(
        return_value=httpx.Response(200, json=[{"id": 7, "name": "Offer Seven"}])
    )
    respx.get("https://tracker.example.com/admin_api/v1/domains").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "example.com"}])
    )
    respx.get("https://tracker.example.com/admin_api/v1/groups", params={"type": "campaigns"}).mock(
        return_value=httpx.Response(200, json=[{"id": 2, "name": "Group"}])
    )
    respx.get("https://tracker.example.com/admin_api/v1/traffic_sources").mock(
        return_value=httpx.Response(200, json=[{"id": 3, "name": "Source"}])
    )
    respx.get("https://tracker.example.com/admin_api/v1/campaigns/4/streams").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": 10, "name": "Google", "offers": []},
                {"id": 11, "name": "Main", "offers": [{"offer_id": 7, "share": 100}]},
            ],
        )
    )

    assert (await client.get("/api/v1/campaigns")).json() == [
        {"id": 4, "name": "Campa", "state": "active", "alias": "campa"}
    ]
    assert (await client.get("/api/v1/offers")).json() == [{"id": 7, "name": "Offer Seven"}]
    options = (await client.get("/api/v1/campaigns/form-options")).json()
    assert options["domains"] == [{"id": 1, "name": "example.com"}]
    assert options["groups"] == [{"id": 2, "name": "Group"}]
    assert options["traffic_sources"] == [{"id": 3, "name": "Source"}]
    rotation = (await client.get("/api/v1/campaigns/4/offers")).json()
    assert rotation["flows"] == [
        {
            "stream_id": 11,
            "name": "Main",
            "offers": [
                {"offer_id": 7, "name": "Offer Seven", "share": 100, "state": "active", "locked": False}
            ],
        }
    ]
```

- [ ] **Step 3: Run to verify failure**

Run: `cd apps/api && uv run pytest tests/presentation/test_read_api.py -q`

Expected: FAIL with 404 for the new routes.

- [ ] **Step 4: Implement use cases**

`apps/api/app/usecase/keitaro/list_campaigns_usecase.py`:

```python
from app.domain.keitaro.repositories import CampaignGateway
from app.domain.keitaro.snapshots import CampaignSummary


class ListCampaignsUseCase:
    def __init__(self, gateway: CampaignGateway) -> None:
        self._gateway = gateway

    async def execute(self) -> list[CampaignSummary]:
        return await self._gateway.list_campaigns()
```

`apps/api/app/usecase/keitaro/list_offers_usecase.py`:

```python
from app.domain.keitaro.repositories import CatalogGateway
from app.domain.keitaro.snapshots import CatalogItem


class ListOffersUseCase:
    def __init__(self, gateway: CatalogGateway) -> None:
        self._gateway = gateway

    async def execute(self, search: str = "") -> list[CatalogItem]:
        offers = await self._gateway.list_offers()
        term = search.strip().lower()
        if not term:
            return offers
        return [offer for offer in offers if term in offer.name.lower()]
```

`apps/api/app/usecase/keitaro/get_form_options_usecase.py`:

```python
from app.domain.keitaro.repositories import CatalogGateway
from app.domain.keitaro.snapshots import CatalogItem


class GetFormOptionsUseCase:
    def __init__(self, gateway: CatalogGateway) -> None:
        self._gateway = gateway

    async def execute(self) -> tuple[list[CatalogItem], list[CatalogItem], list[CatalogItem]]:
        return (
            await self._gateway.list_domains(),
            await self._gateway.list_groups(),
            await self._gateway.list_traffic_sources(),
        )
```

`apps/api/app/usecase/keitaro/refresh_campaign_offers_usecase.py`:

```python
from app.domain.keitaro.entities.flow_offers import FlowOffers
from app.domain.keitaro.repositories import (
    CampaignOfferRepository,
    CatalogGateway,
    FlowGateway,
)
from app.domain.keitaro.value_objects.identifiers import CampaignId


class RefreshCampaignOffersUseCase:
    def __init__(
        self,
        repository: CampaignOfferRepository,
        flows: FlowGateway,
        catalog: CatalogGateway,
    ) -> None:
        self._repository = repository
        self._flows = flows
        self._catalog = catalog

    async def execute(self, campaign_id: CampaignId) -> list[FlowOffers]:
        snapshots = await self._flows.list_flows(campaign_id.value)
        non_empty = [flow for flow in snapshots if flow.offers]
        offers = await self._catalog.list_offers()
        names = {offer.id: offer.name for offer in offers}
        await self._repository.sync_from_keitaro(
            campaign_id,
            non_empty,
            [flow.stream_id for flow in snapshots],
            names,
        )
        return await self._repository.list_by_campaign(campaign_id)
```

- [ ] **Step 5: Implement schemas, responses and dependencies**

`apps/api/app/presentation/api/keitaro/schemas.py`:

```python
from pydantic import BaseModel


class CampaignSummaryResponse(BaseModel):
    id: int
    name: str
    state: str
    alias: str


class CatalogItemResponse(BaseModel):
    id: int
    name: str


class FormOptionsResponse(BaseModel):
    domains: list[CatalogItemResponse]
    groups: list[CatalogItemResponse]
    traffic_sources: list[CatalogItemResponse]


class OfferResponse(BaseModel):
    offer_id: int
    name: str
    share: int
    state: str
    locked: bool


class FlowOffersResponse(BaseModel):
    stream_id: int
    name: str
    offers: list[OfferResponse]


class OfferRotationResponse(BaseModel):
    campaign_id: int
    flows: list[FlowOffersResponse]
```

`apps/api/app/presentation/api/keitaro/responses.py`:

```python
from app.domain.keitaro.entities.flow_offers import FlowOffers
from app.presentation.api.keitaro.schemas import (
    FlowOffersResponse,
    OfferResponse,
    OfferRotationResponse,
)


def to_rotation_response(campaign_id: int, flows: list[FlowOffers]) -> OfferRotationResponse:
    return OfferRotationResponse(
        campaign_id=campaign_id,
        flows=[
            FlowOffersResponse(
                stream_id=flow.stream_id.value,
                name=flow.name,
                offers=[
                    OfferResponse(
                        offer_id=item.offer_id.value,
                        name=item.name,
                        share=item.share.value,
                        state=item.state.value,
                        locked=item.locked,
                    )
                    for item in flow.offers
                ],
            )
            for flow in flows
        ],
    )
```

`apps/api/app/presentation/api/keitaro/dependencies.py`:

```python
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.config import Settings, get_settings
from app.infrastructure.database import get_session
from app.infrastructure.keitaro.campaigns import KeitaroCampaignGateway
from app.infrastructure.keitaro.client import KeitaroClient
from app.infrastructure.keitaro.flows import KeitaroFlowGateway
from app.infrastructure.persistence.campaign_offer_repository import (
    SqlAlchemyCampaignOfferRepository,
)
from app.usecase.keitaro.get_form_options_usecase import GetFormOptionsUseCase
from app.usecase.keitaro.list_campaigns_usecase import ListCampaignsUseCase
from app.usecase.keitaro.list_offers_usecase import ListOffersUseCase
from app.usecase.keitaro.refresh_campaign_offers_usecase import (
    RefreshCampaignOffersUseCase,
)


SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_keitaro_client(settings: SettingsDep) -> AsyncIterator[KeitaroClient]:
    async with KeitaroClient(settings.keitaro_base_url, settings.keitaro_api_key) as client:
        yield client


ClientDep = Annotated[KeitaroClient, Depends(get_keitaro_client)]


def get_campaign_gateway(client: ClientDep) -> KeitaroCampaignGateway:
    return KeitaroCampaignGateway(client)


def get_flow_gateway(client: ClientDep) -> KeitaroFlowGateway:
    return KeitaroFlowGateway(client)


def get_offer_repository(session: SessionDep) -> SqlAlchemyCampaignOfferRepository:
    return SqlAlchemyCampaignOfferRepository(session)


def get_list_campaigns_usecase(
    gateway: Annotated[KeitaroCampaignGateway, Depends(get_campaign_gateway)],
) -> ListCampaignsUseCase:
    return ListCampaignsUseCase(gateway)


def get_list_offers_usecase(
    gateway: Annotated[KeitaroCampaignGateway, Depends(get_campaign_gateway)],
) -> ListOffersUseCase:
    return ListOffersUseCase(gateway)


def get_form_options_usecase(
    gateway: Annotated[KeitaroCampaignGateway, Depends(get_campaign_gateway)],
) -> GetFormOptionsUseCase:
    return GetFormOptionsUseCase(gateway)


def get_refresh_usecase(
    repository: Annotated[SqlAlchemyCampaignOfferRepository, Depends(get_offer_repository)],
    flows: Annotated[KeitaroFlowGateway, Depends(get_flow_gateway)],
    catalog: Annotated[KeitaroCampaignGateway, Depends(get_campaign_gateway)],
) -> RefreshCampaignOffersUseCase:
    return RefreshCampaignOffersUseCase(repository, flows, catalog)
```

- [ ] **Step 6: Add handlers and router**

`apps/api/app/presentation/api/keitaro/handlers/campaigns.py`:

```python
from typing import Annotated

from fastapi import APIRouter, Depends

from app.presentation.api.keitaro.dependencies import (
    get_form_options_usecase,
    get_list_campaigns_usecase,
    get_refresh_usecase,
)
from app.presentation.api.keitaro.responses import to_rotation_response
from app.presentation.api.keitaro.schemas import (
    CampaignSummaryResponse,
    CatalogItemResponse,
    FormOptionsResponse,
    OfferRotationResponse,
)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("", response_model=list[CampaignSummaryResponse])
async def list_campaigns(usecase=Depends(get_list_campaigns_usecase)):
    return [CampaignSummaryResponse(**item.__dict__) for item in await usecase.execute()]


@router.get("/form-options", response_model=FormOptionsResponse)
async def form_options(usecase=Depends(get_form_options_usecase)):
    domains, groups, sources = await usecase.execute()
    return FormOptionsResponse(
        domains=[CatalogItemResponse(**item.__dict__) for item in domains],
        groups=[CatalogItemResponse(**item.__dict__) for item in groups],
        traffic_sources=[CatalogItemResponse(**item.__dict__) for item in sources],
    )


@router.get("/{campaign_id}/offers", response_model=OfferRotationResponse)
async def refresh_offers(
    campaign_id: int,
    usecase=Depends(get_refresh_usecase),
):
    from app.domain.keitaro.value_objects.identifiers import CampaignId

    flows = await usecase.execute(CampaignId(campaign_id))
    return to_rotation_response(campaign_id, flows)
```

`apps/api/app/presentation/api/keitaro/handlers/offers.py`:

```python
from fastapi import APIRouter, Depends

from app.presentation.api.keitaro.dependencies import get_list_offers_usecase
from app.presentation.api.keitaro.schemas import CatalogItemResponse

router = APIRouter(prefix="/offers", tags=["offers"])


@router.get("", response_model=list[CatalogItemResponse])
async def list_offers(search: str = "", usecase=Depends(get_list_offers_usecase)):
    return [CatalogItemResponse(**item.__dict__) for item in await usecase.execute(search)]
```

Modify `apps/api/app/presentation/api/router.py`:

```python
from fastapi import APIRouter

from app.presentation.api.health.handlers import router as health_router
from app.presentation.api.keitaro.handlers.campaigns import router as campaigns_router
from app.presentation.api.keitaro.handlers.offers import router as offers_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(campaigns_router)
api_router.include_router(offers_router)
```

- [ ] **Step 7: Run tests**

Run: `cd apps/api && uv run pytest tests/presentation/test_read_api.py -q`

Expected: PASS. If the test env cache interferes, `get_settings.cache_clear()` in the test handles it.

- [ ] **Step 8: Commit**

```bash
git add apps/api/app/usecase/keitaro apps/api/app/presentation/api apps/api/tests/presentation
git commit -m "feat(api): expose campaigns, offers and flow refresh"
```

---

## Task 5: Campaign Creator

**Files:**
- Create: `apps/api/app/usecase/keitaro/create_campaign_usecase.py`
- Modify: `apps/api/app/presentation/api/keitaro/schemas.py`
- Modify: `apps/api/app/presentation/api/keitaro/handlers/campaigns.py`
- Modify: `apps/api/app/presentation/api/keitaro/dependencies.py`
- Test: `apps/api/tests/presentation/test_create_campaign.py`

**Interfaces:**
- Consumes: `CampaignGateway.create_campaign`, `KeitaroFlowGateway.create_google_flow`, `create_offer_flow`, `CountryCode`.
- Produces:
  - `CreateCampaignRequest` with `name`, `country_code`, `offer_id`, `domain_id`, `group_id`, `traffic_source_id`.
  - `POST /api/v1/campaigns -> 201 CampaignSummaryResponse`.
  - `CreateCampaignUseCase.execute(name, country_code, offer_id, domain_id, group_id, traffic_source_id) -> CampaignSummary`.

- [ ] **Step 1: Write the failing creator test**

Create `apps/api/tests/presentation/test_create_campaign.py`:

```python
import json

import httpx
import respx
from httpx import AsyncClient


@respx.mock
async def test_create_campaign_builds_two_flows(client: AsyncClient) -> None:
    campaign_route = respx.post("https://tracker.example.com/admin_api/v1/campaigns").mock(
        return_value=httpx.Response(200, json={"id": 42, "name": "MX Campaign"})
    )
    flow_route = respx.post("https://tracker.example.com/admin_api/v1/streams").mock(
        side_effect=[
            httpx.Response(200, json={"id": 100}),
            httpx.Response(200, json={"id": 101}),
        ]
    )

    response = await client.post(
        "/api/v1/campaigns",
        json={
            "name": "MX Campaign",
            "country_code": "mx",
            "offer_id": 7,
            "domain_id": 1,
            "group_id": 2,
            "traffic_source_id": 3,
        },
    )

    assert response.status_code == 201
    assert response.json()["id"] == 42
    campaign_body = json.loads(campaign_route.calls[0].request.read())
    assert campaign_body["domain_id"] == 1
    assert campaign_body["group_id"] == "2"
    assert campaign_body["traffic_source_id"] == 3

    google_body = json.loads(flow_route.calls[0].request.read())
    assert google_body["schema"] == "redirect"
    assert google_body["action_type"] == "http"
    assert google_body["action_payload"] == "https://www.google.com"
    assert "action_options" not in google_body
    assert google_body["filters"] == [{"name": "country", "mode": "accept", "payload": ["MX"]}]

    offer_body = json.loads(flow_route.calls[1].request.read())
    assert offer_body["schema"] == "landings"
    assert offer_body["action_type"] == "http"
    assert offer_body["offers"] == [{"offer_id": 7, "share": 100, "state": "active"}]
```

The test uses the configured test env. Ensure `KEITARO_BASE_URL` / `KEITARO_API_KEY` are set in `apps/api/tests/conftest.py` before `create_app()`:

```python
import os

os.environ.setdefault("KEITARO_BASE_URL", "https://tracker.example.com")
os.environ.setdefault("KEITARO_API_KEY", "secret")
```

- [ ] **Step 2: Run to verify failure**

Run: `cd apps/api && uv run pytest tests/presentation/test_create_campaign.py -q`

Expected: FAIL with 405/404 because the POST route is absent.

- [ ] **Step 3: Implement the use case**

`apps/api/app/usecase/keitaro/create_campaign_usecase.py`:

```python
import re
import uuid

from app.domain.keitaro.exceptions import InvalidCountryCodeError
from app.domain.keitaro.repositories import CampaignGateway, FlowGateway
from app.domain.keitaro.snapshots import CampaignSummary
from app.domain.keitaro.value_objects.country import CountryCode


def _slug(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40] or "campaign"
    return f"{base}-{uuid.uuid4().hex[:8]}"


class CreateCampaignUseCase:
    def __init__(self, campaigns: CampaignGateway, flows: FlowGateway) -> None:
        self._campaigns = campaigns
        self._flows = flows

    async def execute(
        self,
        name: str,
        country_code: str,
        offer_id: int,
        domain_id: int,
        group_id: int,
        traffic_source_id: int,
    ) -> CampaignSummary:
        if not name.strip():
            raise InvalidCountryCodeError("Campaign name is required")
        try:
            country = CountryCode(country_code)
        except ValueError as error:
            raise InvalidCountryCodeError(str(error)) from error
        if offer_id <= 0 or domain_id <= 0 or group_id <= 0 or traffic_source_id <= 0:
            raise InvalidCountryCodeError("Offer, domain, group and traffic source are required")

        created = await self._campaigns.create_campaign(
            {
                "name": name.strip(),
                "alias": _slug(name),
                "type": "position",
                "state": "active",
                "domain_id": domain_id,
                "group_id": str(group_id),
                "traffic_source_id": traffic_source_id,
            }
        )
        campaign_id = int(created["id"])
        await self._flows.create_google_flow(campaign_id, country.value)
        await self._flows.create_offer_flow(campaign_id, offer_id)
        return CampaignSummary(
            id=campaign_id,
            name=str(created.get("name", name.strip())),
            state=str(created.get("state", "active")),
            alias=str(created.get("alias", "")),
        )
```

- [ ] **Step 4: Add request schema, dependency and handler**

Append to `apps/api/app/presentation/api/keitaro/schemas.py`:

```python
class CreateCampaignRequest(BaseModel):
    name: str
    country_code: str
    offer_id: int
    domain_id: int
    group_id: int
    traffic_source_id: int
```

Append to `apps/api/app/presentation/api/keitaro/dependencies.py`:

```python
from app.usecase.keitaro.create_campaign_usecase import CreateCampaignUseCase


def get_create_campaign_usecase(
    campaigns: Annotated[KeitaroCampaignGateway, Depends(get_campaign_gateway)],
    flows: Annotated[KeitaroFlowGateway, Depends(get_flow_gateway)],
) -> CreateCampaignUseCase:
    return CreateCampaignUseCase(campaigns, flows)
```

Append to `apps/api/app/presentation/api/keitaro/handlers/campaigns.py`:

```python
from fastapi import status

from app.presentation.api.keitaro.dependencies import get_create_campaign_usecase
from app.presentation.api.keitaro.schemas import CreateCampaignRequest


@router.post("", response_model=CampaignSummaryResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CreateCampaignRequest,
    usecase=Depends(get_create_campaign_usecase),
):
    created = await usecase.execute(
        payload.name,
        payload.country_code,
        payload.offer_id,
        payload.domain_id,
        payload.group_id,
        payload.traffic_source_id,
    )
    return CampaignSummaryResponse(**created.__dict__)
```

- [ ] **Step 5: Run the creator test**

Run: `cd apps/api && uv run pytest tests/presentation/test_create_campaign.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/usecase/keitaro/create_campaign_usecase.py apps/api/app/presentation/api apps/api/tests
git commit -m "feat(api): create campaigns with google and offer flows"
```

---

## Task 6: Local Offer Mutations

**Files:**
- Create: `apps/api/app/usecase/keitaro/add_offer_usecase.py`
- Create: `apps/api/app/usecase/keitaro/delete_offer_usecase.py`
- Create: `apps/api/app/usecase/keitaro/restore_offer_usecase.py`
- Create: `apps/api/app/usecase/keitaro/set_offer_lock_usecase.py`
- Modify: `apps/api/app/presentation/api/keitaro/schemas.py`
- Modify: `apps/api/app/presentation/api/keitaro/handlers/campaigns.py`
- Modify: `apps/api/app/presentation/api/keitaro/dependencies.py`
- Test: `apps/api/tests/presentation/test_offer_mutations.py`

**Interfaces:**
- Consumes: local repository from Task 2, catalog from Task 3.
- Produces endpoints, all returning `OfferRotationResponse`:
  - `POST /campaigns/{campaign_id}/flows/{stream_id}/offers` body `{"offer_id": int}`
  - `DELETE /campaigns/{campaign_id}/flows/{stream_id}/offers/{offer_id}`
  - `POST /campaigns/{campaign_id}/flows/{stream_id}/offers/{offer_id}/restore`
  - `PATCH /campaigns/{campaign_id}/flows/{stream_id}/offers/{offer_id}/lock` body `{"locked": bool}`

- [ ] **Step 1: Write the failing mutation test**

Create `apps/api/tests/presentation/test_offer_mutations.py`:

```python
import httpx
import respx
from httpx import AsyncClient


async def _seed(client: AsyncClient) -> None:
    respx.get("https://tracker.example.com/admin_api/v1/campaigns/42/streams").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": 10, "name": "Main", "offers": [{"offer_id": 1, "share": 100}]},
            ],
        )
    )
    respx.get("https://tracker.example.com/admin_api/v1/offers").mock(
        return_value=httpx.Response(
            200,
            json=[{"id": 1, "name": "One"}, {"id": 2, "name": "Two"}],
        )
    )
    respx.get("https://tracker.example.com/admin_api/v1/offers/2").mock(
        return_value=httpx.Response(200, json={"id": 2, "name": "Two"})
    )
    assert (await client.get("/api/v1/campaigns/42/offers")).status_code == 200


@respx.mock
async def test_add_delete_restore_and_lock(client: AsyncClient) -> None:
    await _seed(client)

    added = await client.post("/api/v1/campaigns/42/flows/10/offers", json={"offer_id": 2})
    assert added.status_code == 200
    offers = {item["offer_id"]: item for item in added.json()["flows"][0]["offers"]}
    assert offers[1]["share"] == 50 and offers[2]["share"] == 50

    duplicate = await client.post("/api/v1/campaigns/42/flows/10/offers", json={"offer_id": 2})
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "OFFER_ALREADY_EXISTS"

    deleted = await client.delete("/api/v1/campaigns/42/flows/10/offers/1")
    offers = {item["offer_id"]: item for item in deleted.json()["flows"][0]["offers"]}
    assert offers[1]["share"] == 0 and offers[1]["state"] == "deleted"
    assert offers[2]["share"] == 100

    restored = await client.post("/api/v1/campaigns/42/flows/10/offers/1/restore")
    offers = {item["offer_id"]: item for item in restored.json()["flows"][0]["offers"]}
    assert offers[1]["share"] == 50 and offers[1]["state"] == "active"

    locked = await client.patch(
        "/api/v1/campaigns/42/flows/10/offers/1/lock", json={"locked": True}
    )
    assert locked.status_code == 200
    assert locked.json()["flows"][0]["offers"][0]["locked"] is True
```

- [ ] **Step 2: Run to verify failure**

Run: `cd apps/api && uv run pytest tests/presentation/test_offer_mutations.py -q`

Expected: FAIL with 404 for the mutation routes.

- [ ] **Step 3: Implement the four use cases**

`apps/api/app/usecase/keitaro/add_offer_usecase.py`:

```python
from app.domain.keitaro.entities.flow_offers import FlowOffers
from app.domain.keitaro.exceptions import FlowNotFoundError
from app.domain.keitaro.repositories import CampaignOfferRepository, CatalogGateway
from app.domain.keitaro.value_objects.identifiers import CampaignId, OfferId


def find_flow(flows: list[FlowOffers], stream_id: int) -> FlowOffers:
    for flow in flows:
        if flow.stream_id.value == stream_id:
            return flow
    raise FlowNotFoundError(f"Flow {stream_id} is not loaded")


class AddOfferUseCase:
    def __init__(self, repository: CampaignOfferRepository, catalog: CatalogGateway) -> None:
        self._repository = repository
        self._catalog = catalog

    async def execute(self, campaign_id: int, stream_id: int, offer_id: int) -> list[FlowOffers]:
        flows = await self._repository.list_by_campaign(CampaignId(campaign_id))
        flow = find_flow(flows, stream_id)
        offer = await self._catalog.get_offer(offer_id)
        flow.add_offer(OfferId(offer_id), offer.name)
        await self._repository.save(CampaignId(campaign_id), flow)
        return await self._repository.list_by_campaign(CampaignId(campaign_id))
```

`apps/api/app/usecase/keitaro/delete_offer_usecase.py`:

```python
from app.domain.keitaro.entities.flow_offers import FlowOffers
from app.domain.keitaro.repositories import CampaignOfferRepository
from app.domain.keitaro.value_objects.identifiers import CampaignId, OfferId
from app.usecase.keitaro.add_offer_usecase import find_flow


class DeleteOfferUseCase:
    def __init__(self, repository: CampaignOfferRepository) -> None:
        self._repository = repository

    async def execute(self, campaign_id: int, stream_id: int, offer_id: int) -> list[FlowOffers]:
        flows = await self._repository.list_by_campaign(CampaignId(campaign_id))
        flow = find_flow(flows, stream_id)
        flow.delete_offer(OfferId(offer_id))
        await self._repository.save(CampaignId(campaign_id), flow)
        return await self._repository.list_by_campaign(CampaignId(campaign_id))
```

`apps/api/app/usecase/keitaro/restore_offer_usecase.py`:

```python
from app.domain.keitaro.entities.flow_offers import FlowOffers
from app.domain.keitaro.repositories import CampaignOfferRepository
from app.domain.keitaro.value_objects.identifiers import CampaignId, OfferId
from app.usecase.keitaro.add_offer_usecase import find_flow


class RestoreOfferUseCase:
    def __init__(self, repository: CampaignOfferRepository) -> None:
        self._repository = repository

    async def execute(self, campaign_id: int, stream_id: int, offer_id: int) -> list[FlowOffers]:
        flows = await self._repository.list_by_campaign(CampaignId(campaign_id))
        flow = find_flow(flows, stream_id)
        flow.restore_offer(OfferId(offer_id))
        await self._repository.save(CampaignId(campaign_id), flow)
        return await self._repository.list_by_campaign(CampaignId(campaign_id))
```

`apps/api/app/usecase/keitaro/set_offer_lock_usecase.py`:

```python
from app.domain.keitaro.entities.flow_offers import FlowOffers
from app.domain.keitaro.repositories import CampaignOfferRepository
from app.domain.keitaro.value_objects.identifiers import CampaignId, OfferId
from app.usecase.keitaro.add_offer_usecase import find_flow


class SetOfferLockUseCase:
    def __init__(self, repository: CampaignOfferRepository) -> None:
        self._repository = repository

    async def execute(
        self, campaign_id: int, stream_id: int, offer_id: int, locked: bool
    ) -> list[FlowOffers]:
        flows = await self._repository.list_by_campaign(CampaignId(campaign_id))
        flow = find_flow(flows, stream_id)
        flow.set_locked(OfferId(offer_id), locked)
        await self._repository.save(CampaignId(campaign_id), flow)
        return await self._repository.list_by_campaign(CampaignId(campaign_id))
```

- [ ] **Step 4: Add dependencies, schema and handlers**

Append to `apps/api/app/presentation/api/keitaro/schemas.py`:

```python
class AddOfferRequest(BaseModel):
    offer_id: int


class LockOfferRequest(BaseModel):
    locked: bool
```

Append to `apps/api/app/presentation/api/keitaro/dependencies.py`:

```python
from app.usecase.keitaro.add_offer_usecase import AddOfferUseCase
from app.usecase.keitaro.delete_offer_usecase import DeleteOfferUseCase
from app.usecase.keitaro.restore_offer_usecase import RestoreOfferUseCase
from app.usecase.keitaro.set_offer_lock_usecase import SetOfferLockUseCase


def get_add_offer_usecase(
    repository: Annotated[SqlAlchemyCampaignOfferRepository, Depends(get_offer_repository)],
    catalog: Annotated[KeitaroCampaignGateway, Depends(get_campaign_gateway)],
) -> AddOfferUseCase:
    return AddOfferUseCase(repository, catalog)


def get_delete_offer_usecase(
    repository: Annotated[SqlAlchemyCampaignOfferRepository, Depends(get_offer_repository)],
) -> DeleteOfferUseCase:
    return DeleteOfferUseCase(repository)


def get_restore_offer_usecase(
    repository: Annotated[SqlAlchemyCampaignOfferRepository, Depends(get_offer_repository)],
) -> RestoreOfferUseCase:
    return RestoreOfferUseCase(repository)


def get_set_lock_usecase(
    repository: Annotated[SqlAlchemyCampaignOfferRepository, Depends(get_offer_repository)],
) -> SetOfferLockUseCase:
    return SetOfferLockUseCase(repository)
```

Append to `apps/api/app/presentation/api/keitaro/handlers/campaigns.py`:

```python
from app.presentation.api.keitaro.dependencies import (
    get_add_offer_usecase,
    get_delete_offer_usecase,
    get_restore_offer_usecase,
    get_set_lock_usecase,
)
from app.presentation.api.keitaro.schemas import AddOfferRequest, LockOfferRequest


@router.post("/{campaign_id}/flows/{stream_id}/offers", response_model=OfferRotationResponse)
async def add_offer(
    campaign_id: int,
    stream_id: int,
    payload: AddOfferRequest,
    usecase=Depends(get_add_offer_usecase),
):
    flows = await usecase.execute(campaign_id, stream_id, payload.offer_id)
    return to_rotation_response(campaign_id, flows)


@router.delete(
    "/{campaign_id}/flows/{stream_id}/offers/{offer_id}",
    response_model=OfferRotationResponse,
)
async def delete_offer(
    campaign_id: int,
    stream_id: int,
    offer_id: int,
    usecase=Depends(get_delete_offer_usecase),
):
    flows = await usecase.execute(campaign_id, stream_id, offer_id)
    return to_rotation_response(campaign_id, flows)


@router.post(
    "/{campaign_id}/flows/{stream_id}/offers/{offer_id}/restore",
    response_model=OfferRotationResponse,
)
async def restore_offer(
    campaign_id: int,
    stream_id: int,
    offer_id: int,
    usecase=Depends(get_restore_offer_usecase),
):
    flows = await usecase.execute(campaign_id, stream_id, offer_id)
    return to_rotation_response(campaign_id, flows)


@router.patch(
    "/{campaign_id}/flows/{stream_id}/offers/{offer_id}/lock",
    response_model=OfferRotationResponse,
)
async def set_offer_lock(
    campaign_id: int,
    stream_id: int,
    offer_id: int,
    payload: LockOfferRequest,
    usecase=Depends(get_set_lock_usecase),
):
    flows = await usecase.execute(campaign_id, stream_id, offer_id, payload.locked)
    return to_rotation_response(campaign_id, flows)
```

- [ ] **Step 5: Run mutation tests**

Run: `cd apps/api && uv run pytest tests/presentation/test_offer_mutations.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/usecase/keitaro apps/api/app/presentation/api apps/api/tests
git commit -m "feat(api): add local offer add delete restore lock"
```

---

## Task 7: Save Offers to Keitaro

**Files:**
- Create: `apps/api/app/usecase/keitaro/save_campaign_offers_usecase.py`
- Modify: `apps/api/app/presentation/api/keitaro/handlers/campaigns.py`
- Modify: `apps/api/app/presentation/api/keitaro/dependencies.py`
- Test: `apps/api/tests/presentation/test_save_offers.py`

**Interfaces:**
- Consumes: local repository, `KeitaroFlowGateway.update_offers`.
- Produces `PUT /api/v1/campaigns/{campaign_id}/offers -> OfferRotationResponse`.
- `SaveCampaignOffersUseCase.execute(campaign_id: int) -> list[FlowOffers]`.

- [ ] **Step 1: Write the failing save test**

Create `apps/api/tests/presentation/test_save_offers.py`:

```python
import json

import httpx
import respx
from httpx import AsyncClient


@respx.mock
async def test_save_sends_only_active_offers(client: AsyncClient) -> None:
    respx.get("https://tracker.example.com/admin_api/v1/campaigns/42/streams").mock(
        return_value=httpx.Response(
            200,
            json=[{"id": 10, "name": "Main", "offers": [{"offer_id": 1, "share": 100}]}],
        )
    )
    respx.get("https://tracker.example.com/admin_api/v1/offers").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "One"}, {"id": 2, "name": "Two"}])
    )
    respx.get("https://tracker.example.com/admin_api/v1/offers/2").mock(
        return_value=httpx.Response(200, json={"id": 2, "name": "Two"})
    )
    respx.get("https://tracker.example.com/admin_api/v1/streams/10").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": 10,
                "campaign_id": 42,
                "type": "regular",
                "name": "Main",
                "schema": "landings",
                "action_type": "http",
                "filters": [],
                "offers": [{"offer_id": 1, "share": 100}],
            },
        )
    )
    put_route = respx.put("https://tracker.example.com/admin_api/v1/streams/10").mock(
        return_value=httpx.Response(200, json={})
    )
    await client.get("/api/v1/campaigns/42/offers")
    await client.post("/api/v1/campaigns/42/flows/10/offers", json={"offer_id": 2})
    await client.delete("/api/v1/campaigns/42/flows/10/offers/1")

    saved = await client.put("/api/v1/campaigns/42/offers")

    assert saved.status_code == 200
    body = json.loads(put_route.calls[0].request.read())
    assert body["offers"] == [{"offer_id": 2, "share": 100, "state": "active"}]
    assert {item["offer_id"] for item in saved.json()["flows"][0]["offers"]} == {1, 2}
```

- [ ] **Step 2: Run to verify failure**

Run: `cd apps/api && uv run pytest tests/presentation/test_save_offers.py -q`

Expected: FAIL with 405/404.

- [ ] **Step 3: Implement the save use case**

`apps/api/app/usecase/keitaro/save_campaign_offers_usecase.py`:

```python
from app.domain.keitaro.entities.flow_offers import FlowOffers
from app.domain.keitaro.repositories import CampaignOfferRepository, FlowGateway
from app.domain.keitaro.value_objects.identifiers import CampaignId
from app.domain.keitaro.value_objects.offer_share import OfferState


class SaveCampaignOffersUseCase:
    def __init__(self, repository: CampaignOfferRepository, flows: FlowGateway) -> None:
        self._repository = repository
        self._flows = flows

    async def execute(self, campaign_id: int) -> list[FlowOffers]:
        domain_id = CampaignId(campaign_id)
        flows = await self._repository.list_by_campaign(domain_id)
        for flow in flows:
            active = [
                (item.offer_id.value, item.share.value)
                for item in flow.offers
                if item.state is OfferState.ACTIVE
            ]
            await self._flows.update_offers(flow.stream_id.value, active)
        return await self._repository.list_by_campaign(domain_id)
```

- [ ] **Step 4: Add dependency and handler**

Append to `apps/api/app/presentation/api/keitaro/dependencies.py`:

```python
from app.usecase.keitaro.save_campaign_offers_usecase import SaveCampaignOffersUseCase


def get_save_offers_usecase(
    repository: Annotated[SqlAlchemyCampaignOfferRepository, Depends(get_offer_repository)],
    flows: Annotated[KeitaroFlowGateway, Depends(get_flow_gateway)],
) -> SaveCampaignOffersUseCase:
    return SaveCampaignOffersUseCase(repository, flows)
```

Append to `apps/api/app/presentation/api/keitaro/handlers/campaigns.py`:

```python
from app.presentation.api.keitaro.dependencies import get_save_offers_usecase


@router.put("/{campaign_id}/offers", response_model=OfferRotationResponse)
async def save_offers(campaign_id: int, usecase=Depends(get_save_offers_usecase)):
    flows = await usecase.execute(campaign_id)
    return to_rotation_response(campaign_id, flows)
```

- [ ] **Step 5: Run save test**

Run: `cd apps/api && uv run pytest tests/presentation/test_save_offers.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/api/app/usecase/keitaro/save_campaign_offers_usecase.py apps/api/app/presentation/api apps/api/tests
git commit -m "feat(api): save offer rotation to keitaro"
```

---

## Task 8: Backend Error Handling, Request IDs and Verification

**Files:**
- Create: `apps/api/app/presentation/errors.py`
- Create: `apps/api/app/presentation/middleware.py`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/presentation/test_errors.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: domain errors, Keitaro errors.
- Produces:
  - Error JSON `{"code": "...", "message": "..."}`.
  - `X-Request-ID` response header.
  - Status mapping: validation 422, not found 404, duplicate 409, Keitaro 5xx 502/503.

- [ ] **Step 1: Write failing error tests**

Create `apps/api/tests/presentation/test_errors.py`:

```python
from httpx import AsyncClient


async def test_missing_flow_returns_machine_code(client: AsyncClient) -> None:
    response = await client.delete("/api/v1/campaigns/42/flows/999/offers/1")
    assert response.status_code == 404
    assert response.json() == {
        "code": "CAMPAIGN_NOT_FOUND",
        "message": "Flow 999 is not loaded",
    }


async def test_request_id_header_is_present(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.headers["x-request-id"]
```

- [ ] **Step 2: Run to verify failure**

Run: `cd apps/api && uv run pytest tests/presentation/test_errors.py -q`

Expected: FAIL because no exception handler and no header.

- [ ] **Step 3: Implement error handlers and request ID middleware**

`apps/api/app/presentation/errors.py`:

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.keitaro.exceptions import (
    CampaignNotFoundError,
    DomainError,
    FlowNotFoundError,
    OfferAlreadyExistsError,
    OfferNotFoundError,
)
from app.infrastructure.keitaro.errors import KeitaroResponseError, KeitaroUnavailableError


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(_: Request, error: DomainError) -> JSONResponse:
        if isinstance(error, (CampaignNotFoundError, FlowNotFoundError, OfferNotFoundError)):
            status_code = 404
        elif isinstance(error, OfferAlreadyExistsError):
            status_code = 409
        else:
            status_code = 422
        return JSONResponse(
            status_code=status_code,
            content={"code": error.code, "message": error.message},
        )

    @app.exception_handler(KeitaroUnavailableError)
    async def handle_unavailable(_: Request, error: KeitaroUnavailableError) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"code": "KEITARO_UNAVAILABLE", "message": str(error)},
        )

    @app.exception_handler(KeitaroResponseError)
    async def handle_keitaro_error(_: Request, error: KeitaroResponseError) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content={"code": "KEITARO_UNAVAILABLE", "message": error.message},
        )
```

`apps/api/app/presentation/middleware.py`:

```python
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

Modify `apps/api/app/main.py`:

```python
from app.presentation.errors import install_error_handlers
from app.presentation.middleware import RequestIdMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handlers(app)
    app.include_router(api_router, prefix="/api/v1")
    return app
```

- [ ] **Step 4: Run error tests and all backend checks**

Run:

```bash
cd apps/api
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```

Expected: all tests pass; ruff and mypy exit 0.

- [ ] **Step 5: Document backend endpoints and local behavior**

Add to `README.md`:

```markdown
## API

- `GET /api/v1/campaigns` — all Keitaro campaigns, paginated internally.
- `GET /api/v1/campaigns/form-options` — domains, campaign groups, traffic sources.
- `GET /api/v1/offers` — all Keitaro offers for local search.
- `POST /api/v1/campaigns` — create a campaign with Google and offer flows.
- `GET /api/v1/campaigns/{id}/offers` — pull flows and offers from Keitaro.
- `POST /api/v1/campaigns/{id}/flows/{stream_id}/offers` — add an offer locally.
- `DELETE /api/v1/campaigns/{id}/flows/{stream_id}/offers/{offer_id}` — soft-delete locally.
- `POST /api/v1/campaigns/{id}/flows/{stream_id}/offers/{offer_id}/restore` — restore locally.
- `PATCH /api/v1/campaigns/{id}/flows/{stream_id}/offers/{offer_id}/lock` — lock/unlock a share.
- `PUT /api/v1/campaigns/{id}/offers` — save active offers and shares to Keitaro.
```

- [ ] **Step 6: Commit**

```bash
git add apps/api README.md
git commit -m "feat(api): standardize errors and request ids"
```

---

## Task 9: Frontend Transport, UI Primitives and Providers

**Files:**
- Modify: `apps/web/package.json` (via pnpm)
- Create: `apps/web/src/shared/api/campaigns.ts`
- Create: `apps/web/src/shared/lib/get-api-error-message.ts`
- Test: `apps/web/src/shared/lib/get-api-error-message.test.ts`
- Create: `apps/web/src/shared/config/countries.ts`
- Create: `apps/web/src/app/testing/render-with-providers.tsx`
- Modify: `apps/web/src/app/layouts/root-layout.tsx`
- Create: shadcn components under `apps/web/src/shared/ui/`

**Interfaces:**
- Consumes: `/api/v1` endpoints from Tasks 4–7.
- Produces:
  - `campaignsApi` object with `list`, `formOptions`, `offers`, `create`, `refreshOffers`, `addOffer`, `deleteOffer`, `restoreOffer`, `lockOffer`, `saveOffers`.
  - Types `CampaignSummary`, `CatalogItem`, `FormOptions`, `OfferItem`, `FlowOffers`, `OfferRotation`, `CreateCampaignPayload`.
  - `getApiErrorMessage(error: unknown): string`.
  - `countryOptions: { code: string; name: string }[]`.

- [ ] **Step 1: Install dependencies and shadcn components**

Run:

```bash
cd apps/web
pnpm add world-countries sonner
pnpm dlx shadcn@latest add select dialog command popover table form checkbox skeleton badge alert card sonner
```

Expected: `src/shared/ui` contains `select.tsx`, `dialog.tsx`, `command.tsx`, `popover.tsx`, `table.tsx`, `form.tsx`, `checkbox.tsx`, `sonner.tsx` or an equivalent toast component. If the CLI writes to a literal `@/shared/ui` directory, move the files to `src/shared/ui` and fix imports. Load the `shadcn` skill before editing generated components.

Replace the generated `apps/web/src/shared/ui/sonner.tsx` with a Vite-safe wrapper so it does not depend on `next-themes`:

```tsx
export { Toaster } from "sonner"
```

Add every new component to `apps/web/src/shared/ui/index.ts`, including `Table`, `TableBody`, `TableCell`, `TableHead`, `TableHeader`, `TableRow`, `Dialog`, `DialogContent`, `DialogHeader`, `DialogTitle`, `Toaster`, and the `Select` family.

- [ ] **Step 2: Write the failing error-message test**

Create `apps/web/src/shared/lib/get-api-error-message.test.ts`:

```typescript
import { describe, expect, it } from "vitest"

import { ApiError } from "@/shared/api/client"
import { getApiErrorMessage } from "@/shared/lib/get-api-error-message"

describe("getApiErrorMessage", () => {
  it("uses the backend message", () => {
    const error = new ApiError(409, "Conflict", {
      code: "OFFER_ALREADY_EXISTS",
      message: "Offer 2 already exists in the flow",
    })
    expect(getApiErrorMessage(error)).toBe("Offer 2 already exists in the flow")
  })

  it("falls back for unknown errors", () => {
    expect(getApiErrorMessage(new Error("boom"))).toBe("Не удалось выполнить запрос")
  })
})
```

- [ ] **Step 3: Run to verify failure**

Run: `cd apps/web && pnpm vitest run src/shared/lib/get-api-error-message.test.ts`

Expected: FAIL because the module does not exist.

- [ ] **Step 4: Implement the transport and helper**

`apps/web/src/shared/lib/get-api-error-message.ts`:

```typescript
import { ApiError } from "@/shared/api/client"

type ErrorPayload = {
  code?: string
  message?: string
}

export function getApiErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const payload = error.payload as ErrorPayload | undefined
    if (payload?.message) {
      return payload.message
    }
    if (payload?.code === "KEITARO_UNAVAILABLE") {
      return "Keitaro недоступен. Проверьте подключение и попробуйте снова."
    }
  }
  return "Не удалось выполнить запрос"
}
```

`apps/web/src/shared/api/campaigns.ts`:

```typescript
import { apiRequest } from "@/shared/api/client"

export type CampaignSummary = {
  id: number
  name: string
  state: string
  alias: string
}

export type CatalogItem = { id: number; name: string }

export type FormOptions = {
  domains: CatalogItem[]
  groups: CatalogItem[]
  traffic_sources: CatalogItem[]
}

export type OfferItem = {
  offer_id: number
  name: string
  share: number
  state: "active" | "deleted"
  locked: boolean
}

export type FlowOffers = {
  stream_id: number
  name: string
  offers: OfferItem[]
}

export type OfferRotation = {
  campaign_id: number
  flows: FlowOffers[]
}

export type CreateCampaignPayload = {
  name: string
  country_code: string
  offer_id: number
  domain_id: number
  group_id: number
  traffic_source_id: number
}

export const campaignsApi = {
  list: () => apiRequest<CampaignSummary[]>("/campaigns"),
  formOptions: () => apiRequest<FormOptions>("/campaigns/form-options"),
  offers: () => apiRequest<CatalogItem[]>("/offers"),
  create: (payload: CreateCampaignPayload) =>
    apiRequest<CampaignSummary>("/campaigns", { method: "POST", body: payload }),
  refreshOffers: (campaignId: number) =>
    apiRequest<OfferRotation>(`/campaigns/${campaignId}/offers`),
  addOffer: (campaignId: number, streamId: number, offerId: number) =>
    apiRequest<OfferRotation>(
      `/campaigns/${campaignId}/flows/${streamId}/offers`,
      { method: "POST", body: { offer_id: offerId } },
    ),
  deleteOffer: (campaignId: number, streamId: number, offerId: number) =>
    apiRequest<OfferRotation>(
      `/campaigns/${campaignId}/flows/${streamId}/offers/${offerId}`,
      { method: "DELETE" },
    ),
  restoreOffer: (campaignId: number, streamId: number, offerId: number) =>
    apiRequest<OfferRotation>(
      `/campaigns/${campaignId}/flows/${streamId}/offers/${offerId}/restore`,
      { method: "POST" },
    ),
  lockOffer: (campaignId: number, streamId: number, offerId: number, locked: boolean) =>
    apiRequest<OfferRotation>(
      `/campaigns/${campaignId}/flows/${streamId}/offers/${offerId}/lock`,
      { method: "PATCH", body: { locked } },
    ),
  saveOffers: (campaignId: number) =>
    apiRequest<OfferRotation>(`/campaigns/${campaignId}/offers`, { method: "PUT" }),
}
```

`apps/web/src/shared/config/countries.ts`:

```typescript
import countries from "world-countries"

const displayNames = new Intl.DisplayNames(["ru"], { type: "region" })

export const countryOptions = countries
  .map((country) => ({
    code: country.cca2,
    name: displayNames.of(country.cca2) ?? country.name.common,
  }))
  .sort((left, right) => left.name.localeCompare(right.name, "ru"))
```

- [ ] **Step 5: Add providers and test renderer**

Modify `apps/web/src/app/layouts/root-layout.tsx` to render `<Toaster richColors />` from `@/shared/ui/sonner` next to `<Outlet />`.

Create `apps/web/src/app/testing/render-with-providers.tsx`:

```tsx
import type { ReactElement } from "react"

import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render } from "@testing-library/react"
import { createMemoryRouter, RouterProvider } from "react-router-dom"

export function renderWithProviders(ui: ReactElement, path = "/") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  const router = createMemoryRouter(
    [{ path: "/campaigns", element: ui }, { path: "/campaigns/new", element: ui }, { path: "/campaigns/:campaignId/edit", element: ui }, { path, element: ui }],
    { initialEntries: [path] },
  )
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}
```

- [ ] **Step 6: Run frontend checks**

Run:

```bash
cd apps/web
pnpm vitest run src/shared/lib/get-api-error-message.test.ts
pnpm typecheck
pnpm fsd:lint
```

Expected: PASS and no FSD violations.

- [ ] **Step 7: Commit**

```bash
git add apps/web/package.json apps/web/pnpm-lock.yaml apps/web/src/shared apps/web/src/app
git commit -m "feat(web): add campaign transport and ui primitives"
```

---

## Task 10: Campaigns List Page

**Files:**
- Create: `apps/web/src/pages/campaigns-list/api/use-campaigns.ts`
- Create: `apps/web/src/pages/campaigns-list/ui/campaigns-list-page.tsx`
- Create: `apps/web/src/pages/campaigns-list/ui/campaigns-list-page.test.tsx`
- Modify: `apps/web/src/pages/campaigns-list/index.ts`

**Interfaces:**
- Consumes: `campaignsApi.list`, `CampaignSummary`.
- Produces: `/campaigns` page with local name filter and edit links.

- [ ] **Step 1: Write the failing list test**

Create `apps/web/src/pages/campaigns-list/ui/campaigns-list-page.test.tsx`:

```tsx
import { screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { renderWithProviders } from "@/app/testing/render-with-providers"
import { campaignsApi } from "@/shared/api/campaigns"

import { CampaignsListPage } from "./campaigns-list-page"

describe("CampaignsListPage", () => {
  beforeEach(() => {
    vi.spyOn(campaignsApi, "list").mockResolvedValue([
      { id: 1, name: "Alpha", state: "active", alias: "alpha" },
      { id: 2, name: "Beta", state: "active", alias: "beta" },
    ])
  })

  it("loads campaigns and filters by name", async () => {
    renderWithProviders(<CampaignsListPage />, "/campaigns")
    expect(await screen.findByText("Alpha")).toBeInTheDocument()
    await userEvent.type(screen.getByPlaceholderText("Поиск по названию"), "bet")
    expect(screen.queryByText("Alpha")).not.toBeInTheDocument()
    expect(screen.getByText("Beta")).toBeInTheDocument()
  })

  it("links to the editor", async () => {
    renderWithProviders(<CampaignsListPage />, "/campaigns")
    const link = await screen.findByRole("link", { name: /Beta/ })
    expect(link).toHaveAttribute("href", "/campaigns/2/edit")
  })
})
```

- [ ] **Step 2: Run to verify failure**

Run: `cd apps/web && pnpm vitest run src/pages/campaigns-list`

Expected: FAIL because the page still renders the stub and has no search input.

- [ ] **Step 3: Implement the query hook and page**

`apps/web/src/pages/campaigns-list/api/use-campaigns.ts`:

```typescript
import { useQuery } from "@tanstack/react-query"

import { campaignsApi } from "@/shared/api/campaigns"

export function useCampaigns() {
  return useQuery({
    queryKey: ["campaigns"],
    queryFn: campaignsApi.list,
    staleTime: 30_000,
  })
}
```

`apps/web/src/pages/campaigns-list/ui/campaigns-list-page.tsx`:

```tsx
import { useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { PlusIcon } from "lucide-react"

import { getApiErrorMessage } from "@/shared/lib/get-api-error-message"
import {
  Alert,
  AlertDescription,
  AlertTitle,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Skeleton,
} from "@/shared/ui"

import { useCampaigns } from "../api/use-campaigns"

export function CampaignsListPage() {
  const [search, setSearch] = useState("")
  const { data, isPending, error } = useCampaigns()
  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase()
    return (data ?? []).filter((item) => item.name.toLowerCase().includes(term))
  }, [data, search])

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Кампании</h1>
          <p className="text-sm text-muted-foreground">Управление офферами в Keitaro.</p>
        </div>
        <Button asChild>
          <Link to="/campaigns/new">
            <PlusIcon data-icon="inline-start" />
            Создать кампанию
          </Link>
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Список кампаний</CardTitle>
          <Input
            aria-label="Поиск кампаний"
            placeholder="Поиск по названию"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {isPending && <Skeleton className="h-24 w-full" />}
          {error && (
            <Alert variant="destructive">
              <AlertTitle>Не удалось загрузить кампании</AlertTitle>
              <AlertDescription>{getApiErrorMessage(error)}</AlertDescription>
            </Alert>
          )}
          {!isPending && !error && filtered.length === 0 && (
            <p className="text-sm text-muted-foreground">Кампании не найдены.</p>
          )}
          {filtered.map((campaign) => (
            <Link
              key={campaign.id}
              to={`/campaigns/${campaign.id}/edit`}
              className="flex items-center justify-between rounded-lg border p-4 hover:bg-accent"
            >
              <span className="font-medium">{campaign.name}</span>
              <span className="text-sm text-muted-foreground">{campaign.state}</span>
            </Link>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
```

Update `apps/web/src/pages/campaigns-list/index.ts`:

```typescript
export { CampaignsListPage } from "./ui/campaigns-list-page"
```

- [ ] **Step 4: Run list tests**

Run: `cd apps/web && pnpm vitest run src/pages/campaigns-list`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/pages/campaigns-list
git commit -m "feat(web): load and search keitaro campaigns"
```

---

## Task 11: Campaign Create Page

**Files:**
- Create: `apps/web/src/pages/campaign-create/model/campaign-create-schema.ts`
- Create: `apps/web/src/pages/campaign-create/api/use-campaign-form.ts`
- Create: `apps/web/src/pages/campaign-create/ui/campaign-create-page.tsx`
- Create: `apps/web/src/pages/campaign-create/ui/campaign-create-page.test.tsx`
- Modify: `apps/web/src/pages/campaign-create/index.ts`

**Interfaces:**
- Consumes: `campaignsApi.formOptions`, `campaignsApi.offers`, `campaignsApi.create`, `countryOptions`.
- Produces: `/campaigns/new` form with required name, country, offer, domain, group, source; navigates to `/campaigns/{id}/edit` on success.

- [ ] **Step 1: Write the failing create-page test**

Create `apps/web/src/pages/campaign-create/ui/campaign-create-page.test.tsx`:

```tsx
import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { renderWithProviders } from "@/app/testing/render-with-providers"
import { campaignsApi } from "@/shared/api/campaigns"

import { CampaignCreatePage } from "./campaign-create-page"

describe("CampaignCreatePage", () => {
  beforeEach(() => {
    vi.spyOn(campaignsApi, "formOptions").mockResolvedValue({
      domains: [{ id: 1, name: "example.com" }],
      groups: [{ id: 2, name: "Group" }],
      traffic_sources: [{ id: 3, name: "Source" }],
    })
    vi.spyOn(campaignsApi, "offers").mockResolvedValue([{ id: 7, name: "Offer Seven" }])
    vi.spyOn(campaignsApi, "create").mockResolvedValue({
      id: 42,
      name: "MX Campaign",
      state: "active",
      alias: "mx-campaign",
    })
  })

  it("submits all required fields", async () => {
    renderWithProviders(<CampaignCreatePage />, "/campaigns/new")

    await userEvent.type(screen.getByLabelText("Название кампании"), "MX Campaign")
    await userEvent.selectOptions(screen.getByLabelText("Гео"), "MX")
    await userEvent.selectOptions(await screen.findByLabelText("Оффер"), "7")
    await userEvent.selectOptions(await screen.findByLabelText("Домен"), "1")
    await userEvent.selectOptions(await screen.findByLabelText("Группа"), "2")
    await userEvent.selectOptions(await screen.findByLabelText("Источник"), "3")
    await userEvent.click(screen.getByRole("button", { name: "Создать" }))

    await waitFor(() =>
      expect(campaignsApi.create).toHaveBeenCalledWith({
        name: "MX Campaign",
        country_code: "MX",
        offer_id: 7,
        domain_id: 1,
        group_id: 2,
        traffic_source_id: 3,
      }),
    )
  })
})
```

- [ ] **Step 2: Run to verify failure**

Run: `cd apps/web && pnpm vitest run src/pages/campaign-create`

Expected: FAIL because the page is a stub.

- [ ] **Step 3: Implement schema, queries and page**

`apps/web/src/pages/campaign-create/model/campaign-create-schema.ts`:

```typescript
import { z } from "zod"

export const campaignCreateSchema = z.object({
  name: z.string().trim().min(1, "Укажите название"),
  country_code: z.string().length(2, "Выберите страну"),
  offer_id: z.coerce.number().int().positive("Выберите оффер"),
  domain_id: z.coerce.number().int().positive("Выберите домен"),
  group_id: z.coerce.number().int().positive("Выберите группу"),
  traffic_source_id: z.coerce.number().int().positive("Выберите источник"),
})

export type CampaignCreateValues = z.infer<typeof campaignCreateSchema>
```

`apps/web/src/pages/campaign-create/api/use-campaign-form.ts`:

```typescript
import { useQuery } from "@tanstack/react-query"

import { campaignsApi } from "@/shared/api/campaigns"

export function useCampaignForm() {
  return {
    options: useQuery({ queryKey: ["campaign-form-options"], queryFn: campaignsApi.formOptions }),
    offers: useQuery({ queryKey: ["offers"], queryFn: campaignsApi.offers, staleTime: 60_000 }),
  }
}
```

`apps/web/src/pages/campaign-create/ui/campaign-create-page.tsx`:

```tsx
import { useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { Link, useNavigate } from "react-router-dom"
import { ArrowLeftIcon } from "lucide-react"
import { toast } from "sonner"

import { countryOptions } from "@/shared/config/countries"
import { campaignsApi, type CreateCampaignPayload } from "@/shared/api/campaigns"
import { getApiErrorMessage } from "@/shared/lib/get-api-error-message"
import {
  Alert,
  AlertDescription,
  AlertTitle,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Label,
} from "@/shared/ui"

import { useCampaignForm } from "../api/use-campaign-form"
import { campaignCreateSchema, type CampaignCreateValues } from "../model/campaign-create-schema"

export function CampaignCreatePage() {
  const navigate = useNavigate()
  const { options, offers } = useCampaignForm()
  const [offerSearch, setOfferSearch] = useState("")
  const filteredOffers = (offers.data ?? []).filter((offer) =>
    offer.name.toLowerCase().includes(offerSearch.trim().toLowerCase()),
  )
  const form = useForm<CampaignCreateValues>({
    resolver: zodResolver(campaignCreateSchema),
    defaultValues: { name: "", country_code: "", offer_id: 0, domain_id: 0, group_id: 0, traffic_source_id: 0 },
  })
  const mutation = useMutation({
    mutationFn: (values: CreateCampaignPayload) => campaignsApi.create(values),
    onSuccess: (campaign) => {
      toast.success("Кампания создана")
      navigate(`/campaigns/${campaign.id}/edit`)
    },
  })

  const select = (
    name: keyof CampaignCreateValues,
    label: string,
    items: { id: number; name: string }[],
  ) => (
    <div className="flex flex-col gap-2">
      <Label htmlFor={name}>{label}</Label>
      <select
        id={name}
        className="h-9 rounded-md border bg-transparent px-3 text-sm"
        {...form.register(name)}
      >
        <option value="0">Выберите</option>
        {items.map((item) => (
          <option key={item.id} value={item.id}>{item.name}</option>
        ))}
      </select>
      {form.formState.errors[name] && (
        <p className="text-sm text-destructive">{form.formState.errors[name]?.message}</p>
      )}
    </div>
  )

  return (
    <div className="flex flex-col gap-6">
      <Button asChild className="w-fit" size="sm" variant="ghost">
        <Link to="/campaigns"><ArrowLeftIcon data-icon="inline-start" />Назад к кампаниям</Link>
      </Button>
      <h1 className="text-2xl font-semibold tracking-tight">Новая кампания</h1>
      <Card>
        <CardHeader><CardTitle>Форма создания</CardTitle></CardHeader>
        <CardContent>
          <form
            className="grid gap-4"
            onSubmit={form.handleSubmit((values) => mutation.mutate(values))}
          >
            <div className="flex flex-col gap-2">
              <Label htmlFor="name">Название кампании</Label>
              <input id="name" className="h-9 rounded-md border bg-transparent px-3 text-sm" {...form.register("name")} />
              {form.formState.errors.name && <p className="text-sm text-destructive">{form.formState.errors.name.message}</p>}
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="country_code">Гео</Label>
              <select id="country_code" className="h-9 rounded-md border bg-transparent px-3 text-sm" {...form.register("country_code")}>
                <option value="">Выберите</option>
                {countryOptions.map((country) => <option key={country.code} value={country.code}>{country.name} ({country.code})</option>)}
              </select>
            </div>
            <Input
              aria-label="Поиск оффера"
              placeholder="Поиск оффера"
              value={offerSearch}
              onChange={(event) => setOfferSearch(event.target.value)}
            />
            {select("offer_id", "Оффер", filteredOffers)}
            {select("domain_id", "Домен", options.data?.domains ?? [])}
            {select("group_id", "Группа", options.data?.groups ?? [])}
            {select("traffic_source_id", "Источник", options.data?.traffic_sources ?? [])}
            {mutation.error && (
              <Alert variant="destructive">
                <AlertTitle>Не удалось создать кампанию</AlertTitle>
                <AlertDescription>{getApiErrorMessage(mutation.error)}</AlertDescription>
              </Alert>
            )}
            <Button disabled={mutation.isPending} type="submit">Создать</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
```

Update `apps/web/src/pages/campaign-create/index.ts` to export the page.

- [ ] **Step 4: Run create-page tests**

Run: `cd apps/web && pnpm vitest run src/pages/campaign-create`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/pages/campaign-create
git commit -m "feat(web): add campaign creation form"
```

---

## Task 12: Campaign Editor — Manual Load and Display

**Files:**
- Create: `apps/web/src/pages/campaign-edit/api/use-campaign-offers.ts`
- Create: `apps/web/src/pages/campaign-edit/ui/flow-offers-card.tsx`
- Create: `apps/web/src/pages/campaign-edit/ui/campaign-edit-page.tsx`
- Create: `apps/web/src/pages/campaign-edit/ui/campaign-edit-page.test.tsx`
- Modify: `apps/web/src/pages/campaign-edit/index.ts`

**Interfaces:**
- Consumes: `campaignsApi.refreshOffers`.
- Produces:
  - Editor initially renders no flows and a `Получить потоки` button.
  - Refresh mutation stores `OfferRotation`.
  - `FlowOffersCard` renders flow name and every offer with share, state and lock state.
  - No network request on mount.

- [ ] **Step 1: Write the failing read test**

Create `apps/web/src/pages/campaign-edit/ui/campaign-edit-page.test.tsx`:

```tsx
import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { renderWithProviders } from "@/app/testing/render-with-providers"
import { campaignsApi } from "@/shared/api/campaigns"

import { CampaignEditPage } from "./campaign-edit-page"

const rotation = {
  campaign_id: 42,
  flows: [
    {
      stream_id: 10,
      name: "Main",
      offers: [
        { offer_id: 1, name: "One", share: 70, state: "active" as const, locked: false },
        { offer_id: 2, name: "Two", share: 30, state: "active" as const, locked: false },
        { offer_id: 3, name: "Old", share: 0, state: "deleted" as const, locked: false },
      ],
    },
  ],
}

describe("CampaignEditPage", () => {
  beforeEach(() => {
    vi.spyOn(campaignsApi, "refreshOffers").mockResolvedValue(rotation)
  })

  it("loads only after pressing the button and renders offers", async () => {
    renderWithProviders(<CampaignEditPage />, "/campaigns/42/edit")
    expect(campaignsApi.refreshOffers).not.toHaveBeenCalled()

    await userEvent.click(screen.getByRole("button", { name: "Получить потоки" }))

    expect(await screen.findByText("Main")).toBeInTheDocument()
    expect(screen.getByText("One")).toBeInTheDocument()
    expect(screen.getByText("70%")).toBeInTheDocument()
    expect(screen.getByText("Old")).toBeInTheDocument()
    expect(screen.getByText("удалён")).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run to verify failure**

Run: `cd apps/web && pnpm vitest run src/pages/campaign-edit`

Expected: FAIL because the page is a stub.

- [ ] **Step 3: Implement the hook, card and page**

`apps/web/src/pages/campaign-edit/api/use-campaign-offers.ts`:

```typescript
import { useMutation } from "@tanstack/react-query"
import { useState } from "react"

import { campaignsApi, type OfferRotation } from "@/shared/api/campaigns"

export function useCampaignOffers(campaignId: number) {
  const [rotation, setRotation] = useState<OfferRotation | null>(null)
  const refresh = useMutation({
    mutationFn: () => campaignsApi.refreshOffers(campaignId),
    onSuccess: setRotation,
  })
  return { rotation, setRotation, refresh }
}
```

`apps/web/src/pages/campaign-edit/ui/flow-offers-card.tsx`:

```tsx
import { LockIcon, Trash2Icon, Undo2Icon } from "lucide-react"

import type { FlowOffers, OfferItem } from "@/shared/api/campaigns"
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui"

type Props = {
  flow: FlowOffers
  onAdd: () => void
  onDelete: (offer: OfferItem) => void
  onRestore: (offer: OfferItem) => void
  onLock: (offer: OfferItem) => void
  disabled?: boolean
}

export function FlowOffersCard({ flow, onAdd, onDelete, onRestore, onLock, disabled }: Props) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>{flow.name}</CardTitle>
          <Button onClick={onAdd} disabled={disabled} size="sm">Добавить оффер</Button>
        </div>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Оффер</TableHead>
              <TableHead>Процент</TableHead>
              <TableHead>Состояние</TableHead>
              <TableHead>Действия</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {flow.offers.map((offer) => (
              <TableRow key={offer.offer_id}>
                <TableCell>{offer.name}</TableCell>
                <TableCell>{offer.share}%</TableCell>
                <TableCell>
                  {offer.state === "deleted" ? <Badge variant="secondary">удалён</Badge> : (
                    <Badge variant={offer.locked ? "default" : "outline"}>{offer.locked ? "зафиксирован" : "активен"}</Badge>
                  )}
                </TableCell>
                <TableCell className="flex gap-2">
                  {offer.state === "deleted" ? (
                    <Button onClick={() => onRestore(offer)} size="sm" variant="outline">
                      <Undo2Icon data-icon="inline-start" />Вернуть
                    </Button>
                  ) : (
                    <>
                      <Button onClick={() => onLock(offer)} size="sm" variant="outline">
                        <LockIcon data-icon="inline-start" />{offer.locked ? "Снять фиксацию" : "Зафиксировать процент"}
                      </Button>
                      <Button onClick={() => onDelete(offer)} size="sm" variant="destructive">
                        <Trash2Icon data-icon="inline-start" />Удалить
                      </Button>
                    </>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
```

`apps/web/src/pages/campaign-edit/ui/campaign-edit-page.tsx` for this task:

```tsx
import { Link, useParams } from "react-router-dom"
import { ArrowLeftIcon } from "lucide-react"

import { getApiErrorMessage } from "@/shared/lib/get-api-error-message"
import { Alert, AlertDescription, AlertTitle, Button, Card, CardContent, CardHeader, CardTitle } from "@/shared/ui"

import { useCampaignOffers } from "../api/use-campaign-offers"
import { FlowOffersCard } from "./flow-offers-card"

export function CampaignEditPage() {
  const { campaignId } = useParams()
  const id = Number(campaignId)
  const { rotation, refresh } = useCampaignOffers(id)

  return (
    <div className="flex flex-col gap-6">
      <Button asChild className="w-fit" size="sm" variant="ghost">
        <Link to="/campaigns"><ArrowLeftIcon data-icon="inline-start" />Назад к кампаниям</Link>
      </Button>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Редактор кампании</h1>
        <Button disabled={refresh.isPending} onClick={() => refresh.mutate()}>Получить потоки</Button>
      </div>
      {refresh.error && (
        <Alert variant="destructive">
          <AlertTitle>Не удалось получить потоки</AlertTitle>
          <AlertDescription>{getApiErrorMessage(refresh.error)}</AlertDescription>
        </Alert>
      )}
      {!rotation && !refresh.isPending && (
        <Card>
          <CardHeader><CardTitle>Потоки не загружены</CardTitle></CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Нажмите «Получить потоки», чтобы загрузить данные из Keitaro.
          </CardContent>
        </Card>
      )}
      {rotation?.flows.map((flow) => (
        <FlowOffersCard
          key={flow.stream_id}
          flow={flow}
          onAdd={() => undefined}
          onDelete={() => undefined}
          onRestore={() => undefined}
          onLock={() => undefined}
        />
      ))}
    </div>
  )
}
```

Update `apps/web/src/pages/campaign-edit/index.ts` to export the page.

- [ ] **Step 4: Run editor read tests**

Run: `cd apps/web && pnpm vitest run src/pages/campaign-edit`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/pages/campaign-edit
git commit -m "feat(web): load campaign flows on demand"
```

---

## Task 13: Campaign Editor — Add, Delete, Restore, Lock and Save

**Files:**
- Create: `apps/web/src/pages/campaign-edit/ui/offer-picker-dialog.tsx`
- Modify: `apps/web/src/pages/campaign-edit/ui/campaign-edit-page.tsx`
- Modify: `apps/web/src/pages/campaign-edit/ui/campaign-edit-page.test.tsx`
- Modify: `apps/web/src/pages/campaign-edit/api/use-campaign-offers.ts`

**Interfaces:**
- Consumes: `campaignsApi.offers`, `addOffer`, `deleteOffer`, `restoreOffer`, `lockOffer`, `saveOffers`.
- Produces:
  - Offer picker excludes offers already present in the target flow, including deleted ones.
  - Every mutation replaces the cached rotation with the backend response.
  - `Сохранить` sends active offers to Keitaro and replaces the rotation.
  - Errors are shown without clearing the current rotation.

- [ ] **Step 1: Extend the failing editor test**

Append to `apps/web/src/pages/campaign-edit/ui/campaign-edit-page.test.tsx`:

```tsx
it("adds, locks and saves through the backend", async () => {
  vi.spyOn(campaignsApi, "offers").mockResolvedValue([
    { id: 1, name: "One" },
    { id: 2, name: "Two" },
    { id: 9, name: "Nine" },
  ])
  vi.spyOn(campaignsApi, "addOffer").mockResolvedValue(rotation)
  vi.spyOn(campaignsApi, "lockOffer").mockResolvedValue(rotation)
  vi.spyOn(campaignsApi, "saveOffers").mockResolvedValue(rotation)

  renderWithProviders(<CampaignEditPage />, "/campaigns/42/edit")
  await userEvent.click(screen.getByRole("button", { name: "Получить потоки" }))
  await userEvent.click(await screen.findByRole("button", { name: "Добавить оффер" }))
  await userEvent.click(await screen.findByText("Nine"))
  await waitFor(() => expect(campaignsApi.addOffer).toHaveBeenCalledWith(42, 10, 9))

  await userEvent.click(screen.getAllByRole("button", { name: /Зафиксировать процент/ })[0])
  await waitFor(() => expect(campaignsApi.lockOffer).toHaveBeenCalledWith(42, 10, 1, true))

  await userEvent.click(screen.getByRole("button", { name: "Сохранить" }))
  await waitFor(() => expect(campaignsApi.saveOffers).toHaveBeenCalledWith(42))
})
```

- [ ] **Step 2: Run to verify failure**

Run: `cd apps/web && pnpm vitest run src/pages/campaign-edit`

Expected: FAIL because add/lock/save buttons are not wired.

- [ ] **Step 3: Implement the offer picker**

`apps/web/src/pages/campaign-edit/ui/offer-picker-dialog.tsx`:

```tsx
import { useQuery } from "@tanstack/react-query"
import { useMemo, useState } from "react"

import { campaignsApi, type FlowOffers } from "@/shared/api/campaigns"
import { Button, Dialog, DialogContent, DialogHeader, DialogTitle, Input } from "@/shared/ui"

type Props = {
  flow: FlowOffers
  open: boolean
  onOpenChange: (open: boolean) => void
  onPick: (offerId: number) => void
}

export function OfferPickerDialog({ flow, open, onOpenChange, onPick }: Props) {
  const [search, setSearch] = useState("")
  const offers = useQuery({ queryKey: ["offers"], queryFn: campaignsApi.offers, enabled: open })
  const used = useMemo(() => new Set(flow.offers.map((offer) => offer.offer_id)), [flow])
  const filtered = (offers.data ?? []).filter(
    (offer) => !used.has(offer.id) && offer.name.toLowerCase().includes(search.trim().toLowerCase()),
  )

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader><DialogTitle>Добавить оффер в «{flow.name}»</DialogTitle></DialogHeader>
        <Input placeholder="Поиск оффера" value={search} onChange={(event) => setSearch(event.target.value)} />
        <div className="flex max-h-80 flex-col gap-1 overflow-y-auto">
          {filtered.map((offer) => (
            <Button key={offer.id} onClick={() => onPick(offer.id)} variant="ghost" className="justify-start">
              {offer.name}
            </Button>
          ))}
          {!offers.isPending && filtered.length === 0 && (
            <p className="text-sm text-muted-foreground">Подходящих офферов нет.</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
```

- [ ] **Step 4: Wire mutations into the editor**

Replace `apps/web/src/pages/campaign-edit/ui/campaign-edit-page.tsx` with:

```tsx
import { useState } from "react"
import { Link, useParams } from "react-router-dom"
import { useMutation } from "@tanstack/react-query"
import { ArrowLeftIcon } from "lucide-react"
import { toast } from "sonner"

import { campaignsApi, type OfferItem, type OfferRotation } from "@/shared/api/campaigns"
import { getApiErrorMessage } from "@/shared/lib/get-api-error-message"
import { Alert, AlertDescription, AlertTitle, Button, Card, CardContent, CardHeader, CardTitle } from "@/shared/ui"

import { useCampaignOffers } from "../api/use-campaign-offers"
import { FlowOffersCard } from "./flow-offers-card"
import { OfferPickerDialog } from "./offer-picker-dialog"

export function CampaignEditPage() {
  const { campaignId } = useParams()
  const id = Number(campaignId)
  const { rotation, setRotation, refresh } = useCampaignOffers(id)
  const [pickerStream, setPickerStream] = useState<number | null>(null)

  const apply = (data: OfferRotation) => setRotation(data)
  const addOffer = useMutation({
    mutationFn: ({ streamId, offerId }: { streamId: number; offerId: number }) =>
      campaignsApi.addOffer(id, streamId, offerId),
    onSuccess: (data) => { apply(data); setPickerStream(null) },
  })
  const deleteOffer = useMutation({
    mutationFn: (payload: { streamId: number; offerId: number }) =>
      campaignsApi.deleteOffer(id, payload.streamId, payload.offerId),
    onSuccess: apply,
  })
  const restoreOffer = useMutation({
    mutationFn: (payload: { streamId: number; offerId: number }) =>
      campaignsApi.restoreOffer(id, payload.streamId, payload.offerId),
    onSuccess: apply,
  })
  const lockOffer = useMutation({
    mutationFn: (payload: { streamId: number; offer: OfferItem }) =>
      campaignsApi.lockOffer(id, payload.streamId, payload.offer.offer_id, !payload.offer.locked),
    onSuccess: apply,
  })
  const save = useMutation({
    mutationFn: () => campaignsApi.saveOffers(id),
    onSuccess: (data) => { apply(data); toast.success("Изменения сохранены в Keitaro") },
  })

  const errors = [refresh.error, addOffer.error, deleteOffer.error, restoreOffer.error, lockOffer.error, save.error]
  const error = errors.find(Boolean)
  const pickerFlow = rotation?.flows.find((flow) => flow.stream_id === pickerStream)

  return (
    <div className="flex flex-col gap-6">
      <Button asChild className="w-fit" size="sm" variant="ghost">
        <Link to="/campaigns"><ArrowLeftIcon data-icon="inline-start" />Назад к кампаниям</Link>
      </Button>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight">Редактор кампании</h1>
        <div className="flex gap-2">
          <Button disabled={refresh.isPending} onClick={() => refresh.mutate()}>Получить потоки</Button>
          <Button disabled={!rotation || save.isPending} onClick={() => save.mutate()}>Сохранить</Button>
        </div>
      </div>
      {error && (
        <Alert variant="destructive">
          <AlertTitle>Ошибка</AlertTitle>
          <AlertDescription>{getApiErrorMessage(error)}</AlertDescription>
        </Alert>
      )}
      {!rotation && !refresh.isPending && (
        <Card>
          <CardHeader><CardTitle>Потоки не загружены</CardTitle></CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Нажмите «Получить потоки», чтобы загрузить данные из Keitaro.
          </CardContent>
        </Card>
      )}
      {rotation?.flows.map((flow) => (
        <FlowOffersCard
          key={flow.stream_id}
          flow={flow}
          disabled={addOffer.isPending || deleteOffer.isPending || restoreOffer.isPending || lockOffer.isPending}
          onAdd={() => setPickerStream(flow.stream_id)}
          onDelete={(offer) => deleteOffer.mutate({ streamId: flow.stream_id, offerId: offer.offer_id })}
          onRestore={(offer) => restoreOffer.mutate({ streamId: flow.stream_id, offerId: offer.offer_id })}
          onLock={(offer) => lockOffer.mutate({ streamId: flow.stream_id, offer })}
        />
      ))}
      {pickerFlow && (
        <OfferPickerDialog
          flow={pickerFlow}
          open
          onOpenChange={(open) => { if (!open) setPickerStream(null) }}
          onPick={(offerId) => addOffer.mutate({ streamId: pickerFlow.stream_id, offerId })}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 5: Run editor tests**

Run: `cd apps/web && pnpm vitest run src/pages/campaign-edit`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/pages/campaign-edit
git commit -m "feat(web): edit offers and shares in existing campaigns"
```

---

## Task 14: End-to-End Verification and Documentation

**Files:**
- Modify: `README.md`
- Modify: `specs/001-keitaro-campaign-manager/checklists/requirements.md`
- Modify: `apps/web/README.md`

**Interfaces:**
- Consumes: all previous tasks.
- Produces: verified build and documented limitations.

- [ ] **Step 1: Run backend checks**

```bash
cd apps/api
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```

Expected: all green.

- [ ] **Step 2: Run frontend checks**

```bash
cd apps/web
pnpm test
pnpm typecheck
pnpm lint
pnpm fsd:lint
pnpm build
```

Expected: all green. Steiger may flag `insignificant-slice` if a page slice has no references; routes reference all three pages, so this should not fire. If it does, merge the page helper into its page UI rather than adding an entity layer.

- [ ] **Step 3: Run the database migration from scratch**

```bash
make db-down
make db-up
make migrate
```

Expected: PostgreSQL starts; Alembic upgrades to head with the `campaign_offer_states` table.

- [ ] **Step 4: Verify against a live Keitaro instance**

Set real values in `.env`:

```dotenv
KEITARO_BASE_URL=https://your-keitaro.example.com
KEITARO_API_KEY=real-key
```

Then verify:

1. `GET /api/v1/campaigns` returns campaigns and local search works.
2. `GET /api/v1/campaigns/form-options` returns domains, groups and traffic sources.
3. Create a campaign with a country, domain, group, source and offer.
4. In Keitaro, confirm two flows: a country-filtered Google redirect and an offer flow.
5. Open the campaign editor, press `Получить потоки`, confirm offers and shares.
6. Add an offer; confirm equal redistribution; lock one offer and add another; confirm the locked share is unchanged.
7. Delete and restore an offer; press `Сохранить`; confirm in Keitaro that only active offers are present.
8. Delete an offer in Keitaro, press `Получить потоки`, confirm it appears deleted and can be restored.

Live contract was already verified on 2026-11-14: `country` exists in `GET /admin_api/v1/stream_filters`, and `GET /admin_api/v1/streams_actions` exposes `http` as the redirect action. Offer flows in the live instance use `schema="landings"`. If the instance changes, update the constants in `apps/api/app/domain/keitaro/constants.py` and the gateway tests.

- [ ] **Step 5: Document limitations**

Add to `README.md`:

```markdown
## Ограничения

- Нет авторизации и ролей.
- Нет автоматической синхронизации: потоки загружаются только по кнопке «Получить потоки».
- Локально хранятся только зафиксированные проценты и удалённые офферы; всё остальное — из Keitaro.
- Если удалить последний активный оффер в потоке и сохранить, поток останется без офферов и при следующем «Получить потоки» будет пропущен по правилу «потоки без офферов не разбираются».
- Создание кампании не откатывается, если Keitaro принял кампанию, но отклонил создание потока.
```

- [ ] **Step 6: Update the spec checklist**

Mark implementation verification complete in `specs/001-keitaro-campaign-manager/checklists/requirements.md` only after the live Keitaro steps pass. Do not mark them complete when using only mocked tests.

- [ ] **Step 7: Final commit**

```bash
git add README.md apps/web/README.md specs/001-keitaro-campaign-manager/checklists/requirements.md
git commit -m "docs: document keitaro campaign manager"
```

---

## Self-Review Notes

- **Spec coverage:** creator fields and two flows → Task 5; manual flow loading and empty-flow skip → Task 4; add/delete/restore/lock shares → Tasks 1, 6; save → Task 7; Keitaro-side deletion → Task 2 sync; local campaign search → Tasks 4, 10; mandatory domain/group/source → Task 5 validation; error display → Task 8 and frontend alerts.
- **Deliberate edge:** deleting the last active offer is allowed. Saving then sends an empty offer list for that flow. This is documented in Task 14 because the spec forbids parsing empty flows on refresh.
- **Live contract risk:** `country`, `redirect`, and `offers` are the only unverified Keitaro vocabulary. Task 14 defines the exact probe and the two constants to change if the instance differs.

