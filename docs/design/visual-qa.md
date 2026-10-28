# Visual QA

## AC-11 accessibility continuation — 2026-10-28

The registry visual suite now runs axe-core with WCAG 2 A/AA, 2.1 AA and 2.2 AA tags before capturing each supported state. An initial 18-test run passed on the isolated Compose production frontend: correction/validation, coach/judge/organization details, and loading/empty/API-error/forbidden states at 1440, 768 and 390 px in both themes. Those responses are intercepted fictional fixtures. Automated scans do not establish full WCAG conformance or replace manual comparison.

The correction form now moves focus to its required reason, associates server feedback with that field, and supports Escape with focus restoration to the invoking button. The regression checks initial focus, Tab/Enter submission, Shift+Tab, the error association and Escape. These forms are inline regions, not modal dialogs; modal focus containment does not apply.

Acceptance coverage:

- Correction and validation: six viewport/theme combinations captured and scanned; keyboard regression covers the sequence above. A mobile dark screenshot was manually inspected for rail, controls, borders, focus and readability.
- Coach/judge/organization details: six combinations scanned and captured for each; complete new manual comparison is pending.
- Loading/empty/API-error/forbidden: six combinations scanned and captured for each; complete new manual comparison is pending.
- Creation, success, conflict, long tables and analytics: existing functional coverage remains; exhaustive keyboard-only journeys and manual comparison are not newly verified by this continuation.

The in-app browser inspection attempt timed out. A subsequent Computer Use inventory returned no apps or browsers and `Computer Use native pipe is unavailable` (Windows error 2). Manual interactive acceptance could not be completed through that tool. Screenshot review and automated browser execution remain distinct evidence. Keep the outstanding manual gates open until actually inspected; the unchanged design reference and a passing axe scan alone cannot close them.

The user subsequently limited this run to critical checks for a test demonstration. The 108-test PostgreSQL suite passed, as did production build, typecheck, ESLint, Ruff, migration checks, design contract and container OpenAPI validation. The live registry/history/analytics/XLSX scenario passed on a fresh isolated Compose database, including workbook parsing and totals 2/3. A complete final browser-suite run was not completed: earlier attempts exposed local origin/Python setup issues and reused-fixture state, and the final full run was stopped at the user's request. This is demonstration readiness evidence, not final AC-11 acceptance or hosted CI evidence for the new commit.

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

## Phase 2 completion review — 2026-10-27

`npm run visual:phase2` captured and refreshed 24 live screenshots: calendar, federation competition detail, athlete competition detail and athlete result history at 1440, 768 and 390 px, each in light and dark mode. The script waits for loaded competition and history records. Representative desktop, tablet and mobile images were visually inspected after the final production rebuild. The original HTML and its CSS hash remain unchanged; `python scripts/check_design_contract.py` passes.

The federation calendar and competition pages retain the indigo numbered sidebar and dotted navigation, document rail, orange actions, stamp statuses, bordered tables and forms. At 768 and 390 px the sidebar yields to the fixed bottom navigation; the header exposes the theme control. The competition workflow remains legible in dark mode on a narrow phone. The history table preserves all result fields with horizontal scrolling on narrow screens, so a full-page capture can show content beyond the 390 px viewport. The fixed bottom bar can appear partway through a full-page capture because its position follows the browser viewport. These are the same responsive behavior and capture limitation recorded for Phase 1. The reference has no equivalent live competition editing or result screens, so those forms extrapolate its borders, typography, spacing and color tokens without introducing another visual system.

The generated protocol PDF was also rendered and inspected: Cyrillic text, version marker, dynamic result columns, judge section, signature placeholders and source-verification warning are legible. The DOCX was parsed and checked for the same participant and column data; no native DOCX page renderer was available in this Windows environment.

## Frontend continuation — 2026-10-27

The homepage's upcoming-event card now uses the competition list, displays the nearest future published event, and distinguishes an empty calendar from an unavailable one. Calendar and athlete history screens distinguish loading, failure and empty results; history discards responses from a previous role view. These changes use existing styles and API contracts.

With the frontend development server running on `http://localhost:3301`, the PowerShell commands `$env:FSP_WEB_URL = 'http://localhost:3301'` and `npx.cmd playwright test tests/frontend-states.spec.ts --workers=1` passed 5 tests using intercepted API responses. The test captures the homepage card at 1440, 768 and 390 px in light and dark themes and checks that the card contents fit. The 1440 px light and 390 px dark captures were inspected: the card, link and surrounding reference-derived layout are legible. Captures are test output, not updated reference baselines. The tests do not exercise a live backend or replace the existing end-to-end and side-by-side visual checks.

The role-aware `/my-competitions` page reuses the shell, stamps and bordered tables for applications and judge assignments. `tests/my-competitions.spec.ts` captures it at 1440, 768 and 390 px in both themes with intercepted API responses; 1440 px light and 390 px dark were inspected. On narrow screens the table scrolls horizontally, with a visible hint and a keyboard-focusable scroll region. This check does not verify a live backend or constitute a new side-by-side reference comparison.

## Phase 3.1 ratings review — 2026-10-27

The `/ratings` page was rebuilt with the existing shell, numbered indigo navigation, document rail, bordered table, stamp status and responsive mobile layout. `tests/ratings.spec.ts` passed against the live Compose web/API services for both an empty state and an expandable published-result breakdown. The backend test `test_protocol_publication_recalculates_rating_from_its_snapshot` covers the live domain sequence from publication to rating, while `test_ratings_api_returns_breakdown_and_deterministic_placement` verifies the API DTO consumed by the page. The page build, typecheck and lint passed. A separate screenshot capture for the populated table was not required for the functional gate; the reference HTML remains unchanged.

## Phase 3.2 regional teams review — 2026-10-27

The `/teams` page reuses the numbered sidebar, document rail, orange actions, bordered tables, stamps, Rubik/Inter/JetBrains Mono tokens and mobile navigation. It adds no new global styles or changes to `fsp-reference.html`. The existing targeted Playwright test uses intercepted API data and checks page rendering; it does not verify manual selection or finalization. A dedicated side-by-side screenshot capture remains a follow-up visual review item.

## Phase 3.2 document and live workflow review — 2026-10-28

On an isolated PostgreSQL Compose project, the live `teams-live.spec.ts` scenario logged in, opened rating provenance, created a team, manually selected and reordered athletes, reloaded the persisted roster, finalized it and downloaded all four documents. The roster and draft-order PDFs and both DOCX files converted with LibreOffice were rendered using PDFium. Their single pages were inspected: Cyrillic names, ranks, team metadata, order and signature placeholders were visible without table clipping for this two-athlete sample. Longer rosters and names remain a separate pagination/overflow gate. The draft form is a demonstration and requires regulatory review against a primary source.

## Phase 3.2 stress review — 2026-10-28

Roster and draft-order PDF and DOCX were generated for 2, 15 and 50 fictional athletes with long Cyrillic names, short, long and missing organization names, and two different seeded sports ranks. All PDF pages and LibreOffice-rendered DOCX pages were visually inspected with PDFium; extracted text contained each athlete, both ranks and the relevant organization examples. The initial DOCX split rows across pages and omitted repeating headers; the exporter now prevents row splitting, repeats headers and adjusts column widths and spacing. PDF documents used 1, 2 and 6 pages respectively; converted DOCX used 1, 2 and 4. The draft form still requires primary-source regulatory review.
# Phase 3.3 registry and participation

On 2026-10-28, `FSP_WEB_URL=http://127.0.0.1:13002 node frontend/scripts/capture-registry-qa.mjs` captured both populated list screens at 1440/768/390 in light and dark themes on an isolated seeded stack. The 12 `screenshots/phase33-{registry,analytics}-{1440,768,390}-{light,dark}.png` files were inspected, alongside the corresponding existing reference captures. A first capture exposed full-page overflow from intrinsic select widths; the controls were constrained and the captures repeated with a document-width assertion. The rail, numbered headings, indigo/orange palette, desktop sidebar, mobile navigation and bordered tables remain visible. At 390px wide tables require horizontal scrolling inside their table container. The fixed bottom navigation appears in full-page screenshots at its viewport position. Charts use native progress indicators, an acknowledged difference from the reference.

These captures cover populated list/report states, not every history-edit form, empty/error state or keyboard-focus sequence; those remain to be visually checked before claiming full AC-11 acceptance. The reference HTML is unchanged.

### Registry correction forms — 2026-10-28

`frontend/tests/registry-visual.spec.ts` passed six viewport/theme combinations against the isolated Compose web service with intercepted fictional API responses. It captures `screenshots/phase33-registry-form-{1440,768,390}-{light,dark}.png`, checks document width and verifies keyboard focus on the correction reason. The 1440 px light and 390 px dark captures were inspected: the document rail, navigation, bordered controls and correction form are visible. This is an interface test with mocked responses, not evidence of backend permissions. The captures do not cover every registry, form, loading/error state, or a side-by-side comparison for every viewport; complete visual acceptance remains outstanding.

The continuation captured 18 additional coach, judge and organization detail/edit views and 24 loading, empty, error and denied states at 1440/768/390 in both themes, using intercepted fictional responses. Six specialist-view checks and six state checks passed; the specialist locator was corrected after an initial ambiguous-selector failure. Screenshots use the `phase33-registry-{coaches,judges,organizations,loading,empty,error,denied}-{width}-{theme}.png` pattern. The desktop light organization, tablet light coach, mobile dark judge/error and desktop light denied examples were inspected. The judge capture includes a current category, its dates and validity; the coach capture includes a confirmed relationship. The fixed mobile navigation can appear in the middle of a full-page capture; narrow tables scroll horizontally. Repeated organization section numbers were corrected and the desktop capture rechecked.

Six additional `phase33-registry-validation-{width}-{theme}.png` captures cover a rejected historical correction. The tests use Tab and Enter to reach the correction button and verify the error; the 390 px dark capture was inspected after moving feedback beside the form. These are intercepted interface tests, not live server authorization tests. The samples do not establish side-by-side comparison of every capture, all validation cases, or complete keyboard navigation, so full visual acceptance remains outstanding.


### 2026-10-28 ? ??????????? ??????????? ? ??????????? ?????????

?? ???????????????? ?????????? ?????????? ??????????????? ????????? ??????? ? grid-?????????. ? `app.css` ????????? ??????????? ?????? ???????, ??????? ??????? ?????? ? ??????, ??????????? ?????? ????????? ???? ? ???????????????? ?????????? ??????????? `.blk`. ????????? HTML ? ??????????? `globals.css` ?? ????????.

??????, ?????????????? ? ????????????? ???????? ?????????? ?? ????? `Toast` ????? portal ? `AppShell`: ??????????? ????? 6 ??????, ?????? ????????, ????? ??? ?????????/??????, ????????? ?????????? ??? ?????? ??????????. ??????????, ???????, ????????? ???????? ? ?????????? ?????? ???????? ?????????? ???????. DRF-?????? ??????????? ?? ?????, ???????? ? ????????? ????? ??? JSON-???????; ??????? ?????? ???????????? ??-??????.

? `frontend/tests/layout-notifications.spec.ts` ???????????? ?????? ????????? ????????????? ?????? API. ????? ???????? ????????? ???????? ??? 1440/768/390 px ? ????? ????? ??????; ?????? `application-cards.png` ??????????? ? `frontend/test-results/`. ??????????? desktop light, tablet light ? mobile dark: ??????? ?????? ????????, ???/?????/?????? ?? ????????????, ??????? ??? ???????????, ??????????????? ???????????? ???????? ???. ??????????? ????????? ????????????? ?????? ???????? ? ?? ???????? ?????.

????????? ?? `frontend`: `$env:FSP_WEB_URL='http://localhost:3100'; npm.cmd run test:e2e -- tests/layout-notifications.spec.ts --workers=1`, ?????????????? ???????? `npm.cmd run dev -- --port 3100`. ? ???? ?????? Next dev ????????????? `localhost`: ????????? ????? `127.0.0.1` ??????????? dev-???????. Google Fonts ?????????? ? ??????????? ?????; ?????? ?????????? fallback-??????. ???????? ?? mock API ?? ???????????? backend workflow.

???????? ????????: `npm.cmd run typecheck` ? exit 0; `npm.cmd run lint` ? exit 0; `npm.cmd run build` ? exit 0, 16 ???????; `python scripts/check_design_contract.py` ? PASS; `git diff --check` ? exit 0. ??????? ?????????? ??????: 13 passed (6 ????????? + 2 ??????????? + 5 ????????? ???????????); ??? ???????? mobile registry light/dark ??????? ?????????? ????????????? region-???? ? ??????????, ????? ??????????? ?????? ? 2 passed, ??????? axe ? ???????????? ?????. ????? ??????? 15 ????????? ??????. ????? ??????? ?????? ???????; ?????? E2E ?? ??????????: ????????? Compose-??????? ?? ????????, live-???????? ????????? ??? API ?? ??????. ?????? ????????? `p[role=alert]` ???????? ?? ????? alert ?????? `.toast-viewport`, ????? ????????? portal ? ?? ??????????? ????????? Next route announcer.


### 2026-10-28 ? role-dependent navigation

Desktop and mobile menus now share the same role visibility rules (`frontend/src/lib/navigation.ts`). Federation-only teams, registry and participation analytics are absent for athlete/coach/judge/guest. Public calendar, disciplines and ratings retain their existing access. Personal pages are restricted to their applicable assigned active roles; direct URLs do not mount unavailable page controls or start their requests. During a role transition protected content is removed until the response arrives, and an unavailable current route is replaced by the dashboard. Signed-in homepage hides register/login calls to action. Reference HTML/CSS unchanged.

Verification: `FSP_WEB_URL=http://localhost:3100`, `npm.cmd run test:e2e -- tests/role-navigation.spec.ts tests/role-selector.spec.ts --workers=2`: 14 passed (27.2s), mocked API. `npm.cmd run typecheck`, `npm.cmd run lint`, `python scripts/check_design_contract.py`: passed. This run verified DOM visibility and navigation behavior, not fresh screenshot comparisons or live backend authorization.


### 2026-10-28 ? ratings table presentation

Scoped `.ratings-table` styling removes native gray button backgrounds, aligns numeric columns right, emphasizes the rating total and keeps publication stamps on one line. Athlete buttons expose expansion with a chevron and `aria-controls`; the calculation uses a separate full-width table row. The table has a keyboard-focusable horizontal scroll region on narrow screens. Existing reference colors, borders, typography and stamps remain unchanged.

Typecheck/lint/build and design-contract check passed. Existing mocked published-result Playwright test passed; it now captures 1440/768/390 px in both themes and checks page overflow and nowrap statuses. Reviewed desktop dark and mobile light captures in `frontend/test-results/ratings-ratings-page-expands-a-published-result-breakdown/`. Desktop column spacing was then tightened to fit the available document column; mobile horizontal scrolling is intentional. Live backend was not exercised.
