# Проверка mandatory part 1 — 2026-10-28

Ветка: `codex/mandatory-case-completion`. Исходный SHA: `ee60893d2278001aaa6b704943230c0bd2db6eeb`. Реализация: `b41ca965d4bae2246732caac8095d0ee96397f66`; завершающие исправления кода: `99cc63da252cab311d7209ce86354e8cad84627d`. Последующий коммит документации/скриншотов не меняет runtime. PR не создан, ветка не отправлялась, merge не выполнялся. `gh pr view` после разрешённого сетевого доступа подтвердил отсутствие PR текущей ветки; hosted CI этого SHA отсутствует.

## Окружение и команды

Изолированный Compose project `fspmandatory`: PostgreSQL 16, Python 3.13/Django 5.2.18, Node 24/Next 16.4.3, Google Chrome/Playwright. Стенд: web `http://127.0.0.1:13001`, API порт 18001, БД порт 55433, Mailpit `http://127.0.0.1:18025`. Исходный `fsp-platform` и его данные не сбрасывались. Изолированный PostgreSQL volume создавался новым, миграции/фиктивный seed прошли при первом запуске; повторные старты сохраняют данные.

Настройки стенда PowerShell:

```powershell
$env:FSP_DB_PORT='55433'
$env:FSP_API_PORT='18001'
$env:FSP_WEB_PORT='13001'
$env:FSP_MAILPIT_PORT='18025'
$env:DEMO_SEED_ENABLED='1'
$env:DEMO_ENVIRONMENT='local'
$env:DJANGO_CSRF_TRUSTED_ORIGINS='http://127.0.0.1:13001,http://localhost:13001'
docker compose -p fspmandatory up -d --build --wait
```

Backend: `docker compose -p fspmandatory run --rm --no-deps -v C:/Users/User/Documents/ChatGPT/fsp-platform/backend:/app api python manage.py test --noinput` — **137 passed, 0 failed, 0 skipped, 409.272s**. Выполнен на реализации до финальной текстовой локализации формата в exporter; после неё `tests.test_competitions` — **10 passed, 13.548s**. Более ранние 118/126/134 и целевые 44 теста также прошли, но не заменяют эти результаты.

`docker compose -p fspmandatory exec -T api ruff check .` — прошёл после упорядочения импортов. `python manage.py makemigrations --check --dry-run` — `No changes detected`. `python manage.py check` — без ошибок. `scripts/check_openapi_schema.py` внутри одноразового контейнера — `PASS: docs/openapi.yaml matches warning-free generation`. Все новые поля/маршруты включены в сохранённую схему.

Frontend: `npm.cmd run typecheck`, `npm.cmd run lint` — exit 0. `docker compose ... up -d --build ... --wait` выполнил production build: компиляция/TypeScript и 17 страниц прошли; все пять сервисов запущены. `python scripts/check_design_contract.py` — PASS; `git diff --check` — без whitespace ошибок.

Браузерная среда (из `frontend`):

```powershell
$env:FSP_WEB_URL='http://127.0.0.1:13001'
$env:FSP_MAILPIT_URL='http://127.0.0.1:18025'
$env:FSP_E2E_COMPOSE_PROJECT='fspmandatory'
$env:PYTHONPATH='C:/Users/User/Documents/ChatGPT/fsp-platform/tmp/xlsx-test-deps'
npm.cmd run test:e2e -- --workers=1
```

`PYTHONPATH` здесь нужен лишь локальной машине, где openpyxl установлен во временную папку; на CI зависимость устанавливается штатным шагом. На чистой машине достаточно установить openpyxl согласно CI. Реальный login throttle не отключался: последовательный запуск необходим, чтобы live tests не конкурировали за общий лимит 5 входов/минуту.

## Итог браузерной проверки

Полный последовательный запуск на runtime `99cc63d`: **115 passed / 1 failed, 7.5m**. Единственный сбой — гонка ожидания logout в `registry-live.spec.ts`, runtime не менялся. После добавления `await expect(page).toHaveURL(/\/$/)` перед следующим переходом целевой повтор: **1 passed, 10.1s**. Все 116 сценариев имеют успешное свидетельство, но единый полный прогон 116/116 после этой тестовой правки **не выполнялся**; результат не переименовывается в 116 passed. Логи сохранены в `docs/evidence/mandatory-2026-10-28/`.

Полный прогон включил live конкурсы/модерацию/судью/результаты/публикации/разряд, категорию и SMTP Mailpit, четыре реестра/двухлетнюю XLSX, рейтинги/ручную сборную/файлы, role/logout races и axe/визуальные состояния. Шесть новых viewport/theme тестов прошли, созданы все 24 PNG. TypeScript/lint/production build и API/design проверки прошли отдельно.

## Разобранные сбои и ограничения доказательств

- Первый полный браузерный набор: 95 passed / 21 failed. Мобильная тема имела несовпадающее visible/accessibility имя; toast имел временно низкий контраст при opacity-анимации. Исправлены исходники, правила axe не ослаблялись.
- Устаревшие тесты ожидали текст закрытой страницы вместо уже реализованного перенаправления в кабинет; теперь проверяют redirect и отсутствие прежних данных. Один mock не описывал новый consent DTO — исправлен mock.
- Второй полный набор с двумя worker: 114 passed / 2 failed; живые login запросы упёрлись в throttle, повторный перевод организации создал несколько исторических строк. Перевод теперь выбирает другую организацию и следующую дату от текущего периода; проверки учитывают несколько записей. При повторе обнаружены ещё два старых ожидания закрытой страницы в live registry — обновлены на фактическую навигацию.
- Последовательный прогон на `99cc63d` прошёл live регистрацию/перевод/сопоставление XLSX, но обнаружил ещё одну гонку в тесте: после клика «Выйти» переход на аналитику прерывал незавершённый logout. Добавлено ожидание главной страницы до следующего перехода. Это исправление только теста; session/logout API не изменялся.
- Новый отдельный `mandatory-live.spec.ts` неоднократно прошёл: категория → решение → сохранённое уведомление → SMTP capture; IDOR отказ; read через клавиатуру; согласие withdrawal/renewal; профиль РУСАДА; реальный XLSX download.

## Файлы, приватность и визуальный осмотр

Новые backend тесты открывают ZIP/DOCX/XLSX, проверяют содержимое, latest publication, пустые результаты, formula injection и object scope. Образцы реальных защищённых API скачаны в `tmp/mandatory-documents/`: protocol PDF/DOCX, regulations DOCX, athlete XLSX, personal-protocol PDF. DOCX разобраны как OOXML, XLSX открыт openpyxl: 7 строк, имя фиктивного спортсмена, version=1. PDF содержат текст на кириллице, по одной странице; отрендерены и осмотрены: таблицы/заголовки/версия/предупреждение/подвал читаемы, выписка содержит одну строку, полный протокол — три. Временные образцы не входят в deliverable и не выдаются за официальные формы.

Скриншоты: `docs/design/screenshots/mandatory/` — dashboard/profile/history/qualifications × 1440/768/390 × light/dark. Осмотрены dashboard desktop light/mobile dark, profile mobile light, history tablet dark, qualifications desktop dark. Сохранены numbered sidebar, dotted navigation, document rail, orange accents, stamp borders, theme и mobile nav. На узких экранах широкая таблица имеет горизонтальную прокрутку. Bottom nav перекрывает фиксированную полосу viewport на full-page скриншоте; контент доступен прокруткой, поля/кнопки проверяются браузером. Полный ручной обход всех элементов каждой роли не подменяется axe.

## Незакрытые gates

- Первичные актуальные ЕВСК/формы/нормативы не верифицированы: web connector вернул 401 `token_revoked`. Непроверенные правила не дают подсказку. Для официального применения нужна сверка источника и версии, а не смена флага ради демонстрации.
- Production SMTP credentials отсутствуют, доставка в реальный внешний ящик не проверена. Mailpit подтверждает локальный SMTP, `sent` — принятие SMTP сервером; после аварии возможна at-least-once повторная доставка.
- Hosted CI на итоговый SHA не запускался; PR/push требуют отдельного явного разрешения согласно пользовательскому заданию.
- Тренер запрашивает связь по известному email; отдельного поиска спортсменов по имени в реестре и пользовательского экрана полного журнала связей эта ветка не добавляет. История переходов сохранена в AuditEvent. UI просмотра ledger исправлений квалификаций остаётся через API; форма исправления федерации реализована.
- В исходных демонстрационных опубликованных протоколах встречаются английские названия событий/уровней. Исторические snapshots не переписывались; служебная подпись формата переведена на русский. Новые события вводятся на русском.

Все восемь групп получили работающие дополнения и проверки, но общий статус — **partial** до закрытия перечисленных gates. D1–D12 не включены в оценку. Детали AC-01–AC-18 — в `docs/acceptance-matrix.md`.
