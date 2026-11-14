# Keitaro Campaign Manager

Внутренний инструмент для работы с рекламным трекером Keitaro:

1. создание кампании с двумя потоками (гео-редирект на Google + оффер);
2. редактор офферов существующей кампании.

> **Текущий статус:** инициализировано окружение монорепозитория. Бизнес-логика, интеграция с Keitaro API и миграции ещё не добавлены. Требования — в [`specs/001-keitaro-campaign-manager/spec.md`](specs/001-keitaro-campaign-manager/spec.md).

## Структура

```
.
├── apps/
│   ├── api/                 # FastAPI + SQLAlchemy (DDD / Onion)
│   │   ├── app/
│   │   │   ├── domain/          # сущности, value objects, интерфейсы репозиториев
│   │   │   ├── usecase/         # сценарии приложения
│   │   │   ├── infrastructure/  # конфиг, БД, адаптеры
│   │   │   └── presentation/    # FastAPI routers, схемы
│   │   ├── alembic/             # миграции
│   │   └── tests/
│   └── web/                 # React + Vite + FSD
│       └── src/
│           ├── app/             # провайдеры, роутер, стили, layouts
│           ├── pages/           # страницы-заглушки
│           └── shared/          # ui-kit (shadcn), api-клиент, config, lib
├── infra/
│   └── docker-compose.yml   # PostgreSQL для локальной разработки
├── specs/                   # спецификация фичи
├── Makefile
└── .env.example
```

Архитектура backend — по skill `python-fastapi-ddd-skill`, структура frontend — по skill
`feature-sliced-design`. Спека намеренно не дублирует их правила.

## Требования

- Python 3.12+ и [uv](https://docs.astral.sh/uv/)
- Node.js 22+ и pnpm 12+
- Docker + Docker Compose (для PostgreSQL)
- GNU Make

## Быстрый старт

```bash
cp .env.example .env

make install      # uv sync + pnpm install
make db-up        # PostgreSQL в Docker
make migrate      # alembic upgrade head (пока без ревизий)
make dev          # API :8000 и web :5173 в одном терминале
```

Открыть:

- приложение — http://localhost:5173
- Swagger API — http://localhost:8000/docs
- healthcheck — http://localhost:8000/api/v1/health

Остановить БД:

```bash
make db-down
```

## Переменные окружения

Корневой `.env` (см. `.env.example`):

| Переменная | Назначение |
|---|---|
| `DATABASE_URL` | async DSN PostgreSQL для API и Alembic |
| `KEITARO_BASE_URL` | URL админки Keitaro |
| `KEITARO_API_KEY` | API-ключ Keitaro (только на сервере) |
| `CORS_ORIGINS` | разрешённые origin'ы через запятую |

Frontend читает `VITE_API_BASE_URL` из `apps/web/.env` (см. `apps/web/.env.example`). По умолчанию используется `/api/v1`, а Vite проксирует `/api` на `http://localhost:8000`.

## Команды

| Команда | Что делает |
|---|---|
| `make dev` | запускает API и frontend |
| `make dev-api` / `make dev-web` | запускает только одну часть |
| `make db-up` / `make db-down` | PostgreSQL в Docker |
| `make migrate` | применяет миграции |
| `make revision m="..."` | генерирует миграцию |
| `make test` | pytest + vitest |
| `make lint` | ruff + oxlint + Steiger (FSD) |
| `make typecheck` | mypy + tsc |
| `make fmt` | ruff format |

## Что уже готово

- Монорепо `apps/api` + `apps/web`, общий `.env.example`, Makefile, compose с PostgreSQL.
- FastAPI-приложение с healthcheck, CORS, настройками, async SQLAlchemy-сессией и Alembic.
- React-приложение: Vite, React Router, TanStack Query, shadcn/ui, FSD-слои `app/pages/shared`, страницы-заглушки.
- Тесты-заглушки: `pytest` для healthcheck и `vitest` для `cn`.
- Линтеры: `ruff`, `mypy`, `oxlint`, `steiger`.

## Что дальше

- Клиент Keitaro API и use cases создания/редактирования кампаний.
- SQLAlchemy-модели и первые миграции.
- Реальные формы, поиск офферов, редактор потоков и весов.
- Генерация TS-клиента из OpenAPI.
