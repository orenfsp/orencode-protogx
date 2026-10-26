# Local demo accounts

Run `docker compose exec -T api python manage.py seed_demo` after the stack starts. The command works only when `DJANGO_DEBUG=1`, creates reserved fictional `example.test` identities, and can be rerun without duplicating users, roles, guardians, or consent records. It sets the password only when creating an account; reruns preserve any changed password. Do not run this command with real user data.

All new accounts use password `DemoOnly2026!` for the local demonstration:

- `demo.federation@example.test` — federation and athlete; use the sidebar to switch roles.
- `demo.athlete@example.test` — athlete.
- `demo.coach@example.test` — coach.
- `demo.judge@example.test` — judge.
- `demo.junior@example.test` — junior athlete with a fictional guardian record pending verification.

The seeded `demo_seed` consent records are synthetic test fixtures, not legally verified consent. The junior guardian remains pending verification. These accounts exercise Phase 1 sign-in and role selection; competition, results, and protocol demonstrations require the later domain workflow.
