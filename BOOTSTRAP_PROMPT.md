# First message to Codex

You are the lead Codex orchestrator for OrenKod 2026 FSP. The repository root is the current working directory. Read, in this order: `AGENTS.md`, `docs/MASTER_PROMPT.md`, `docs/design/fsp-reference.html`.

IMPORTANT: Follow the attached HTML design strictly. Do not propose a replacement theme or generic UI kit. Django REST Framework + Next.js App Router + TypeScript + PostgreSQL are mandatory.

Do this in controlled stages:

1. Inspect the existing repository and environment; never overwrite user changes. Confirm the precise workspace root. Summarize mandatory acceptance criteria AC-01 through AC-18.
2. Discover available MCP servers and tools. Check whether the reliable DeepSeek MCP is connected and whether `get_project_context` can read `AGENTS.md` and `docs/design/fsp-reference.html` using relative paths only. Report failures honestly; do not pretend the server is connected.
3. Propose and document a five-developer ownership split, shared API contracts, a domain model, task dependencies, allowed paths, tests, and the first end-to-end workflow. Codex owns core architecture and shared design primitives.
4. Begin with a reproducible Django + DRF + PostgreSQL / Next.js skeleton, Docker Compose, and an exact copy of the supplied visual design's tokens and responsive AppShell. Do not replace the reference HTML.
5. Once a working baseline is verified, implement one end-to-end scenario: competition creation → athlete application → moderation → results → discipline-configurable protocol preview/publication → athlete results history. Expand only after tests pass.
6. Delegate bounded, non-conflicting tasks to DeepSeek MCP where the tools exist and requests are within the configured root. Validate the returned proposal before applying. Do not give agents uncontrolled permission to change protected shared files.
7. Run actual migrations, backend tests, Next.js build, and available screenshot comparisons at 1440/768/390px in light and dark themes. Track results in `docs/acceptance-matrix.md` and `docs/design/visual-qa.md`.

At the end of each stage, provide a concise list of files changed, commands run, tests and actual outcomes, DeepSeek tools/models actually used, blockers, and the next concrete development tasks. Do not report success for untested steps.
