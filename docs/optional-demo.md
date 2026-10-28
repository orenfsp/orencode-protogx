# Дополнительные сценарии: запуск и демонстрация

Д1–Д12 находятся в объединённой ветке `codex/integrate-optional-d1-d12`,
runtime `0c43b00`. В исходном кейсе они **необязательны**; полное завершение
всех двенадцати не заявляется. Общий исторический реестр уже включён,
Д6/Д9 читают его данные. Оставшийся пробел Д3: зачисление в группу не меняет
общий отчёт. Д4/Д7/Д8 используют вымышленные правила, Д12 partial по форме.
[Текущая трассировка](case-optional-traceability.md),
[аудит](tz-readiness-audit-2026-10-28.md),
[проверка объединения](integration-verification.md).

Основной inbox — `/api/v1/notifications/`, дополнительный —
`/api/v1/optional-notifications/`. Оба outbox и optional-напоминания
обслуживает существующий notification worker.

## Архитектура и данные

`backend/apps/extensions/` расширяет существующие `accounts.User`, `UserRole`, `Guardian`, `PersonalDataConsent`, `catalogs.Organization`, `CoachAthleteLink`, `AuditEvent`, `ProtocolPublication`, квалификации, рейтинги и сборную. Второй базы идентичностей и альтернативных браузерных прав нет. Обычные API используют существующую session/CSRF-защиту и проверяют активную назначенную роль. Читатель министерства — тот же User с Django permission `extensions.view_ministry_dashboard`, без роли на запись.

Модели сгруппированы по назначению:

| Домен | Основные модели | Инвариант |
| --- | --- | --- |
| Уведомления | Notification | уникальная пара получатель/событие; SMTP outbox с ограничением повторов |
| Д10/Д12 | ParticipationCertificate, JudgingDocument | снимок опубликованного результата либо назначений; защищённые документы |
| Д3 | TrainingOrganization/Group/Membership/Session, Attendance | существующие организации и пользователи; даты включительны; один открытый период на спортсмена/дисциплину |
| Д4 | AssessmentNorm/Attempt, Attestation | новая версия вместо изменения использованного порога; объяснение и исходная попытка сохраняются |
| Д7/Д8 | ProgressionRule, AwardScheme/Rate/Petition | демонстрационные, версионные правила; расчёт не присваивает право или разряд |
| Д5 | ReviewPolicy/Case/Evidence/History | state machine с ревизией; доказательства приватны; старый протокол не изменяется |
| Д6 | IndicatorEvidence | документ связан с показателем/годом; источник каждого числа указан |
| Д2 | IntegrationClient/Identity, ResultImport, WebhookDelivery/Attempt | scoped token только на разрешённые события; импорт сначала staged; webhook ID стабилен при повторах |
| Д1 | DOT Application/Grant/AccessToken, OIDCClientPolicy/SharingConsent/GuardianAuthorization | библиотечный code/PKCE S256, отдельное согласие, минимум claims; несовершеннолетнему требуется отдельное подтверждённое разрешение представителя |

Аддитивные миграции extensions `0001`–`0016` и миграции `django-oauth-toolkit`
применяются обычным `manage.py migrate`. Миграция 0016 разводит обратную связь
дополнительного inbox (`optional_notifications`) с основным. Существующие
таблицы идентичностей, согласий, результатов и протоколов не переписываются.

## Быстрый локальный запуск

Из корня репозитория, PowerShell. Используйте существующее локальное окружение или создайте отдельное; не перезаписывайте `.env` с рабочими данными.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe scripts/prepare_optional_demo.py
Get-Content tmp/optional-demo.env | ForEach-Object {
  $taskSetting = $_ -split '=', 2
  Set-Item -Path ('Env:' + $taskSetting[0]) -Value $taskSetting[1]
}
```

Подготовка создаёт **только локальные игнорируемые** `tmp/fsp-id-demo.pem` и `tmp/optional-demo.env`, сохраняет существующие файлы и не печатает секреты. Для PostgreSQL задайте `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` на свою **изолированную локальную** БД. В проверке использовались контейнер `fsp-optional-postgres`, порт 55432, БД/пользователь `fsp_optional`; это не основная БД проекта.

```powershell
Set-Location backend
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py seed_optional
..\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --noreload
```

На Windows при отсутствии DejaVu Sans можно задать `PROTOCOL_PDF_FONT=C:/Windows/Fonts/arial.ttf`. Контейнер уже устанавливает DejaVu. Во втором терминале из `frontend/`: `npm.cmd ci`, `npm.cmd run build`, `npm.cmd run start`. Сайт — `http://127.0.0.1:3000/services`. Dev server также поддерживается. Существующий Next.js proxy `/api/` сохраняется; OIDC redirect/login/consent обрабатывает Django на порту 8000.

`seed_optional` вызывает исходный `seed_demo` с прежними ограничениями local/debug/opt-in. Он добавляет фиктивную школу, четыре этапа групп, историческое зачисление, вымышленный норматив печати и попытку, демонстрационные справочники пути/премий, наблюдателя министерства и public OIDC client. Повторный seed проверен тестом: история и справочники не дублируются, пароли не сбрасываются. Выпуск справок, решений и пакетов выполняется через реальные UI/API, а не заранее подставленными документами.

## Docker Compose

Основной `docker-compose.yml` работает независимо от внешних сервисов и OIDC-ключей. После подготовки `tmp/` можно включить локальный OIDC ключ:

```powershell
docker compose -f docker-compose.yml -f docker-compose.optional.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.optional.yml exec -T api python manage.py seed_optional
```

Override монтирует ключ read-only и использует внешние порты 8000/3000. При иных портах настройте issuer/public URL согласованно. Не запускайте новый Compose на портах работающего экземпляра; задайте отдельный project name/порты, как в README. Два фиктивных внешних клиента ниже запускаются локальным Python; их не следует помещать в контейнер с неизменённым loopback issuer.

## Фиктивные учётные записи

Пароль только для этих локальных записей: `DemoOnly2026!`. При повторном seed существующий пароль сохраняется.

| Email | Доступ |
| --- | --- |
| demo.federation@example.test | выбрать активную «Федерация» |
| demo.athlete@example.test | собственные справки, апелляции, история и путь |
| demo.coach@example.test | подтверждённые подопечные и своя группа |
| demo.judge@example.test | назначенные соревнования и собственные документы |
| demo.ministry@example.test | право чтения `/ministry`; роли на запись отсутствуют |

## Воспроизводимые сценарии

| Сценарий | Действия и проверяемый результат |
| --- | --- |
| Д10 | Спортсмен → «Справки» → выбрать участие → сформировать → скачать PDF → открыть QR/«Проверить» в гостевом окне. ФИО скрыто по умолчанию; ФИО несовершеннолетнего публично не раскрывается. Отзыв или новая версия протокола меняет результат проверки. |
| Д12 | Судья → «Документы о судействе» → состав коллегии/собственный отчёт → PDF; DOCX доступен через `?file_format=docx`. Источник — назначения; для отчёта исключаются будущие и draft события. Формы демонстрационные, фактическая работа и официальная форма требуют подтверждения. |
| Д11 | Гость → «Начать заниматься»: шесть дисциплин, опубликованная фиктивная школа, будущие опубликованные события, ссылки на регламент/регистрацию. Непубличные карточки исключены. |
| Д9 | Наблюдатель → `/ministry` → год → календарь и опубликованные составы. POST и доменные операции записи запрещены. Email/дата рождения не раскрываются, ФИО несовершеннолетних скрыты. Полный отчёт AC-11 пока недоступен. |
| Д3 | Федерация создаёт карточку/группу; тренер с подтверждённой связью зачисляет спортсмена, записывает занятие/присутствие. Перевод закрывает старый период предыдущим днём. Спортсмен не получает чужую посещаемость или лог занятия. |
| Д4 | Тренер → измерение выбранной версии → значение/дата/подтверждение → объяснение сравнения. Предварительная аттестация показывает отсутствующие/непройденные требования; подтверждение переводит в следующий этап. История видна после перевода. Всё вычисление по sample rules обозначено демонстрацией. |
| Д7 | `/progression` показывает действующий и потенциальный следующий разряд, недостающие результаты и будущие события по возрасту/уровню; только спортсмен/связанный по дисциплине тренер/федерация. `/glossary` открыт всем. |
| Д6 | Федерация → диапазон минимум двух лет → групповые числа/организации/проведённые события → источник → подтверждающий документ → XLSX с методикой/fingerprint. Число групп не выдаётся за полный региональный реестр. |
| Д5 | Спортсмен подаёт апелляцию, прикладывает PNG/JPEG/TXT или ссылку. Назначенный рецензент/федерация начинают рассмотрение, запрашивают материалы, пишут обоснованное решение. Федерация может передать исправление в API либо сначала проверить его существующим редактором результатов и при удовлетворении опубликовать новую версию. Старый snapshot сохраняется, рейтинг пересчитывается. Санкции разрешены только явно внесённой ReviewPolicy с источником. |
| Д8 | Федерация → автоматически вычисленные кандидаты/суммы из последних годовых протоколов → проверить → подготовить пакет → DOCX/PDF → статусы prepared/sent/awarded (все демонстрационные). Изменённое основание блокирует следующий статус до подготовки нового пакета. |
| Д2 | См. [контракт интеграций](optional-integrations.md): выдать token/scopes/event/expiry, сопоставить external athlete ID, загрузить пакет, рассмотреть. Принятые результаты требуют обычной валидации и публикации. Подписанные доставки видны в UI. |
| Д1 | Запустить `python scripts/demo_oidc_client.py` из окружения проекта. Открыть `http://127.0.0.1:9012`, нажать «Войти через ФСП ID», войти, разрешить scopes, увидеть userinfo, выйти из тестового клиента. Клиент проверяет подпись/JWKS, issuer/audience/nonce/expiry и соответствие sub; выход отзывает token и локальную сессию клиента. Сессия федерации управляется отдельно. |

## Операционные команды

```powershell
python manage.py run_optional_deadlines
python manage.py deliver_notifications --limit 1
python manage.py deliver_webhooks --limit 10
```

В объединённом Compose `process_notifications --loop` автоматически обрабатывает
основную и дополнительную очереди, а также вызывает optional deadline job.
Команды выше пригодны для отдельных циклов. Webhook по-прежнему доставляется
отдельной `deliver_webhooks`; его consumer нужно запустить. Deadline job создаёт
дедуплицированные напоминания за 30 дней до настроенного срока ходатайства.
По умолчанию backend использует SMTP, Compose направляет его в Mailpit.
Настраиваются `EMAIL_HOST`, `EMAIL_PORT`, при необходимости user/password/TLS/SSL.
Реальная SMTP-передача проверена локально с вымышленными `.test` адресами;
получение production-ящиком не проверялось. При сбое после SMTP-приёма возможен
повтор: доставка at least once, а не exactly once.

Для production ключ подписи и Fernet key задаются вне исходников. OIDC использует HTTPS issuer; HTTP разрешён только loopback в DEBUG. Ротация: новый RSA PEM как активный, прежний PEM через `FSP_OIDC_INACTIVE_KEY_FILES` на период жизни старых токенов/JWKS-кэша, затем перезапуск сервиса; JWKS не выдаёт приватные параметры. Смена client secret и redirect/scope policy отзывает прежние токены/согласия. У несовершеннолетних базовое согласие Guardian **не** разрешает внешнее раскрытие: нужен отдельный OIDCGuardianAuthorization с scopes, версией текста и подтверждением; последующее согласие пользователя также обязательно. Юридическая достаточность документов здесь не заявляется.

## Проверки

Backend: `python manage.py test`; отдельная функция: `python manage.py test tests.test_optional_oidc` и соответствующий модуль из трассировки. PostgreSQL обязателен для проверки блокировок/конкурентных операций; SQLite — дополнительная быстрая проверка. `python manage.py makemigrations --check --dry-run`, `ruff check .`, `python manage.py spectacular --validate --fail-on-warn --file ../docs/openapi.yaml`. Из корня: `python scripts/check_design_contract.py`, `python scripts/check_openapi_schema.py`.

Frontend: `npm.cmd run typecheck`, `npm.cmd run lint`, `npm.cmd run build`. При работающих API, Next.js и фиктивном OIDC клиенте: `$env:FSP_OPTIONAL_LIVE='1'; npm.cmd run test:e2e -- --workers=1`. Без флага только шесть специальных live tests пропускаются, что не считается их прохождением. Команды, результаты и ограничения конкретного прогона фиксируются в [verification](optional-verification.md). `python scripts/sync_optional_styles.py --check` сверяет упакованный OIDC CSS с существующими стилями Next.js.

### Изолированный SQLite fallback только для локального демо

Если локальный Docker недоступен, после загрузки `tmp/optional-demo.env` задайте `DATABASE_ENGINE=sqlite` и **новый** абсолютный `SQLITE_PATH`, например `<repo>/tmp/optional-demo.sqlite3`. Затем выполните migrate/seed_optional/runserver. Это не меняет основной `.env`, прежнюю SQLite БД или PostgreSQL. Так восстановлена последняя локальная демонстрация после host I/O сбоя. Production и проверка PostgreSQL concurrency продолжают требовать PostgreSQL.
