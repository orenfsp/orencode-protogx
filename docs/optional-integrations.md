# Контракт Д1/Д2

Все примеры вымышленные. JSON-схемы запросов и session/bearer security schemes опубликованы в [OpenAPI](openapi.yaml). Реальные партнёры не подключались.

## Д2: токены и ресурсы

Федерация выдаёт `POST /api/v1/integrations/`:

```json
{"name":"Вымышленная платформа","scopes":["events:read","results:import","webhooks:receive"],"competitions":[1],"expires_at":"2026-11-01T12:00:00+05:00","webhook_url":"https://consumer.example.test/webhook"}
```

Замените ID/срок на свои локальные demo записи. Ответ один раз содержит `token` и при наличии webhook — `webhook_secret`; в БД хранится SHA-256 token и зашифрованный Fernet signing secret. `INTEGRATION_ENCRYPTION_KEY` задаётся вне исходников. Список клиентов и аудит секреты не возвращают. POST `integrations/{id}/revoke/` немедленно запрещает bearer-запросы. Проверяются expiry, scopes, event grants, активность владельца и назначенная ему федерация.

| Scope | Доступ |
| --- | --- |
| events:read | GET `external/events/`, только разрешённые недрафтовые события |
| results:import | POST `external/results/`, только одобренные заявки разрешённого опубликованного события |
| webhooks:receive | подписанные события в outbox; не даёт входящего доступа к результатам |

Это отдельный opaque bearer для внешней системы. Он не используется как браузерная сессия или FSP ID token и не открывает обычные federation routes.

## Импорт результатов

Федерация сначала создаёт точное сопоставление `POST integrations/identities/`:

```json
{"client":1,"external_id":"fictional-athlete-1","athlete":2}
```

Автоматического поиска по ФИО/email нет. Далее внешний клиент с `Authorization: Bearer <local-demo-token>` вызывает POST `external/results/`:

```json
{"competition":1,"idempotency_key":"fictional-results-v1","rows":[{"external_athlete_id":"fictional-athlete-1","application_id":3,"status":"classified","place":2,"score":"90.000","metrics":{"solved_tasks":2}}]}
```

Числовые ID берутся из своей demo БД. Metrics должны соответствовать шаблону дисциплины; статусы/места/score проходят существующую проверку. Не более 500 строк. Повтор client/key с тем же содержимым возвращает прежний пакет; изменённое содержимое — HTTP 409. Несовпадение athlete/application/event, неизвестная identity, дубли участника и недопустимые metrics отклоняются.

Пакет создаётся `staged` без записи в официальный протокол. Федерация POST `integrations/imports/{id}/decision/` с `{ "action":"accept", "reason":"Сопоставление и данные проверены" }`. Принятый ввод **снимает** прежнюю validation: последующие `results/{id}/validate/` и `competitions/{id}/protocol-publish/` остаются обязательными. Перед overwrite сравнивается сохранённый исходный snapshot, строки блокируются. `reject` не меняет результаты. `rollback` восстанавливает исходные данные только до последующей проверки/изменения; после этого применяется обычная коррекция с новой версией протокола. В истории и рейтинге до публикации остаётся прежняя официальная версия.

## Вебхуки

События: `competition.published`, `application.decided` только для approved, `protocol.published`. Payload содержит audit event ID, competition ID, resource type/ID; персональные данные отсутствуют. Outbox создаётся в транзакции исходного события. Для одной пары client/event — одна delivery.

```json
{"event":"protocol.published","event_id":123,"competition_id":1,"resource_type":"protocolpublication","resource_id":4}
```

Заголовки: `X-FSP-Delivery` — стабильный UUID; `X-FSP-Timestamp` — timestamp конкретной попытки; `X-FSP-Signature: sha256=<hex>`. Подпись — HMAC-SHA256 от точных байтов `timestamp + '.' + delivery_uuid + '.' + body`. Consumer обязан проверить constant-time подпись, допустимое время (demo ±300 s), затем дедуплицировать UUID до побочного эффекта. Пример: [demo_integration_consumer.py](../scripts/demo_integration_consumer.py). Секрет берётся из `FSP_DEMO_WEBHOOK_SECRET`, в логах не печатается; receipts хранятся локально в игнорируемом `tmp/`.

`deliver_webhooks` делает максимум пять попыток с задержкой `30 * 2^attempt` секунд; 2xx — успех, остальные статусы — ошибка. ID сохраняется между попытками; timeout 5 s, redirect/proxy env не используются, ответ читается ограниченно. История попыток содержит исход/status code, без секретов и response body. Доставка at least once, consumer обеспечивает дедупликацию.

`FSP_WEBHOOK_HOSTS` — обязательный явный allowlist хостов. Разрешается HTTPS; private/link-local/multicast адреса запрещены. DNS проверяется перед доставкой, соединение закрепляется за проверенным IP, TLS проверяет первоначальный hostname. Только в явно настроенном DEBUG demo допускается loopback HTTP (`FSP_WEBHOOK_ALLOW_LOOPBACK=1`) для клиента на 127.0.0.1:9011. Разрешение hostname само по себе не разрешает внутренний IP в production.

## Д1: OIDC

`django-oauth-toolkit==3.4.1` обслуживает `/o/authorize/`, `/o/token/`, `/o/userinfo/`, `/o/revoke_token/`, `/o/logout/`, discovery `/o/.well-known/openid-configuration` и JWKS `/o/.well-known/jwks.json`. Issuer задаётся явно. Включён только code flow с S256 PKCE; implicit/password/refresh выдача отключена, code живёт 60 s, access/ID token — 300 s. Access tokens хранятся hashed/redacted at rest; ID token подписан RS256, userinfo проверяет audience и действующее согласие. Admin client secret хешируется библиотекой.

Администрирование: POST `fsp-id/clients/`, PUT `fsp-id/clients/{id}/`, POST `.../rotate-secret/`, POST `.../disable/`. Только активная федерация. Exact HTTPS redirect URI без wildcard/fragment/userinfo; local HTTP только в DEBUG. DOT self-service registration, DCR и device routes не опубликованы.

| Scope | Claims / источник |
| --- | --- |
| openid | стабильный псевдонимный public sub (как объявлено в discovery), без email/DOB |
| profile | full_name существующего User |
| fsp_roles | текущие назначения UserRole |
| fsp_disciplines | дисциплины заявок, подтверждённых тренерских связей и действующих зачислений |
| fsp_rank | последние действующие записи SportRankHistory по дисциплине |

Форма согласия привязывается к валидированным hidden fields исходного запроса и user session, действует 10 min. Проверяются state, nonce, PKCE и scopes; изменённая форма отклоняется. Согласие пользователя хранится отдельно от общего согласия на обработку. Для minor обязательны существующий verified Guardian и дополнительный scope/client-specific `OIDCGuardianAuthorization`, подтверждённый федерацией с версией текста и приватным evidence URL. API `fsp-id/guardian-authorizations/` и `.../{id}/revoke/` ограничен федерацией. Отзыв любого необходимого согласия запрещает дальнейший userinfo; endpoint отзыва также удаляет коды/токены.

Фиктивный relying party [demo_oidc_client.py](../scripts/demo_oidc_client.py) выполняет **реальный** browser redirect/login/consent/callback, проверяет JWKS/RS256, issuer, audience, nonce, exp/iat и совпадение sub в ID token/userinfo. State/verifier/tokens находятся в ограниченной по времени серверной памяти; секреты не выводятся в HTML. Logout тестового клиента — POST с CSRF и server-side revoke, затем удаление его сессии. Это проверенная локальная совместимость с данным клиентом, без заявления о подключении реальной сторонней системы.
