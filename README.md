# FSP OrenKod 2026

Early Phase 1 platform foundation. The mandatory design source is `docs/design/fsp-reference.html`; it is unchanged. Functional scope and pending acceptance gates are recorded in `docs/implementation-plan.md` and `docs/acceptance-matrix.md`.

## Run with Docker Compose

Copy `.env.example` to `.env` and replace the local passwords and Django secret. Run `docker compose up --build`. The frontend is at `http://localhost:3000`, API at `http://localhost:8000/api/v1/health/`, OpenAPI at `/api/schema/`, docs at `/api/docs/`. Migrations run when the API service starts. The database persists in a named Compose volume.

## Local development and checks

Backend: install `backend/requirements.txt`; set `DATABASE_ENGINE=sqlite` only for local tests, then run `python backend/manage.py migrate` and `python backend/manage.py test` (or `pytest backend/tests`). For the deployed path, use PostgreSQL.

Frontend: `cd frontend`, `npm ci`, `npm run typecheck`, `npm run lint`, `npm run build`, `npm run dev`. The frontend rewrites `/api/*` to `API_INTERNAL_URL` (default `http://127.0.0.1:8000` for local development; the Docker image compiles with `http://api:8000`).

Run `python scripts/check_design_contract.py` to verify that the reference HTML and extracted shared CSS still match the committed design contract.

After Compose starts, `python scripts/smoke_auth.py` exercises registration, session login/logout, role denial, and the six-discipline catalog through the frontend proxy. It creates one randomly named fictional test account in the local database.

Registration always creates an athlete role. Federation and other roles require trusted administrator assignment. For minors, submitted guardian details remain pending verification; online self-attestation is not claimed as production-grade legal verification.
