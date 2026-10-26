"""Regenerate the shared token/style baseline without editing the visual reference."""
from pathlib import Path
import re

root = Path(__file__).resolve().parent.parent
reference = root / "docs/design/fsp-reference.html"
match = re.search(r"<style>(.*?)</style>", reference.read_text(encoding="utf-8"), re.DOTALL)
if not match:
    raise SystemExit("Reference style block not found")
(root / "frontend/src/app/globals.css").write_text(match.group(1).strip() + "\n", encoding="utf-8")
