# Keitaro Campaign Manager

Внутренний инструмент для работы с рекламным трекером Keitaro:

1. создание кампании с двумя потоками (гео-редирект на Google + оффер);
2. редактор офферов существующей кампании.

> **Текущий статус:** реализованы список и поиск кампаний, форма создания и редактор офферов. Локальные проверки и live read-only проверка пройдены; создание и сохранение в живом Keitaro ещё не проверены. Требования — в [`specs/001-keitaro-campaign-manager/spec.md`](specs/001-keitaro-campaign-manager/spec.md).

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
│           ├── pages/           # список, создание, редактор, 404
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
# Заполните KEITARO_BASE_URL и KEITARO_API_KEY в .env.

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

Compose запускает только PostgreSQL; API и web запускаются локально через Make.
`db-down` сохраняет volume с данными, поэтому повторный запуск не создаёт пустую БД.

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

## Возможности

- Список кампаний из Keitaro с постраничной загрузкой backend и локальным поиском по названию.
- Создание: название, одна ISO-2 страна, поиск оффера, обязательные домен, группа и источник.
- Два потока: гео-фильтр с HTTP-редиректом на Google и поток выбранного оффера.
- Ручная загрузка потоков, добавление, удаление, возврат и фиксация долей офферов; сохранение по кнопке.
- Равное распределение незакреплённой доли; если все активные офферы закреплены, новый получает 0%.
- Ошибки и частичные результаты отображаются в UI; локальные изменения при ошибке сохранения остаются.

### Пустые каталоги

Если в Keitaro нет доменов, групп, источников или офферов, форма сообщает об этом
и блокирует создание. Добавьте реальные записи в Keitaro и нажмите «Обновить каталоги».
Приложение не создаёт эти справочники и не подставляет фиктивные значения.
При проверке 2026-11-14 live API вернул 0 доменов, 1 группу и 0 источников.

## Ограничения

- Нет авторизации и ролей, автоматической синхронизации и нескольких подключений Keitaro.
- «Получить потоки» — явное обновление из Keitaro, а не чтение локального черновика.
- PostgreSQL хранит рабочий снимок загруженных офферов (ID, имена, доли, состояния и фиксации),
  включая локальные добавления/удаления до сохранения. Это больше, чем только locked/deleted.
  Перезапуск API не стирает БД; после перезагрузки страницы снимок не восстанавливается автоматически в UI.
  Повторное получение потоков сверяет состав с Keitaro и может заменить несохранённые изменения;
  активные зафиксированные доли сохраняются, исчезнувшие офферы становятся удалёнными.
- При удалении последнего активного оффера сохранение отправляет пустой список.
  Следующее получение пропускает такой поток и удаляет его локальный снимок: вернуть оффер из этого экрана уже нельзя.
- Создание кампании и запись нескольких потоков не атомарны: принятые Keitaro изменения не откатываются.
  После частичной ошибки проверьте состояние Keitaro перед повтором.
- Нет контроля конкурентного редактирования или разрешения конфликтов между пользователями.

## Проверки

```bash
make test
make lint
make typecheck
(cd apps/api && uv run ruff format --check .)
(cd apps/web && pnpm build)
```

2026-11-14: 173 backend и 49 frontend тестов прошли; typecheck, форматирование,
FSD lint и production build прошли. Oxlint выдаёт 3 предупреждения Fast Refresh
в shared UI; Vite предупреждает о большом JS chunk (около 1.25 MB / 321 kB gzip).
Миграция проверена на отдельной пустой PostgreSQL БД до `568bd7ab16ea`.
Браузерная проверка с реальным локальным API и mocked upstream покрыла создание и загрузку;
добавление/фиксация/удаление/возврат/сохранение проверены через HTTP API с PostgreSQL.
Live проверены только чтение, поиск и пустые каталоги. Live create/save и удаление на стороне
Keitaro остаются непроверенными; mock-проверки не заменяют эти критерии приёмки.

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
автоматически; GET и PUT делают до трёх попыток на сетевые ошибки и 5xx.
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
