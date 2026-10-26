# ФСП — запуск Codex + DeepSeek MCP на Windows

## 0. Предупреждение о ключе
Если токен провайдера (включая BasisWeb) ранее попадал в чат, логи или репозиторий, отзовите его у провайдера и выпустите новый. Не вставляйте секреты в Master Prompt, AGENTS.md, config.toml и Git.

## 1. Распакуйте этот архив
Рекомендуемый путь: `C:\Users\User\Documents\ChatGPT\fsp-platform`. В корне должны лежать `AGENTS.md`, `BOOTSTRAP_PROMPT.md`, `docs/MASTER_PROMPT.md`, `docs/design/fsp-reference.html`.

## 2. Откройте PowerShell в корне
```powershell
$project = "$env:USERPROFILE\Documents\ChatGPT\fsp-platform"
Set-Location $project
Test-Path .\docs\MASTER_PROMPT.md
Test-Path .\docs\design\fsp-reference.html
python --version
node --version
npm --version
git --version
docker --version
codex --version
```
Первые две проверки должны вернуть `True`. Проверьте запуск Docker Desktop, если используется Docker Compose.

## 3. Не меняйте пути к Python/MCP-скриптам, если они существуют
Текущие прежние MCP-скрипты находятся в другом каталоге. Это нормально: скрипт сервера != папка проекта.

## 4. Резервная копия конфигурации Codex
```powershell
$config = Join-Path $env:USERPROFILE '.codex\config.toml'
Copy-Item $config "$config.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
notepad $config
```
Пример нового блока находится в `config/mcp-reliable.example.toml`. Добавляйте его в конец, если имя `[mcp_servers.deepseek_reliable]` ещё не используется. Не удаляйте существующие `deepseek_coder`, `deepseek_validator`.

Важнейший параметр:
`ORCHESTRATOR_PROJECT_ROOT = 'C:\Users\User\Documents\ChatGPT\fsp-platform'`.
Если выбрать другой каталог, обязательно измените это значение. Подменять путь к самому `deepseek_mcp_v2_reliable.py` на путь проекта **не нужно**.

Для `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL` и модели Flash/Pro используйте только реально проверенные настройки своего MCP-провайдера; не подставляйте вымышленные URL и названия.

## 5. Ключ провайдера и запуск
Для Codex CLI, запущенного из этого же PowerShell, можно временно установить ключ без сохранения в истории команд:
```powershell
if (-not $env:DEEPSEEK_API_KEY) {
    $secureKey = Read-Host 'DeepSeek-compatible API key' -AsSecureString
    $env:DEEPSEEK_API_KEY = [System.Net.NetworkCredential]::new('', $secureKey).Password
}
[bool]$env:DEEPSEEK_API_KEY
codex mcp list
codex
```
Результат проверки должен быть `True`; содержимое ключа не печатайте. Если MCP требует другую переменную ключа, используйте фактическое название из его конфигурации. Для VS Code/других приложений переменные среды из этого PowerShell автоматически не передаются.

## 6. В первой сессии Codex
Вставьте содержимое `BOOTSTRAP_PROMPT.md` или попросите Codex прочесть этот файл и начать по нему. Сначала проверьте подключение инструментов, разрешённый корень и строгое чтение HTML-макета. Не запускайте все модули сразу.

## 7. Git
Если новая папка не является репозиторием:
```powershell
git init -b main
git add AGENTS.md BOOTSTRAP_PROMPT.md START_HERE.md .gitignore docs config/mcp-reliable.example.toml
git commit -m 'chore: bootstrap FSP design and orchestration instructions'
```
Перед `git add` убедитесь, что `.env`, токены и другие секреты не попали в список отслеживаемых файлов.

## 8. После первого успешного запуска
Приоритет: backend health → OpenAPI → авторизация и роли → визуально точный AppShell → один полный сценарий соревнования → только затем остальные модули и параллельная разработка.

## 9. Диагностика
- `MCP disconnected`: проверить пути в `.codex/config.toml`, версию Python, наличие ключа в окружении процесса Codex, провайдерские HTTPS URL и перезапустить Codex.
- `Path outside workspace`: изменить `ORCHESTRATOR_PROJECT_ROOT` на текущий проект и использовать относительные пути в запросах к MCP.
- `Codex still running`: это сообщение установщика, а не ошибка проекта; полностью закрыть Codex/VS Code перед повторным запуском *установщика*.
- Предложенный код изменяет `docs/design/fsp-reference.html`: отклонить как нарушение договора о дизайне.
