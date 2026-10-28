# FSP OrenKod 2026

Для новых разработчиков и независимых AI-ассистентов: [документация команды](docs/team/README.md).

Платформа на Django/DRF, PostgreSQL и Next.js. Текущее задание — обязательные требования кейса, часть 1. Неизменяемый визуальный контракт: `docs/design/fsp-reference.html`. [Трассировка кейса](docs/case-mandatory-traceability.md), [матрица AC](docs/acceptance-matrix.md), [OpenAPI](docs/openapi.yaml) отделяют реализацию от фактически выполненных проверок.

## Run with Docker Compose

Copy `.env.example` to `.env` and replace the local passwords and Django secret. Run `docker compose up --build`. The frontend is at `http://localhost:3000`, API at `http://localhost:8000/api/v1/health/`, OpenAPI at `/api/schema/`, docs at `/api/docs/`. The API applies migrations and runs the opt-in demo seeder before becoming healthy. Next.js waits for that healthcheck. The database persists in a named Compose volume.

## Regional team demo and automatic seeding

Compose startup performs migrations before seeding. Copy `.env.example` to `.env` to opt in locally. The command requires `DJANGO_DEBUG=1`, `DEMO_SEED_ENABLED=1`, `DEMO_ENVIRONMENT=local` and a local database host. Production and staging must disable these settings. The command creates fictional users, competitions, published protocols, calculated ratings and regional teams; see [docs/demo-scenarios.md](docs/demo-scenarios.md).

Списки сборных и кандидатов используют API-пагинацию; экран загружает страницы и поддерживает поиск. Исторический реестр и отчёт о численности реализованы отдельно в `apps/registry`: организации, дисциплины, муниципалитеты, годы и реальные XLSX. Методика: [participation-methodology.md](docs/participation-methodology.md).

## Local development and checks

Основная проверка backend: `docker compose exec -T api python manage.py test --noinput`. Для локального Python установите `backend/requirements.txt` и настройте PostgreSQL. SQLite пригоден лишь для ограниченной локальной разработки: он не проверяет PostgreSQL exclusion constraints и блокировки.

Frontend: `cd frontend`, `npm ci`, `npm run typecheck`, `npm run lint`, `npm run build`, `npm run dev`. The frontend rewrites `/api/*` to `API_INTERNAL_URL` (default `http://127.0.0.1:8000` for local development; the Docker image compiles with `http://api:8000`).

With Compose running, run `npm run test:e2e` from `frontend/` for the Chrome role, theme and full competition workflow tests. Run `npm run visual:qa` for Phase 1 captures and `npm run visual:phase2` for competition and history captures at 1440/768/390 px in light and dark themes; see `docs/design/visual-qa.md`. These commands use an installed Google Chrome.

Run `python scripts/check_design_contract.py` to verify that the reference HTML and extracted shared CSS still match the committed design contract.

After Compose starts, `python scripts/smoke_auth.py` exercises registration, session login/logout, role denial, and the six-discipline catalog through the frontend proxy. It creates one randomly named fictional test account in the local database.

For repeatable local accounts, follow `docs/demo-scenarios.md`. You may rerun `docker compose exec -T api python manage.py seed_demo`; it preserves existing passwords. To validate a clean database without touching development data, choose an unused Compose project name and alternate host ports: set `FSP_DB_PORT`, `FSP_API_PORT`, `FSP_WEB_PORT` and `DJANGO_CSRF_TRUSTED_ORIGINS`, then run `docker compose -p <unique-name> up -d --build`. The project name scopes its PostgreSQL volume.

Registration always creates an athlete role. Federation and other roles require trusted administrator assignment. For minors, submitted guardian details remain pending verification; online self-attestation is not claimed as production-grade legal verification.

## Phase 2 walkthrough

Sign in as `demo.federation@example.test` with the local-only password in `docs/demo-scenarios.md`. In **Calendar**, create a draft competition, choose a discipline, age groups, an unverified template, dates and regulations, then publish it. Sign in as `demo.athlete@example.test` to apply. The federation approves the application and assigns `demo.judge@example.test`; the judge enters a result, which the federation validates. Preview and publish a versioned protocol, then download that version as PDF or DOCX. The athlete's **History** then shows the published result. Coaches use **Coach links** to find a consenting adult by name or request a discipline-specific link by known athlete email; the athlete must confirm it before the coach can apply for them. All demo identities and test scores are fictional.

Templates are configurable and versioned per discipline. Seeded templates are explicitly unverified demo structures. Check the current primary sports rules and the Appendix No. 5 example before any official document use; publication in this system does not claim regulatory or EVSK compliance.
## CI и проверки

Команды локальных проверок, изолированный PostgreSQL и GitHub Actions описаны в [docs/CI.md](docs/CI.md). Статус AC-11 см. в [матрице приёмки](docs/acceptance-matrix.md).

## Где проверить обязательные функции

1. Адаптивный frontend: `/dashboard`, `/competitions`, `/qualifications`, `/registry`, `/analytics/participation`, `/ratings`, `/teams`; светлая/тёмная тема, настольная и мобильная навигация. Новые screenshot/axe проверки: `mandatory-visual.spec.ts`.
2. Backend и контент: `/api/docs/`, шесть дисциплин, возрастные группы и календарные записи. Типы соревнований редактируются в кабинете федерации; новые названия сохраняются в справочник при создании события.
3. Четыре кабинета: одна учётная запись и назначенные роли; переключение в sidebar или мобильном списке. `/profile` — личный профиль и отметка РУСАДА, `/coach-links` — поиск по имени, запрос, подтверждение/приостановление/возобновление/завершение и читаемая история связей. Кабинет содержит историю согласий и отзыв/возобновление. Проверка личности представителя не установлена.
4. Соревнования: создание и публикация, положение DOCX, явное открытие/закрытие регистрации, календарный план ЕКП/регион, фильтр по возрасту, заявки, модерация, судейские должности, результаты, версии протокола и история. `/history` даёт спортсмену личную выписку из версии протокола без строк других участников.
5. Разряды, категории и сроки: `/qualifications` — заявки, решения с приказом/датами, история, аудируемые исправления реквизитов и просмотр прежних/новых значений под номером приказа. Подсказки формируются только по правилам, отмеченным проверенными; демо-правила такими не являются. Уведомления сохраняются в кабинете и отправляются через SMTP worker; [настройка и ограничения](docs/notifications.md). Сроки отчётов задаёт федерация; напоминание до 1 февраля не включает автоматический расчёт премий.
6. Численность: `/registry`, `/analytics/participation` — исторические периоды, минимум два года, разрезы и XLSX; `registry-live.spec.ts` сопоставляет API, UI и файл.
7. Рейтинг и сборная: `/ratings` — сезон/дисциплина, баллы/коэффициенты, исходные публикации; `/teams` — ручной отбор, порядок, состав и проект приказа. Действующее отстранение исключает спортсмена из видимого рейтинга.
8. Документы: протокол PDF/DOCX у федерации; личная выписка PDF и отчёт выступлений XLSX у спортсмена; отчёт подтверждённых подопечных XLSX у тренера; состав и проект приказа PDF/DOCX; динамика численности XLSX у федерации. Файлы берутся из сохранённых данных и защищены на сервере. Формы демонстрационные до сверки первоисточников.

Д1–Д12 и собственные дополнительные сценарии не входят в это задание. Ранее существующий публичный навигатор не является новой реализацией optional-функции в этой ветке. Обязательное и дополнительное разграничены в [трассировке](docs/case-mandatory-traceability.md); фиктивные аккаунты и безопасный demo-пароль — в [demo-scenarios.md](docs/demo-scenarios.md).

## Уведомления в демонстрации

После `docker compose up -d --build` Mailpit открывается на `http://localhost:8025`, worker работает автоматически. `docker compose exec -T api python manage.py process_notifications` запускает один дополнительный безопасный цикл. Реальная доставка production-провайдером требует credentials и отдельного подтверждения; Mailpit доказывает локальную SMTP-доставку.

Новый E2E: из `frontend` запустите `npm.cmd run test:e2e -- tests/mandatory-live.spec.ts --workers=1`, предварительно задав `FSP_MAILPIT_URL=http://127.0.0.1:8025` для стандартного Compose. На изолированном стенде также задайте `FSP_WEB_URL`, `FSP_MAILPIT_URL` и доверенный CSRF origin с соответствующими портами.


## Итог локальной приёмки обязательной части

Код `223bebe28ac7fc1f5e4244f42d0e642b68fd3bdd`: **139 backend tests**, **118 browser tests**, typecheck/lint/production build/ruff/migrations/OpenAPI/design — passed. Полный браузерный запуск выполнен одним worker, без отключения login throttle. [Отчёт с командами и ограничениями](docs/mandatory-verification.md), [неизменяемые свидетельства](docs/evidence/mandatory-2026-10-28/README.md), [поиск и журналы](docs/coach-links-and-history.md), [сверка нормативных источников](docs/regulatory-source-review.md).

Текущий изолированный стенд: `http://127.0.0.1:13001`, Mailpit `http://127.0.0.1:18025`. Все изменения в `codex/mandatory-case-completion`; push/PR/merge не выполнялись. Программная реализация проверена локально. Production receipt, действующие консолидированные нормативы/официальные формы и реальная проверка представителя не подтверждены; hosted CI итогового SHA не запускался.
