# Phase 2 competition contract and verification

## Ownership and data model

Codex owns `backend/apps/competitions`, its five additive migrations, `docs/openapi.yaml`, the Next.js DTOs and workflow components, and permission decisions. The Phase 1 custom user, roles, consent, catalog and visual tokens remain in place. The reference HTML is unchanged.

- `AgeGroup` defines configurable inclusive age bounds. `CalendarEntry` stores EKP or regional source, entry number, year and reference URL.
- `Competition` links a discipline, age groups, template version, calendar entry, dates, deadline and regulations. `CompetitionStage` holds format and dates for hybrid stages.
- `CoachAthleteLink` requires athlete confirmation for a specific discipline. Pending coach responses hide the athlete ID and name. Coaches request by exact email without a lookup response that discloses account existence.
- `Application` is unique for competition and athlete. It stores submitter, moderation decision and reason. `JudgeAssignment` is unique for competition and judge.
- `Result` stores status, optional place/score, template-defined JSON metrics, author and validator. Only approved applicants may have results; unclassified statuses cannot carry invented scores or places.
- `ProtocolTemplate` is immutable and versioned for one discipline. Its field definitions validate metric type and required status; its columns determine protocol preview layout. Six distinct, explicitly unverified demo templates are seeded. New versions are created in the federation UI.
- `ProtocolPublication` stores an immutable JSON snapshot with every approved application, its template version, publishing user and time. `AuditEvent` stores changes and before/after details for material Phase 2 actions.

## State and access rules

`draft → published` is federation-only and requires a future registration deadline. Federation can edit setup until the first application; after that eligibility fields and stages are frozen. All setup is frozen after the first protocol publication. Application submission requires a published competition, open deadline, assigned athlete role, age eligibility and recorded consent. Minors additionally require verified guardian consent. A coach requires a confirmed link for the competition's discipline. Application moderation is federation-only and can decide only pending requests. An assigned judge may see approved applicants for that competition and enter results; the federation may enter and validate results. Publication blocks pending applications and unvalidated entered results, rechecks approved participants' consent, locks the relevant rows, snapshots every approved applicant, and creates the next version. Athlete history reads only the latest published version and only that athlete's row. Draft competitions and protocol snapshots are not publicly exposed.

`GET /api/v1/competitions/` and detail reads are public for published competitions. Other contracts, including age groups, calendar entries, templates, applications, coach links, judges, results, preview, publication and history, are documented in `docs/openapi.yaml` and served at `/api/schema/` and `/api/docs/`. Mutations use same-origin session authentication plus CSRF. The browser API helper requests a CSRF token before each unsafe method.

## Verification gates

- Django tests: 23/23 plus four subtests on SQLite and PostgreSQL cover the Phase 1 regressions plus competition lifecycle, age/guardian/deadline and coach permissions, assigned judging, two metric schemas, all-applicant preview, consent recheck, immutable version correction, PDF/DOCX export and long-name wrapping, private history and audit events.
- `ruff check .`, `makemigrations --check --dry-run`, `spectacular --validate`, Next.js typecheck/lint/build, Compose API health and Chrome E2E are required. Exact latest results are recorded in the acceptance matrix and task response.
- The Chrome Phase 2 test exercises the visible federation → athlete → federation → judge → federation → athlete workflow against PostgreSQL. The visual capture command reviews calendar, federation/athlete competition detail and history at 1440/768/390 px in light and dark modes.

## Regulatory and scope limits

The template fields are proposed demonstration structures. The customer-supplied Appendix No. 5 URL is an example and has not been verified against the current primary source; formats may vary by discipline. No score, placement or EVSK qualification is inferred by the platform. Versioned PDF and DOCX exports are rendered from immutable published snapshots and conspicuously labeled as demonstration documents requiring source verification. Later phases still own sports ranks, ratings, regional teams, notifications, participation trends and other document types, including XLSX. Guardian verification is an administrator-confirmed status, not an external legal identity integration.
