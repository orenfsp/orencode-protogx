# Стандартный контракт задачи

Заполняет руководитель **до** передачи человеку или его AI. Указанный allowlist важнее общей карты владельцев. Агент не начинает неоднозначную кросс-модульную задачу без выяснения владения и контракта.

```text
Task ID:
Цель и граница задачи:
Назначенный участник:
Рабочая ветка:
Base branch и starting commit:
Документы для чтения:
Allowed paths (точный список):
Forbidden paths (включая shared interfaces):
Существующие интерфейсы: endpoint/DTO/model/component и ссылка на исходник:
Ожидаемое поведение, в том числе ошибки/права:
Зависимости от других задач и владельцев:
Acceptance criteria (измеримые):
Обязательные тесты/команды и окружение:
Ожидаемые deliverables: код/тест/скриншот/документ/commit/PR:
Definition of Done: scope, тесты, review, handoff, clean diff:
Порядок эскалации при изменении контракта:
```

## Пример из существующего проекта: изолированное улучшение теста

Пример **не является выданным заданием и не запускает Phase 3**. Его можно назначить только после сверки текущих тестов, чтобы не дублировать имеющийся кейс.

```text
Task ID: QA-EXAMPLE-01
Цель: добавить один регрессионный backend тест, который доказывает,
  что пользователь с активной ролью judge не читает заявки чужого соревнования.
Участник: № 2, backend соревнований.
Ветка: task/QA-EXAMPLE-01-judge-scope.
Base: main, hash указывает руководитель в момент выдачи (например, 600562d для исходного среза).
Документы: docs/team/{README,BACKEND_GUIDE,API_CONTRACTS,AUTH_AND_PERMISSIONS,TESTING}.md;
  docs/phase2-architecture.md; AGENTS.md.
Allowed: backend/tests/test_competitions.py.
Forbidden: backend/apps/**, backend/config/**, frontend/**, docs/openapi.yaml,
  docs/design/fsp-reference.html, любые migrations.
Контракт: GET /api/v1/applications/?competition=<id>;
  ApplicationsView.get фильтрует judge через competition__judge_assignments__judge
  и status=approved; active_role проверяет require_role.
Поведение: назначенный судья видит approved заявку своего события,
  чужое событие не раскрывается; неавторизованная роль отклоняется.
Зависимости: никаких изменений API/DB/DTO.
Acceptance: один целевой тест падает при снятии object filter и проходит
  на текущей реализации; существующие тесты не регрессируют.
Тесты: docker compose exec -T api python manage.py test tests.test_competitions;
  docker compose exec -T api ruff check .
Deliverables: один focused commit, diff только allowed файла, handoff с выводом.
Done: фактический pass, отсутствие правок production-кода и shared контрактов,
  review руководителя.
Если для теста понадобится менять API/model/fixture за пределами allowed —
  представить proposal руководителю, не внедрять обход.
```

Перед выдачей этого примера проверьте, не покрыт ли тот же случай существующим `test_judge_and_protocol_object_scope`: цель задачи должна добавлять конкретный недостающий аспект, а не повторять тест без ценности.
