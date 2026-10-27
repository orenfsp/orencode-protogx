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

The seeded `demo_seed` consent records are synthetic test fixtures, not legally verified consent. One junior guardian remains pending verification; a separate fictional junior has verified guardian consent. The command creates four regional teams across 2025/2026 and disciplines: one team with two manually selected athletes, one different-discipline team, one prior-season team and one empty team. The highest-rated eligible athlete is deliberately left out of the populated roster. Re-running it preserves passwords, applications, publications, ratings, memberships and unchanged audit history.

## Automatic Compose startup

Copy `.env.example` to `.env` and run `docker compose up --build`. The API waits for PostgreSQL health, applies migrations, then runs `seed_demo` when `DJANGO_DEBUG=1`, `DEMO_SEED_ENABLED=1` and `DEMO_ENVIRONMENT=local` are set, and the database host is local. Image builds never connect to the database. To rerun manually use `docker compose exec -T api python manage.py seed_demo`; to disable demo data set `DEMO_SEED_ENABLED=0`. Production and staging must use `DJANGO_DEBUG=0` and keep the seed flag disabled.

## Regional team walkthrough

Login as `demo.federation@example.test` / `DemoOnly2026!`, switch to the federation role, open **Команды**, choose season, discipline and age group, then open the populated demo team. Inspect rating and eligibility context, add or remove an eligible athlete, move members with the arrows, and download the roster or draft order as PDF/DOCX. The generated draft is explicitly marked as unsigned and is not a legally issued order.

The **Утвердить состав** action finalizes a non-empty draft team and records the federation decision. Document downloads create an audit event with the selected document type and format. The seeded competition path includes four published protocols, fourteen applications, seven calculated ratings and current contribution provenance; repeated seeding leaves these counts unchanged.
