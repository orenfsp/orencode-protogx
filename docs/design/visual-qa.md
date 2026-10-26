# Visual QA

Reference: `fsp-reference.html` (SHA-256 `2362C4D1AEC5D54FA075215D6FDF986416D23D8402FBF33342D29671C5D043A2`). It is immutable.

Phase 1 maps the reference variables to `frontend/src/app/globals.css`, the numbered indigo sidebar and role selector to `AppShell`, the document rail to `.main::before`, and the fixed mobile bottom navigation to `.mobtab`. Rubik, Inter, and JetBrains Mono are loaded with the same font weights. The light/dark token values and 900px/520px breakpoints come from the reference CSS.

`python scripts/check_design_contract.py` passes: it checks the immutable HTML hash and the extracted CSS text. This confirms the token source but does not establish screenshot fidelity. Mocked hash and CSS mismatches both returned failure during validation.

## Executed screenshot review

`cd frontend && npm run visual:qa` captured the reference and running Compose homepage at 1440×900, 768×900, and 390×844 in light and dark themes. The 12 images are in `docs/design/screenshots/`, named `reference-*` and `site-*`. The script waits for the six-discipline table and fonts, then verifies the rendered body background in each theme before capture.

- At 1440 px, both use the 268 px indigo sidebar, orange numbered dotted links, a 48 px dotted document rail, Rubik hero, rotated outlined card, and bordered content. The Next.js shell has four live navigation links rather than the reference's seven static federation links because the remaining modules do not exist yet.
- At 768 and 390 px, both hide the sidebar at the 900 px breakpoint, retain the narrower document rail, and show the four-item fixed bottom navigation. The mobile hero and cards fit the viewport without clipping. The Next.js table is horizontally scrollable; the reference hides a table column at this breakpoint.
- Light and dark palette values, border treatments, and stamp headings visibly match. The live page uses real catalog rows and a truthful empty-calendar card, while the reference contains fictitious KPI counts and a dated competition card. These content differences change section heights and CTA wrapping. The reference's mobile CTA wraps to two rows at 390 px; the current shorter live labels fit on one row.

AC-18 remains `partial`: the homepage shell and table were visually reviewed in six combinations, but registration form/detail screens, role-specific dashboards, status states, and any future competition UI still need side-by-side review. The theme switcher lives in the hidden desktop sidebar, so mobile users cannot currently toggle theme from the mobile navigation; this needs an accessible mobile control. Do not interpret screenshot similarity as completion of the missing workflows.

## Phase 1 completion review — 2026-10-27

The earlier gap above was resolved. `npm run visual:qa` now captures six reference and six live homepage images plus 48 live images for calendar, login, registration, privacy and four role dashboards at 1440, 768 and 390 px in both themes. The capture checks fonts, body palette, loaded dashboard metrics and visible mobile navigation. Representative images were inspected at desktop and mobile sizes; the numbered indigo sidebar, dotted links and document rail, orange emphasis, Rubik/Inter/JetBrains Mono, bordered cards and tables, and stamp headings remain consistent with the immutable reference. The public calendar still correctly says no events exist. The role screens show real account/catalog counts and state that competition workflows are pending.

The mobile header now has an accessible light/dark control and a role selector for multi-role accounts. Playwright verifies theme persistence after reload, navigation, all four dashboard loads, and desktop/mobile role switching. The four-item fixed bottom navigation is retained. Full-page screenshots can show that fixed bar partway through a tall page because it is anchored to the viewport during capture. Small content and spacing differences from the reference follow the live data and added accessible controls; no design token or reference HTML was changed. New Phase 2 screens must receive the same viewport/theme review.
