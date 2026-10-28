# Контракт интегратора: mandatory part 1

Назначение: пользователь передал `C:\Users\User\Downloads\codex-fsp-01-mandatory.md`, затем официальный PDF и подтвердил продолжение. Дата начала 2026-10-28. Ветка `codex/mandatory-case-completion`, исходный SHA `ee60893d2278001aaa6b704943230c0bd2db6eeb`, исходная интеграционная ветка `alpha`. Merge, force-push и публикация не разрешены. Чужие untracked audit/report/worktree файлы сохраняются.

Владелец всех пяти tracks — Codex как единственный интегратор: core/users/permissions/schema; competitions/documents; sports domain; federation frontend; cabinets/QA. Последовательная интеграция без независимого редактирования shared interfaces. Разрешённые пути: `backend/apps`, `backend/config`, `backend/tests`, `frontend/src`, `frontend/tests`, `.github/workflows/ci.yml`, `docker-compose.yml`, `.env.example`, `README.md`, соответствующие `docs/`. Reference `docs/design/fsp-reference.html` и extracted `frontend/src/app/globals.css` неизменяемы.

Новые контракты: notifications/read/report-deadlines; profile/consents; qualification corrections; coach-link lifecycle; competition registration/regulations/types; athlete report/personal protocol. Единая session/CSRF схема и существующие User/UserRole сохранены; миграции добавочные. Общие DTO и OpenAPI обновляет интегратор.

Приёмка: восемь строк case table на с.5–6, вложенные процессы с.1–5 и deliverables с.9; отдельное сопоставление 18 AC в `docs/case-mandatory-traceability.md`. PostgreSQL regression/locking/IDOR/role checks; warning-free OpenAPI; migration drift; TypeScript/lint/build; Chrome E2E/SMTP capture; desktop/tablet/mobile light/dark screenshots и axe; файлы открываются/разбираются, а не проверяются только по статусу 200.

DeepSeek: фактические инструменты обнаружены; `get_project_context` проверил существующий `backend/apps/competitions/services.py`. Ограниченная задача checklist негативных проверок уведомлений с allowlist `backend/tests/test_notifications.py` завершилась `provider_http_503`, proposal отсутствует, файлы не записывались. Модель и endpoint не предполагались. Дальнейшую реализацию выполнил интегратор.

Внешние gates: production email receipt/credentials, сверка действующих первоисточников, hosted CI на final SHA. Демо/локальная интеграция не заменяет эти gates. Они описываются как unverified/blocked, а не passed.

Результат реализации: `b41ca96`, завершающие исправления `99cc63d`. Точное свидетельство команд, статусы восьми групп и ограничения — [mandatory-verification.md](../../mandatory-verification.md), [case-mandatory-traceability.md](../../case-mandatory-traceability.md). Общий статус сохраняется partial при незакрытых внешних и продуктовых gates.
