# Объединение локального проекта и D1–D12 — 28.10.2026

Ветка результата: `codex/integrate-optional-d1-d12`. Локальная исходная версия
`d506a98`, сохранённые незакоммиченные доработки `131c057`; удалённый источник
`origin/feat/case-optional-d1-d12` = `b3a2884`. Истории объединены обычным merge,
без переписывания исходных веток. Push не выполнялся.

## Выбор реализаций

- Сохранены локальные обязательные процессы, исторические реестры, отчёты,
  согласия, защита сессий и ролей, toast, навигация и доработки пагинации сборной.
- Добавлены extensions, OAuth Toolkit и страницы D1–D12 из удалённой ветки.
- Сохранён SMTP/Mailpit вместо отката к console email backend.
- Основной `/api/v1/notifications/` сохраняет прежний контракт. Дополнительная
  очередь использует `/api/v1/optional-notifications/`. Разведены сериализаторы
  OpenAPI и обратная связь User (`optional_notifications`, миграция extensions
  0016). Общие события не создают дублирующую дополнительную рассылку.
- Постоянный `process_notifications --loop` обслуживает обе очереди и
  напоминания дополнительных премий. Webhook CLI сохраняется отдельно.
- D6/D9 используют установленный локальный registry и исходную методику
  calendar-year-v1. Тесты проверяют два годовых ряда, права и отдельные inbox API.
- CSS страниц OIDC пересобран из текущих globals.css/app.css. Reference HTML
  и извлечённый globals.css сохранены без изменений.

Автоматическое слияние выявило 10 конфликтующих файлов. Дополнительно реальные
проверки выявили E304 моделей уведомлений и коллизию имён OpenAPI. Ошибки
исправлены; проверки повторены. DeepSeek MCP успешно использован для узкого
read-only review адаптера D9/registry; замечаний о форме данных не обнаружено.
Тесты выполнял интегратор.

## Исполненная проверка

- PostgreSQL: **172 tests, OK, 500.624 s**. Полный набор выполнен на объединённой
  реализации. После старта процесса переименован дополнительный сериализатор и
  добавлен no-store prefix; окончательная схема проверена отдельно.
- Ruff: `All checks passed!`; migration drift: `No changes detected`.
- `check_openapi_schema.py`: warning-free generation совпадает с docs/openapi.yaml.
- TypeScript и ESLint: exit 0.
- Docker production build: exit 0, Next.js 16.4.3, 33 маршрута.
- `check_design_contract.py`: PASS; `sync_optional_styles.py --check`: PASS.

- Основной Chrome: **120 passed, 6 optional skipped, 0 failed, 10.0 m**.
- Отдельный enabled optional-live: **6 passed, 0 skipped, 0 failed, 35.2 s**,
  включая OIDC callback/userinfo/revoke. Это отдельные прогоны.
- Целевые окончательные inbox/D6/D9: **4 passed, 7.241 s**.
- Первый optional-live: 4 passed / 1 failed / 1 not run. Выявлен None в
  active_role аудита наблюдателя. После исправления middleware и регрессии
  active_role=None: **3 backend passed, 2.336 s**, затем все 6 optional-live
  прошли. Полный 172-test backend и основной Chrome были до последнего
  исправления; оно проверено целевыми и live-тестами.

Журналы: [evidence](evidence/integration-2026-10-28/). Успешная интеграция
не означает полного закрытия кейса: последующий
[аудит ТЗ](tz-readiness-audit-2026-10-28.md) выявил функциональные и нормативные
пробелы.

## Воспроизведение

Используется существующий изолированный Compose `fspmandatory` с сохранением
volume. Порты: web 13001, API 18001, PostgreSQL 55433, Mailpit 18025. Локальные
ключи и конфигурация OIDC находятся только в игнорируемом tmp, секреты в Git
не добавлены. Дополнительные фиктивные данные добавлены `seed_optional`.

```powershell
$env:FSP_DB_PORT='55433'
$env:FSP_API_PORT='18001'
$env:FSP_WEB_PORT='13001'
$env:FSP_MAILPIT_PORT='18025'
$env:DEMO_SEED_ENABLED='1'
$env:DEMO_ENVIRONMENT='local'
$env:DJANGO_CSRF_TRUSTED_ORIGINS='http://127.0.0.1:13001,http://localhost:13001'
docker compose -p fspmandatory up -d --build --wait
docker compose -p fspmandatory exec -T api python manage.py seed_optional
docker compose -p fspmandatory exec -T api python manage.py test --noinput
```

Для опционального OIDC используется override по образцу
`docker-compose.optional.yml`: issuer `http://127.0.0.1:18001`, public URL
`http://127.0.0.1:13001`, ключ read-only. Точный локальный override сохранён как
`tmp/integration.compose.yml`; после подготовки tmp:

```powershell
docker compose -p fspmandatory -f docker-compose.yml -f tmp/integration.compose.yml up -d --wait
```

Из frontend: `FSP_WEB_URL=http://127.0.0.1:13001`,
`FSP_MAILPIT_URL=http://127.0.0.1:18025`, `FSP_E2E_COMPOSE_PROJECT=fspmandatory`;
`npm.cmd run test:e2e -- --workers=1`. Для полного XLSX сценария нужен openpyxl.
Для optional-live дополнительно `FSP_OPTIONAL_LIVE=1`,
`FSP_OIDC_ISSUER=http://127.0.0.1:18001` и запущенный `scripts/demo_oidc_client.py`
на порту 9012. Фиктивные учётные записи — в docs/optional-demo.md.

## Границы

Нормативная актуальность правил, официальность документов, реальные внешние
интеграции/SMTP и hosted CI не подтверждаются локальными тестами. Сохраняются
демонстрационные обозначения норм, премий и документов и эксплуатационные
ограничения optional workspaces из исходного отчёта. Исходные audit файлы,
архив и чужие worktrees сохранены вне merge commit. Автогенерируемый локальный
next-env.d.ts также не включён в commit.
