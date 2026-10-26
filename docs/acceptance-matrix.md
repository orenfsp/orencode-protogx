# Acceptance matrix

Status is based on executed evidence. `partial` means a foundation exists but the full acceptance test has not passed.

| ID | Status | Evidence / next gate |
| --- | --- | --- |
| AC-01 | partial | Next.js build and Compose web pass; viewport browser review pending |
| AC-02 | implemented | PostgreSQL Compose healthy, migrations checked, 8 tests and proxy API smoke pass |
| AC-03 | partial | Role assignment/switch/denial backend test passes; multi-dashboard browser flow pending |
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
| AC-16 | partial | Compose build, migration check, and auth smoke pass; fictional seed and fresh startup pending |
| AC-17 | implemented | Unchanged reference committed; design-contract checker passes SHA-256 and exact extracted CSS comparison; mapping documented |
| AC-18 | not_implemented | Six viewport/theme screenshot comparisons pending |
