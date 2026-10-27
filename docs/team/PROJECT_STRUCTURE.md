# Структура репозитория

| Путь | Что в нём есть сейчас | Владелец изменения |
| --- | --- | --- |
| `AGENTS.md`, `BOOTSTRAP_PROMPT.md` | общие инструкции | руководитель |
| `backend/config/settings.py`, `urls.py` | Django, DRF, маршруты `/api/v1/`, схема | руководитель |
| `backend/apps/accounts/` | `User`, роли, согласие, guardian, auth/dashboard, `seed_demo` | руководитель |
| `backend/apps/catalogs/` | шесть дисциплин и открытый read API | руководитель |
| `backend/apps/competitions/` | весь код Phase 2: модели, сериализаторы, сервисы, views, экспорты | ответственный за соревнования в выделенных файлах; общие контракты — через руководителя |
| `backend/apps/*/migrations/` | схема и начальные справочники; `competitions/0001`–`0005` | только согласованное изменение |
| `backend/tests/` | Django тесты auth, dashboard, catalog, seed, workflow | владелец задачи в выделенном тестовом файле |
| `frontend/src/app/` | App Router: `page.tsx`, `dashboard`, `competitions`, `[id]`, `coach-links`, `history`, `login`, `register`, `privacy` | владелец страницы; `layout.tsx`, CSS — руководитель |
| `frontend/src/components/` | общий `AppShell`; формы `CompetitionEditor`, `TemplateEditor`, `ResultEditor` | владелец формы только по заданию; AppShell — руководитель |
| `frontend/src/lib/api.ts` | клиент, shared TypeScript DTO, CSRF | руководитель |
| `frontend/tests/` | Playwright Phase 1/2 и helpers | QA/назначенный автор |
| `frontend/scripts/` | скриншоты визуальной проверки | QA по заданию |
| `docs/openapi.yaml` | сохранённая схема DRF | руководитель |
| `docs/design/fsp-reference.html` | неизменяемый визуальный контракт | **никто не редактирует** |
| `docs/design/visual-qa.md`, `screenshots/` | свидетельства визуального сравнения | QA после проверки |
| `docker-compose.yml`, `.env.example`, Dockerfile | запуск трёх сервисов | руководитель |
| `scripts/check_design_contract.py` | hash и точное сравнение CSS | руководитель |

Папок `backend/apps/results`, `registry`, `ratings`, `teams`, `analytics`, `frontend/src/features/*` пока нет. Упоминание этих путей в [implementation-plan.md](../implementation-plan.md) относится к плану, а не к текущей реализации. См. [TEAM_ROLES.md](TEAM_ROLES.md) перед выдачей задания.
