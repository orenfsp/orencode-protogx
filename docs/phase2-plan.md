# Phase 2 — complete competition workflow

Phase 1 is verified in `docs/acceptance-matrix.md` and `docs/phase1-baseline.md`. Phase 2 has not started. Codex owns new shared DTOs, permissions, migrations, protocol contracts and design primitives. The immutable reference HTML remains the visual contract.

## Delivery order and gates

1. **Freeze schema and permissions.** Define organization and athlete profiles with dated discipline participation; calendar entries; competitions, age groups and stages; applications; judge assignments; results; protocol template versions, publication records and audit events. Version the DTOs in `docs/openapi.yaml`. A user may hold several roles, but each request must check the active assigned role and object ownership. Minor applications require verified guardian consent; no public personal identifiers.
2. **Calendar and registration.** Federation creates a competition with one of six catalog disciplines, level/type, format and optional hybrid stages, dates, location, age groups, registration deadline, regulations and EKP/regional calendar reference. Public and eligible athlete views read stored records. Athlete application validates age, deadline, consent and duplicate submission server-side.
3. **Moderation and judges.** Federation approves/rejects applications with reasons and audit records. Federation assigns judges; a judge sees only their own assignments. Coach actions are limited to confirmed athlete links when that model is introduced.
4. **Results and discipline templates.** Federation records result status and discipline-specific metrics only for approved applications. No-show and missing-result statuses carry no fabricated score or placement. Store configurable template versions and field definitions; prove at least two disciplines render different protocol columns without code changes.
5. **Preview, publish and history.** Protocol preview includes every approved participant, including non-winners and no-shows. Publication creates an immutable version and audit trail; corrections create a new version. Published results populate the athlete's own history. Mark the generated form as a draft until the primary official source and current rules are verified; do not claim EVSK or official protocol compliance.
6. **End-to-end verification.** PostgreSQL migrations and domain tests must pass for eligibility, object permissions, all-participant protocols, two template variants, correction audit and published history. Run frontend typecheck, lint, build, Chrome workflow tests, and 1440/768/390 light/dark screenshots. Update AC-05–AC-08 and AC-15 only from executed evidence.

## First demonstrable path

Federation creates an algorithmic competition → athlete with valid consent applies → federation approves → judge assignment is visible to that judge → federation records a result and a no-show → protocol preview includes both approved athletes → federation publishes → athlete sees their result in history. Repeat protocol rendering with a second discipline template before declaring AC-07 complete.
