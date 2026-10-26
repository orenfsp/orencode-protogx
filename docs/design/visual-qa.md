# Visual QA

Reference: `fsp-reference.html` (SHA-256 `2362C4D1AEC5D54FA075215D6FDF986416D23D8402FBF33342D29671C5D043A2`). It is immutable.

Phase 1 maps the reference variables to `frontend/src/app/globals.css`, the numbered indigo sidebar and role selector to `AppShell`, the document rail to `.main::before`, and the fixed mobile bottom navigation to `.mobtab`. Rubik, Inter, and JetBrains Mono are loaded with the same font weights. The light/dark token values and 900px/520px breakpoints come from the reference CSS.

Pending visual gate: render original and Next.js at 1440px, 768px, and 390px in both themes. Compare sidebar width, rail positions, typography, gutters, borders, stamps, forms, table overflow, active navigation, and bottom navigation. Record actual screenshot results here before marking AC-18 implemented.
