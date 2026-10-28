# ProtoGX CI

`.github/workflows/ci.yml` runs on pull requests to `main` (including drafts), pushes to `main`, and manual dispatch. Runs for the same PR or ref supersede older runs. The token is read-only; the workflow does not deploy or use production credentials. Actions are pinned by commit.

- **Backend / PostgreSQL** installs `backend/requirements.txt` under Python 3.13, starts PostgreSQL 16 with test-only credentials, migrates, runs system and migration checks, the full Django suite, Ruff and warning-free OpenAPI comparison.
- **Frontend / build** installs the lockfile with Node 24 and runs typecheck, ESLint and production build.
- **Design contract** verifies the unchanged reference HTML and extracted CSS.
- **E2E / Compose** starts the existing Compose stack in an isolated runner, with the explicit local demo flags, runs Chrome Playwright sequentially and uploads browser failure artifacts. Login throttling remains enabled. Synthetic fixture data are reserved for the isolated environment. Tests may change that disposable database; never aim this job at production.

Local equivalents: from `backend`, run `python manage.py migrate`, `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py test`, and `ruff check .` against an isolated PostgreSQL instance. From the repository root run `python scripts/check_openapi_schema.py` and `python scripts/check_design_contract.py`. From `frontend`, run `npm ci`, `npm run typecheck`, `npm run lint`, `npm run build`, and `npm run test:e2e -- --workers=1` against a separately started, locally seeded Compose stack. The live XLSX test requires `openpyxl` in the Python invoked by `FSP_PYTHON` (defaults to `python`).

For failures inspect the specific job log, the first failing command, and the uploaded Playwright test results; validate PostgreSQL health, seed guards and web/API readiness before rerunning. Do not disable authorization, CSRF or throttles to make tests pass. Screenshots and traces are limited to fictional CI fixtures and retained seven days.

Once hosted runs actually pass, configure protection for `main` in repository settings: require a PR, the exact observed backend, frontend, design and E2E job check names, at least one independent review where supported, resolved conversations, and no force pushes or bypass except explicitly approved administrators. Do not enable these rules on the basis of an unexecuted workflow; repository rules are not changed by this PR.

This workflow and the full AC-11 workflow remain under verification; consult the PR checks for actual hosted results. The current registry implementation is incomplete and is not acceptance evidence for AC-11.
