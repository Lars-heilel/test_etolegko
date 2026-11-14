# Keitaro Campaign Manager

Внутренний инструмент для работы с рекламным трекером Keitaro:

1. создание кампании с двумя потоками (гео-редирект на Google + оффер);
2. редактор офферов существующей кампании.

> **Текущий статус:** backend реализует создание кампаний и локальный редактор офферов с сохранением в Keitaro. Frontend пока содержит страницы-заглушки. Требования — в [`specs/001-keitaro-campaign-manager/spec.md`](specs/001-keitaro-campaign-manager/spec.md).

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
make migrate      # alembic upgrade head
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
- Backend: клиент Keitaro, use cases, модели и миграция локального кеша офферов, тесты API и доменной логики; frontend: `vitest` для `cn`.
- Линтеры: `ruff`, `mypy`, `oxlint`, `steiger`.

## Что дальше

- Реальные формы, поиск офферов, редактор потоков и весов.
- Генерация TS-клиента из OpenAPI.

## API

- `GET /api/v1/health` — состояние API.
- `GET /api/v1/campaigns` — все кампании Keitaro, пагинация внутри backend.
- `GET /api/v1/campaigns/form-options` — домены, группы кампаний, источники трафика.
- `GET /api/v1/offers` — каталог офферов; `?search=` фильтрует имена локально.
- `POST /api/v1/campaigns` — создание кампании с Google- и offer-потоками.
- `GET /api/v1/campaigns/{id}/offers` — обновление локального кеша потоков и офферов из Keitaro.
- `POST /api/v1/campaigns/{id}/flows/{stream_id}/offers` — локальное добавление оффера.
- `DELETE /api/v1/campaigns/{id}/flows/{stream_id}/offers/{offer_id}` — локальное soft-delete.
- `POST /api/v1/campaigns/{id}/flows/{stream_id}/offers/{offer_id}/restore` — восстановление.
- `PATCH /api/v1/campaigns/{id}/flows/{stream_id}/offers/{offer_id}/lock` — фиксация/разблокировка доли.
- `PUT /api/v1/campaigns/{id}/offers` — сохранение активных офферов и долей в Keitaro.

Редактор работает с загруженными потоками. Локальные изменения сохраняются в БД,
но отправляются в Keitaro только через PUT. Refresh сохраняет доли активных locked-офферов,
помечает исчезнувшие офферы deleted и убирает пустые/исчезнувшие потоки.
При ошибке локальная транзакция откатывается; удалённые записи не откатываются.
Создание и сохранение нескольких потоков не атомарны. POST создания не повторяется
автоматически; GET и PUT наследуют ограниченные retry клиента на сетевые ошибки и 5xx.
После частичной ошибки проверьте Keitaro перед повтором: результат неудачного запроса
может быть неизвестен.

### Ошибки и request ID

Ошибки приложения имеют верхнеуровневые `code` и `message` (без обёртки `detail`):

| HTTP | code | Причина |
|---|---|---|
| 422 | `VALIDATION_ERROR` | Неверные поля, страна или доли; ошибки полей содержат `errors` |
| 404 | `CAMPAIGN_NOT_FOUND` | Не найдена кампания, загруженный поток или оффер |
| 409 | `OFFER_ALREADY_EXISTS` | Оффер уже присутствует, включая deleted |
| 502 | `KEITARO_UNAVAILABLE` | Ошибка ответа Keitaro или частичного создания/сохранения |
| 503 | `KEITARO_UNAVAILABLE` | Недоступность/таймаут, исчерпанные retry на 5xx или отсутствующая конфигурация Keitaro |

Частичное создание дополнительно возвращает `campaign_id` (может быть null),
`failed_step`, `confirmed_flows`; сохранение — `failed_stream_id`, `confirmed_stream_ids`.
Сообщения upstream, ключи и исходные значения полей не включаются в ошибки.
Стандартные HTTP-ошибки маршрутизации FastAPI сохраняют свой формат.

Ответы успешных запросов и обработанных ошибок содержат `X-Request-ID`, доступный через CORS.
Один входной ID из 1–128 ASCII-символов `A-Z a-z 0-9 . _ -` сохраняется;
отсутствующий, повторяющийся или некорректный ID заменяется случайным UUID hex.
ID доступен обработчикам как `request.state.request_id` и служит корреляции, не авторизации.

Backend-проверки без обращений к живому Keitaro:

```bash
cd apps/api
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy app
```
