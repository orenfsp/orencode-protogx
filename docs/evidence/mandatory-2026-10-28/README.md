# Исполненные проверки mandatory part 1

Код: `99cc63da252cab311d7209ce86354e8cad84627d`; реализация `b41ca965d4bae2246732caac8095d0ee96397f66`; baseline `ee60893d2278001aaa6b704943230c0bd2db6eeb`. Ветка: `codex/mandatory-case-completion`. Документация/PNG и исправление ожидания logout в тесте сохраняются отдельно и не меняют runtime.

Содержимое каталога — фактические журналы локального выполнения, не hosted CI:

- `backend.txt`: 137 PostgreSQL tests, OK.
- `documents.txt`: 10 competition/document tests после локализации формата, OK.
- `browser.txt`: полный последовательный Chrome run; точное число/ошибки — в конце файла.
- `browser-registry-recheck.txt`: повтор конкретного исправленного live registry сценария.
- `screenshots.json`: SHA-256 24 live PNG, reference HTML и extracted CSS.

Среда: изолированный Compose `fspmandatory`; web 13001, API 18001, PostgreSQL 55433, Mailpit 18025. Реальные персональные данные и credentials не использовались. Ссылки на исходники, команды и ограничения: [mandatory-verification.md](../../mandatory-verification.md).
