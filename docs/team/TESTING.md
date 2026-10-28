# Проверки и точные команды

Актуальная схема автоматизации и настройки изолированного CI описаны в [docs/CI.md](../CI.md). Исторические результаты ниже не заменяют результаты текущего запуска.

Статус ниже относится к текущему документационному спринту 2026-10-27; «проверено» означает **команда реально выполнена**, а «поддерживается» означает найденный script/config и исторические свидетельства в [матрице](../acceptance-matrix.md), но не новый прогон. Все команды запускайте из указанной директории. Тестовая БД Django создаётся и удаляется тестовым runner; существующий Compose volume не сбрасывается.

| Из корня, PowerShell | Назначение | Текущий результат |
| --- | --- | --- |
| `docker compose ps` | состояние сервисов | проверено: `db` и `api` healthy, `web` up |
| `docker compose exec -T api python manage.py test` | backend suite на PostgreSQL | проверено: 23 теста, OK, exit 0 |
| `docker compose exec -T api ruff check .` | Python lint | проверено: `All checks passed!`, exit 0 |
| `docker compose exec -T api python manage.py makemigrations --check --dry-run` | drift моделей/миграций | проверено: `No changes detected`, exit 0 |
| `docker compose exec -T api python manage.py spectacular --validate --file /tmp/fsp-doc-schema.yaml` | сгенерировать/валидировать OpenAPI внутри контейнера | проверено: exit 0; сохранённый `docs/openapi.yaml` сверяйте отдельно по paths/operations |
| `python scripts/check_design_contract.py` | SHA-256 HTML и точный extracted CSS | проверено: `PASS`, exit 0 |
| `python scripts/check_openapi_schema.py` | warning-free генерация OpenAPI и сравнение с `docs/openapi.yaml` | проверено в изолированном Python-окружении PR #1: `PASS`, exit 0 |
| `docker compose exec -T api python manage.py migrate` | применить миграции | команда присутствует в startup и исторически проверена; отдельно в этом спринте не запускалась |
| `docker compose exec -T api python manage.py seed_demo` | фиктивные аккаунты | исторически проверена; отдельно в этом спринте не запускалась |
| `python -m pip install -r backend/requirements.txt` | локальные Python-зависимости | команда подтверждена `requirements.txt`, но в этом спринте не выполнялась; Compose уже собран |

В `frontend/` (в PowerShell `npm.cmd`, потому что `npm` может вызвать запрещённый `npm.ps1`):

| Команда | Назначение | Текущий результат |
| --- | --- | --- |
| `npm.cmd ci` | зависимости из lockfile | поддерживается Dockerfile и lockfile; отдельно не запускалась |
| `npm.cmd run typecheck` | `tsc --noEmit` | проверено: exit 0 |
| `npm.cmd run lint` | `eslint .` | проверено: exit 0 |
| `npm.cmd run build` | Next production build | проверено: compile, TypeScript и генерация 10 static pages прошли, exit 0 |
| `npm.cmd run test:e2e` | Playwright Phase 1/2 | первый параллельный со сборкой прогон: 6/7, exit 1; Phase 2 упал на `page.goto('/login')` по таймауту 10 s |
| `npm.cmd run test:e2e -- tests/phase2.spec.ts --workers=1` | повтор конкретного сбоя после сборки | проверено: 1/1, exit 0, 45.7 s; нет свидетельства функционального дефекта из первого таймаута |
| `npm.cmd run visual:qa` | снимки Phase 1 | поддерживается `capture-visual-qa.mjs`; требует Chrome и Compose |
| `npm.cmd run visual:phase2` | 24 снимка Phase 2 | поддерживается `capture-phase2-qa.mjs`; требует Chrome и Compose |

`playwright.config.ts` использует `channel:"chrome"`, `FSP_WEB_URL` либо `http://127.0.0.1:3000`. Скриншоты сохраняются в `docs/design/screenshots/`; запуск capture может переписать tracked PNG, поэтому в документационном спринте не запускайте его без задачи на обновление baseline. Визуальное соответствие проверяют **осмотром** снимков при 1440/768/390 px в светлой и тёмной теме, а не только кодом выхода. `backend/pytest.ini` настроен для `pytest`, но основной проверенный путь — Django `manage.py test`. `frontend/package.json` не содержит отдельного unit-test script.

Если вы меняете только docs, минимальный gate: ссылки и пути, `git diff --check`, invariant design hash, schema/source cross-check и отсутствие правок runtime. Для backend/frontend задачи добавьте соответствующий набор выше. Не называйте незапущенную проверку успешной.
