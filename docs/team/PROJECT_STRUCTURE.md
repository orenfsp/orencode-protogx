# Структура репозитория

Актуально для runtime `0c43b00`.
[Архитектура](ARCHITECTURE.md), [статус](CURRENT_STATUS.md),
[правила владения](AI_AGENT_RULES.md).

- `backend/config/` — settings/URL/ASGI/WSGI, PostgreSQL, DRF, OpenAPI,
  регистрация модулей, SMTP и opt-in OIDC.
- `backend/apps/accounts/`, `catalogs/` — идентичности/роли/согласия,
  профиль, дисциплины/организации и seed_demo.
- `backend/apps/competitions/` — соревнования, заявки, coach links,
  судьи/результаты, шаблоны/версии протоколов и экспорт.
- `backend/apps/qualifications/`, `ratings/`, `teams/` —
  квалификации, рейтинги/ограничения, ручная сборная и документы.
- `backend/apps/registry/`, `notifications/` —
  исторический реестр/аналитика/XLSX, основной inbox/outbox/worker.
- `backend/apps/extensions/` — Д1–Д12, models/services/views/URLs,
  OAuth Toolkit integration, шаблоны страниц OIDC и seed_optional.
- `backend/apps/*/migrations/` — версионная схема и справочники;
  extensions содержит 0001–0016. Изменения согласует интегратор.
- `backend/tests/` — auth/workflow/permissions, квалификации, реестры,
  рейтинг/сборная, уведомления, optional_* и проверки схемы.
- `frontend/src/app/` — App Router, страницы обязательных кабинетов и
  процессов, analytics/participation, services и дополнительные экраны.
- `frontend/src/components/` — AppShell, формы соревнований/результатов,
  реестров и квалификаций, NotificationCenter, FeatureWorkspace, ReportFilters.
- `frontend/src/lib/` — API/CSRF, общие DTO, навигация и ограничения UI.
- `frontend/tests/` — mocked state/race/permission проверки и live/browser/visual.
- `scripts/` — design/OpenAPI проверки, визуальные captures через frontend scripts,
  подготовка optional demo, тестовые OIDC/consumer и вспомогательные проверки.
- `docs/` — требования, текущие аудит/матрица/памятка, контракты и evidence.
- `docs/design/fsp-reference.html` — неизменяемый исходный дизайн.
- `docker-compose.yml` — db/api/web/mailpit/notifications;
  `docker-compose.optional.yml` — локальный opt-in OIDC override.
- `tmp/` — игнорируемые локальные ключи, overrides, зависимости и QA-файлы;
  этот каталог не является поставляемой конфигурацией нового клона.

Shared модели/роли/DTO/OpenAPI, permissions, Compose, AppShell и общие стили
изменяются только интегратором или по его контракту. Независимые агенты
получают точный allowlist. Исторические отчёты не расширяют текущую задачу.
