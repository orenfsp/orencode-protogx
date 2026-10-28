# Поставка обязательной части

Рабочая ветка: `codex/mandatory-case-completion`. Baseline: `ee60893d2278001aaa6b704943230c0bd2db6eeb`. Финальная программная ревизия: `223bebe28ac7fc1f5e4244f42d0e642b68fd3bdd`. После неё фиксируются только документация и свидетельства. Push, Draft PR и merge не выполнялись.

## Состав изменений

Основные новые модули (полный diff доступен от baseline до программной ревизии):

```text
backend/apps/
  accounts/profile.py                 # личный профиль и согласия
  competitions/coach_directory.py     # ограниченный поиск и журнал связи
  competitions/link_lifecycle.py      # приостановление/возобновление/завершение
  competitions/registration.py        # регистрация и положение
  competitions/reports.py             # личная выписка и отчёт выступлений
  competitions/types.py               # управляемые типы соревнований
  notifications/                     # модель inbox/outbox, SMTP, scheduler, worker
  qualifications/corrections.py       # журнал исправлений реквизитов
frontend/src/
  app/profile/page.tsx
  components/CoachAthleteSearch.tsx
  components/RecordHistory.tsx
  components/NotificationCenter.tsx
  components/FederationOperations.tsx
  components/ConsentPanel.tsx
  components/CoachLinkLifecycle.tsx
frontend/tests/
  mandatory-live.spec.ts
  mandatory-visual.spec.ts
  coach-history-live.spec.ts
docs/
  openapi.yaml
  case-mandatory-traceability.md
  acceptance-matrix.md
  mandatory-verification.md
  regulatory-source-review.md
  design/screenshots/mandatory/
  evidence/mandatory-2026-10-28/
```

Существующие ratings/registry/teams/competition services сохранены и дополнены проверками scope, актуальных отстранений, российских уровней, minor privacy и аудитом. Compose дополнен SMTP capture и worker, миграции добавочные. Исходные reference HTML/CSS не изменены. Чужие untracked audit/report/worktree файлы сохранены.

## Архитектура и данные

Django/DRF единолично проверяет назначенную активную роль, владельца объекта и согласия; Next.js использует прежний session/CSRF и общий `api()`. PostgreSQL хранит пользователей/роли, исторические периоды реестра, соревнования/заявки/судей/результаты, immutable publications, квалификационные решения/corrections, ratings/contributions и ручные сборные. Новые поля профиля и состояния связи дополняют существующие модели.

Domain audit в той же транзакции ставит минимальные уведомления в `Notification`; уникальный event key предотвращает дубли. Worker блокирует строки через `SKIP LOCKED`, повторно проверяет доступ и отправляет SMTP с retry/backoff. Отдельного брокера и второй системы авторизации нет. SMTP принятие и PostgreSQL не образуют одну транзакцию: после аварии возможна повторная доставка.

Файлы формируются из сохранённых исторических данных/версий. Личная выписка и XLSX подопечного имеют отдельный object scope; опубликованные snapshots не переписываются исправлением текущего профиля. Квалификационные реквизиты имеют ledger до/после, а юридический разряд остаётся решением федерации.

Контракты: [OpenAPI](openapi.yaml), [уведомления](notifications.md), [поиск и история](coach-links-and-history.md), [квалификации](qualifications.md), [рейтинг](ratings.md), [методика численности](participation-methodology.md).

## Проверка и демонстрация

Итоговые результаты и точные команды backend/browser/build/migrations находятся в [mandatory-verification.md](mandatory-verification.md), а восемь групп кейса и 18 отдельных AC — в [трассировке](case-mandatory-traceability.md) и [матрице](acceptance-matrix.md). D1–D12 не реализовывались в этой задаче и не включены в оценку.

На текущей машине web открыт на `http://127.0.0.1:13001`, Mailpit на `http://127.0.0.1:18025`. Фиктивные аккаунты: `demo.federation@example.test`, `demo.athlete@example.test`, `demo.coach@example.test`, `demo.judge@example.test`; локальный пароль для новых seed-аккаунтов `DemoOnly2026!`. Повторный seed сохраняет изменённые пароли. Полный безопасный запуск и дополнительные тестовые личности — [README](../README.md), [demo-scenarios](demo-scenarios.md).

Путь показа: федерация создаёт/публикует соревнование → спортсмен подаёт заявку → федерация одобряет и назначает судью → судья вводит результат → федерация проверяет/публикует протокол → спортсмен видит историю/личную выписку → заявка на разряд/решение → уведомление в кабинете/Mailpit → двухлетний XLSX → рейтинг → ручной состав сборной/проект приказа. Отдельно тренер ищет зарегистрированного вымышленного взрослого, запрашивает связь, спортсмен подтверждает; после приостановления оба видят журнал.

Для официальной эксплуатации остаются внешние проверки: действующие нормы/формы, реальная личность представителя, SMTP credentials/получение письма и hosted CI итогового SHA. Демо не объявляется нормативно утверждённой или опубликованной production системой.
