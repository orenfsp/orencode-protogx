# ProtoGX CI

`.github/workflows/ci.yml` runs on pull requests to `main` (including drafts), pushes to `main`, and manual dispatch. Runs for the same PR or ref supersede older runs. The token is read-only; the workflow does not deploy or use production credentials. Actions are pinned by commit.

- **Backend / PostgreSQL** installs `backend/requirements.txt` under Python 3.13, starts PostgreSQL 16 with test-only credentials, migrates, runs system and migration checks, the full Django suite, Ruff and warning-free OpenAPI comparison.
- **Frontend / build** installs the lockfile with Node 24 and runs typecheck, ESLint and production build.
- **Design contract** verifies the unchanged reference HTML and extracted CSS.
- **E2E / Compose** starts the existing Compose stack in an isolated runner, with the explicit local demo flags, runs Chrome Playwright sequentially and uploads browser failure artifacts. Login throttling remains enabled. Synthetic fixture data are reserved for the isolated environment. Tests may change that disposable database; never aim this job at production.

Local equivalents: from `backend`, run `python manage.py migrate`, `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py test`, and `ruff check .` against an isolated PostgreSQL instance. From the repository root run `python scripts/check_openapi_schema.py` and `python scripts/check_design_contract.py`. From `frontend`, run `npm ci`, `npm run typecheck`, `npm run lint`, `npm run build`, and `npm run test:e2e -- --workers=1` against a separately started, locally seeded Compose stack. The live XLSX test requires `openpyxl` in the Python invoked by `FSP_PYTHON` (defaults to `python`).

The live profile-creation test registers a fictional adult through the normal consent form, then assigns coach and judge roles as explicit test setup using `docker compose exec`. Set `FSP_E2E_COMPOSE_PROJECT` to the isolated local project name; CI uses its existing `COMPOSE_PROJECT_NAME`. The fixture refuses to run unless Django debug, local demo seed flags and a local database host are all present; the test exercises rejection with `DEMO_ENVIRONMENT=production` inside the isolated container before applying the local fixture. Never point it at staging or production. It does not insert consent or create a federation role.

For failures inspect the specific job log, the first failing command, and the uploaded Playwright test results; validate PostgreSQL health, seed guards and web/API readiness before rerunning. Do not disable authorization, CSRF or throttles to make tests pass. Screenshots and traces are limited to fictional CI fixtures and retained seven days.

GitHub has reported the job names `Backend / PostgreSQL`, `Frontend / build`, `Design contract`, and `E2E / Compose` on the PR run. After all four succeed on the final head, open repository **Settings → Rules → Rulesets**, create a branch ruleset targeting `main`, require a pull request and at least one independent review where supported, require review conversations to be resolved, and add the four observed checks under required status checks. Block force pushes and restrict bypass permissions. Verify the exact check names in the final run before saving. Branch protection has not been changed by this PR.

This workflow and the full AC-11 workflow remain under verification; consult the PR checks for actual hosted results. The current registry implementation is incomplete and is not acceptance evidence for AC-11.
