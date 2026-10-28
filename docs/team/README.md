# Документация команды FSP OrenKod 2026

Текущая ветка `codex/integrate-optional-d1-d12`, runtime-код `0c43b00`.
Обязательные процессы и Д1–Д12 находятся в одном проекте. Полная готовность
по ТЗ не заявляется; статусы берутся из аудита, а не из числа passed-тестов.

## Начать здесь

1. [README проекта](../../README.md) — запуск, маршруты, ограничения.
2. [CURRENT_STATUS.md](CURRENT_STATUS.md) — текущее состояние и границы задачи.
3. [Памятка перед защитой](../defense-criteria-guide-2026-10-28.md) — все 29 пунктов оценки.
4. [Аудит ТЗ](../tz-readiness-audit-2026-10-28.md), [матрица AC](../acceptance-matrix.md)
   и [Д1–Д12](../case-optional-traceability.md) — что работает и что partial.
5. [QUICK_START.md](QUICK_START.md), [TESTING.md](TESTING.md) —
   команды и фактически выполненные проверки.

## Разработка и владение

Все агенты следуют [AI_AGENT_RULES.md](AI_AGENT_RULES.md) и работают по
[контракту задачи](TASK_TEMPLATE.md). Интегратор единолично принимает изменения
общих интерфейсов, моделей, разрешений и дизайна. Текущее пользовательское
назначение — обновление документации; оно не запускает новую разработку.

[ARCHITECTURE.md](ARCHITECTURE.md), [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md),
[GIT_WORKFLOW.md](GIT_WORKFLOW.md), [TEAM_ROLES.md](TEAM_ROLES.md),
[TASK_ASSIGNMENT.md](TASK_ASSIGNMENT.md) и [AGENT_BOOTSTRAP_PROMPT.md](AGENT_BOOTSTRAP_PROMPT.md)
объясняют структуру и порядок работы. Старые списки реализованных модулей
в этих руководствах сверяются с CURRENT_STATUS, OpenAPI и кодом.

## Предметные руководства

- [BACKEND_GUIDE.md](BACKEND_GUIDE.md), [DATABASE.md](DATABASE.md).
- [FRONTEND_GUIDE.md](FRONTEND_GUIDE.md), [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md).
- [API_CONTRACTS.md](API_CONTRACTS.md), [AUTH_AND_PERMISSIONS.md](AUTH_AND_PERMISSIONS.md).
- [ENVIRONMENT.md](ENVIRONMENT.md), [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
- [INTEGRATION_CHECKLIST.md](INTEGRATION_CHECKLIST.md), [CI](../CI.md).
- [Методика численности](../participation-methodology.md),
  [уведомления](../notifications.md), [внешние API/OIDC](../optional-integrations.md).

Источники требований: [MASTER_PROMPT](../MASTER_PROMPT.md), исходный кейс и
критерии оценки, описанные в аудите/памятке. Эталонный
[HTML](../design/fsp-reference.html) не изменяется;
[visual QA](../design/visual-qa.md) содержит фактические границы осмотра.

## Исторические отчёты

[Объединение 0c43b00](../integration-verification.md),
[обязательная часть 223bebe](../mandatory-verification.md),
[optional до merge](../optional-verification.md),
[Phase 1](../phase1-baseline.md), [Phase 2](../phase2-architecture.md).
Старые назначения и test counts относятся к указанным ревизиям.
