# Codex Project Instructions — FSP OrenKod 2026

## Sources of truth
1. Read `docs/MASTER_PROMPT.md` for functional requirements and acceptance criteria AC-01 to AC-18.
2. Read `docs/design/fsp-reference.html` BEFORE writing any frontend code. Treat the HTML/CSS as the mandatory visual contract. Never change the reference file.
3. Backend: Django + Django REST Framework. Frontend: Next.js App Router + TypeScript. Database: PostgreSQL.
4. The design must retain its numbered indigo sidebar, dotted navigation, document rail, orange accents, Rubik/Inter/JetBrains Mono fonts, stamp-style badges, table borders, themes, and mobile bottom nav. Do not replace with generic shadcn defaults.

## Orchestrator and delegated tools
- Codex is the sole integrator and owner of shared architecture, permissions, API schemas, design tokens, shared components, and merge decisions.
- When the DeepSeek MCP is available and validated, delegate small bounded tasks to it. First discover actual tool names and signatures. Expected names in this orchestrator version: `get_project_context`, `implement_task`, `repair_task`, `review_code`, `validate_proposal`; do not assume tools are present unless listed.
- Use Flash for uncomplicated implementation, Pro for complex reasoning when model routing is configured and tested. Never assume model names or provider endpoints.
- Give delegated work explicit allowed paths, input context, data contracts, acceptance criteria, and tests. Do not send credentials, `.env`, private data, or arbitrary repository content.
- DeepSeek output is a proposal, not a permission to write files. Validate schemas, allowed relative paths, scope, context freshness and code before applying. Use isolated branches/worktrees for parallel changes.
- Retry/repair only bounded concrete failures. If MCP fails, report it honestly and do not claim DeepSeek performed the work.
- At each milestone run relevant tests/builds and provide exact pass/fail evidence.

## Project coordination
- Initially freeze: Django custom User model and roles, shared DTO/OpenAPI schema, base migrations, and Next.js design tokens/layout.
- Organize five ownership tracks as described in Section 15 of the master prompt. Never let contributors independently edit shared interfaces or styling contracts.
- Keep `docs/acceptance-matrix.md` current. Mark items `implemented`, `partial`, or `not_implemented` based on executed evidence.
- Do not ship a static demo as a completed workflow. Prohibit fabricated official protocol or EVSK compliance claims.
- Use fictitious seed identities only. Preserve role-based/object-level authorization and guardian consent requirements for minors.
- For protocols, preserve discipline-specific templates and source verification requirement in Section 7.

## Original bootstrap task (completed)
`BOOTSTRAP_PROMPT.md` records the initial inventory, reference inspection, implementation plan, and executable baseline. Phase 1 and Phase 2 are documented; use current status and an assigned task contract for new work. Keep the original design file unchanged.

## Team collaboration and agent discovery
- The shared onboarding index is [docs/team/README.md](docs/team/README.md). All agents must follow [docs/team/AI_AGENT_RULES.md](docs/team/AI_AGENT_RULES.md) and the assigned [task contract](docs/team/TASK_TEMPLATE.md); the lead alone makes integration decisions.
- Before a task, check [current status](docs/team/CURRENT_STATUS.md), [acceptance evidence](docs/acceptance-matrix.md), the actual code, branch, and allowed paths. Use the relevant backend, frontend, API, authentication, design, Git, and testing guides linked from the team index.
- For frontend work, read `frontend/AGENTS.md` and the unchanged `docs/design/fsp-reference.html`. Do not start Phase 3 without an explicit new assignment.
