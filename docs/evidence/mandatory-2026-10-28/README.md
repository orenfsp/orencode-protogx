# Исполненные проверки mandatory part 1

Финальный код `223bebe28ac7fc1f5e4244f42d0e642b68fd3bdd`, ветка `codex/mandatory-case-completion`; baseline `ee60893d2278001aaa6b704943230c0bd2db6eeb`. Последующий commit документации/PNG не меняет код. Это реальные локальные журналы, не hosted CI.

- `backend-139.txt`: финальный Python, PostgreSQL 139 passed / 367.625s.
- `browser-118.txt`: единый полный финальный Chrome 118 passed / 7.6m, 0 failed/0 skipped.
- `coach-history-targeted.txt`: 2 passed / 25.0s, включая шесть coach viewport/theme/keyboard/axe состояний.
- `production-build.txt`: production build Next.js/TypeScript, 17 страниц.
- `screenshots.json`: SHA-256 30 live PNG, reference HTML и extracted CSS, code SHA.
- `regulatory-sources.json`: скачанные файлы и SHA-256; их проверка описана в `docs/regulatory-source-review.md`. Производный PDF помечен именем `evsk-2025.pdf`; оригинал — DOC.

Исторические журналы сохранены: `backend.txt` (137), `documents.txt` (10), `browser.txt` (115 pass/1 fail), `browser-registry-recheck.txt` (1 pass), `browser-118-before-fix.txt` (117 pass/1 fail, неоднозначный locator причины). Они не являются финальным статусом.

Среда: изолированный `fspmandatory`; web 13001, API 18001, PostgreSQL 55433, Mailpit 18025. Секреты/реальные персональные данные не использовались. Полные команды и ограничения: [mandatory-verification.md](../../mandatory-verification.md).
