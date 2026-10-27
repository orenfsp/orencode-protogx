# PR integration review — 2026-10-27

Base `main`: `f7beaa6312147513a14e1362d6f89c3b679e5db3`. PR #1 original head: `61c2839ffcca863f4a7a88f5794130f20c84728b`. PR #2 head: `ebe2189b39487db053378b94cfd69f40c5f3bfa1`.

## PR #1 — qualifications

The repair binds new rank applications to the latest publication and the matching participant row, stores a copy of the evidence, keeps legacy provenance unknown rather than inventing it, removes access after a coach link is revoked, rechecks consent and guardian status, and scopes page state to user and role. It adds a nullable `revoked_at` to consent records: the latest record determines whether consent is current, and the existing dashboard, competition and qualification checks use that rule. A user-facing withdrawal and renewal workflow is not included. Historic records and applications are read-only in Django admin; correction of an existing historic entry remains a separate requirement.

The results endpoint returns paginated candidates with metadata and validates the latest published row; the response count counts candidates before snapshot and hint filtering. The dashboard links to qualifications, and OpenAPI describes the page and decision-record objects. Tests cover changed evidence, later publication, missing rows, coach revocation, consent withdrawal and renewal, guardian verification, more than 300 candidates, admin restrictions, stale role responses, navigation and the live competition-to-qualification workflow.

Individual verification: the final PostgreSQL suite passed 54/54; system check, migration drift, Ruff, TypeScript, ESLint, production build, design contract and 4 focused browser tests passed. The live workflow passed. OpenAPI validation returned zero errors and four enum-naming warnings. An earlier full-suite run failed because a DOCX assertion compared ZIP timestamps; an isolated retry passed. The corrected assertion compares every archived member's contents instead of container timestamps.

DeepSeek Pro requests, IDs, accepted and rejected findings, and the schema-validation retry are documented in [delegation-log.md](delegation-log.md). DeepSeek did not write files or run tests. Existing consent records remain valid unless marked withdrawn, and old rank applications cannot be assigned a trustworthy publication retroactively.

## PR #2 — frontend continuation

No code changes were required. The focused Playwright suite passed 13/13 and the existing live competition workflow passed. Reference, homepage, calendar, dashboard, history and role-aware competition captures were inspected at 1440, 768 and 390 pixels in both themes; the implementation retains the rail, indigo navigation, typography, orange accents, bordered tables and mobile navigation. It substitutes live competition data for the reference's static example and adds a mobile theme control. Narrow tables require horizontal scrolling; the new competition page explicitly indicates this. Reference and page captures are in the local temporary directory `fsp-pr2-visual-review` and are not committed baselines.

## Combined integration

PR #2 first is the proposed order. A detached integration worktree based on PR #2 revealed one textual conflict in `frontend/src/app/dashboard/page.tsx`: both PRs add an action on the same line. The test-only resolution retains both the role-aware competition link and the qualifications link; it has not been committed or merged to `main`. A separate integration stack with a new PostgreSQL volume applied both migrations and completed the production build, migration drift check, Ruff and design-contract check. The combined PostgreSQL suite passed 54/54 and the combined browser suite passed 18/18, including the live workflow. OpenAPI validation had zero errors and four enum-naming warnings.

Before any merge, fetch the heads again, reconcile the dashboard conflict without losing either link, rerun affected checks on the resulting tree, and obtain explicit team-lead merge authorization. No branch protection is bypassed.
