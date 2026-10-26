# Acceptance matrix

Status is based on executed evidence. `partial` means a foundation exists but the full acceptance test has not passed.

| ID | Status | Evidence / next gate |
| --- | --- | --- |
| AC-01 | implemented | Compose web serves responsive homepage; 1440/768/390 Playwright screenshots captured in both themes |
| AC-02 | implemented | PostgreSQL Compose healthy, migrations checked, 8 tests and proxy API smoke pass |
| AC-03 | implemented | Four role-specific dashboards use the protected `auth/dashboard/` API; server rechecks active assignment on every read. PostgreSQL role/revocation tests and desktop/mobile Playwright switching pass. Domain workflow panels remain Phase 2+ work. |
| AC-04 | implemented | Six catalog rows verified in backend test and Compose proxy smoke |
| AC-05 | not_implemented | Competition workflow pending |
| AC-06 | not_implemented | Approved-participant protocol test pending |
| AC-07 | not_implemented | Two discipline template test pending |
| AC-08 | not_implemented | Published result/history test pending |
| AC-09 | not_implemented | Rank/category review tests pending |
| AC-10 | not_implemented | Dashboard and SMTP delivery test pending |
| AC-11 | not_implemented | Two-year XLSX test pending |
| AC-12 | not_implemented | Rating fixtures and formula test pending |
| AC-13 | not_implemented | Manual team selection test pending |
| AC-14 | not_implemented | Real-data document export test pending |
| AC-15 | partial | Role denial and CSRF tests pass; audit and object permissions pending |
| AC-16 | implemented | Two isolated Compose projects created new PostgreSQL volumes without touching development data. Fresh migrations and automatic five-account fictional seed passed; API healthcheck gates Next.js startup; PostgreSQL tests, API/proxy smoke and demo login pass. |
| AC-17 | implemented | Unchanged reference committed; design-contract checker passes SHA-256 and exact extracted CSS comparison; mapping documented |
| AC-18 | implemented | Reference/homepage and 48 additional public/auth/dashboard captures at 1440/768/390 in both themes completed; representative desktop/mobile images visually inspected. Mobile theme persistence, role selector and bottom navigation pass browser tests; future workflow screens require their own QA. |
