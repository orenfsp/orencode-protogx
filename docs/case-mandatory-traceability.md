# Обязательные требования кейса — историческая трассировка

> Срез реализации `223bebe` до объединения. Его заявления «нет пробела» и
> all-pass не являются текущей оценкой исходного ТЗ. Последующий
> [аудит](tz-readiness-audit-2026-10-28.md) выявил отсутствие настроенной
> подсветки ЕВСК и приёмки заданных форм; [критерии защиты](defense-criteria-guide-2026-10-28.md)
> дополнительно уточнили С3 и Т2. Текущие статусы — в [матрице](acceptance-matrix.md).

Дата 2026-10-28; ветка `codex/mandatory-case-completion`; baseline `ee60893d2278001aaa6b704943230c0bd2db6eeb`; финальный код `223bebe28ac7fc1f5e4244f42d0e642b68fd3bdd`. Прочитан предоставленный 11-страничный PDF. Его восемь групп на с.5–6, подробности с.1–5 и deliverables с.9 сопоставлены с отдельными проектными AC-01…AC-18.

`implemented` — программная реализация; `tested` — выполненная локальная проверка этой реализации; `verified externally` требует самостоятельного свидетельства. Production receipt, legal verification и hosted CI не считаются выполненными.

| case section/page | mandatory behavior | related project AC | existing code/routes | missing items | tests/evidence | status | blocker |
| --- | --- | --- | --- | --- | --- | --- | --- |
| группа 1, с.5/9 | Responsive frontend, четыре кабинета, темы, формы/навигация/состояния | 01,03,17,18 | AppShell; app/; navigation; reference | Нет известного программного пробела | Chrome 118; 30 live PNG + registry/ratings states, axe/keyboard; design PASS | implemented, tested | Нет |
| группа 2, с.5 | Django/DRF/PostgreSQL; шесть дисциплин; контент/справочники | 02,04,16 | catalogs; competitions; types; OpenAPI; Compose | Нет | PostgreSQL 139; migrations/schema/ruff; fresh seed | implemented, tested | Нет |
| группа 3, с.5; с.1–3 | Multi-role кабинеты; federation metrics/queues; четыре реестра | 03,11,15 | auth/dashboard; registry; report-deadlines; UpcomingEvents | Нет | role/revocation/races; registry live | implemented, tested | Нет |
| с.3 | Профиль, без организации, дисциплины/стаж/представитель/РУСАДА | 09,11,15 | profile; registry; AntiDoping; ConsentPanel | Нет программного пробела | profile privacy/URL/date; live consent/RUSADA | implemented, tested | Проверка внешнего сертификата не заявляется |
| с.3 | Coach search → discipline link → athlete confirms → suspended/ended/history | 05,09,15 | coach-athlete-directory; coach-links; lifecycle/history UI | Нет | Новый live E2E + 6 viewport/theme/keyboard/axe; owner/stranger API | implemented, tested | Поиск minor только своему тренеру; initial email request сохранён |
| с.3–5 | Согласия/представитель; отзыв/возобновление/история | 03,09,15 | PersonalDataConsent; Guardian; profile/consents | Нет программного пробела | consent/guardian/negative tests, live withdrawal/renewal | implemented, tested | Реальная identity/signature verification unverified |
| группа 4, с.5; с.2–4 | Event/ЕКП/регион/format/stages/regulations/registration/entries/moderation/judges | 05 | competitions; registration; regulations; applications; judge assignments | Нет | Live Phase2; age/deadline/role/coach checks | implemented, tested | Нет |
| с.2–3 | Все approved, discipline templates, snapshots/corrections/history | 06,07,08 | publish_protocol; publications; history; personal excerpt | Нет программного пробела | Snapshot/content/privacy/latest-publication tests; live history | implemented, tested | Действующие официальные формы unverified |
| группа 5, с.6; с.2–4 | Rank/category requests, result proof, review/order/dates/history/corrections | 09 | qualifications; correction ledger; RecordHistory | Нет | Rank/category live; discipline scope/IDOR; ledger before/after | implemented, tested | Правила ЕВСК не verified, их hints отключены |
| с.2/5 | Deadlines events/reports/ranks/categories/1 февраля | 09,10 | notifications.scheduler; report-deadlines; qualification-deadlines | Нет | Scheduler dedup/role tests; cabinet UI | implemented, tested | Напоминание по кейсу, расчёт премии D8 исключён |
| с.5 | Persisted cabinet + external channel, send/read/retry/dedup | 10 | notifications; worker; SMTP; Mailpit; NotificationCenter | Нет кода интеграции | Real SMTP capture + backend concurrency/retry/revocation | implemented, tested locally | Production credentials/receipt unverified |
| группа 6, с.6; с.4 | Историческая численность ≥2 лет, filters/breakdowns/XLSX/provenance | 11 | registry/analytics/exporters; analytics/participation | Нет | API/UI/workbook consistency, periods/corrections, live export | implemented, tested | Нет |
| группа 7, с.6; с.4 | Season+discipline points/×1.2/exclusions/age/min-rank/explanation | 12 | ratings rules/contributions/services; /ratings | Нет | Decimal/defaults/mapping/republication/privacy tests; browser breakdown | implemented, tested | Баллы — изменяемые defaults кейса, не закон |
| с.4 | Manual team selection, roster/draft order/audit | 13 | teams; exporters; /teams | Нет | Live ratings→team→documents; long-name/large roster render | implemented, tested | Проект неподписанный, official form unverified |
| группа 8, с.6; с.4 | Protocol, team, athlete results, counts in real files | 14 | competitions/teams/registry exporters; reports | Нет программного пробела | Parsed DOCX/XLSX; rendered PDF; empty/formula/private checks | implemented, tested | Формы demo до сверки действующей редакции |
| с.5 §9 | Actor/role/time/change journal, access/consents, fictional seed | 15 | AuditEvent; middleware; domain services; owner querysets | Нет известного программного пробела | 139 backend tests; role/logout browser races; minor redaction | implemented, tested | Guardian identity отдельно unverified |
| с.9 | Sources, run/demo README, model/API, feature inventory/evidence | 02,16 | README; docs/team; openapi; evidence; CI workflow | Hosted run отсутствует | Local build/checks/logs; reproducible Compose | implemented, tested locally | Push/Draft PR не разрешены; hosted CI not_run |

## Что закрыто относительно baseline

Добавлены notifications inbox/outbox/worker/SMTP/scheduler, федеративные сроки отчётов и типы соревнований; профиль РУСАДА, consent withdrawal/renewal/history; все lifecycle статусы связей, поиск спортсмена и читаемые журналы; явная регистрация/положение DOCX; личная протокольная выписка и XLSX выступлений; correction ledger/UI; audit active role; текущие отстранения и русские уровни рейтинга; публичная анонимизация minor; повторяемые live fixtures и устранение mobile overflow/aria/contrast дефектов.

Итог локальной приёмки: PostgreSQL **139 passed**, полный Chrome **118 passed**, build/typecheck/lint/ruff/migrations/OpenAPI/design passed. Результаты и точные команды: [mandatory-verification.md](mandatory-verification.md). Проектные AC имеют локальный pass; официальное/production соответствие остаётся **partially verified** из-за явно перечисленных внешних gates. Программных незакрытых пунктов, ранее отмеченных для coach search/history, больше нет.

## Различия источников требований

- Кейс разрешает один внешний канал на выбор; email выбран из-за более строгого AC-10 master prompt. Mailpit проверяет SMTP, не production receipt.
- Кейс не фиксирует палитру/шрифты; принятый проектный контракт сохраняет reference HTML и CSS/hash, Rubik/Inter/JetBrains Mono, sidebar/document rail/stamps/mobile nav.
- Формат файла зависит от документа; кейс не требует все три формата у каждого отчёта.
- До 1 февраля — обязательное напоминание; расчёт премий D8 и D1–D12 вне задачи. Никакая optional-функция не включена в процент обязательного выполнения.
- Доступные оригиналы нормативов проверены выборочно: [источники и границы](regulatory-source-review.md). Непроверенные правила/формы не объявляются официальными.

Интегратор единолично ведёт пять ownership tracks и общие DTO/permissions/design. Контракт, границы DeepSeek MCP и результаты ограниченного ревью — [task contract](team/tasks/MANDATORY_PART_1.md), [coach/history](coach-links-and-history.md). Чужие untracked audit/report/worktree файлы сохранены.
