# Частые проблемы

| Симптом | Проверка и действие |
| --- | --- |
| PowerShell отказывает `npm.ps1` из-за Execution Policy | Используйте `npm.cmd` (`npm.cmd run typecheck`); не нужно ослаблять системную политику. |
| `api` не становится healthy | `docker compose ps`, затем `docker compose logs api`; проверьте БД, переменные и миграции. Не удаляйте том. |
| `web` не стартует | `web` ждёт healthy `api`. Проверьте API прежде, чем пересобирать frontend; затем `docker compose logs web`. |
| Порт 3000/8000/5432 занят | Настройте `FSP_WEB_PORT`, `FSP_API_PORT`, `FSP_DB_PORT`, обновите `DJANGO_CSRF_TRUSTED_ORIGINS` и `FSP_WEB_URL`; внешний порт не меняет `API_INTERNAL_URL=http://api:8000` внутри Compose. |
| 403 при POST/PATCH | Проверьте login, активную назначенную роль, объектную область, CSRF token и trusted origin. UI role selector не выдаёт назначение. |
| Несовершеннолетний не может подать заявку | Guardian с регистрации остаётся `pending_verification`; требуется административно подтверждённый `verified` и согласие, согласно текущему сервису. Не обходите проверку фиктивным score. |
| Coach не видит athlete | До `confirmed` link ответ намеренно скрывает id/имя; запрос привязан к дисциплине. |
| Протокол не публикуется | Все заявки должны быть решены, все введённые результаты валидированы, согласия актуальны; повторной версии нужна `correction_reason`. Approved без результата допустим и попадёт как `pending_result`. |
| PDF/DOCX содержит demo-warning | Шаблонный источник не верифицирован; экспорт не является официальным нормативным документом. |
| Playwright сообщает, что Chrome не найден | Установите Google Chrome, так как конфиг использует `channel:"chrome"`; сервисы Compose и нужный baseURL должны отвечать. |
| Локальный Python ищет PostgreSQL | Используйте `docker compose exec -T api ...` или явно установите `DATABASE_ENGINE=sqlite` только для локальной проверки. |
| `git push` или PR не работают | У текущего клона нет remote; запросите URL и доступ у руководителя, проверьте `git remote -v`. Не придумывайте remote. |

Для воспроизводимого бага передайте команду, exit code, релевантный лог **без секретов**, branch/hash, endpoint/роль/объект и ожидаемое поведение. Смотрите [AUTH_AND_PERMISSIONS.md](AUTH_AND_PERMISSIONS.md) и [TESTING.md](TESTING.md).
