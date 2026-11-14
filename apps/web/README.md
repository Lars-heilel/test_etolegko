# Web

React 19 + Vite + TypeScript, React Router, TanStack Query, shadcn/ui.
FSD-слои: `app`, `pages`, `shared`. Общий запуск API и PostgreSQL — в
корневом [`README.md`](../../README.md).

Маршруты: `/campaigns` — список и локальный поиск; `/campaigns/new` — создание;
`/campaigns/:id/edit` — ручная загрузка и редактор офферов.

Из `apps/web`:

```bash
pnpm dev
pnpm build
pnpm typecheck
pnpm test
pnpm lint
pnpm fsd:lint
```

`pnpm install` устанавливает зависимости. Dev-сервер: http://localhost:5173.
`VITE_API_BASE_URL` задаётся в `apps/web/.env`, по умолчанию `/api/v1`;
Vite проксирует `/api` на API :8000. Ключ Keitaro хранится только на backend.
Production build помещается в `dist`; при раздаче требуется SPA fallback
и доступный API (dev proxy в production отсутствует).

Создание требует существующих оффера, домена, группы и источника из Keitaro.
Пустой каталог блокирует форму; после заполнения в Keitaro нажмите «Обновить каталоги».
Редактор загружает потоки только по кнопке «Получить потоки». Изменения записываются
в локальную БД, а в Keitaro — по «Сохранить». Перезагрузка страницы не восстанавливает
черновик автоматически; новая загрузка сверяет его с upstream. Ошибки сохранения
сохраняют текущие данные в UI. После частичной записи проверьте Keitaro перед повтором.

Проверено 2026-11-14: 49 тестов, typecheck, lint/FSD и build; lint имеет 3 существующих
Fast Refresh warning, build — предупреждение размера bundle. Chromium с реальным API:
live read-only список/поиск/пустые каталоги и mock создание/загрузка. Live запись не проверена.
