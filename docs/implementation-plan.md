# FSP OrenKod 2026 implementation plan

The functional contract is `docs/MASTER_PROMPT.md`; the visual contract is the unchanged `docs/design/fsp-reference.html`. This document freezes Phase 1 interfaces and organizes delivery. It does not claim that later workflows exist.

**Phase 1 completion (2026-10-27):** the four role dashboard foundations, mobile theme/role controls, expanded visual QA, and clean-volume startup gate are verified. `GET /api/v1/auth/dashboard/` is the new role-checked read contract in `docs/openapi.yaml`. The initial Phase 2 competition workflow is planned in `docs/phase2-plan.md`; its domain models and endpoints are not implemented yet.

## Architecture and first vertical slice

- `backend/`: Django 5 + DRF, PostgreSQL in Compose, `drf-spectacular` OpenAPI, Django session authentication and CSRF. `/api/v1/` is the versioned API. Django admin is for internal catalog maintenance.
- `frontend/`: Next.js App Router + TypeScript. A same-origin `/api/*` rewrite routes browser requests to Django. Shared CSS variables and the AppShell are derived from the reference HTML. Browser code never stores credentials in local storage.
- `db`: PostgreSQL 16 with a named volume. `web` and `api` use environment-based configuration. Local tests may use SQLite via an explicit test setting; PostgreSQL remains the deployed database.
- First slice: register with consent → sign in → obtain assigned roles → select active role in the server session → read the six-discipline catalog. Federation roles are provisioned by an administrator, never self-assigned at registration.

## Frozen Phase 1 data and permissions

`User` is a custom email-identified model. `UserRole(user, role)` stores multiple assigned roles; `active_role` lives in the server session and is checked against these assignments on every protected request. `PersonalDataConsent` records version and time. `Guardian` stores restricted guardian details and confirmation evidence for a minor. `Discipline` is a catalog record; its six initial values are inserted by data migration. Registration does not make legal claims about the sufficiency of online guardian verification.

The next domain slices use `Organization`, `AthleteProfile`, `AthleteDiscipline` with dated participation, `CoachAthleteLink` with explicit confirmation, `Competition`/`CompetitionStage`/`CompetitionCalendarEntry`, `CompetitionApplication`, `JudgeAssignment`, `CompetitionResult`/`ResultMetric`, `DocumentTemplate`/`GeneratedDocument`, `RankApplication`, `JudgeCategoryApplication`, `RatingRule`, `RegionalTeam`/`TeamMember`, `Notification`, and `AuditEvent`. Results must reference approved applications. Published protocol versions must retain the template version and include every approved participant. Ratings derive from the same published results, and manual team membership remains separate from ratings.

## Initial API contract

All responses are JSON, except OpenAPI. Error responses use DRF validation errors and appropriate 400/401/403/404 status codes. Cookie sessions require `X-CSRFToken` on unsafe browser requests.

| Method | Path | Request | Response |
| --- | --- | --- | --- |
| GET | `/api/v1/health/` | — | `{ "status": "ok" }` |
| GET | `/api/v1/auth/csrf/` | — | `{ "csrfToken": "…" }` and CSRF cookie |
| POST | `/api/v1/auth/register/` | `email`, `password`, `full_name`, `date_of_birth`, `consent`, `consent_version`; guardian fields required for minors | `{ "user": MeDTO }` |
| POST | `/api/v1/auth/login/` | `email`, `password` | `{ "user": MeDTO }` |
| POST | `/api/v1/auth/logout/` | — | 204 |
| GET | `/api/v1/auth/me/` | — | `MeDTO` |
| POST | `/api/v1/auth/active-role/` | `{ "role": "athlete" }` | `MeDTO` |
| GET | `/api/v1/disciplines/` | — | `[{ "code", "name" }]` |

`MeDTO = { id, email, full_name, roles: Role[], active_role: Role | null }`; roles are `federation`, `athlete`, `coach`, `judge`. Guardian data is absent from this DTO. Future endpoints in Master Prompt §5 must be versioned and reviewed before frontend adoption.

## Phases and dependencies

1. **Phase 1 — foundation:** Django/Next/Compose, schema, user/roles/consent, catalog, reference-faithful shared shell, auth UI, backend tests, typecheck/build, startup verification.
2. **Phase 2 — first full workflow:** competition creation, eligibility, athlete application, federation moderation, judge assignment, result entry, configurable protocol preview/publication, athlete history. This is the first full end-to-end gate.
3. **Phase 3 — domain breadth:** coach links, ranks and judge categories, rating rules and manual team selection, two-year participation analytics, exports, notifications, auditing.
4. **Phase 4 — stabilization:** full role dashboards, seed data with fictional identities, security/object tests, visual screenshots at 1440/768/390px in both themes, reproducible startup and demo.

## Five ownership tracks

| Track | Allowed future paths | Contract and gate |
| --- | --- | --- |
| 1. Codex architecture/integration | `backend/config`, `backend/apps/accounts`, `backend/apps/catalogs`, migrations, `frontend/src/components/shell`, `frontend/src/app/globals.css`, root Compose/docs | Sole owner of shared schema, roles, tokens, merges |
| 2. Competitions | `backend/apps/competitions`, `backend/apps/results`, `backend/apps/judging`, protocol services in `backend/apps/documents` | Approved application/result and template contracts; domain/API tests |
| 3. Sports domain | `backend/apps/registry`, `backend/apps/qualifications`, `backend/apps/ratings`, `backend/apps/teams`, `backend/apps/analytics` | Object permissions and versioned rules; domain tests |
| 4. Federation UI | `frontend/src/features/federation`, federation routes | Use frozen DTOs and shared components; build and visual review |
| 5. Other roles/QA | `frontend/src/features/athlete`, `coach`, `judge`, E2E and demo docs | Use frozen DTOs and shared components; E2E and visual review |

Bounded DeepSeek candidates after external disclosure approval: a single competition serializer/service with fixed DTOs and tests; a rating formula pure function with case fixtures; or a code review of explicitly selected, non-sensitive files. Codex validates returned paths, JSON shape, code, tests, and design fidelity before applying any proposal. No delegated task may alter shared user, API, migration, token, or AppShell contracts.
