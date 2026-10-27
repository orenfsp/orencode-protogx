# Сессии, CSRF и разрешения

`backend/config/settings.py` задаёт DRF `SessionAuthentication` и глобальное `IsAuthenticated`. Публичные views явно ставят `AllowAny`: health, csrf, register/login, список дисциплин, GET возрастных групп/календарных записей/шаблонов, GET опубликованных соревнований. Для unsafe browser-запроса `frontend/src/lib/api.ts` сначала получает CSRF token и отправляет его в `X-CSRFToken`; register/login/logout/active-role дополнительно обёрнуты `csrf_protect`. Cookies: session `HttpOnly`, `SameSite=Lax`; CSRF `SameSite=Lax`. Допустимые origins берутся из `DJANGO_CSRF_TRUSTED_ORIGINS`.

`UserRole` хранит **назначенные** роли `federation`, `athlete`, `coach`, `judge`. `active_role` — строка в серверной сессии. `POST auth/active-role/` принимает только одно из этих значений и проверяет назначение; `require_role()` каждый раз проверяет обе стороны. Даже для multi-role пользователя операция федерации требует активной `federation`. Регистрация выдаёт только `athlete`; переключение не создаёт роль. `DashboardView` отдельно перепроверяет роль перед счётчиками. Внешний AI не меняет эту модель без руководителя.

## Объектные границы Phase 2

| Данные/операция | Доступ по коду |
| --- | --- |
| Публичные соревнования | список/деталь `published` и `closed`; draft видит federation |
| Заявки | federation — все; athlete — свои; coach — связанные подтверждённой связью нужной дисциплины; judge — approved в назначенных соревнованиях |
| Подача заявки | athlete только за себя; coach за athlete при `confirmed` link соответствующей дисциплины; сервер проверяет срок, возраст и согласие |
| Модерация, template, публикация, протокол, download | активная federation |
| Judge assignment | федерация назначает пользователя с ролью judge; судья читает свои назначения |
| Результаты | federation либо назначенный judge; валидация — federation |
| История | только активный athlete и только его строка последней версии |
| Coach link | coach запрашивает по email без раскрытия наличия учётной записи; athlete подтверждает/отклоняет собственный link; до подтверждения coach не видит athlete id/name |

Для несовершеннолетнего запись `Guardian` при регистрации начинается со статуса `pending_verification`. Заявка и публикация протокола требуют `confirmation_status="verified"`; автоматической юридической проверки нет. `PersonalDataConsent` требуется при подаче заявки и повторно проверяется перед публикацией. Протокол и PDF/DOCX приватны; не создавайте публичные URL к файлам по догадке. `AuditEvent` хранит часть material actions, но не заменяет проверки доступа.

Типичные ответы: 401/403 для неавторизованного/недостаточной роли, 404 для отсутствующего объекта, 400 для DRF/domain validation. Фактический статус анонимной session-auth просьбы может зависеть от DRF и view; тестируйте код ответа конкретного endpoint. Тесты границ: `backend/tests/test_auth.py`, `test_dashboard.py`, `test_competitions.py`. В UI условный показ формы улучшает опыт, но не является защитой.
