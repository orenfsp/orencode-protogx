# OrenKod 2026 — FSP Case Analysis and Development Master Prompt

> **Purpose of this file:** an analysis of the case “Unified Digital Platform of the Sports Programming Federation of the Orenburg Region” and a ready-to-use technical specification/prompt for an AI development agent or orchestrator.  
> **Preferred stack:** **Django + Django REST Framework** (backend), **Next.js + TypeScript** (frontend), **PostgreSQL** (database).  
> **MANDATORY visual source of truth:** `docs/design/fsp-reference.html` — unmodified copy of the user-supplied `ФСП-итог — копия.html`. The AI must closely reproduce this design in Next.js, not generate a new visual concept.  
> **Requirements source:** 11-page PDF “КЕЙС_ОренКод_2026_Цифровая_платформа_ФСП”.  
> **External protocol example provided by the customer:** [Appendix No. 5 — Recommended Programming Competition Protocol Template](https://sudact.ru/law/pravila-vida-sporta-sportivnoe-programmirovanie-utv-prikazom/prilozhenie-n-5/rekomenduemyi-obrazets-protokola-po-programmirovaniiu/).

**Note on the protocol source:** The link was provided by the user. The contents of that webpage were not verified online when preparing the original document. Therefore, the fields listed below constitute a *proposed implementation structure*, not a verbatim reproduction of Appendix No. 5. Before issuing a document for official use, verify the form and the current regulatory requirements against the primary source.

---

# Part I. Case Analysis

## 1. Problem Statement

The customer is the regional branch of the Sports Programming Federation (FSP) in the Orenburg Region. Currently, information about athletes, coaches, judges, organizations, and competition results is scattered across spreadsheets and correspondence. A unified system is needed to connect **profiles → competitions → applications → results → protocols → sports ranks → ratings → regional team → reports**.

**Additional user-defined implementation constraint:** the supplied HTML design is an authoritative visual reference for the frontend. The implementation must reproduce its distinctive appearance across pages and roles while replacing static mock content with real working data. The reference is not a substitute for the functional requirements listed below.

**Core product value:** the federation enters data once and reuses it throughout its other workflows. For instance, a competition result simultaneously feeds an athlete's performance history, the competition protocol, the ranking, and the evidence used to evaluate eligibility for a sports rank.

## 2. Mandatory Functional Modules

| No. | Module | What must work |
|---|---|---|
| 1 | Responsive frontend | Public pages, dashboards, FSP-inspired interface for desktops/tablets/smartphones |
| 2 | Backend and content management | API, business logic, reference catalogs, administration |
| 3 | Roles and dashboards | Federation, athlete, coach, judge; multiple roles for one user; switching without logging in again |
| 4 | Competitions | Calendar, regulations, application submission and moderation, judging panel, result entry, protocols, performance history |
| 5 | Sports ranks and judge categories | Applications, review, assignment/confirmation, validity periods, notifications through at least one external channel |
| 6 | Registry and participation trends | Athletes, coaches, judges, organizations; participation report covering **at least 2 years**, `.xlsx` export |
| 7 | Ratings and regional team | Points per discipline and season, transparent formula, filters, manual team selection, draft order |
| 8 | Documents | Competition protocol, regional team list and draft order, athlete participation report, participation-count report; `.docx`, `.pdf`, or `.xlsx` as appropriate |

The case description additionally requires an audit log, consent to personal-data processing, deadline tracking, official competition-calendar plans, coach–athlete links, sports disciplines, and age groups. These are not optional enhancements: they are conditions for implementing the main workflows.

### Six disciplines supported from day one

1. Algorithmic programming.
2. Product programming.
3. Information-security systems programming.
4. Artificial-intelligence systems programming.
5. Robotics programming.
6. Unmanned aerial systems programming.

**Architectural implication:** disciplines must be modeled as a reference catalog, rather than as scattered `if/else` statements. Disciplines may have different scoring methods, result fields, ranking criteria, competition stages, judging metadata, and final protocol formats.

## 3. User Roles and Core Workflows

| Role | Key capabilities |
|---|---|
| **Federation** | Create competitions, moderate applications, maintain registries, assign judges, enter results, publish protocols, review sports-rank/judge-category applications, generate ratings, regional teams, and reports |
| **Athlete** | Manage profile and consent, browse age-eligible competitions, apply, track results, sports rank and documents; request a sports rank independently if not linked to a coach |
| **Coach** | Request a discipline-specific athlete link that the athlete must confirm; register linked athletes, view results and sports-rank deadlines, submit sports-rank applications |
| **Judge** | View assignments, history of judged competitions, category and expiration date, and the status of category assignment/confirmation applications |

**Critical feature:** a user may simultaneously be an athlete, coach, and judge. Switching the active dashboard must not grant new privileges: the backend checks both the assigned role and permission to access the specific object.

## 4. Most Important Business Rules

### 4.1. Competitions and Results

- A competition has a discipline, level/status, type (championship, junior championship, cup, etc.), age groups, dates, location, format (in-person/online/hybrid), regulations, and registration deadline.
- Hybrid events may consist of stages in different formats, for example online development followed by an in-person project defense.
- The competition links to an official calendar plan: the Russian Ministry of Sport's Unified Calendar Plan (EKP) or the regional calendar; its entry number is retained.
- The final protocol automatically includes **all participants with approved applications**, not just winners. A no-show or missing result must have its own status without fabricating scores or placements.
- Once published, results appear in athletes' performance histories. Republishing or correcting a protocol must leave an audit trail.

### 4.2. Sports Ranks and Judge Categories

- A sports-rank application refers to **a specific competition and a specific result**.
- The federation reviews the application and records the decision, assignment date, official order, and validity period.
- Automated highlighting of potentially qualifying results under the Unified All-Russian Sports Classification (EVSK) is **a preliminary recommendation**, not an automatic legal assignment of a rank.
- Official submission through Gosuslugi is handled **outside the platform**; do not invent an integration.
- Judge categories are managed separately from athletes' sports ranks.

### 4.3. Athlete Ratings

The following are the initial recommended points from the case; the federation may adjust them:

| Competition level | 1st place | 2nd place | 3rd place |
|---|---:|---:|---:|
| Russian Championship | 100 | 80 | 60 |
| Russian Junior Championship | 80 | 60 | 40 |
| Interregional / district | 60 | 45 | 30 |
| Regional | 40 | 30 | 20 |

Formula per season and discipline:

```text
base_score = sum of the athlete's points across all eligible competitions in the season
prize_count = number of competitions in the season where the athlete placed 1st–3rd
stability_coefficient = 1.2 if prize_count >= 2, otherwise 1.0
rating_score = base_score * stability_coefficient
```

- Athletes with an active disqualification or suspension **must be excluded** from the ratings.
- The ratings page must provide filters by age group, minimum sports rank, discipline, and season, plus an itemized breakdown of every awarded point.
- The original case specifies points **only for places 1–3**. Do not invent official values for other placements: they earn no points in the default mode unless the federation configures an expanded points table.
- Forming a regional team is a **manual federation selection** from eligible athletes, not automatic assignment according to ratings.

### 4.4. Participation Statistics

Reporting trends across two or more years requires dates when an athlete began participating and, where applicable, ceased participation or changed organization or discipline. Storing only today's user count cannot yield correct historical statistics.

Dimensions: year, organization, discipline, age group, and municipality. Do not double-count a person involved in several disciplines in the overall unique-athlete total; clearly label any discipline-specific counts in which that person appears in multiple breakdowns.

### 4.5. Security and Personal Data

- Registration requires consent to personal-data processing; minors require consent from a legal guardian.
- The demonstration environment must use **fictional personal data only**.
- Record who changed what and when for applications, results, sports ranks, status transitions, and other material actions.
- Do not disclose minors' information, documents, or personal identifiers to unauthorized users.

## 5. Optional Features and Prioritization

The PDF lists D1–D12: regional FSP ID (OIDC), external integrations, training groups and attendance logs, sports-training standards and certification, appeals, regional sport-development indicators, athlete progression and glossary, Governor's awards, a Ministry of Sport dashboard, QR-verifiable participation certificates, a newcomer navigator, and judging documents. Teams may also propose their own features.

**Recommendation for a 48-hour hackathon:**

| Priority | Enhancement | Rationale |
|---|---|---|
| P2 — first after mandatory features | **D10. Participation certificate with QR code** | Visually compelling end-to-end demonstration with a public authenticity check |
| P2 — second | **D11. Newcomer navigator** | Reuses the existing calendar and catalogs; improves the public-facing website |
| P2 — third | **D12. Judging documents** | Reuses judge assignments and the document-generation engine |
| P2 — if time permits | **D6. Regional development indicators** | Reuses participation reporting, the calendar, and competition protocols |
| Later | D1, D2, D3, D4, D5, D7, D8, D9 | More complex rules, integrations, or distinct workflows; must not jeopardize the core MVP |

This is **a proposed implementation priority**, not a customer requirement to build every optional feature.

## 6. Hackathon Checkpoints

| Hour | Case expectation | Suggested demonstration |
|---|---|---|
| **22 — Checkpoint 1** | Idea, differentiation, MVP, optional scenarios, tech stack | Architecture diagram, data model, screen map, API contract, working dashboard shells, first test flow |
| **42 — Checkpoint 2** | 1–2 end-to-end scenarios, 2–3-minute video or running demo | Competition → application → moderation → result → protocol → athlete history; optionally rating → regional team |
| **48 — Code freeze and Checkpoint 3** | Repository, README, demo data, API/model documentation, feature list and verification instructions | Reproducible startup, demo accounts, automated tests, export links, acceptance matrix |

---

# Part II. Ready-to-Use Master Prompt for an AI Development Agent / Orchestrator

> The following section is self-contained and can be given to Codex or another development agent in its entirety. Every requirement that something “must work” refers to **real code and functioning workflows**, not merely a design, stub, or description of a solution.

## 1. Your Role and Main Objective

You are the **lead full-stack architect, technical lead, and AI developer**. Your task is to build a functioning unified digital platform for the Sports Programming Federation in the Orenburg Region, based on the OrenKod 2026 case requirements. The application must be suitable both for a live demonstration to the jury and for subsequent development.

Build **a monorepo with Django REST Framework as the backend and Next.js as the frontend**. The system must be responsive, provide clear dashboards for the federation, athletes, coaches, and judges, support all six disciplines, and integrate data into complete end-to-end business workflows.

**Main implementation rules:**

1. Do not replace Django with Flask/FastAPI or Next.js with Django templates or a separate React/Vite frontend.
2. Implement actual database and API operations; do not present a static prototype as a completed feature.
3. Never sacrifice mandatory case requirements for complex optional functionality.
4. Separate domain logic from presentation. Rating formulas, age eligibility, protocols, and access controls must be enforced server-side.
5. Do not invent “official” legal requirements or document forms where they are not supplied. Make rules configurable and flag the need for regulatory verification.
6. If a repository already exists, inspect it first. Preserve existing data and working functionality; do not delete or overwrite others' changes unnecessarily.
7. Maintain honest status labels: `implemented`, `partial`, `not_implemented`, `blocked`.
8. Run migrations, tests, and frontend builds regularly. Do not declare a task finished while startup errors remain.

### 1.1. NON-NEGOTIABLE REQUIREMENT — EXACT DESIGN DIRECTION FROM USER-SUPPLIED HTML

**DESIGN CONTRACT — MUST FOLLOW. THIS IS A RELEASE-BLOCKING REQUIREMENT.**

The project owner has already created the visual language and sample page. **Do not invent an alternative design.** The single authoritative visual reference is the attached HTML file:

- Original filename: **`ФСП-итог — копия.html`**.
- Required repository copy: **`docs/design/fsp-reference.html`**. Copy the original HTML and embedded CSS **without modifying it**. Include it in version control; it is the permanent design reference for every developer and AI agent.
- If the reference file is absent, locate the supplied attachment and copy it to that exact path **before building UI screens**. Do not substitute a generic FSP-themed website or shadcn default themes. If the asset has not actually been supplied, report the missing dependency rather than claim design compliance.

**Priority and interpretation:** treat this file as a visual specification, **not** an optional mockup or loose inspiration. For styles and layouts, the priority is (1) this HTML design, (2) a shared implementation design-token/component library derived from it, (3) framework defaults only when they do not conflict. Functional requirements, privacy, keyboard accessibility, content legibility, and responsiveness still apply. If a new screen is not explicitly drawn, **extrapolate its appearance from this visual system**; do not replace the visual system. Any intentional deviation must be documented with a concrete functional or accessibility justification, and approved by the project owner when possible.

#### A. Required design tokens and visual identity

Extract and implement the reference tokens from its actual CSS rather than inventing equivalents:

| Element | Reference specification |
|---|---|
| Primary brand color | Indigo **`#221F73`** for the light-theme sidebar, accents, and outlines |
| Signal/action color | Orange **`#FF9900`** for calls to action, active navigation accents, important status marks, and emphasis |
| Light-theme surfaces/text | Paper **`#FFFFFF`**, main text **`#1B1C21`**, secondary text **`#5C5C66`**, lightly tinted accent surfaces **`#EEEDF9`** |
| Dark-theme identity | Preserve the reference's distinct dark variables (for example page `#1C1B45`, sidebar `#0B0A24`, accent `#A6A3FF`) and the orange signal color; do not simply invert the light screen |
| Typography | **Rubik** for titles/section headings/branding; **Inter** for standard interface text; **JetBrains Mono** for counters, numbered sections, tabular metrics and identifiers; preserve visual weights, tight heading spacing, and hierarchy |
| Shape language | Strong rectangular geometry, sharp or very slightly rounded edges, **visible outlines**, dotted separators, underlined text fields, double-bordered and slightly rotated “stamp” labels; do not adopt pill-shaped controls or fully rounded cards |
| Interactions | Primary orange button, indigo secondary/inverted button, 3px offset hard shadow, visible keyboard focus; status treatment with the same stamped styles |
| Main chromatic palette | Indigo + orange. Neutral and semantic shades may use the reference's token values; **no arbitrary new accent palette**, gradients, glassmorphism, or glossy dashboard patterns |

This table summarizes, but **never supersedes, the attached HTML/CSS**. The original stylesheet is the definitive source for exact values, spacing, borders, dark-mode colors, and component treatments.

#### B. Reproduce the reference composition

- **Desktop shell:** approximately **268px persistent indigo left sidebar**, numbered navigation entries with dotted dividers and orange highlights; role/account selector and theme toggle near the bottom. Reproduce its logo lockup, alignment, dense-but-readable hierarchy, and active-item indicator.
- **Main area:** preserve the characteristic **left document-binding rail with repeated holes and a thin vertical line**, the main gutters, and the spacious paper/document aesthetic. The rail is a defining brand motif, **not** an optional decoration.
- **Hero/top area:** use the reference's large stacked Rubik headline, orange underline treatment, short introduction, orange/outlined action buttons, and slightly rotated “upcoming competition” callout with an offset shadow when this content is appropriate (especially on the public landing page). The supplied slogan **“Пиши код. Побеждай. В Оренбуржье.”** defines the landing-page heading treatment.
- **Section layout:** reproduce the left-numbered section headers and content on the right (the reference uses a **150px section-label column** with a **32px** gap on desktop). Keep prominent horizontal rules and a restrained, information-dense editorial style.
- **Dashboard and tables:** recreate four-across outlined KPI cells where space allows, JetBrains Mono figures, the underlined selected tabs, rigid bordered data grids, selected-row accent strip, and outlined square pagination.
- **Forms and statuses:** replicate the reference's underline-only inputs, focus/error states, square checkboxes, orange/indigo stamp badges, simple bordered alerts, and other shown UI states. New dialogs, calendars, select menus, search/filter controls, uploads, and charts must use the **same tokens and shape language**.
- **Responsive layout:** preserve the actual design's transition to **mobile navigation at widths ≤900px**, hide the desktop sidebar in favor of the **fixed bottom navigation**, narrow the document rail, stack section headers/content, and adjust statistics/cards for smaller screens; the **≤520px** compact layout must remain usable. For tables containing required business information, prefer horizontal scrolling or expandable row details instead of permanently hiding essential fields merely to mimic a decorative demo.
- **Theme:** both **light and dark versions** must reflect the HTML's token definitions. The Next.js implementation may use client state and persisted preference to implement the switch, but it must visually match both supplied themes. Do not switch to shadcn's unrelated default dark palette.

#### C. Transfer the design to a working Next.js application

1. **First inspect the entire HTML and its embedded CSS**, including selectors, breakpoints, state variants, and responsive rules. Identify reusable primitives and create a single design-token source (`globals.css` custom properties, Tailwind theme/configuration, or an equivalent centralized stylesheet) before implementing independent screens.
2. Create a reusable **`AppShell`** and design-faithful components for `Sidebar`, `MobileTabBar`, `SectionHeading`, `MetricTile`, `DataTable`, `Tabs`, `Button`, `StatusStamp`, `Input`, `Alert`, `UpcomingCompetition`, `Pagination`, and `ThemeToggle`; adapt names if necessary, but not their styling contract.
3. Apply these components **consistently to all public pages, federation/athlete/coach/judge dashboards, auth screens, forms, lists, document workflows, and new routes**. Preserve the design's visual family even when a page has no direct counterpart in the HTML.
4. Do not paste the original static HTML as the finished application, embed it as an iframe, or leave its mock buttons inert. Rebuild it using **Next.js + TypeScript components with real Django API integration**. Text, statistics, competition dates, statuses, tables and profile identities shown in the reference are **illustrative placeholders**, not live data that should be hard-coded.
5. **Tailwind, shadcn/ui, and Lucide are implementation tools, not design authorities**. Use unstyled primitives and override every default style that deviates from the reference. Avoid introducing a second design system, conflicting component libraries, default shadcn rounded-card layouts, or one-off colors in feature branches.
6. Prioritize an accurate shared shell and the reference page's main components **before** expanding to all role-specific routes. Use responsive accessible behavior for keyboard focus, color contrast, forms, statuses and navigation.
7. In team development, **every frontend contributor must read `docs/design/fsp-reference.html` before coding**. The orchestrator owns the shared tokens and core components; no agent may restyle the application, replace its typography/colors, or introduce independent UI patterns without explicit approval. Review frontend pull requests for design fidelity as well as functional correctness.

#### D. Mandatory visual verification and definition of done

- Add **`docs/design/visual-qa.md`** documenting the reference-to-Next.js mapping (tokens, components, routes, differences) and any justified deviations.
- Use Playwright (or the project's screenshot tooling) to render **the supplied original HTML** and **the implemented screens** at representative widths, including **1440px desktop, 768px tablet, and 390px mobile**, in **both light and dark themes**. Capture and compare screenshots side-by-side; review at least the landing/dashboard shell, tables, typical forms, navigation, and status components. Where the original has no corresponding screen, compare the reusable design components and shell.
- Fix unapproved discrepancies in sidebar width, rail, typography, palette, spacing, border geometry, component states, footer/mobile navigation, and dark mode before marking frontend work complete. Dynamic data/content can differ; **the visual language and matching screen structure must not**.
- Test at least keyboard navigation/focus, mobile menu navigation, usable overflow of tabular data, theme switching, and real API-backed button flows. Screenshot parity alone does not make a page functional.
- Add **design fidelity** as an explicit acceptance gate: a feature whose workflow functions but whose UI ignores the reference is **`partial`**, not `implemented`. Do not claim fidelity without checking rendered output against the HTML.

**Prohibited shortcuts:** generic “inspired by the reference” redesigns; default Tailwind/shadcn aesthetics; arbitrary gradients, colors, and oversized rounded cards; removal of the document rail; replacing the numbered sidebar with a generic header on desktop; omitting the reference's mobile bottom navigation; ignoring dark mode; or claiming the static HTML is a completed functional frontend.

## 2. Approved Technology Stack

| Layer | Technologies | Purpose |
|---|---|---|
| Backend | **Python 3.12+, Django 5.x, Django REST Framework** | API, models, business logic, access control, administration |
| Database | **PostgreSQL** | Primary persistent storage |
| API contract | `drf-spectacular`, OpenAPI 3 | Schema documentation and team coordination |
| Filtering | `django-filter` | Registries, calendar, ratings |
| Frontend | **Next.js (App Router), React, TypeScript** | Public website and role-based dashboards |
| UI | Tailwind CSS, shadcn/ui, Lucide **styled strictly to match `docs/design/fsp-reference.html`** | Reference-faithful responsive pages, tables, forms, dialogs; no default theme substitution |
| Data fetching | TanStack Query, typed API client | Requests, caching, loading/error state management |
| Forms | React Hook Form + Zod | Client-side validation; server-side validation is mandatory |
| Charts | Recharts | Participation trends, dashboards |
| Documents | `python-docx`, `openpyxl`, PDF renderer with Cyrillic support | DOCX/XLSX/PDF |
| Backend tests | `pytest`, `pytest-django` | Unit/API tests |
| Frontend tests | Playwright, optionally Vitest | E2E and component tests |
| Deployment | Docker Compose, `.env.example` | Reproducible local startup |

**Authentication:** Prefer **Django sessions + CSRF**, with a shared origin through a Next.js rewrite/reverse proxy mapping `/api/` to Django. Do not store access tokens in `localStorage`. If frontend and backend use separate domains, explicitly configure cookies, CSRF, proxy headers, and CORS without allowing all origins. Django admin may manage internal catalogs, but it **must not replace** the Next.js federation dashboard.

**Background jobs:** For the 48-hour MVP, a scheduled Django management command for deadline checks is acceptable. Add Celery/Redis only if truly necessary; do not make them prerequisites for running the platform.

## 3. Proposed Repository Layout

```text
fsp-platform/
├── backend/
│   ├── config/                  # settings, urls, ASGI/WSGI
│   ├── apps/
│   │   ├── accounts/           # users, roles, consent
│   │   ├── catalogs/           # disciplines, regions, age groups
│   │   ├── registry/           # athletes, coaches, judges, organizations
│   │   ├── competitions/       # calendar, stages, regulations, applications
│   │   ├── judging/            # judge assignments and categories
│   │   ├── results/            # metrics, rankings, result publication
│   │   ├── qualifications/     # sports ranks, applications, EVSK
│   │   ├── ratings/            # ratings by season and discipline
│   │   ├── teams/              # regional team
│   │   ├── documents/          # template configuration and export
│   │   ├── analytics/          # participation and reports
│   │   ├── notifications/      # notifications and deadlines
│   │   └── audit/              # important change history
│   ├── tests/
│   ├── requirements.txt (or pyproject.toml)
│   └── manage.py
├── frontend/
│   ├── src/app/
│   ├── src/components/
│   ├── src/features/
│   ├── src/lib/api/
│   └── package.json
├── docs/
│   ├── architecture.md
│   ├── data-model.md
│   ├── api-contract.md
│   ├── protocol-templates.md
│   ├── demo-scenarios.md
│   ├── design/
│   │   ├── fsp-reference.html    # exact original user-designed visual reference
│   │   └── visual-qa.md           # design parity checklist/screenshots
│   └── acceptance-matrix.md
├── docker-compose.yml
├── .env.example
└── README.md
```

This is a recommended logical organization. Small Django apps may be combined if the interfaces remain clear and doing so accelerates delivery of a working MVP. Do not build a microservices architecture.

## 4. Domain Model and Relationships

Design Django models, migrations, serializers, and APIs. At minimum, implement the following entities (you may improve names without removing functionality):

| Entity | Essential fields / relationships |
|---|---|
| `User` | Login, email, full name, date of birth where needed for profile, active status |
| `UserRole` | User, role (`federation`, `athlete`, `coach`, `judge`), status/permissions |
| `PersonalDataConsent` | Data subject, consent type, text version, timestamp, confirmation method, guardian where necessary |
| `Guardian` | Minor's legal guardian, relationship, consent confirmation status, restricted access |
| `Discipline` | Code, exact name, active status, field/rule configuration |
| `Organization` | Name, type, municipality, contacts, status |
| `AthleteProfile` | User, municipality, organization or “independent/unaffiliated,” participation start year, sports rank |
| `AthleteDiscipline` | Athlete, discipline, participation dates, training stage, change history |
| `CoachProfile` | User, organization, relevant disciplines |
| `CoachAthleteLink` | Coach, athlete, discipline, link status, request/confirmation/termination dates |
| `JudgeProfile` | User, judge details |
| `JudgeCategoryHistory` | Category, official order, assignment date, validity period, confirmation |
| `Competition` | Name, discipline, level/status, type, dates, location, format, regulations, deadlines, season |
| `CompetitionStage` | Stage, order, mode (in-person/online), dates, additional settings |
| `CompetitionCalendarEntry` | Calendar type (EKP/regional), calendar entry number, year |
| `AgeGroup` | Name, limits/rules version, eligibility reference date, competition relationship |
| `CompetitionApplication` | Competition, athlete, applicant, status, rejection reason, submission/decision time |
| `JudgeAssignment` | Judge, competition, judging position |
| `MetricDefinition` | Discipline, metric name, data type, unit, ordering/scoring rules |
| `CompetitionResult` | Competition, approved application, placement if applicable, points, status, publication date |
| `ResultMetric` | Result, metric, validated typed value |
| `SportRankHistory` | Rank, athlete, supporting evidence, official order, assignment/expiry dates |
| `RankApplication` | Athlete, initiator, competition, result, requested rank, decision and status |
| `JudgeCategoryApplication` | Judge, request type, status, decision, dates, documents |
| `QualificationRule` | Configurable EVSK criteria, discipline, version, effective dates, source link |
| `RatingRule` | Competition level, placement, points, season/version, stability coefficient |
| `Disqualification` | Athlete, start/end dates, status, grounds (restricted access) |
| `RegionalTeam` / `TeamMember` | Season, discipline, age group, manually selected roster, decision, draft order |
| `DocumentTemplate` | Document type, discipline/competition type, version, field schema, status, template file |
| `GeneratedDocument` | Type, data source, template version, file path, date, creator |
| `Notification` | Recipient, event, channel, delivery, read status, error |
| `AuditEvent` | Actor, active role, entity, action, timestamp, sanitized change details |

**Model requirements:**

- Store separate **histories** of coach–athlete relationships, sports ranks, and judge categories; new records must not erase past ones.
- Allow an athlete to have several coaches **across different disciplines**, and verify the relevant relationship for each workflow.
- Do not use a single string `role` field as the sole permission source. Implement many-to-many role assignments and active-role checks.
- Do not force every discipline into a single “score + place” result format: scoring metrics differ.
- Every manually entered result must reference an approved application.
- Prevent duplicate applications by the same athlete for the same competition, according to the event rules.
- When catalogs or coefficients change, preserve the rule version used for already published results and documents.
- Store start/end dates for time-bound relationships to reconstruct participation counts and valid categories at historical points in time.

## 5. Backend API

Build a REST API under `/api/v1/`, with the schema at `/api/schema/` and interactive documentation at `/api/docs/`. The following is **a proposed contract**, not one imposed by the source PDF. If endpoints change, synchronize the frontend and OpenAPI specification.

| HTTP | Endpoint | Purpose |
|---|---|---|
| `POST` | `/auth/register/` | Register and record all required consents |
| `POST` | `/auth/login/` | Sign in |
| `POST` | `/auth/logout/` | Sign out |
| `GET` | `/auth/me/` | Profile, assigned roles, active role |
| `POST` | `/auth/active-role/` | Select dashboard and verify that the role is assigned |
| `GET` | `/disciplines/` | Catalog of all six disciplines |
| `GET` | `/organizations/` | Organization catalog |
| `GET` | `/athletes/` | Registry with role-aware personal-data filtering |
| `GET` | `/coaches/` | Coach registry |
| `GET` | `/judges/` | Judge registry |
| `POST` | `/coach-links/` | Request a discipline-specific link to an athlete |
| `POST` | `/coach-links/{id}/confirm/` | Athlete confirms the relationship |
| `GET/POST` | `/competitions/` | Calendar and competition creation |
| `GET/PATCH` | `/competitions/{id}/` | Competition detail and management |
| `POST` | `/competitions/{id}/publish/` | Publish competition details/regulations |
| `GET/POST` | `/competitions/{id}/applications/` | List/create applications, subject to permissions |
| `POST` | `/applications/{id}/review/` | Approve/reject with a reason |
| `GET/POST` | `/competitions/{id}/judges/` | Judging panel and assignments |
| `GET/POST` | `/competitions/{id}/results/` | View/enter results |
| `POST` | `/competitions/{id}/protocol/preview/` | Preview the protocol |
| `POST` | `/competitions/{id}/protocol/publish/` | Publish a version of the final protocol |
| `GET` | `/competitions/{id}/protocol/download/?format=pdf` | Template-based export |
| `GET/POST` | `/rank-applications/` | Sports-rank applications |
| `POST` | `/rank-applications/{id}/review/` | Federation decision |
| `GET/POST` | `/judge-category-applications/` | Judge-category applications |
| `POST` | `/judge-category-applications/{id}/review/` | Federation decision |
| `GET` | `/ratings/?season=...&discipline=...` | Detailed ratings and filters |
| `GET/POST` | `/teams/` | Regional teams by discipline and season |
| `POST` | `/teams/{id}/members/` | Manually edit team membership |
| `GET` | `/teams/{id}/documents/` | Team list and draft order |
| `GET` | `/analytics/participation/?from_year=...&to_year=...` | Participation counts and breakdowns over a period |
| `GET` | `/analytics/participation/export/` | XLSX export |
| `GET` | `/athletes/me/history/` | Performance history |
| `GET` | `/notifications/` | Personal notifications |
| `GET` | `/federation/dashboard/` | Federation metrics and action items |
| `GET` | `/audit/` | Audit log, authorized users only |
| `GET` | `/document-templates/` | View available templates |
| `POST/PATCH` | `/document-templates/` | Federation-managed template configuration |

**API requirements:** pagination, filtering, search, ordering, validated DTOs, predictable `400/401/403/404/409` responses, object-level permissions, proper transactions, and duplicate-action protection. All critical operations must be atomic.

## 6. Required End-to-End Workflows

### Scenario A — From Competition Creation to Athlete History

```text
Federation creates a competition
  → specifies discipline, age groups, regulations, and deadline
  → publishes the event and opens registration
  → athlete/coach submits an application
  → federation approves or rejects the application
  → federation assigns judges
  → federation enters results for approved participants
  → system computes/validates rankings according to discipline configuration
  → system generates a protocol preview
  → federation confirms and publishes the protocol
  → result appears in the athlete's history and rating calculation
  → system sends notifications
```

Rules:
- Do not allow applications after the deadline unless the federation performs an explicitly permitted override action.
- Coaches may register only athletes with an active, confirmed link for the applicable discipline.
- Age eligibility is determined by the configured age-group rules and the reference date specified by the regulations; never use arbitrarily chosen age boundaries.
- The protocol must use approved applications and show all participants, including those without a valid result.
- A participant must not receive two different placements unless there is an explicitly specified tie-handling rule.
- Changing a published protocol creates a separate new version with a reason and an audit record.

### Scenario B — Athlete Sports Rank

```text
Competition result is published
  → system flags possible EVSK eligibility if qualification rules are configured
  → coach, or an athlete without a coach, submits a sports-rank application
  → application references the competition and the result
  → federation reviews the application
  → federation records the final decision, official order, and validity period
  → profile and notifications are updated
```

Implement judge categories as a separate, analogous review workflow.

### Scenario C — Ratings and Regional Team

```text
Federation selects season + discipline + age group
  → system collects confirmed results from published protocols
  → excludes currently disqualified/suspended athletes
  → awards configured points for each competition
  → applies the ×1.2 stability coefficient for >= 2 podium finishes
  → shows the source of every awarded point
  → federation manually selects regional team members
  → exports the roster and draft order
```

### Scenario D — Registry and Reporting

```text
Federation maintains athlete/organization/discipline registries
  → system preserves participation and organization-affiliation history
  → user selects a period of at least 2 years
  → indicators are calculated by year, municipality, organization, discipline, and age
  → table and chart are displayed
  → XLSX file can be downloaded
```

## 7. SPECIAL REQUIREMENT: Configurable Competition Protocols by Discipline

This is one of the most important architectural requirements. **Do not hard-code a single protocol template** shared unchanged across algorithmic programming, product programming, information security, AI, robotics, and unmanned aerial systems.

### 7.1. Mandatory External Reference Template

Use this user-provided resource as **the starting point**:

**[Recommended Programming Competition Protocol — Appendix No. 5](https://sudact.ru/law/pravila-vida-sporta-sportivnoe-programmirovanie-utv-prikazom/prilozhenie-n-5/rekomenduemyi-obrazets-protokola-po-programmirovaniiu/)**

**Important:** This is an example and source for document structure, **not an unchangeable universal template**. The document format and required fields may vary depending on the discipline, event, and current regulations. If the document can be accessed through the link, verify its actual fields and structure before reproducing it precisely. If the link is unavailable, do not present an assumed reconstruction as a verbatim official form; label it “demonstration template — verification required.”

### 7.2. Protocol Engine

Build a `ProtocolTemplateEngine` subsystem (or equivalent) with the following capabilities:

1. **Template selection** by discipline, competition type, rule version, and effective date. If no specialized template exists, use an explicitly labeled universal baseline template.
2. **Administrative configuration:** the federation can define the title, sections, table columns, signature/judging positions, sorting, and displayed metrics. Do not permit arbitrary execution of user-provided code or HTML templates.
3. **Schema storage** in the database (`JSONField`, with server-side JSON Schema/Pydantic-style validation), or a similarly validated declarative configuration. Do not store arbitrary Python expressions.
4. **Versioning:** a published protocol is bound to specific template and data versions. Editing a later template must not change documents already issued.
5. **Common input data:** competition, discipline, level/status, stages, judging panel, every approved participant, results, and metadata.
6. **Discipline-specific extensions:** number of solved tasks / penalty time / tests; project assessment and defense criteria; information-security metrics; AI metrics; robotics/UAS results and stages — **as configurable examples only**, not as assertions of currently binding official rules.
7. **Export:** well-formatted PDF and DOCX, with Cyrillic support, protocol number/version, and generation date.
8. **Preview and federation approval** before publication, plus the ability to save drafts and review version history.
9. **Formal signature fields** for the chief judge, secretary, and other positions according to the selected form. Do not claim that a rendered signature field is a legally valid electronic signature.

### 7.3. Proposed Baseline Fields (Subject to Verification)

**Header:** competition name, discipline, competition type/level, age group, date and venue, organizer, format/stage, and approval details according to the selected template.

**Participant table:** row number, placement (if determined), athlete's name/identifier within the allowed data scope, municipality/organization, result/score, discipline-specific metrics, and status (“classified,” “did not start,” “disqualified,” etc. according to the selected rules).

**Closing section:** judging panel and roles, signature/date fields, document number/version, and notes.

This list **has not been verified as an exact reproduction of the regulatory appendix**. First cross-check the original, then adapt it to the discipline.

### 7.4. Declarative Template Example (Not an Official Document)

```json
{
  "code": "algorithmic_basic_demo",
  "label": "Demonstration protocol: algorithmic programming",
  "discipline_code": "algorithmic",
  "template_version": 1,
  "status": "demo_unverified",
  "reference_url": "https://sudact.ru/law/pravila-vida-sporta-sportivnoe-programmirovanie-utv-prikazom/prilozhenie-n-5/rekomenduemyi-obrazets-protokola-po-programmirovaniiu/",
  "columns": [
    {"key": "place", "label": "Place", "type": "integer", "optional": true},
    {"key": "athlete_name", "label": "Participant", "type": "string"},
    {"key": "organization", "label": "Organization", "type": "string"},
    {"key": "score", "label": "Result", "type": "decimal", "optional": true},
    {"key": "result_status", "label": "Status", "type": "string"}
  ],
  "sort": [{"key": "place", "direction": "asc", "nulls": "last"}],
  "signature_roles": ["chief_judge", "secretary"]
}
```

Create **at least two demonstration configurations** with noticeably different column sets, for example algorithmic and product programming. Demonstrate that an administrator can update the configuration **without modifying source code**. Keep one shared generation engine for all six disciplines.

## 8. Role-Based Access Control, Authentication, and Data Protection

- Support one account with multiple roles and store `active_role` in the server-side session.
- A user can select only a role assigned to them. Being an athlete must not permit access to someone else's medical, personal, or judging documents.
- The federation has elevated privileges, but important modifications must be recorded in `AuditEvent`.
- Use object-level permissions. Coaches may view/edit athletes only within the scope of a confirmed relationship and the appropriate discipline.
- Enforce state transitions and deadlines server-side. Never trust frontend-submitted roles, placements, rating points, or calculated age.
- Retain the timestamp and version of the consent text. For minors, capture legal guardian details and consent status; do not claim that a simple checkbox UI alone is legally adequate for production use.
- Handle uploaded files securely: allowed types, size limits, private storage, and download authorization. Prevent path traversal and uploading executable files as documents.
- Use **entirely fictional identities** in demo/seed data, without real passport details, SNILS numbers, addresses, phone numbers, or personal email addresses.
- Implement reasonable login throttling, CSRF/XSS defenses, and protection against bulk record enumeration. Use Django's secure built-in password hashing.
- Expose only explicitly authorized fields publicly; never publish guardian details.

## 9. Next.js Pages

### 9.1. Public Pages

- `/` — homepage with the platform name, upcoming competitions, and intuitive navigation.
- `/competitions` — public calendar with filters for discipline, dates, age group, and level.
- `/competitions/[id]` — event details, registration status, regulations, and published results/protocol.
- `/login`, `/register` — sign-in and registration with personal-data consent.
- `/about` — information on sports programming and its six disciplines.

### 9.2. Shared Dashboard Layout

- Sidebar on large displays and compact responsive navigation on mobile.
- Switch between assigned roles without signing in again.
- Breadcrumbs, error messages, empty states, loading states, and access-denied screens.
- Accessible UX: understandable form labels, keyboard navigation, sufficient contrast, and visible focus states.

### 9.3. Federation Dashboard `/dashboard/federation`

- Main analytics: participants, competitions, applications awaiting review, active/expiring ranks and categories, deadlines.
- Athlete, coach, judge, and organization registries (search, filters, profiles).
- Create/edit competitions and upload regulations.
- Moderate applications, assign judges, enter results.
- Preview protocols, select discipline-specific templates, and publish them.
- Review sports-rank and judge-category applications.
- Ratings, regional team selection, and draft-order export.
- Yearly participation report and export.
- Rating-coefficient and document-template settings.
- Permission-limited audit log.

### 9.4. Athlete Dashboard `/dashboard/athlete`

- Personal details, organization, disciplines, coaches, current sports rank and expiration date.
- Competition listings with age-group eligibility and deadline guidance.
- Submit/track applications; performance history and links to protocols.
- Consents and RUSADA anti-doping course status (date, certificate link, `https://rusada.ru/` link).
- Submit a sports-rank request independently if there is no applicable coach.

### 9.5. Coach Dashboard `/dashboard/coach`

- Search for an athlete and request a confirmed discipline-specific relationship.
- Athlete roster, relationship-status history, and competition performance.
- Register linked athletes, apply for their sports ranks, and view a deadline calendar.

### 9.6. Judge Dashboard `/dashboard/judge`

- Current category and expiration date.
- Application for category assignment/confirmation and its status.
- Assignments with judging positions, judging history, and notifications.

**MANDATORY visual design:** The **user-supplied `docs/design/fsp-reference.html` is the authoritative UI specification**, as defined by **Section 1.1**. Reproduce its indigo/orange visual identity, precise typography, document-binding rail, numbered sidebar, left-labeled sections, stamp-like statuses, outlined tables and controls, light/dark themes, and mobile bottom navigation. Extend the *same* system to screens absent from the HTML. Do **not** replace it with another generic sports/technology visual style. The custom reference is not an assertion that its colors or logo are the official federation identity; keep that distinction clear.

## 10. Configurable Business Logic

### Calendar and Age Groups

- The federation can add competition types through a managed catalog.
- Competition level, competition type, and inclusion in the EKP/regional calendar are separate entities or independent attributes.
- Age groups and eligibility rules must be configured in versioned settings tied to regulations/discipline/competition. Do not hard-code numeric boundaries without a source.
- Support in-person, online, and hybrid competitions, including stages with differing formats.

### Ratings

- Seed the point table with **100/80/60, 80/60/40, 60/45/30, 40/30/20** for the corresponding four levels in the case.
- Rating formula: season point total × `1.2` if the athlete has at least two podium finishes that season, otherwise × `1.0`.
- The federation can change the coefficient and points table while preserving rule versions.
- When coefficients change, clearly identify the rule version applied by a recalculation. Never silently rewrite historical documents.
- A disqualification active on the relevant date excludes the athlete from the ratings according to the specified period rule.
- Protocols and ratings must reference the same published result; do not create two independent sources of truth.

### Deadline Tracking and Notifications

Required events: registration opening/closing, application-status changes, protocol publication, sports-rank/category application changes, approaching rank/category expirations, and reporting deadlines. The case also names a Governor's award nomination deadline **before February 1**; implement full award automation separately only if D8 is selected.

Send notifications **in the dashboard and via at least one external channel**, preferably SMTP email. Mailpit may be used for local demonstrations, but identify it clearly as a test mail server. Printing an email to a console alone is not enough to claim that a working external notification channel exists.

## 11. Documents and Exports

The platform must provide:

1. Final competition protocol — configurable template with PDF/DOCX export.
2. Regional team roster and draft official order — DOCX/PDF.
3. Athlete competition participation report — PDF/DOCX/XLSX, as appropriate.
4. “Number of People Participating in Sports Programming in the Orenburg Region” report — **XLSX**, with at least two years and the required breakdowns.

Files must be generated from real database records, render Cyrillic text correctly, contain readable tables, dates, and document numbers, and support regeneration and version history. The backend must enforce access permissions for non-public exports.

### First Selected Optional Enhancement — D10

Once all mandatory modules are complete, implement a **participation certificate with a number and QR code** leading to a public authenticity-verification page. Expose only the minimum necessary information on that page, especially for minors. A QR code does not substitute for a valid electronic signature and must not imply independent legal validity.

## 12. Demo Data

Create an idempotent Django management command, for example:

```bash
python manage.py seed_demo
```

It must generate:

- All **6 disciplines**.
- Several organizations and municipalities within the Orenburg Region (all personal details in demo profiles must be fictional).
- Users in all four roles, including at least one account with **multiple** roles.
- Athletes across different age groups, organizations, participation start dates, and sports-rank statuses.
- A confirmed coach → athlete relationship and at least one pending relationship request.
- Competitions in these states: registration open, registration closed, results published.
- An example hybrid competition with stages in different formats.
- Approved and rejected applications; judge assignments.
- Published protocols that include **every approved participant**, not just winners.
- Results that allow verification of the ×1.2 stability coefficient.
- Historical participation counts for **at least two consecutive years**.
- Sports ranks/categories approaching expiration and applications awaiting review.
- At least two discipline-specific protocol template versions/configurations.

Provide demo account credentials **only** for local/test environments in `docs/demo-scenarios.md`. Never publish production secrets.

## 13. Validation and Tests

Write automated tests for the following scenarios:

1. Registration creates a user and retains the required consent.
2. Users can switch only to roles they have been assigned.
3. An athlete cannot modify another athlete's applications.
4. A coach cannot apply on an athlete's behalf without a confirmed relationship.
5. Duplicate competition registration is prevented when disallowed.
6. Registration deadlines are checked by the backend.
7. Every approved participant appears in the protocol, while rejected applicants do not.
8. Participants without a valid scored result are displayed with the correct status and without fabricated placement.
9. Protocols for different disciplines use **different** column sets.
10. Editing a template does not corrupt a previously published protocol.
11. Competition results appear in both athlete history and ratings.
12. The rating-points table matches the original case exactly.
13. The coefficient is `1.2` for two podium results and `1.0` for one.
14. An active disqualification excludes an athlete from the relevant ratings.
15. Rating-rule changes are versioned and do not silently replace previous calculations.
16. A sports-rank application refers to a specific result and passes through review.
17. An athlete is not automatically assigned a rank merely because an EVSK eligibility hint is displayed.
18. The participation report covers two or more years and does not inflate unique participation counts when athletes have multiple disciplines.
19. Exported XLSX files open correctly and contain expected data.
20. Publication and status-transition operations are written to the audit log.
21. Notifications are created for important events; external-channel delivery is validated through a test adapter.
22. The backend prevents unauthorized users from downloading private documents.

Additionally, implement the **visual reference screenshot comparison and responsive/theme checks** specified in Section 1.1. Keep screenshots or reproducible capture commands and discrepancies in `docs/design/visual-qa.md`.

Add at least **one Playwright E2E test**: sign in → choose role → submit application → moderate it → enter result → publish protocol → see result in dashboard. Verify role switching in a separate E2E or integration test.

Run `ruff`/Python lint, backend tests, OpenAPI generation, `tsc --noEmit`, Next.js lint, and `next build`. Do not claim that tests passed unless they were actually executed.

## 14. 48-Hour Plan and Implementation Order

Work in short vertical slices: database + API + UI + tests + demo data. Build the critical path first, then broaden feature coverage. These time targets are **internal planning goals**, not guarantees.

### Stage 1 — By Hour 22

- Set up the monorepo architecture, Docker Compose, database, OpenAPI, and basic navigation. **Copy and commit the reference HTML, establish its exact design tokens, and implement the shared reference-faithful desktop/mobile shell before individual frontend screens.**
- Agree on entities, roles, API, and state models.
- Implement authentication/role switching and reference catalogs.
- Build an initial competition-creation and application-submission flow.
- Prepare the dynamic protocol schema and two configurations.
- Present the concept, target workflows, optional features, and stack at Checkpoint 1.

### Stage 2 — By Hour 42

- Deliver the working flow: competition creation → application → moderation → results → protocol → athlete history.
- Implement judge assignments and the four core dashboards.
- Add rating calculations with the coefficient and manual regional-team selection.
- Implement basic sports ranks/judge categories, deadline tracking, and external email notifications.
- Add registry management, the two-year XLSX report, and primary document exports.
- Demonstrate **1–2 live end-to-end workflows**, or record a 2–3-minute video.

### Stage 3 — By Hour 48

- Finish outstanding mandatory requirements and stabilize the UI and tests. **Compare original HTML and Next.js screenshots in light/dark at desktop/tablet/mobile viewports, resolve design drift, and document visual QA.**
- If time allows, implement D10 (QR certificate), followed by D11/D12.
- Verify clean setup from the README on a fresh machine/in containers.
- Prepare demo accounts and reproducible verification workflows.
- Complete `docs/acceptance-matrix.md`: implemented, partial, missing, and how to test each item.
- Ensure the repository contains a README, source code, fictional demo data, data-model documentation, and API descriptions.

## 15. Parallel Work Organization (Five Developers)

Use **one shared API contract** and agreed data models. The orchestrator makes architectural decisions; individual team members/AI agents must not independently change shared contracts. Assign code ownership as follows:

| Team member | Ownership | Deliverables |
|---|---|---|
| 1. Architecture/integration | Django bootstrap, users, roles, permissions, database, CI, API schema | Backend core, OpenAPI, migrations |
| 2. Competitions | Calendar, applications, judges, results, dynamic protocols | Backend competitions/results/documents |
| 3. Sports domain logic | Registries, coach links, ranks, ratings, regional team, statistics | Backend registry/qualifications/ratings/analytics |
| 4. Federation frontend | Dashboard, registries, competition management calendar, moderation, protocols, reporting | Next.js federation features |
| 5. Other dashboards and QA | Athlete/coach/judge dashboards, API integration, E2E, demo | Next.js role features, Playwright, documentation |

**Orchestration rules:**

- Freeze the API contract and core DTOs first. If an endpoint is not ready, the frontend may use **isolated mocks** that are removed later. Never leave demo stubs masquerading as final functionality.
- Give each contributor a dedicated branch/worktree, explicit directories, and acceptance criteria.
- Forbid unilateral modifications of the shared user model, role schema, root configuration, **design tokens, shared UI primitives, and visual contract** without orchestrator approval.
- Require working migrations, documented API changes, tests, no merge conflicts, correct access control, **and review of frontend changes against the supplied HTML design** before integration.
- Do not automatically merge unverified changes or overwrite other contributors' work.

## 16. MVP Acceptance Criteria

Treat a mandatory workflow as implemented **only if the full chain actually works** and has clear verification instructions:

| ID | Criterion | Verification |
|---|---|---|
| AC-01 | Next.js actually serves a responsive frontend | Desktop and mobile UI |
| AC-02 | Django DRF works with PostgreSQL | API, migrations, persistent records |
| AC-03 | A single account has several dashboards | Sign-in and active-role switching |
| AC-04 | All six disciplines are available | Catalog, filters, competition creation |
| AC-05 | Calendar, applications, moderation, and judge assignment work | End-to-end scenario |
| AC-06 | Protocol includes every approved participant | Protocol containing winners and non-winners |
| AC-07 | Different disciplines can have different protocols | Switch template/columns without code changes |
| AC-08 | Results appear in athlete history | Compare competition and dashboard data |
| AC-09 | Sports-rank and judge-category requests go through review | Application → decision → validity period |
| AC-10 | Dashboard and email notifications work | Event and delivery record in Mailpit/SMTP |
| AC-11 | Participation trends cover at least 2 years | Table/chart plus XLSX |
| AC-12 | Ratings correctly calculate totals and ×1.2 coefficient | Reference data and tests |
| AC-13 | Regional team membership is selected manually | Pick members and generate draft order |
| AC-14 | Documents are built from database records | PDF/DOCX/XLSX contain real stored data |
| AC-15 | Important actions are audited and access is restricted | Audit entries and 403 tests |
| AC-16 | Project can be started reproducibly | README, Docker Compose, seed data, tests |
| **AC-17** | **Frontend uses the supplied HTML as the mandatory design source of truth** | The unchanged reference is committed at `docs/design/fsp-reference.html`; token/component mapping documented; no unauthorized redesign or second style system |
| **AC-18** | **Frontend closely matches the reference across desktop/mobile and light/dark modes** | Side-by-side Playwright screenshot review at 1440/768/390px, documented differences, faithful sidebar/document rail, component and navigation states; working accessible controls |

Do not claim full completion of all mandatory requirements when only partial implementations exist. Use `partial` or `not_implemented` for any incomplete item.

## 17. Required Final Response from the AI Agent

When the work is complete, provide **actual code deliverables, not plans in place of code**:

1. A tree of created files and an architecture overview.
2. Implemented workflows with completeness status and links to modules/screens.
3. Commands for running the application, migrations, demo-data seeding, tests, and build.
4. Demo accounts and walkthrough instructions (test data only).
5. OpenAPI documentation and a description of the data model.
6. Actual results from executed tests, type checks, and builds, including any remaining failures.
7. Selected optional features and evidence that they work.
8. Known limitations, TODOs, and regulatory aspects needing legal verification (especially protocols and EVSK rules).
9. For every **AC-01…AC-18**, a `pass`, `partial`, or `fail` status with an explanation.
10. **Visual fidelity evidence:** exact reference-file path, screenshot captures or reproducible commands, desktop/tablet/mobile and light/dark review summary, and all deviations from the original HTML.

**Begin by inspecting the current repository AND the supplied `docs/design/fsp-reference.html`; freeze the shared design-token/component contract alongside the data schema. Implement a visually faithful frontend shell and one functioning end-to-end workflow, then deliver remaining mandatory modules in sequence.**

---

# Part III. Sources and Scope of Requirements

## Regulations Listed in the Case

- Federal Law No. 329-FZ “On Physical Culture and Sports in the Russian Federation.”
- Federal Law No. 152-FZ “On Personal Data.”
- Rules of the Sport of Sports Programming, approved by Russian Ministry of Sport Order No. 584 dated August 11, 2023.
- Federal Sports Training Standard for Sports Programming, approved by Russian Ministry of Sport Order No. 445 dated June 24, 2025.
- Regulation on the Unified All-Russian Sports Classification (EVSK).
- Orenburg Region Governor's Decree No. 93-uk dated March 4, 2011 (awards for sporting achievements).
- **Additional user-supplied source:** [Appendix No. 5 — Recommended Protocol Template](https://sudact.ru/law/pravila-vida-sporta-sportivnoe-programmirovanie-utv-prikazom/prilozhenie-n-5/rekomenduemyi-obrazets-protokola-po-programmirovaniiu/).

Numbers and dates are reproduced **from the case PDF**; currently effective versions have not been independently verified. Before launching an official production system, verify current regulations, consent forms, validity periods for sports ranks and judge categories, and discipline-specific rules.

## What the Case Does Not Require

- A separate native mobile application; a responsive website is sufficient.
- Real Gosuslugi or other government information-system integration.
- Implementing all twelve optional scenarios.
- Automatically assigning official sports ranks on the basis of placement.
- One immutable protocol template for all six disciplines.

## Final Architecture Decision

**Django/DRF** owns reliable sports data, statuses/workflows, permissions, history, ratings, document generation, and the API. **Next.js** serves the responsive public site and all four fully functional dashboards **using the exact user-supplied HTML visual system as a non-negotiable design reference**. **PostgreSQL** stores interconnected entities and their history; **configurable, versioned templates** make it possible to change protocol formats without rewriting competition logic.

Main demo storyline: **create competition → apply → approve → enter result → publish discipline-specific protocol → see result in history and rating → use it for sports-rank review and regional-team selection**.
