# INTEGRATE-OPTIONAL-2026-10-28

User assignment: combine the current local project with ProtoGX branch
`feat/case-optional-d1-d12`, preserve the better behavior and run careful tests.

Integrator: Codex. Branch: `codex/integrate-optional-d1-d12`.
Local starting commit: `d506a98`; local working changes preserved in `131c057`.
Remote input: `b3a2884` (fetched from origin).

Allowed paths: files changed by either input under backend/, frontend/, scripts/,
documentation, Compose and example configuration; additive compatibility migrations
and integration regressions. Existing local audit files and worktrees are excluded
from the merge commit. Never change the reference HTML or extracted globals.css,
commit secrets, reset database volumes or rewrite either source branch.

Contracts: retain local registry/history, session/CSRF, role navigation, mandatory
notification API and SMTP delivery; add optional extensions and OIDC provider.
The optional inbox has a distinct `optional-notifications/` API. Reuse the existing
registry report methodology in D6/D9. Changes to shared contracts are owned here
by the integrator under the user's explicit merge assignment.

Acceptance: both histories are merge parents; no conflict markers; PostgreSQL full
suite, Chrome suite, optional live workflows, lint/typecheck/build, migration drift,
warning-free OpenAPI and design checks have actual recorded results. Failures are
investigated and corrected, not hidden by weakening permissions or assertions.

No push, remote PR merge, production deployment or regulatory certification is
part of this local integration. Final evidence: `docs/integration-verification.md`.
