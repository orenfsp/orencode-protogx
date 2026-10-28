# Протокол проверки Д1–Д12 — 28.10.2026

Ветка: `feat/case-optional-d1-d12`, база `origin/main=45be07172ec7e1e641fe3433c3902b010fc793c1`. Первоначально рабочее дерево чистое. Двенадцать отдельных feature commits: Д10 `3522745`, Д12 `4a08cac`, Д11 `9acc27b`, Д9 `3106b66`, Д3 `05508ad`, Д4 `1158a3c`, Д7 `f3a1d38`, Д6 `d638686`, Д5 `4828702`, Д8 `16a8ddf`, Д2 `d80dc84`, Д1 `45a03bc`. Последующий integration/hardening commit содержит выполненные проверки и уточнения безопасности. Ничего не отправлялось и не сливалось в main/alpha.

## Выполненные проверки

| Проверка | Фактический результат и граница |
| --- | --- |
| Исходная main, `manage.py test` на SQLite до изменений | 85 tests, OK, 2 PostgreSQL concurrency tests skipped |
| Полный PostgreSQL regression с extensions до последней guardian-sharing модели | **114 tests, OK, без пропусков**, 268.439 s; отдельный контейнер/БД/порт, существующие данные проекта не использовались |
| Последний PostgreSQL rerun после добавления 115-го теста | **Не завершён**: создание тестовой БД прервалось `could not fsync … I/O error`; отдельно `migrate extensions.0014` прервался при восстановлении PostgreSQL. Это инфраструктурный blocker, не pass |
| Последний полный SQLite regression | **117 tests, OK, skipped=2**, 235.759 s; два пропуска — только PostgreSQL concurrency tests. Это не заменяет последний PostgreSQL gate |
| Дополнительные PostgreSQL targeted checks до I/O сбоя | 21 tests, OK: управление OIDC clients/secrets, PKCE/expiry/revoke/CSRF/key rotation, private training/attestation/review/certificate, ministry roster privacy, repeated seed и live HTTP webhook consumer |
| Последняя guardian-sharing механика на SQLite | В составе 115-test suite и отдельного OIDC-прогона проверен запрет minor external sharing при одном базовом Guardian consent, отдельное scope/client authorization и немедленный revoke |
| Первоначальный полный Chrome browser regression с PostgreSQL demo | **51 tests, 51 passed**, 2.5 min: существующие Phase 1/2, role/logout races, qualifications, ratings, team documents и шесть optional live tests |
| Обновлённые optional browser tests на изолированной SQLite demo | **6 tests, 6 passed**; реальная сеть/API/документы, без API response mocks в этом файле; повтор после последней стилевой синхронизации фиксируется тем же тестовым файлом |
| Финальный browser targeted run после hardening | **7 tests, 7 passed**, 12.1 s: шесть live workflows плюс отдельный mocked-response тест удаления ранее загруженных приватных данных после 403. Это отдельный прогон, не заявление о полном повторе 51 теста |
| Compose configuration | `docker compose -f docker-compose.yml -f docker-compose.optional.yml config --quiet` прошёл; это проверка конфигурации, не свежая сборка и запуск контейнеров |
| `manage.py migrate` на изолированной SQLite demo | Все миграции, включая extensions.0015 и DOT, применены; seed_optional прошёл; существующие fictional cases сохранились при аддитивном расширении |
| `manage.py seed_optional` повторно в тесте | Counts norms/attempts/rates/groups/memberships/client policies не меняются; прежние пароли не сбрасываются |
| `makemigrations --check --dry-run` | No changes detected на финальном source; попытка PostgreSQL consistency read во время сбоя отдельно не считается проверкой PG history |
| OpenAPI `spectacular --validate --fail-on-warn` | Финальная схема с отдельными scope/format enum names и integrationBearer extension генерируется без warnings/errors; сохранена в docs/openapi.yaml |
| `npm.cmd run typecheck`, `npm.cmd run lint` | passed; один промежуточный ESLint процесс получил sandbox memory allocation failure, повтор вне ограниченного процесса и последующие обычные прогоны прошли |
| `npm.cmd run build` | passed, compile + TypeScript + 30 generated static pages; новые страницы используют прежний AppShell/styles |
| `ruff check` | passed после targeted formatting новых modules/tests; mandatory business source не форматировался массово |
| `check_design_contract.py` | PASS: original reference и extracted globals.css неизменны |
| `sync_optional_styles.py --check` | PASS: OIDC stylesheet — точная упаковка существующих globals.css + app.css; самостоятельная тема удалена |
| Реальный SMTP | Из outbox отправлялись только fictional `.test` recipients в локальный Mailpit v1.20.3; sink показал сообщения, отдельная ограниченная отправка дала `Delivered in bounded batch: 1`. В реальную почту писем не отправляли |
| Webhook network | Автотест создал настоящий loopback HTTP consumer, проверил HMAC/timestamp и две доставки одного UUID с одним receipt. Другой тест проверил 503/retry/history через контролируемую transport replacement |

Команды для воспроизведения: [optional-demo.md](optional-demo.md). Текущие feature statuses: [traceability](case-optional-traceability.md). Выходы отдельных прогонов перечислены отдельно, они не объединяются в вымышленный «всё прошло на PostgreSQL после последнего изменения».

## Браузерная и визуальная граница

`frontend/tests/optional-live.spec.ts` включает:

1. Public newcomer + шесть captures при 1440/768/390 в light/dark. Capture ожидает фактическую загрузку карточки, а не только заголовок.
2. Athlete self-service PDF → гостевая QR verification без ФИО → appeal → настоящий multipart TXT evidence → защищённый download link → progression.
3. Federation real-data training/assessment/development/integrations/awards screens и подготовка award package.
4. Judge-generated panel document.
5. Ministry GET/year filter и отказ POST.
6. Реальный внешний demo RP: browser redirect → Django login → consent → code callback → JWT/JWKS/issuer/audience/nonce/expiry checks → userinfo → local-client logout + token revoke.

Контрольные captures сохраняются в `frontend/test-results/` и выбранные evidence copies — в `docs/design/screenshots/optional-*`. Исходный reference HTML не менялся. Новые формы используют `.workflow-form`, `.inp`, `.btn`, `.note`, `.blk`, `.tw` и прежние tokens. OIDC login/consent получают те же CSS байты, шрифты, numbered indigo sidebar, document rail, orange actions, dotted navigation и mobile navigation; theme toggle на Django странице не сохраняет тему между переходами. Полная попиксельная приёмка каждой новой формы во всех состояниях не заявляется.

Исправленные во время проверки дефекты: userinfo относительный URI мешал audience validation; no-referrer на auth form превращал Origin в null и блокировал Django CSRF; normalized hidden claims требовали привязки к отрисованной форме; attestation history должна оставаться видимой после закрытия membership; scope enum collisions и custom authenticator должны быть описаны в OpenAPI.

## Оставшиеся gates

- **AC-11 / PR #5:** текущая main ещё не содержит исторический registry. Д3 имеет самостоятельный групповой отчёт; его автоматическое включение/согласование с полной registry methodology не реализовано. Д6 и Д9 поэтому не имеют полного регионального participation report. Read adapters не считаются интеграционной проверкой.
- **Нормативы:** актуальные первичные ФССП/поправки, ЕВСК, Указ №93-ук и официальные формы документов не проверены. Пороги, премии и статусы назначения — демонстрационные; документ платформы не устанавливает право, выплату или разряд.
- **Финальный PostgreSQL gate:** требуется свободное место и работоспособный Docker/PostgreSQL, затем migrate и весь текущий 117-test regression. Host disk заполнился; PostgreSQL получил fsync/recovery errors, Docker Desktop API вернул 500. Graceful restart завершился timeout. Удалён только проверенный generated `.next/cache`; созданное для задачи `.venv` сжато NTFS. Никакие исходники, чужие проекты, основные БД/тома не очищались.
- **Deployment:** локальная совместимость OIDC/mock consumer проверена; production HTTPS, реальные RP, реальный SMTP, реальное министерство/партнёры и государственные системы не подключались. Compose override подготовлен; его полный свежий rebuild/run после изменения зависимостей не завершался в этом окружении и не считается отдельным pass.
- **Д5 санкции:** дополнительный 5-test targeted прогон на SQLite прошёл: отсутствие policy/порядка обжалования блокирует санкцию; дисквалификация сохраняет effective period и пересчитывает другие дисциплины; техническое поражение сохраняет базовые типы Result и effective date; закрытое дело не принимает новые доказательства. Юридическая допустимость конкретного реального решения по-прежнему не заявляется; policy должна соответствовать проверенному регламенту.
- **Масштабирование:** приватные списки demo-workspaces местами ограничены 100 строками или не имеют полноценной пагинации. Это эксплуатационное ограничение, не замена большого production registry UI.
