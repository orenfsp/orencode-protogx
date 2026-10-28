# Acceptance matrix — 2026-10-28

Код `223bebe28ac7fc1f5e4244f42d0e642b68fd3bdd`, ветка `codex/mandatory-case-completion`. `implemented` — работающий программный сценарий с исполненным свидетельством; это не юридическая сертификация или production rollout. Для финальной проверки все проектные AC имеют локальное свидетельство. Внешние gates перечислены отдельно и не переименованы в passed.

| ID | Status | Исполненное свидетельство и границы |
| --- | --- | --- |
| AC-01 | implemented | Live Next.js, четыре кабинета, desktop/tablet/mobile, две темы; full Chrome 118 passed. |
| AC-02 | implemented | Django/DRF + PostgreSQL, миграции, 139 tests, API health, warning-free OpenAPI. |
| AC-03 | implemented | Одна запись User, назначенные роли/активный кабинет; backend role/revocation и browser switching/races. |
| AC-04 | implemented | Шесть дисциплин в catalog/seed/filters, разные шаблоны; backend и live создание события. |
| AC-05 | implemented | Federation create/publish → athlete entry → moderation → judge assignment/result; coach scope, age/deadline/guardian отрицательные тесты. |
| AC-06 | implemented | Snapshot включает всех approved, включая pending_result без выдуманного места/балла; backend publication test. |
| AC-07 | implemented | Разные типизированные метрики и версионные шаблоны для дисциплин; создание новой версии API/UI. Официальная актуальность форм unverified. |
| AC-08 | implemented | Последняя immutable publication → только собственная история; live E2E и приватная выписка. |
| AC-09 | implemented | Разряд/категория: заявление → решение/приказ/срок → история; discipline scope; correction ledger/UI; full backend/browser pass. ЕВСК-подсказки только по verified rules, демо-правила не verified. |
| AC-10 | implemented | Transactional inbox/outbox, SMTP/Mailpit, retries/dedup/concurrent workers/read/role+object scope; live category → cabinet → SMTP capture. Production mailbox receipt unverified. |
| AC-11 | implemented | Четыре реестра, исторические периоды/исправления, ≥2 года, filters/API/UI/XLSX consistency; live registry/create, keyboard/axe/viewport tests pass в полном наборе. |
| AC-12 | implemented | Versioned points, discipline/season, ×1.2, precise Russian levels, latest source, active exclusions, age/rank filters, minor redaction, breakdown; PostgreSQL и browser tests. |
| AC-13 | implemented | Только ручной отбор федерацией, ordering/audit/provenance; live rating → team → PDF/DOCX. Документы — неподписанный демо-проект. |
| AC-14 | implemented | Сохранённые данные → protocol/team PDF/DOCX, participation XLSX, personal excerpt PDF/DOCX, regulations DOCX. OOXML/XLSX/PDF content/layout/private-download checks pass. Официальные формы отдельно unverified. |
| AC-15 | implemented | Actor/active role/time/before/after/reasons; транзакционный audit и append ledger; role/IDOR/revoked link/consent/private exports отрицательные тесты в 139-test наборе. Онлайн проверка личности представителя не заявляется. |
| AC-16 | implemented | Fresh isolated Compose migrations/fictional seed, повторный старт/seed сохраняет данные; README и demo accounts; пять сервисов запущены. |
| AC-17 | implemented | Неизменённые reference HTML/extracted CSS, SHA manifest и design-contract PASS. |
| AC-18 | implemented | 30 live PNG: 5 экранов × 3 widths × 2 themes; registry/rating состояния, overflow/axe/keyboard, представительный ручной осмотр. Нет заявления об исчерпывающем ручном обходе всех элементов. |

Итог: **139 backend passed**, **118 browser passed**, typecheck/lint/production build/ruff/migration drift/OpenAPI/design contract passed. Журналы: [evidence](evidence/mandatory-2026-10-28/README.md); команды/разбор прошлых сбоев: [verification](mandatory-verification.md).

Для отчётности проекта: AC-01…AC-18 — **pass в указанной локальной границе**. Для production/официальной эксплуатации: нормативная актуальность и guardian identity — unverified; реальный SMTP receipt — unverified; hosted CI итогового SHA — not_run. Эти ограничения не скрываются за локальным pass. Восемь групп кейса и отличия от более строгого master prompt — в [трассировке](case-mandatory-traceability.md).
