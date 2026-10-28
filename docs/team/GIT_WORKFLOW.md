# Git для пяти разработчиков

На момент аудита `HEAD=600562d`, ветка `main`, рабочее дерево было чистым, `git remote -v` вернул **пустой список**. Поэтому конкретный URL клонирования и команда создания PR у хостинга требуют ручной настройки руководителем. Не публикуйте репозиторий автоматически и не выдумывайте GitHub URL.

`main` — интеграционная ветка. Обычные участники не делают direct push в `main`; одна задача = одна ветка = один владелец файлов. Руководитель выдаёт base commit, разрешённые пути и контракт задачи. Не коммитьте `.env`, токены, персональные данные, `node_modules`, `.next`, локальные БД или generated dependencies. Перед merge нужны тесты, review и [integration checklist](INTEGRATION_CHECKLIST.md). Никакого force push или reset общей ветки без явного разрешения.

## Команды для новичка (PowerShell)

После того как руководитель выдаст реальный `<REPOSITORY_URL>`:

```powershell
git clone <REPOSITORY_URL> fsp-platform
Set-Location fsp-platform
git remote -v
git status --short --branch
git switch main
git pull --ff-only origin main
git switch -c task/FSP-123-short-name
```

`origin` в этих примерах появится после клонирования URL. В текущем локальном клоне его **нет**. Перед каждой правкой убедитесь, что `git branch --show-current` показывает вашу task-ветку и `git status --short` не содержит чужих файлов.

```powershell
git diff --check
git diff --stat
git add -- <только-разрешённые-пути>
git diff --cached --stat
git commit -m "docs: explain FSP-123 onboarding step"
git push -u origin task/FSP-123-short-name
```

Не используйте `git add .`, пока не проверили список. После push откройте Pull Request из task-ветки в `main` в интерфейсе фактически выбранного хостинга. Если установлен и авторизован GitHub CLI **и remote действительно GitHub**, допустима команда `gh pr create --base main --head task/FSP-123-short-name --fill`; это условный пример, здесь не проверен.

## Обновление ветки и конфликты

Перед обновлением сохраните/закоммитьте свою работу. Для начинающих предпочтителен merge без переписывания опубликованной истории:

```powershell
git fetch origin
git switch task/FSP-123-short-name
git merge origin/main
git status
```

При конфликте откройте каждый файл с маркерами `<<<<<<<`, `=======`, `>>>>>>>`, изучите обе версии и договоритесь с владельцем общего контракта; не выбирайте вслепую `ours/theirs`. Исправьте, затем `git add -- <разрешённые-файлы>`, `git commit`, запустите проверки и `git push`. Если разрешить безопасно нельзя, остановите merge через `git merge --abort` и передайте конфликт руководителю. После merge повторите API/permission/визуальные проверки затронутой области.

## Ошибки и восстановление

| Ситуация | Безопасное действие |
| --- | --- |
| Случайно начали работу на `main`, без commit | `git switch -c task/FSP-123-short-name`; изменения останутся в новой ветке, проверьте status |
| Не тот файл добавлен в index | `git restore --staged -- <file>`; файл остаётся в рабочем дереве |
| Локальная правка файла без commit не нужна | сначала `git diff -- <file>`; затем только осознанно `git restore -- <file>` — это удаляет локальную правку |
| Неудачный локальный merge | `git merge --abort`; сначала проверьте `git status` |
| Уже отправили ошибочный commit в общую ветку | сообщите руководителю; исправление новым commit либо согласованным `git revert`, без force push |
| Потеряли ветку/commit | `git reflog` для поиска hash; восстановление согласуйте до изменения общей истории |

Руководитель принимает PR только после отчёта по [TASK_TEMPLATE.md](TASK_TEMPLATE.md) и сверки с [TEAM_ROLES.md](TEAM_ROLES.md).
# CI

Условия запуска проверок и подготовка защиты `main` описаны в [CI.md](../CI.md). Не включайте обязательные проверки по неподтверждённым именам: используйте фактические имена успешно выполненных GitHub Actions.
