# Текущий статус — mandatory part 1, 2026-10-28

Назначение пользователя: `codex-fsp-01-mandatory.md` + официальный PDF, с подтверждением «заканчивай до конца». Ветка `codex/mandatory-case-completion`; baseline `ee60893d2278001aaa6b704943230c0bd2db6eeb`; финальный код **`223bebe28ac7fc1f5e4244f42d0e642b68fd3bdd`**. Документационный спринт ниже исторический; это явное новое разрешение обязательной разработки. D1–D12 вне задачи.

Программные сценарии всех восьми обязательных групп реализованы и локально проверены. Последние пробелы — coach search по имени, journal связей и ledger квалификаций в UI — закрыты. Общая архитектура, роли/session/CSRF, PostgreSQL и reference сохранены.

**PostgreSQL 139 passed / 0 failed / 0 skipped (367.625s); полный Chrome 118 passed / 0 failed / 0 skipped (7.6m).** Typecheck/lint/production build (17 страниц), ruff, migration drift, warning-free OpenAPI и design contract прошли. Сохранены 30 live PNG пяти экранов × 3 widths × 2 themes; новые coach keyboard/axe/overflow состояния прошли. Все AC-01…AC-18 имеют локальный pass в описанной границе.

Точные команды/логи/сбои: [verification](../mandatory-verification.md), [evidence](../evidence/mandatory-2026-10-28/README.md); [AC matrix](../acceptance-matrix.md); [восемь групп](../case-mandatory-traceability.md); [coach/history](../coach-links-and-history.md).

Стенд `fspmandatory`: web `http://127.0.0.1:13001`, Mailpit `http://127.0.0.1:18025`, пять сервисов работают. Демо-аккаунты/пароль — [demo-scenarios.md](../demo-scenarios.md). Данные исходного `fsp-platform` не сбрасывались. Push/PR/merge не выполнялись.

Внешние gates не объявляются passed: production SMTP credentials/receipt; действующие консолидированные нормативы и официальные формы; реальная identity/signature verification представителя; hosted CI финального SHA. Web доступ восстановился, несколько исходных документов скачаны/выборочно осмотрены, найдены расхождения подписи ссылки ЕВСК с содержимым: [source review](../regulatory-source-review.md). Демо-шаблоны не verified; реальные письмо/законность не подменяются Mailpit/checkbox. Предыдущее ограниченное implement_task MCP вернуло 503; повторное review_code вернуло предложения через настроенную модель, интегратор сам проверил/реализовал изменения.

## Исторический snapshot — 2026-10-27 (не текущая оценка)

Код сверён с базовым `HEAD=600562d` и [матрицей AC-01…AC-18](../acceptance-matrix.md). В текущем спринте отдельно исполнены проверки, перечисленные в [TESTING.md](TESTING.md); остальные свидетельства относятся к [Phase 1](../phase1-baseline.md) и [Phase 2](../phase2-architecture.md). **Phase 3: NOT STARTED / НЕ НАЧАТА.** Этот документационный спринт не добавляет функциональности.

| Область | Статус | Реальная граница |
| --- | --- | --- |
| Compose, PostgreSQL, Django/DRF, Next.js | implemented | `db`, `api`, `web`; healthcheck, миграции и фиктивный seed в debug |
| Регистрация, session login/logout, CSRF, 4 роли | implemented | регистрация даёт `athlete`; иные роли назначает доверенный администратор; guardian записывается как `pending_verification` |
| Четыре кабинета и переключение ролей | implemented для сводок | один маршрут `/dashboard`, данные `auth/dashboard/`; специализированные доменные экраны размещены на иных маршрутах |
| Шесть дисциплин, возрастные группы, календарные записи | implemented | дисциплины seeded; группы и записи доступны на чтение, федерация может создавать |
| Соревнование → заявка → модерация → судья → результат | implemented | тесты Phase 2 и реальный API; отдельного закрытия соревнования нет |
| Версионные дисциплинарные шаблоны и протокол | implemented для demo workflow | snapshot всех approved, приватный preview/list/download, source verification остаётся обязательной |
| Личная история спортсмена | implemented | последняя опубликованная версия; только собственная строка |
| PDF и DOCX опубликованного протокола | partial для всего AC-14 | остальные типы документов и XLSX отсутствуют |
| Аудит и object permissions | partial для всей платформы | Phase 2 события и проверки покрыты; общий аудит будущих модулей ещё не существует |
| Разряды и категории судей | not_implemented | AC-09 |
| Email/внешние уведомления | not_implemented | AC-10, SMTP/Mailpit сервиса нет |
| Реестр и аналитика участия за 2 года, XLSX | not_implemented | AC-11 |
| Рейтинг и ручной отбор сборной | not_implemented | AC-12, AC-13 |

Матрица фиксирует AC-01…AC-08, AC-16…AC-18 как `implemented`, AC-14/15 как `partial`, AC-09…AC-13 как `not_implemented`. `source_verified` у демо-шаблонов ложен; предоставленная ссылка на образец не подтверждена сверкой с актуальным первоисточником. Публикация демо-протокола не подтверждает соответствие официальной форме или ЕВСК. Самостоятельное подтверждение опекуна при регистрации также не является юридической проверкой. Все seed-личности фиктивные.

Следующий этап требует отдельного назначения и согласования модели, DTO, прав, миграций и источников нормативных правил. В текущем спринте это только список будущих зависимостей.
