# Действующие API-контракты

Источник путей и полей — [сохранённая OpenAPI-схема](../openapi.yaml), `backend/config/urls.py`, `apps/*/{urls,views,serializers,services}.py` на `600562d`. Swagger: `/api/docs/`, schema: `/api/schema/`. Префикс ниже — `/api/v1/`. Схема `drf-spectacular` описывает успешные ответы и часть запросов; **роли и бизнес-ошибки уточнены по коду**, они не полностью перечислены в YAML. DTO на клиенте принадлежат руководителю: `frontend/src/lib/api.ts`.

Все POST/PATCH требуют CSRF token; защищённые операции дополнительно требуют session cookie. Публичные register/login создают сессию после CSRF-проверки. `GET` публичен только там, где написано «публично». Ошибки: DRF выдаёт 400 для serializer/domain validation (обычно словарь поля или `detail`), 403 при отказе роли/объекта, 404 для отсутствующего id; анонимный запрос к защищённому endpoint отклоняется. `api<T>()` преобразует неуспешный JSON в `Error`. Не полагайтесь на наличие единой error DTO.

## Служебные и учётная запись

| Метод и путь | Доступ | Запрос → успешный ответ; ограничения |
| --- | --- | --- |
| `GET health/` | публично | `{status:"ok"}`; проверяет только HTTP готовность API |
| `GET auth/csrf/` | публично | `{csrfToken:string}` и cookie |
| `POST auth/register/` | публично + CSRF | `email`, `password` (min 8 и Django validators), `full_name`, `date_of_birth`, `consent:true`, `consent_version:"v1-demo-2026-10-27"`; для minor также `guardian_name`, `guardian_relationship`, `guardian_consent:true` → 201 `{user:MeDTO}` и сессия; duplicate email/дата/согласие → 400 |
| `POST auth/login/` | публично + CSRF | `{email,password}` → `{user:MeDTO}` и сессия; неверные данные → 400; throttle `5/min` → 429 |
| `POST auth/logout/` | login + CSRF | пустое тело → 204 |
| `GET auth/me/` | login | `MeDTO` |
| `POST auth/active-role/` | login + CSRF | `{role:Role}` → `MeDTO`; не назначенная роль → 403, неизвестная → 400 |
| `GET auth/dashboard/` | назначенная активная роль | `{role,metrics:[{label,value}],guardian_status:string|null}`; отозванная/поддельная роль → 403; анонимный запрос отклоняется (тест допускает 401 или 403) |

`MeDTO = {id:number,email:string,full_name:string,roles:Role[],active_role:Role|null}`, где `Role = federation | athlete | coach | judge`. Guardian details в ответ не входят. Dashboard — сводка, а не универсальный API будущих модулей.

`RegisterSerializer.validate` принимает только точную текущую demo-версию `consent_version="v1-demo-2026-10-27"`; иной идентификатор даёт 400. Это ограничение исходника, а не произвольно выбранный пример.

## Справочники и шаблоны

| Метод и путь | Доступ | Запрос → ответ; ограничения |
| --- | --- | --- |
| `GET disciplines/` | публично | массив `{id,code,name}` только активных дисциплин |
| `GET age-groups/` | публично | массив `{id,name,min_age,max_age}` |
| `POST age-groups/` | federation | `{name,min_age,max_age}` → 201 тот же DTO; `min_age <= max_age` в модели, допустимость ввода проверяйте тестом |
| `GET calendar-entries/` | публично | массив `{id,source,entry_number,title,year,reference_url}` |
| `POST calendar-entries/` | federation | поля DTO без `id` → 201; `source=ekp|regional`, уникальны `(source,entry_number,year)` |
| `GET templates/?discipline=<code>` | публично | массив **всех версий** `ProtocolTemplate`, в том числе `source_verified=false`; фильтр по коду дисциплины необязателен, дополнительной фильтрации по верификации нет |
| `POST templates/` | federation | `discipline`, `name`, `competition_type?`, `rule_version?`, `effective_from?`, `metric_fields`, `columns`, `sections`, `signature_roles`, `sort`, `source_url?`, `source_note?` → 201 новая версия; `version` вычисляет сервер, `source_verified` read-only/false. Неверные колонки/поля/сортировка → 400 |

`ProtocolTemplate` дополнительно возвращает `id`, `discipline_code`, `version`, `source_verified`. `metric_fields` — список объектов `{key,label,type:"number"|"string",required:boolean}`; ключ уникален и является identifier. `columns` включает `athlete` и `status`, без повторов, а также все обязательные метрики. `sections` включает `header`,`participants`; допустимы также `judges`,`signatures`. `sort={key:<отображаемая колонка>,direction:"asc"|"desc"}`. Шаблоны демо не подтверждены официальным источником.

## Соревнования и заявки

| Метод и путь | Доступ | Запрос → ответ; ограничения |
| --- | --- | --- |
| `GET competitions/?discipline=<code>` | публично; активная federation видит drafts | массив `CompetitionDTO`; federation видит **все** drafts, остальные — только `published`/`closed` (при их отсутствии `[]`, не 403) |
| `POST competitions/` | federation | `CompetitionDTO` без read-only полей → 201 draft; требует `age_reference_date`, ≥1 `age_groups`, подходящий `template`, `registration_deadline < starts_at < ends_at`; hybrid требует `stages` |
| `GET competitions/{id}/` | публично для published/closed | `CompetitionDTO`; draft для не-federation → 403 |
| `PATCH competitions/{id}/` | federation | partial `CompetitionDTO` → обновлённый DTO; после первой заявки поля eligibility/шаблон/этапы заморожены, после первой публикации протокола заморожены все настройки |
| `POST competitions/{id}/publish/` | federation | пустое тело → `CompetitionDTO` со `state=published`; только draft и будущий deadline |
| `GET applications/?competition=<id>` | federation, athlete, coach, judge | массив `ApplicationDTO`, отфильтрованный по объектам роли; judge видит лишь approved назначенного события |
| `POST applications/` | athlete/coach | `{competition,athlete,age_group}` → 201 pending `ApplicationDTO`; роль athlete только за себя; coach — подтверждённая связь дисциплины; опубликованное соревнование, срок, возраст и согласие обязательны; уникальна пара competition+athlete |
| `POST applications/{id}/decision/` | federation | `{status:"approved"|"rejected",reason?}` → `ApplicationDTO`; только pending, для rejected нужна причина |
| `GET coach-links/` | coach/athlete | массив связей собственной роли; до подтверждения coach не получает `athlete`/имя |
| `POST coach-links/` | coach | `{athlete_email,discipline}` → 202 с нейтральным `detail`, даже если аккаунт не найден; повторную пару не создаёт |
| `POST coach-links/{id}/decision/` | собственный athlete | `{status:"confirmed"|"rejected"}` → `CoachLinkDTO`; только pending |

`CompetitionDTO`: `id,title,discipline,discipline_name,age_groups,age_group_details,level,competition_type,format,starts_at,ends_at,registration_deadline,age_reference_date,allow_ties,location,regulations,calendar_entry,template,state,stages,created_by,created_at,updated_at`. `format=online|in_person|hybrid`; stage содержит `order,name,format,starts_at,ends_at`. `ApplicationDTO`: `id,competition,athlete,athlete_name,age_group,submitted_by,status,decision_reason,decided_by,submitted_at,decided_at`; сервер владеет status и полями решения.

## Судейство, результаты, протокол и история

| Метод и путь | Доступ | Запрос → ответ; ограничения |
| --- | --- | --- |
| `GET judge-choices/` | federation | массив `{id,full_name}` пользователей с ролью judge |
| `GET judge-assignments/?competition=<id>` | federation/свой judge | массив `JudgeAssignmentDTO` |
| `POST judge-assignments/` | federation | `{competition,judge,role_label}` → 201 DTO; judge обязан иметь роль, пара уникальна |
| `GET results/?competition=<id>` | federation/назначенный judge | массив `ResultDTO`, judge ограничен своими соревнованиями |
| `POST results/` | federation/назначенный judge | `{application,status,place?,score?,metrics?}` → 201 новый или 200 при повторном POST для той же `application` (one-to-one `Result`); заявка approved и событие published, `classified` требует place или score и метрики шаблона; другие статусы без place/score/metrics. При исправлении сервер **сбрасывает отметку** `validated_by`, а все проверки ввода применяются заново |
| `POST results/{id}/validate/` | federation | пустое тело → `ResultDTO` с `validated_by`; повторная валидация → 400 |
| `GET competitions/{id}/protocol-preview/` | federation | `ProtocolSnapshot`, без сохранения публикации |
| `POST competitions/{id}/protocol-publish/` | federation | `{correction_reason?}` → 201 `ProtocolPublication`; pending заявки и невалидированные результаты блокируют публикацию; для версии >1 причина обязательна |
| `GET competitions/{id}/protocols/` | federation | массив опубликованных версий с `snapshot` |
| `GET competitions/{id}/protocols/{version}/download/?file_format=pdf|docx` | federation | бинарный attachment из snapshot; иной формат → 400, отсутствующая версия → 404 |
| `GET history/` | athlete | массив `{competition_id,competition_title,version,published_at,row}`; только собственная строка последней публикации каждого события |

`ResultDTO = {id,application,status,place,score,metrics,validated_by,updated_by,updated_at}`; `status=classified|no_show|unclassified|disqualified`. `ProtocolSnapshot` содержит `competition_id/title`, `discipline`, `template_id/version`, `source_verified/note/url`, `sections`, `signature_roles`, `sort`, `metadata`, `judges`, `columns:[{key,label}]`, `rows`. В каждой row есть `application_id`, `athlete_id`, `athlete`, `age_group`, `status`, `place`, `score` и метрики шаблона. Строка approved без результата получает `pending_result`, `place=null`, `score=null`. Публикация содержит `id,competition,version,template,snapshot,correction_reason,published_by,published_at`.

## Региональные команды

`GET /api/v1/teams/` и `GET /api/v1/teams/{id}/candidates/` доступны только с активной ролью федерации и возвращают `{count,next,previous,results}` по 50 записей; номер страницы задаётся параметром `page`. В `members` поле `organization_name` содержит текущее название организации либо `null`. Состав формируется только вручную; доступ к истории и скачиванию документов также проверяется на сервере. Полный контракт приведён в `docs/openapi.yaml`.

## Право менять контракт

`docs/openapi.yaml`, backend сериализаторы/routes, `frontend/src/lib/api.ts`, аутентификация и модели — общие интерфейсы. Независимый агент **не меняет** их по собственной инициативе. Он передаёт руководителю: проблему, текущий endpoint/DTO, предложенный diff полей/статусов, потребителей, миграцию/обратную совместимость, требования доступа и тесты. Руководитель утверждает контракт и назначает владельца реализации; после изменений регенерирует/сверяет OpenAPI и frontend DTO. До утверждения не публикуйте новый endpoint в документации как существующий.

## Реестр и исправления истории (частичная реализация)

Только активная назначенная роль федерации может читать `/api/v1/registry/options/`, реестры и историю, менять основные поля существующих людей, организацию или создавать, закрывать и исправлять периоды. `POST athletes/{id}/history/{kind}/{period_id}/correct/` принимает `expected`, полный `corrected` и непустой `reason`; устаревшая версия возвращает 409, недопустимые даты или пересечения — 400. Изменение записывается в аудит транзакционно; удаление периода API не предоставляет. PATCH профиля не создаёт роли и не меняет согласия или опекунов. Назначение ролей и регистрация продолжают использовать существующий механизм аккаунтов.

`GET analytics/participation/` и `GET analytics/participation/export/` возвращают заголовок `X-Report-Fingerprint`; тот же отпечаток записан на листе «Методика» XLSX. Семантика и ограничения описаны в [методике](../participation-methodology.md). Реестр и интерфейс ещё не закрывают все требования AC-11; ориентируйтесь на матрицу приёмки и полную схему OpenAPI.
