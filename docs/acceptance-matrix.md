# Acceptance matrix

Status is based on executed evidence. `partial` means a foundation exists but the full acceptance test has not passed.

| ID | Status | Evidence / next gate |
| --- | --- | --- |
| AC-01 | implemented | Compose web serves responsive homepage; 1440/768/390 Playwright screenshots captured in both themes |
| AC-02 | implemented | PostgreSQL Compose healthy, all five competition migrations applied, 23 backend tests and proxy API smoke pass |
| AC-03 | implemented | Four role-specific dashboards use the protected `auth/dashboard/` API; server rechecks active assignment on every read. PostgreSQL role/revocation tests and desktop/mobile Playwright switching pass. Domain workflow panels remain Phase 2+ work. |
| AC-04 | implemented | Six catalog rows verified in backend test and Compose proxy smoke |
| AC-05 | implemented | PostgreSQL API tests and Chrome Phase 2 E2E pass: federation create/publish → athlete application → moderation → judge assignment → result entry/validation. Coach confirmed-link application, deadline, age and guardian checks pass backend tests. |
| AC-06 | implemented | Backend end-to-end test verifies two approved participants in preview and published snapshot, including one with `pending_result`; no fabricated score/place. |
| AC-07 | implemented | Six seeded discipline-specific demo templates; backend test proves algorithmic `solved_tasks` and product `project_note` columns and metric types differ. Federation can create new template versions through API/UI. Official source remains unverified. |
| AC-08 | implemented | Backend test verifies latest immutable protocol version flows into only the athlete's own history; Chrome E2E confirms the visible history after publication. |
| AC-09 | partial | Qualifications APIs, federation decisions, audited history, published-row evidence and revocation-aware consent have PostgreSQL tests. End-to-end verification and reviewed source rules remain required; withdrawal/renewal UI and audited historical correction are not implemented. |
| AC-10 | not_implemented | Dashboard and SMTP delivery test pending |
| AC-11 | not_implemented | Two-year XLSX test pending |
| AC-12 | implemented | Versioned rating rules, exact default podium table, Decimal formula, automatic recalculation after protocol publication/correction, latest-publication provenance without duplicate counting, event-date suspension/disqualification exclusion, federation-only mutation endpoints, discipline-scoped filters/pagination, API breakdowns, 10 rating backend tests, OpenAPI validation, responsive ratings page, and Playwright empty/populated breakdown states pass. |
| AC-13 | partial | Manual team management, federation authorization, audit and exports exist. Final end-to-end browser, concurrency, eligibility-change and document rendering verification remain incomplete. |
| AC-14 | partial | Published protocol PDF/DOCX are generated from immutable database snapshots, with Cyrillic font, dynamic columns, version footer and private download authorization. PostgreSQL test and Chrome downloads pass; PDF visually inspected. Other document types and XLSX remain future work. |
| AC-15 | partial | Phase 2 audit events and role/object tests pass, including unconfirmed coach denial, assigned judge scope, private athlete history, withdrawn-consent publication block, and 403 role denial. Full platform-wide audit coverage remains future work. |
| AC-16 | implemented | Two isolated Compose projects created new PostgreSQL volumes without touching development data. Fresh migrations and automatic five-account fictional seed passed; API healthcheck gates Next.js startup; PostgreSQL tests, API/proxy smoke and demo login pass. |
| AC-17 | implemented | Unchanged reference committed; design-contract checker passes SHA-256 and exact extracted CSS comparison; mapping documented |
| AC-18 | implemented | Reference unchanged and design checker passes. Phase 1 and 24 refreshed Phase 2 calendar, competition and history screenshots were captured at 1440/768/390 in both themes; representative desktop/tablet/mobile images were visually reviewed. Numbered sidebar, document rail, dotted navigation, outlined tables, stamps, mobile bottom nav and theme control are retained. Differences and mobile table scrolling are documented in visual QA. |
