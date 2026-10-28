# Итог проверки mandatory part 1 — 2026-10-28

Ветка `codex/mandatory-case-completion`; baseline `ee60893d2278001aaa6b704943230c0bd2db6eeb`; финальный код **`223bebe28ac7fc1f5e4244f42d0e642b68fd3bdd`**. Последующая фиксация отчётов, журналов и PNG не меняет runtime или тесты. PR не создан, push/merge не выполнялись; hosted CI этого SHA не запускался. Локальные проверки ниже не выдаются за GitHub Actions.

## Фактически выполненные проверки

- PostgreSQL/Django: **139 passed, 0 failed, 0 skipped, 367.625s**. Включены роли/объекты/consent, история и поиск, документы, рейтинги/сборная, уведомления, конкурентные worker и дедупликация.
- Полный Chrome/Playwright, один worker: **118 passed, 0 failed, 0 skipped, 7.6m** на финальном коде. Это единый полный успешный запуск, а не сумма целевых повторов. Включены live процессы соревнования/разряда, категории/SMTP Mailpit, реестров/двухлетнего XLSX, рейтинга/ручной сборной и файлов, role/logout races, visual/axe.
- `npm.cmd run typecheck`, `npm.cmd run lint` — exit 0. Production `docker compose -p fspmandatory build web` — exit 0: Next.js 16.4.3, TypeScript, 17 страниц.
- Backend `ruff check .` — `All checks passed!`; `makemigrations --check --dry-run` — `No changes detected`; Django system check — без ошибок.
- `scripts/check_openapi_schema.py` в контейнере — `PASS: docs/openapi.yaml matches warning-free generation`.
- `python scripts/check_design_contract.py` — PASS; `git diff --check` — exit 0. Reference HTML и extracted `globals.css` неизменны.
- Изолированный Compose `fspmandatory`: пять сервисов работают; db/api/mailpit имеют статус healthy. Fresh migrations/фиктивный seed выполнены при создании отдельного volume, повторные старты сохраняют данные. Исходный `fsp-platform` не сбрасывался.

Фактические журналы: [evidence](evidence/mandatory-2026-10-28/README.md). Backend проверен до коммита на том же содержимом Python; после него менялись только frontend/тест и документация. Full browser выполнен после фиксации `223bebe28ac7fc1f5e4244f42d0e642b68fd3bdd`. SHA и контрольные суммы снимков записаны в manifest.

## Воспроизведение

Из корня в PowerShell:

```powershell
$env:FSP_DB_PORT='55433'
$env:FSP_API_PORT='18001'
$env:FSP_WEB_PORT='13001'
$env:FSP_MAILPIT_PORT='18025'
$env:DEMO_SEED_ENABLED='1'
$env:DEMO_ENVIRONMENT='local'
$env:DJANGO_CSRF_TRUSTED_ORIGINS='http://127.0.0.1:13001,http://localhost:13001'
docker compose -p fspmandatory up -d --build --wait
docker compose -p fspmandatory exec -T api python manage.py test --noinput
docker compose -p fspmandatory exec -T api python manage.py makemigrations --check --dry-run
docker compose -p fspmandatory exec -T api ruff check .
python scripts/check_design_contract.py
```

Полный backend прогон здесь исполнялся в одноразовом API-контейнере с mount `backend:/app`: `docker compose -p fspmandatory run --rm --no-deps -v C:/Users/User/Documents/ChatGPT/fsp-platform/backend:/app api python manage.py test --noinput`. Схема проверялась с mount корня в `/workspace`, workdir `/workspace/backend`: `python /workspace/scripts/check_openapi_schema.py`.

Из `frontend` после `npm ci` (Chrome установлен):

```powershell
$env:FSP_WEB_URL='http://127.0.0.1:13001'
$env:FSP_MAILPIT_URL='http://127.0.0.1:18025'
$env:FSP_E2E_COMPOSE_PROJECT='fspmandatory'
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run test:e2e -- --workers=1
```

Live XLSX test требует Python/openpyxl, как указано в CI. На этой машине зависимость установлена во временный каталог и передан `PYTHONPATH=C:/Users/User/Documents/ChatGPT/fsp-platform/tmp/xlsx-test-deps`; на обычной машине достаточно доступного openpyxl. Реальный login throttle 5/min не отключался, поэтому live tests запускаются одним worker. Backend проверяет PostgreSQL locks/constraints; SQLite не заменяет этот прогон.

## Новые сценарии и исправленные сбои

Поиск тренером → запрос → подтверждение спортсменом → приостановление → журнал обоих владельцев; федерация исправляет реквизиты → видит прежние/новые значения и причину. Отдельно 2 passed / 25.0s, затем оба вошли в полный успешный набор. 6 новых coach screenshot/keyboard/axe состояний входят в первый live test.

Предыдущий полный набор 118 тестов дал 117 passed / 1 failed: повторяющаяся причина в сохранённой истории делала locator неоднозначным. Тест теперь использует уникальную причину, история не очищается. Новая мобильная проверка обнаружила native select вне контейнера формы: длинное название дисциплины расширяло страницу. Поле перенесено в существующий `workflow-form`, overflow устранён без правок reference/CSS. Более ранние тестовые logout races, неполные mocks, mobile aria-label и временный контраст toast исправлены ранее; ошибки не скрывались ослаблением axe.

## Файлы и визуальная приёмка

30 live PNG: dashboard/profile/history/qualifications/coach-links × 1440/768/390 × light/dark, `docs/design/screenshots/mandatory/`. Проверки page overflow и axe serious/critical проходят; coach search и summary работают клавиатурой. Ранее registry и рейтинги также покрыты viewport/theme/state тестами полного набора. Осмотрены представительные desktop/tablet/mobile снимки, включая новый coach desktop light/mobile dark. Сохранены sidebar numbering, dotted navigation, document rail, stamps, indigo/orange, темы и bottom nav. Широкие таблицы прокручиваются в своём контейнере; full-page screenshot фиксирует sidebar/bottom nav в положении последнего viewport. Это особенность capture, не заявление о ручном обходе каждого элемента.

Образцы реальных защищённых API: protocol PDF/DOCX, regulations DOCX, athlete XLSX, personal protocol PDF. DOCX проверены как OOXML, XLSX открыт openpyxl и содержит сохранённую версию/данные, кириллица PDF извлечена, страницы отрендерены и осмотрены. Тесты проверяют latest publication, пустой файл, formula injection и приватность. Личная выписка содержит только собственную строку, полный демонстрационный протокол — три. Прежние snapshots с историческими англоязычными названиями не переписывались.

## Точные внешние ограничения

1. Email: SMTP adapter/worker и реальное принятие Mailpit проверены. Credentials production-провайдера и получение внешним ящиком не предоставлены/не проверены. `sent` означает принятие SMTP, возможен at-least-once повтор при аварии. Процедура — [notifications.md](notifications.md).
2. Нормативы: часть файлов ФСП скачана и выборочно осмотрена, обнаружено расхождение названия ссылки ЕВСК с содержимым. Действующая консолидированная редакция всех норм/шести форм не установлена. Непроверенные правила не дают подсказок, шаблоны остаются демонстрационными. URL/хеши/границы — [regulatory-source-review.md](regulatory-source-review.md).
3. Представитель: сведения/согласие/история и проверки сохранены; личность и реальная подпись представителя организационно не подтверждаются онлайн checkbox. Демо-личности вымышленные.
4. Hosted CI: нет запуска на финальном SHA; push/Draft PR требуют отдельного разрешения по пользовательскому заданию. Ветка остаётся локальной, merge не выполнялся.

Работающие программные сценарии восьми групп реализованы и локально проверены; полное официальное/production соответствие не объявляется. D1–D12 не входят в задачу. Статусы проектных AC отдельно зафиксированы в [матрице](acceptance-matrix.md).
