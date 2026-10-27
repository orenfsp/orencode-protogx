# FSP OrenKod 2026

Для новых разработчиков и независимых AI-ассистентов: [документация команды](docs/team/README.md).

Phase 2 competition workflow on the Phase 1 platform. The mandatory design source is `docs/design/fsp-reference.html`; it is unchanged. Scope, API contracts and acceptance evidence are recorded in `docs/phase2-architecture.md`, `docs/openapi.yaml` and `docs/acceptance-matrix.md`.

## Run with Docker Compose

Copy `.env.example` to `.env` and replace the local passwords and Django secret. Run `docker compose up --build`. The frontend is at `http://localhost:3000`, API at `http://localhost:8000/api/v1/health/`, OpenAPI at `/api/schema/`, docs at `/api/docs/`. The API applies migrations and, with `DJANGO_DEBUG=1`, idempotently seeds five fictional demo accounts before becoming healthy. Next.js waits for that healthcheck. The database persists in a named Compose volume; `seed_demo` refuses non-debug environments.

## Local development and checks

Backend: install `backend/requirements.txt`; set `DATABASE_ENGINE=sqlite` only for local tests, then run `python backend/manage.py migrate` and `python backend/manage.py test` (or `pytest backend/tests`). For the deployed path, use PostgreSQL.

Frontend: `cd frontend`, `npm ci`, `npm run typecheck`, `npm run lint`, `npm run build`, `npm run dev`. The frontend rewrites `/api/*` to `API_INTERNAL_URL` (default `http://127.0.0.1:8000` for local development; the Docker image compiles with `http://api:8000`).

With Compose running, run `npm run test:e2e` from `frontend/` for the Chrome role, theme and full competition workflow tests. Run `npm run visual:qa` for Phase 1 captures and `npm run visual:phase2` for competition and history captures at 1440/768/390 px in light and dark themes; see `docs/design/visual-qa.md`. These commands use an installed Google Chrome.

Run `python scripts/check_design_contract.py` to verify that the reference HTML and extracted shared CSS still match the committed design contract.

After Compose starts, `python scripts/smoke_auth.py` exercises registration, session login/logout, role denial, and the six-discipline catalog through the frontend proxy. It creates one randomly named fictional test account in the local database.

For repeatable local accounts, follow `docs/demo-scenarios.md`. You may rerun `docker compose exec -T api python manage.py seed_demo`; it preserves existing passwords. To validate a clean database without touching development data, choose an unused Compose project name and alternate host ports: set `FSP_DB_PORT`, `FSP_API_PORT`, `FSP_WEB_PORT` and `DJANGO_CSRF_TRUSTED_ORIGINS`, then run `docker compose -p <unique-name> up -d --build`. The project name scopes its PostgreSQL volume.

Registration always creates an athlete role. Federation and other roles require trusted administrator assignment. For minors, submitted guardian details remain pending verification; online self-attestation is not claimed as production-grade legal verification.

## Phase 2 walkthrough

Sign in as `demo.federation@example.test` with the local-only password in `docs/demo-scenarios.md`. In **Calendar**, create a draft competition, choose a discipline, age groups, an unverified template, dates and regulations, then publish it. Sign in as `demo.athlete@example.test` to apply. The federation approves the application and assigns `demo.judge@example.test`; the judge enters a result, which the federation validates. Preview and publish a versioned protocol, then download that version as PDF or DOCX. The athlete's **History** then shows the published result. Coaches use **Coach links** to request a discipline-specific link by athlete email; the athlete must confirm it before the coach can apply for them. All demo identities and test scores are fictional.

Templates are configurable and versioned per discipline. Seeded templates are explicitly unverified demo structures. Check the current primary sports rules and the Appendix No. 5 example before any official document use; publication in this system does not claim regulatory or EVSK compliance.
