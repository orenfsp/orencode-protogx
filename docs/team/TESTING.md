# Проверки и результаты

Команды ниже относятся к объединённой реализации. Для существующего стенда
добавляйте `-p fspmandatory`; для обычного Compose оставляйте без `-p`.
Проверяйте project name: тесты создают отдельную тестовую БД, но live browser
сценарии добавляют фиктивные записи в выбранную demo-БД.

## Что уже выполнено

- До последнего исправления аудита наблюдателя: полный PostgreSQL —
  **172 passed, 500.624 s**; основной Chrome — **120 passed / 6 optional skipped,
  10.0 m**.
- После исправления `active_role=None`: **3 целевых backend passed, 2.336 s**;
  отдельный enabled optional-live — **6 passed, 35.2 s**. Перед ним был
  неуспешный optional-прогон 4 passed / 1 failed / 1 not run; ошибка исправлена.
- Последующий аудит текущего кода: **49 backend passed, 67.781 s**.
- Проверка критериев: read-only наполнение дисциплин (результаты по 2 из 6);
  С3 в транзакции с откатом (иная дисциплина спортсмена принята, HTTP 201).
- TypeScript/ESLint/production build, Ruff, migration drift, warning-free OpenAPI,
  design contract и синхронизация OIDC CSS прошли в интеграционной границе.

Это разные прогоны. Полный backend и основной Chrome после последнего runtime-fix
не повторялись. Для обновления документации функциональные наборы не запускались.
[Журнал объединения](../integration-verification.md),
[evidence объединения](../evidence/integration-2026-10-28/),
[аудит](../tz-readiness-audit-2026-10-28.md),
[evidence аудита](../evidence/tz-audit-2026-10-28/),
[дополнительные проверки критериев](../evidence/criteria-review-2026-10-28/).

## Backend

Из корня в PowerShell:

```powershell
docker compose exec -T api python manage.py check
docker compose exec -T api python manage.py test --noinput
docker compose exec -T api ruff check .
docker compose exec -T api python manage.py makemigrations --check --dry-run
docker compose exec -T api python manage.py spectacular --validate --fail-on-warn --file /tmp/fsp-schema.yaml
python scripts/check_design_contract.py
python scripts/sync_optional_styles.py --check
```

Генерация схемы внутри контейнера не доказывает совпадение с сохранённым
`docs/openapi.yaml`. Для точной сверки скрипт должен видеть корень репозитория:

```powershell
$taskRoot = (Get-Location).Path.Replace('\','/')
docker compose run --rm --no-deps -v "${taskRoot}:/workspace" -w /workspace/backend api python /workspace/scripts/check_openapi_schema.py
```

Контейнерные команды проверяют код образа; после runtime-правок сначала
пересоберите образ либо используйте осознанный bind mount исходников.
PostgreSQL нужен для constraints/locks/concurrency; SQLite не заменяет этот gate.

## Frontend и Chrome

Из `frontend/`:

```powershell
npm.cmd ci
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
npm.cmd run test:e2e -- --workers=1
```

Для существующего стенда перед Playwright:

```powershell
$env:FSP_WEB_URL='http://127.0.0.1:13001'
$env:FSP_MAILPIT_URL='http://127.0.0.1:18025'
$env:FSP_E2E_COMPOSE_PROJECT='fspmandatory'
```

Chrome должен быть установлен. Live XLSX требует доступный Python/openpyxl.
Сборка и тесты одного frontend не запускаются одновременно. Login throttle
не отключается; один worker снижает конфликты живых сценариев.

## Дополнительные live-сценарии

Нужны `seed_optional`, подготовленные локальные ключи и работающий тестовый
OIDC-клиент на 9012. Issuer должен совпадать с настройкой API:

```powershell
$env:FSP_OPTIONAL_LIVE='1'
$env:FSP_OIDC_ISSUER='http://127.0.0.1:18001'
npm.cmd run test:e2e -- tests/optional-live.spec.ts --workers=1
```

Без флага шесть optional-live тестов пропускаются; пропуск не считается pass.
[Подготовка OIDC и consumer](../optional-demo.md).
Webhook доставляет отдельная `deliver_webhooks`; основной notification worker
обслуживает inbox/outbox и напоминания.

## Визуальные и документационные проверки

`npm.cmd run visual:qa` и `npm.cmd run visual:phase2` сохраняют снимки.
Скриншоты не заменяют осмотр; capture может переписать tracked PNG.
[Объём ручной проверки](../design/visual-qa.md).

Для docs-only изменения: локальные ссылки/пути, согласованность статусов
и команд с кодом/Compose/OpenAPI, `git diff --check`, design contract.
Не называйте старый прогон новым и не суммируйте пересекающиеся наборы тестов.
