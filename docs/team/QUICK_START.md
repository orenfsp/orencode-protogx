# Быстрый старт

Актуально для объединённого runtime-кода `0c43b00`.
Remote репозитория: `https://github.com/KAIROS-2000/ProtoGX.git`.
Текущая интеграционная ветка локальная; её наличие на remote не предполагается.
[Текущее состояние](CURRENT_STATUS.md), [README](../../README.md).

## Стандартный локальный запуск

Нужны Docker с Compose; Node/npm и Chrome — для frontend/Playwright.
В PowerShell из корня:

```powershell
if (-not (Test-Path -LiteralPath .env)) { Copy-Item .env.example .env }
docker compose up -d --build --wait
docker compose ps
```

Перед первым запуском задайте свои локальные пароль БД и Django secret.
Seed выполняется только при `DJANGO_DEBUG=1`, `DEMO_SEED_ENABLED=1`,
`DEMO_ENVIRONMENT=local` и локальном хосте БД. API сначала применяет миграции,
затем условный seed. Текущие пароли и существующая история сохраняются.
Не удаляйте volume ради повторного запуска.

Сайт: `http://localhost:3000`; API: `http://localhost:8000/api/v1/health/`;
Swagger: `http://localhost:8000/api/docs/`; Mailpit: `http://localhost:8025`.
Аккаунты: [demo-scenarios.md](../demo-scenarios.md).

Дополнительные записи:

```powershell
docker compose exec -T api python manage.py seed_optional
```

Эта команда также требует локальных demo flags. OIDC-ключ не нужен для
обычных кабинетов; полный ФСП ID подготавливается по [optional-demo.md](../optional-demo.md).

## Существующий изолированный стенд

Для `fspmandatory` используются порты 13001/18001/55433/18025.
Не запускайте второй экземпляр на тех же портах. В новом окружении задайте
свои свободные `FSP_WEB_PORT`, `FSP_API_PORT`, `FSP_DB_PORT`,
`FSP_MAILPIT_PORT` и согласованный `DJANGO_CSRF_TRUSTED_ORIGINS`.
[Воспроизведение объединения](../integration-verification.md).

## Проверки

```powershell
docker compose exec -T api python manage.py test --noinput
docker compose exec -T api ruff check .
docker compose exec -T api python manage.py makemigrations --check --dry-run
python scripts/check_design_contract.py
python scripts/sync_optional_styles.py --check
```

Из frontend: `npm.cmd ci`, `npm.cmd run typecheck`, `npm.cmd run lint`,
`npm.cmd run build`. Не запускайте сборку одновременно с тестами против того
же frontend. [Полные команды и evidence](TESTING.md).

Для новых задач: [AI_AGENT_RULES.md](AI_AGENT_RULES.md),
[контракт](TASK_TEMPLATE.md). Нормативные и визуальные источники сохраняются;
сама документация не разрешает новый функциональный этап.
