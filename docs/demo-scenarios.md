# Local demo accounts

Run `docker compose exec -T api python manage.py seed_demo` after the stack starts using the local demo settings below. The command creates reserved fictional `example.test` identities and can be rerun without duplicating users, roles, guardians, or consent records. It sets the password only when creating an account; reruns preserve any changed password. Do not run this command with real user data.

All new accounts use password `DemoOnly2026!` for the local demonstration:

- `demo.federation@example.test` — federation and athlete; use the sidebar to switch roles.
- `demo.athlete@example.test` — athlete.
- `demo.coach@example.test` — coach.
- `demo.judge@example.test` — judge.
- `demo.junior@example.test` — junior athlete with a fictional guardian record pending verification.
- `demo.athlete2@example.test` and `demo.athlete3@example.test` — additional adult athletes, selected manually for the example team.
- `demo.junior.verified@example.test` — fictional junior with a verified demo guardian record.

The seeded `demo_seed` consent records are synthetic test fixtures, not legally verified consent. One junior guardian remains pending verification; a separate fictional junior has verified guardian consent. The command creates four regional teams across 2025/2026 and disciplines: two teams are populated by explicit manual decisions, one is for a prior season and one is empty. The highest-rated eligible athlete is deliberately left out of the algorithmic roster. Re-running it preserves passwords, applications, publications, ratings, memberships and unchanged audit history. Two fictitious rank histories use published-result evidence and are not verified EVSK decisions.

Three fictional organizations and optional athlete profiles demonstrate short and long Cyrillic affiliations, including one profile without an organization. Team documents show the current organization or «Не указана». Seed reruns do not overwrite an existing profile's affiliation. This minimal current affiliation does not implement the AC-11 registry or affiliation history.

An isolated fresh Compose run on 2026-10-28 produced 8 users, 3 organizations, 4 athlete profiles, 6 competitions, 14 applications, 4 protocol publications, 7 ratings, 13 total rating-contribution records (10 current), 4 teams and 3 memberships. A second seed kept these counts and the 3 team decision records unchanged. Browser workflows may add independent test records.

## Automatic Compose startup

Copy `.env.example` to `.env` and run `docker compose up --build`. The API waits for PostgreSQL health, applies migrations, then runs `seed_demo` when `DJANGO_DEBUG=1`, `DEMO_SEED_ENABLED=1` and `DEMO_ENVIRONMENT=local` are set, and the database host is local. Image builds never connect to the database. To rerun manually use `docker compose exec -T api python manage.py seed_demo`; to disable demo data set `DEMO_SEED_ENABLED=0`. Production and staging must use `DJANGO_DEBUG=0` and keep the seed flag disabled.

## Regional team walkthrough

Login as `demo.federation@example.test` / `DemoOnly2026!`, switch to the federation role, open **Команды**, choose season, discipline and age group, then open the populated demo team. Inspect rating and eligibility context, add or remove an eligible athlete, move members with the arrows, and download the roster or draft order as PDF/DOCX. The generated draft is explicitly marked as unsigned and is not a legally issued order.

The **Утвердить состав** action finalizes a non-empty draft team and records the federation decision. Document downloads create an audit event with the selected document type and format. The seeded competition path includes four published protocols, fourteen applications, seven calculated ratings and current contribution provenance. Two additional competition fixtures are keyed by month and show open and closed registration; reruns in the same month preserve their data. On a new month the command adds new examples without rewriting earlier ones.
