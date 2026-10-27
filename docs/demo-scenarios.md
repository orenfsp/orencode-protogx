# Local demo accounts

Run `docker compose exec -T api python manage.py seed_demo` after the stack starts. The command works only when `DJANGO_DEBUG=1`, creates reserved fictional `example.test` identities, and can be rerun without duplicating users, roles, guardians, or consent records. It sets the password only when creating an account; reruns preserve any changed password. Do not run this command with real user data.

All new accounts use password `DemoOnly2026!` for the local demonstration:

- `demo.federation@example.test` — federation and athlete; use the sidebar to switch roles.
- `demo.athlete@example.test` — athlete.
- `demo.coach@example.test` — coach.
- `demo.judge@example.test` — judge.
- `demo.junior@example.test` — junior athlete with a fictional guardian record pending verification.

The seeded `demo_seed` consent records are synthetic test fixtures, not legally verified consent. The junior guardian remains pending verification and is intentionally ineligible for team selection. The command also creates three 2026 regional teams: one populated by a manual federation decision, one for another discipline, and one empty team. Re-running it preserves passwords, memberships and unchanged audit history.

## Automatic Compose startup

Copy `.env.example` to `.env` and run `docker compose up --build`. The API waits for PostgreSQL health, applies migrations, then runs `seed_demo` when both `DJANGO_DEBUG=1` and `DEMO_SEED_ENABLED=1` are set. Image builds never connect to the database. To rerun manually use `docker compose exec -T api python manage.py seed_demo`; to disable demo data set `DEMO_SEED_ENABLED=0`. Production and staging must use `DJANGO_DEBUG=0` and keep the seed flag disabled.

## Regional team walkthrough

Login as `demo.federation@example.test` / `DemoOnly2026!`, switch to the federation role, open **Команды**, choose season, discipline and age group, then open the populated demo team. Inspect rating and eligibility context, add or remove an eligible athlete, move members with the arrows, and download the roster or draft order as PDF/DOCX. The generated draft is explicitly marked as unsigned and is not a legally issued order.
