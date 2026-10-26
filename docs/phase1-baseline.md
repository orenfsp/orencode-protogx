# Phase 1 recovery baseline — 2026-10-27

## Repository audit

The workspace already contained the Django/DRF accounts and catalog apps, custom user migrations, Next.js App Router shell and authentication pages, PostgreSQL Compose stack, OpenAPI file, tests, and source design. Git `main` had no commits; all source files were untracked. The untracked file inventory was reviewed before staging. `.gitignore` excludes `.env`, Python environments and caches, local SQLite files, `node_modules`, `.next`, logs, and TypeScript build output. `git check-ignore` confirmed exclusions for `.env`, local SQLite, installed dependencies, and `.next`. `.env.example` contains placeholders only. A targeted credential-pattern scan found no embedded credential; `START_HERE.md` mentions the `DEEPSEEK_API_KEY` variable but contains no value.

The source reference SHA-256 is `2362C4D1AEC5D54FA075215D6FDF986416D23D8402FBF33342D29671C5D043A2`, matching `docs/design/visual-qa.md`. The HTML was not edited.

## Executed baseline

| Check | Outcome |
| --- | --- |
| Local SQLite Django tests | Pass: 8 tests |
| Compose PostgreSQL Django tests | Pass: 8 tests |
| `ruff check backend` | Pass |
| `makemigrations --check --dry-run` | Pass: no changes |
| `docker compose exec -T api python manage.py migrate --check` | Pass |
| OpenAPI `spectacular --validate --fail-on-warn` | Pass |
| `npm.cmd run typecheck` | Pass |
| `npm.cmd run lint` | Pass |
| `npm.cmd run build` | Pass: 7 static routes |
| `docker compose up -d --build --no-deps web` | Pass; db healthy, api and web up |
| `python scripts/smoke_auth.py` against Compose | Pass: registration, login/logout, role denial, catalog, health |

The first proxy smoke failed because Next.js removed API trailing slashes and Django redirected back. `frontend/next.config.ts` now preserves the slash in the rewrite, and the rebuilt Compose smoke passed. PowerShell blocked `npm.ps1`; `npm.cmd` worked. Sandbox Docker access required the approved `docker compose` command prefix. A redundant OpenAPI validation output generated during checking was removed before staging.

## Incomplete Phase 1 gates

- Reference and Next.js homepage screenshots have been captured at 1440, 768, and 390 px in both themes; broader screen/state comparison and a mobile theme control remain open.
- `seed_demo` now creates fictional accounts and passes idempotence and non-debug refusal tests. A fully clean Compose volume startup has not been exercised.
- A seeded multi-role browser login and role switch now pass in Playwright. Role-specific dashboard features remain to be built; the current dashboard shows account and active role only.
- The read-only design-contract check is now available as `python scripts/check_design_contract.py`; it passes against the committed reference and CSS. Responsive screenshot comparison remains open.
- Begin Phase 2 only after the shared competition DTO, permission rules, and migrations are frozen by Codex. No competition workflow exists yet.

## Continued Phase 1 checks

The seed command was run twice against the existing PostgreSQL Compose database. The backend test suite grew from 8 to 10 passing tests, including seed idempotence and refusal with `DEBUG=False`. The rebuilt API retained its migration state. `ruff check backend scripts`, `npm.cmd run typecheck`, and `npm.cmd run lint` pass. Playwright captured 12 homepage images and the seeded role-switch E2E test passed (1 test) after Codex fixed the shared dashboard state. An initial browser login failure exposed missing `127.0.0.1:3000` in the default trusted origins; the Compose/API defaults now include both localhost forms. `docs/design/visual-qa.md` records visual differences and remaining gates.
