# Матрица приёмки AC-01–AC-18

Актуализировано 28.10.2026. Runtime-код `0c43b00`,
ветка `codex/integrate-optional-d1-d12`.
`implemented` — технический сценарий с указанным свидетельством;
`partial` — незакрытое требование или приёмка; `not_implemented` —
реализация отсутствует. Полного pass по ТЗ нет.

Сами требования AC заданы [MASTER_PROMPT](MASTER_PROMPT.md).
[Аудит PDF](tz-readiness-audit-2026-10-28.md) и
[29 критериев оценки](defense-criteria-guide-2026-10-28.md) используют
исходные документы организаторов; веса критериев не заменяются числом тестов.

| ID | Статус | Реализация, свидетельство и граница |
| --- | --- | --- |
| AC-01 | implemented | Рабочий Next.js, кабинеты и responsive/theme проверки. Полный ручной осмотр новых форм отдельно в AC-18. |
| AC-02 | implemented | Django/DRF/PostgreSQL, миграции, API health и warning-free OpenAPI. Интеграционный PostgreSQL-прогон — 172 passed до последнего audit fix. |
| AC-03 | implemented | Несколько назначенных ролей, активный кабинет, серверные права; backend и Chrome switching/logout/race проверки. |
| AC-04 | implemented | Все шесть дисциплин в справочнике/шаблонах/создании событий. Демо-соревнования и результаты только по двум: условие максимума Т2 ещё не закрыто. |
| AC-05 | implemented | Создание/публикация → заявка → модерация → судья/результат проходит. Возраст/сроки/согласия/дисциплина coach link проверяются. Отдельного запрета по отсутствующей дисциплине самого спортсмена нет — ограничение С3 требует трактовки. |
| AC-06 | implemented | Публикация включает всех approved, в том числе pending_result без выдуманного места; rejected не включаются. |
| AC-07 | implemented | Дисциплинарные типизированные метрики, колонки и новые версии шаблонов работают. Приёмка заданной формы не закрыта, см. AC-14. |
| AC-08 | implemented | Личная история из собственной строки последней immutable publication; полный competition browser workflow прошёл. |
| AC-09 | partial | Заявки/основание/решение/приказ/срок/история/исправления работают. Подсветка ЕВСК на стенде не настроена: QualificationRule 0. Аудит повторил qualification tests. |
| AC-10 | implemented | Сохранённый inbox/outbox, SMTP/Mailpit, worker, retry/read/dedup/role+object scope; категория → кабинет → SMTP проверены. Production mailbox receipt не проверялся. |
| AC-11 | implemented | Основной исторический реестр, два года и больше, разрезы/API/UI/XLSX с fingerprint проверены. Д3 TrainingMembership не попадает в общий отчёт автоматически; это отдельный незакрытый optional-сценарий. |
| AC-12 | implemented | Версии баллов, сезон/дисциплина, Decimal и 1.2, latest-source provenance, ограничения, фильтры и breakdown проверены. |
| AC-13 | implemented | Ручной отбор/порядок/аудит, рейтинг → состав → PDF/DOCX; проект приказа неподписанный, форма требует проверки. |
| AC-14 | partial | Файлы из БД, форматы/содержимое/приватные downloads проверены. Все 6 текущих шаблонов протокола unverified, заданные формы не приняты. |
| AC-15 | implemented | Серверные роли/объекты/согласия, журнал actor/active role/before/after/reason. Observer active_role=None исправлен и повторно проверен. Реальная identity verification представителя не заявляется. |
| AC-16 | implemented | Compose, migrations, opt-in seed, повторный запуск с сохранением данных, инструкции и фиктивные аккаунты. Hosted CI финального runtime SHA не запускался. |
| AC-17 | implemented | Reference HTML и extracted globals.css не изменены; design-contract PASS. |
| AC-18 | partial | Основные viewport/theme/axe/keyboard проверки и представительные осмотры есть. Ручная приёмка всех расширенных дополнительных форм/состояний не завершена. |

## Дополнительные сценарии и критерии защиты

[Текущая трассировка Д1–Д12](case-optional-traceability.md):
Д1/Д2/Д5/Д9/Д10/Д11 реализованы в описанных demo-границах;
Д3/Д4/Д6/Д7/Д8/Д12 — partial. Правила Д4/Д7/Д8 вымышленные.
Готовность С7 процесса разряда не означает готовность нормативной подсветки ЕВСК.
П1/П2 зависят от выступления; отдельный собственный сценарий Р2 не принят.

## Исполненные свидетельства

До последнего исправления аудита: 172 backend passed (500.624 s),
основной Chrome 120 passed/6 optional skipped (10.0 m).
После исправления: 3 целевых backend passed (2.336 s), отдельный optional-live
6 passed (35.2 s). Последующий аудит текущего кода: 49 backend passed (67.781 s).
Полные наборы после последнего runtime-fix не повторялись; числа не суммируются.

[Интеграционный отчёт](integration-verification.md),
[evidence объединения](evidence/integration-2026-10-28/),
[evidence аудита](evidence/tz-audit-2026-10-28/),
[проверка С3/Т2](evidence/criteria-review-2026-10-28/),
[команды](team/TESTING.md).
Исторические 139 backend/118 Chrome на `223bebe` описаны в
[mandatory-verification.md](mandatory-verification.md); они не являются
текущей оценкой полноты ТЗ.

Production SMTP, государственные интеграции и hosted CI не добавляются
в обязательный список исходного PDF. Действующие нормативы, формы и реальная
проверка представителя остаются явными границами эксплуатации.
