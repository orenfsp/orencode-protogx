# Хранение данных и миграции

Рабочая БД — PostgreSQL 16 (`db` в `docker-compose.yml`) с именованным томом `postgres_data`. Django использует `POSTGRES_*`; `DATABASE_ENGINE=sqlite` — явное локальное исключение. Нельзя очищать том, пересоздавать БД или переписывать базовые миграции ради удобства разработки.

| App / миграции | Модели и связи |
| --- | --- |
| `accounts/0001_initial.py` | `User` (email unique), `UserRole` (unique user+role), `Guardian` (minor→User), `PersonalDataConsent` (user→User, guardian nullable) |
| `catalogs/0001_initial.py`, `0002_seed_disciplines.py` | `Discipline` (`code` unique), шесть seed-дисциплин |
| `competitions/0001_initial.py` … `0005_protocoltemplate_competition_type_and_more.py` | `AgeGroup`, `CalendarEntry`, `ProtocolTemplate`, `Competition` и `CompetitionStage`, `CoachAthleteLink`, `Application`, `JudgeAssignment`, `Result`, `ProtocolPublication`, `AuditEvent`; конфигурационные seed и обратные backfill-миграции |

Существенные ограничения БД: `CalendarEntry` unique `(source, entry_number, year)`; `ProtocolTemplate` unique `(discipline, version)`; `CompetitionStage` unique `(competition, order)`; `CoachAthleteLink` unique `(coach, athlete, discipline)`; `Application` unique `(competition, athlete)`; `JudgeAssignment` unique `(competition, judge)`; `Result.application` — one-to-one; `ProtocolPublication` unique `(competition, version)`. `Competition.age_groups` — M2M, `discipline`/`template`/`calendar_entry` защищены `PROTECT`. `ProtocolPublication.snapshot` — JSON снимок опубликованной версии; изменение текущих `Result` не переписывает старый снимок.

`AgeGroup` задаёт включающие границы `min_age`/`max_age`; `CalendarEntry` хранит указатель на ЕКП/региональный календарь, но ссылка не доказывает официального соответствия. `ProtocolTemplate` хранит `metric_fields`, `columns`, `sections`, `signature_roles`, `sort` в JSON и метаданные источника. `Result.metrics` валидируется против выбранной версии шаблона. `AuditEvent` хранит `actor`, тип/id объекта, необязательное соревнование и `before/after`, но текущий аудит охватывает лишь реализованные Phase 2 переходы. Нет моделей разрядов, рейтинга, сборной, уведомлений или исторического реестра.

## Процедура изменения схемы

1. Согласуйте модель, влияние на существующие строки, DTO и права с руководителем. Один разработчик владеет конкретной миграцией.
2. Создайте **новую** миграцию в назначенном app; не меняйте уже применённые `0001–0005`. Для обязательного нового поля предусмотрите безопасный backfill и обратимость, если это возможно.
3. Просмотрите операции миграции, зависимости и данные. Выполните `docker compose exec -T api python manage.py makemigrations --check --dry-run` после фиксации; ожидается `No changes detected`.
4. На изолированном Compose project/тестовой БД выполните `python manage.py migrate`, тесты и проверку схемы. Не запускайте опасную обратную миграцию или `down -v` на общей БД.
5. Передайте руководителю migration file, контракт, последствия для существующих данных и результаты. Правка `accounts.User`, ролей и shared моделей никогда не делается агентом самостоятельно.

Текущий Compose `api` выполняет миграции при старте. Команды и переменные — в [ENVIRONMENT.md](ENVIRONMENT.md), проверки — в [TESTING.md](TESTING.md).
