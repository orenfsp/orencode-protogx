# Разработка backend

Backend — Django 5, DRF, `drf-spectacular`, PostgreSQL. Конфигурация и маршруты — `backend/config/settings.py`, `backend/config/urls.py`. Все HTTP-маршруты перечислены в [API_CONTRACTS.md](API_CONTRACTS.md). Никакого отдельного `permissions.py` сейчас нет: роль проверяют views и `require_role`, объект ограничивается выборкой и проверками сервиса.

## `accounts`

**Назначение:** email-идентификация, session login/logout, несколько ролей, согласие и guardian. `models.py`: `User(AbstractUser)` без username; `UserRole` с уникальностью `(user, role)`; `PersonalDataConsent` с версией/способом подтверждения; `Guardian` с `confirmation_status`. `serializers.py`: `RegisterSerializer` проверяет пароль, дату рождения, `consent=true`, точную demo-версию `v1-demo-2026-10-27`; несовершеннолетнему требует сведения и согласие представителя. `create` атомарно создаёт пользователя, роль спортсмена, guardian и согласие. `MeSerializer` выдаёт только `id`, `email`, `full_name`, `roles`, `active_role`, без данных guardian.

`views.py`: `CsrfView`, `RegisterView`, `LoginView`, `LogoutView`, `MeView`, `ActiveRoleView`, `DashboardView`. `urls.py` подключён под `/api/v1/auth/`. Login ограничен `5/min`; register/login/logout/active-role защищены CSRF, `SessionAuthentication` является глобальным. `DashboardView` повторно проверяет назначение роли перед счётчиками; athlete получает только свой guardian status. `management/commands/seed_demo.py` создаёт пять фиктивных записей лишь при `DEBUG=1`, повторный запуск сохраняет существующие пароли. Тесты: `backend/tests/test_auth.py`, `test_dashboard.py`, `test_seed_demo.py`.

**Точка расширения:** изменение модели `User`, набора ролей, guardian/consent или DTO требует архитектурного решения, миграции, тестов доступа и согласования с frontend. Саморегистрация не выдаёт federation/coach/judge.

## `catalogs`

`Discipline(code, name, is_active, config)` — справочник; `0002_seed_disciplines.py` вводит шесть дисциплин. `DisciplineSerializer` возвращает лишь `id`, `code`, `name`; `DisciplineListView` открыто читает активные записи через `/api/v1/disciplines/`. `admin.py` содержит административное управление; отдельного write API нет. Тест — `backend/tests/test_catalog.py`. Изменение кодов дисциплин затрагивает шаблоны, фильтры, seed и протоколы; согласуйте со владельцем контракта.

## `competitions`

`models.py` содержит `AgeGroup`, `CalendarEntry`, `ProtocolTemplate`, `Competition`, `CompetitionStage`, `CoachAthleteLink`, `Application`, `JudgeAssignment`, `Result`, `ProtocolPublication`, `AuditEvent`. Связи и ограничения подробно в [DATABASE.md](DATABASE.md). `serializers.py` валидирует форму соревнования: соответствие дисциплины/типа/даты шаблона, порядок дат, обязательную дату вычисления возраста и группу, вложенные этапы hybrid; `create/update` сохраняют M2M и этапы. В `views.py` лежат роли, фильтры видимости, переходы и аудит. `services.py` содержит правила eligibility, шаблона/результата и сборку/публикацию snapshot. `exporters.py` генерирует PDF/DOCX исключительно из сохранённой публикации. Тесты — `backend/tests/test_competitions.py`.

Состояния: `Competition` объявляет `draft`, `published`, `closed`, но код переводит только `draft → published`; отдельной операции закрытия нет. `Application`: `pending → approved/rejected`, решение только для pending; отказ требует `reason`. `CoachAthleteLink`: `pending → confirmed/rejected` по решению спортсмена. `Result`: `classified`, `no_show`, `unclassified`, `disqualified`; не классифицированный результат не несёт score/place/metrics. Повторная запись результата снимает `validated_by`; федерация валидирует снова. `ProtocolPublication` не изменяется: следующий выпуск создаёт версию с `correction_reason`.

`@transaction.atomic` используется при создании/изменении соревнования, публикации, создании шаблона, подаче/решении заявки, вводе/валидации результата, решении по coach link; `publish_protocol` атомарен в сервисе. `select_for_update` стоит на критичных строках при публикации соревнования и протокола, заявке решения, вводе/валидации результата, coach link. Не переносите доменные проверки только в React. Аудит вызовов `audit` следует выполнять в той же транзакции, когда он защищает изменение.

## Как добавить backend-функцию после выдачи задания

1. Зафиксируйте владельца путей и согласуйте DTO, роли, объектную видимость, состояния и миграции с руководителем по [TASK_TEMPLATE.md](TASK_TEMPLATE.md).
2. Начните с поведения и отрицательных проверок в `backend/tests/`. Для существующего соревнования дополняйте `services.py` и сериализатор по их текущей ответственности; view отвечает за HTTP/выборку.
3. Сохраняйте валидацию на сервере и атомарность связанного изменения; пишите `AuditEvent` для материального перехода. Не раскрывайте PII через новые списки.
4. После согласования схемы создайте миграцию `docker compose exec -T api python manage.py makemigrations <app>`; ревьюируйте SQL/операции и зависимость от `accounts.User`. Не удаляйте поля/таблицы или существующий том.
5. Обновите `docs/openapi.yaml` через `spectacular` только вместе с утверждённым контрактом и frontend DTO; проверьте список маршрутов, ошибки и тесты.
6. Выполните [TESTING.md](TESTING.md), передайте перечень фактических команд и результатов. Миграции текущего проекта: `accounts/0001`, `catalogs/0001–0002`, `competitions/0001–0005`.

Новый модуль Phase 3 не является заданием этого спринта.
