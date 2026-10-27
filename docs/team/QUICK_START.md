# Быстрый старт

Проверено в Windows PowerShell 2026-10-27: Docker Compose уже обслуживал `db`, `api`, `web`; команда `docker compose ps` показала здоровые `db` и `api`. Запуск нового окружения по этим инструкциям основан на текущих `docker-compose.yml` и Dockerfile. Не выполняйте `docker compose down -v`: том `postgres_data` хранит данные.

## Подготовка

Нужны Git, Docker с Compose, Python 3.13 для локальных скриптов, Node/npm для фронтенда и установленный Google Chrome для Playwright. Remote у текущего клона **не настроен**; URL репозитория выдаёт руководитель. Команды клонирования — в [GIT_WORKFLOW.md](GIT_WORKFLOW.md).

Из корня репозитория:

```powershell
Copy-Item .env.example .env
# Заполните локальные POSTGRES_PASSWORD и DJANGO_SECRET_KEY в .env
docker compose up -d --build
docker compose ps
```

Откройте `http://localhost:3000`; API: `http://localhost:8000/api/v1/health/`; схема: `http://localhost:8000/api/schema/`; Swagger UI: `http://localhost:8000/api/docs/`. Сервис `api` при запуске делает `migrate`; в `DJANGO_DEBUG=1` также вызывает идемпотентный `seed_demo`. `web` ждёт healthcheck API. Если порты заняты, настройте `FSP_DB_PORT`, `FSP_API_PORT`, `FSP_WEB_PORT` и соответствующий `DJANGO_CSRF_TRUSTED_ORIGINS` до запуска; детали — [ENVIRONMENT.md](ENVIRONMENT.md).

## Первый вход и проверка

Фиктивные аккаунты перечислены в [demo-scenarios.md](../demo-scenarios.md). Локальный `seed_demo` сохраняет изменённые пароли при повторном запуске. Для быстрой проверки:

```powershell
docker compose exec -T api python manage.py test
docker compose exec -T api ruff check .
python scripts/check_design_contract.py
```

Из `frontend/` в PowerShell используйте `npm.cmd`, если политика выполнения запрещает `npm.ps1`:

```powershell
npm.cmd ci
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
```

Полный список, условия Playwright и статус проверок — в [TESTING.md](TESTING.md). Локальный Python без `DATABASE_ENGINE=sqlite` обращается к PostgreSQL; безопаснее выполнять Django-команды через работающий контейнер. Перед первой правкой прочтите [AI_AGENT_RULES.md](AI_AGENT_RULES.md) и получите конкретный [контракт задачи](TASK_TEMPLATE.md).
