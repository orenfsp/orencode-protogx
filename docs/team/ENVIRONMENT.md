# Окружение и переменные

`docker-compose.yml` определяет `db` (`postgres:16-alpine`, named volume `postgres_data`), `api` (Python 3.13 + Django), `web` (Node 24 + Next production build), `mailpit` и фоновый worker `notifications`. `api` ждёт healthy БД, выполняет миграции и при явном разрешении demo seed запускает идемпотентный `seed_demo`; `web` и worker ждут healthy API. SMTP настройки и ограничения доставки описаны в [notifications.md](../notifications.md). Redis не требуется.

| Переменная | Где используется | Что задать локально |
| --- | --- | --- |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | `db`, `api` | отдельные локальные значения из `.env.example`; секрет не коммитить |
| `DJANGO_SECRET_KEY` | `api` | длинная случайная локальная строка, не значение по умолчанию |
| `DJANGO_DEBUG` | `api` | `1` для фиктивного seed; `seed_demo` отказывается работать при `0` |
| `DJANGO_ALLOWED_HOSTS` | Django | hostname API, значения через запятую |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Django | точные URL origin фронтенда, включая изменённый порт |
| `FSP_DB_PORT`, `FSP_API_PORT`, `FSP_WEB_PORT` | Compose host ports | по умолчанию 5432/8000/3000; пригодны для отдельного Compose project |
| `API_INTERNAL_URL` | Next rewrite/build | Compose: `http://api:8000`; локальный default `http://127.0.0.1:8000` |
| `DATABASE_ENGINE` | Django local | `sqlite` только для явного локального теста; по умолчанию PostgreSQL |
| `FSP_WEB_URL` | Playwright | необязательный baseURL вместо `http://127.0.0.1:3000` |

`.env.example` не содержит production credentials; скопируйте в `.env` и измените секреты. `.gitignore` исключает `.env`, `node_modules`, `.next`, `*.sqlite3`, Playwright outputs. Не вставляйте реальные секреты в issue, PR или AI prompt.

## Команды запуска

PowerShell из корня:

```powershell
Copy-Item .env.example .env
docker compose up -d --build
docker compose ps
docker compose exec -T api python manage.py migrate
docker compose exec -T api python manage.py seed_demo
```

Последние две команды при обычном старте уже выполнены startup command; повторять миграцию или seed можно для проверки, но не используйте seed с реальными пользователями. `seed_demo` работает только в debug. Для локального backend без Docker команда установки из существующего `requirements.txt` — `python -m pip install -r backend/requirements.txt` (в этом спринте не выполнялась). После настройки PostgreSQL: `python backend/manage.py migrate`, затем `python backend/manage.py runserver`; для быстрых локальных тестов допустим явно заданный `DATABASE_ENGINE=sqlite`. Frontend: `Set-Location frontend; npm.cmd ci; npm.cmd run dev`. Эти локальные install/dev команды подтверждены файлами конфигурации, но не выполнялись в текущем спринте. В Bash/macOS/Linux замените `Copy-Item` на `cp`, `Set-Location` на `cd`, `npm.cmd` на `npm`.

Если нужно испытать чистую установку, используйте **другое имя Compose project и отдельные свободные порты**, как в корневом [README](../../README.md); этот документ не предлагает трогать существующий том. При завершении обычной работы `docker compose stop` оставляет данные на месте. Подробнее об отказах — [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
