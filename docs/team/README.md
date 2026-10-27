# Работа команды над FSP OrenKod 2026

Этот раздел — входная точка для пяти разработчиков и их независимых AI-ассистентов. Состояние зафиксировано по коду на `600562d` (2026-10-27). Перед новой задачей сверяйте документы с текущей веткой: код и исполняемые тесты определяют реализованное поведение, [Master Prompt](../MASTER_PROMPT.md) — цель, [матрица приёмки](../acceptance-matrix.md) — достигнутые критерии.

**Сейчас идёт документационный спринт. Phase 3 не начата.** Задачи на новые функции выдаются отдельно после решения руководителя.

## С чего начать

1. [QUICK_START.md](QUICK_START.md) — запуск без очистки существующих данных.
2. [CURRENT_STATUS.md](CURRENT_STATUS.md) — что реально работает.
3. [ARCHITECTURE.md](ARCHITECTURE.md), [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) — слои и владельцы правил.
4. [GIT_WORKFLOW.md](GIT_WORKFLOW.md), [TEAM_ROLES.md](TEAM_ROLES.md), [TASK_ASSIGNMENT.md](TASK_ASSIGNMENT.md) — пять параллельных участников.
5. Для AI: [AI_AGENT_RULES.md](AI_AGENT_RULES.md), [AGENT_BOOTSTRAP_PROMPT.md](AGENT_BOOTSTRAP_PROMPT.md), [TASK_TEMPLATE.md](TASK_TEMPLATE.md).

## Справочники по работе

| Область | Документ |
| --- | --- |
| Django, правила домена | [BACKEND_GUIDE.md](BACKEND_GUIDE.md) |
| Next.js, страницы и компоненты | [FRONTEND_GUIDE.md](FRONTEND_GUIDE.md) |
| Модели и миграции | [DATABASE.md](DATABASE.md) |
| Существующие HTTP-контракты | [API_CONTRACTS.md](API_CONTRACTS.md) |
| Сессия, CSRF, роли и объекты | [AUTH_AND_PERMISSIONS.md](AUTH_AND_PERMISSIONS.md) |
| Обязательный визуальный контракт | [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md) |
| Переменные и Compose | [ENVIRONMENT.md](ENVIRONMENT.md) |
| Проверки | [TESTING.md](TESTING.md) |
| Частые сбои | [TROUBLESHOOTING.md](TROUBLESHOOTING.md) |
| Приёмка чужой ветки | [INTEGRATION_CHECKLIST.md](INTEGRATION_CHECKLIST.md) |

Нормативный визуальный источник — [неизменяемый HTML](../design/fsp-reference.html); [результаты визуальной проверки](../design/visual-qa.md) объясняют текущие отличия. [Phase 1](../phase1-baseline.md) и [Phase 2](../phase2-architecture.md) содержат историческую проверку этапов. Никакая документация команды не разрешает самостоятельно менять общие модели, API, авторизацию или токены оформления.
