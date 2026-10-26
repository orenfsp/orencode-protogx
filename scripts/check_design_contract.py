#!/usr/bin/env python3
"""Read-only design-contract checker.

Verifies that:
  1. docs/design/fsp-reference.html is byte-for-byte unchanged against the
     verified immutable SHA-256 digest.
  2. frontend/src/app/globals.css is exactly equal to the text of the first
     <style>...</style> block in the reference HTML, stripped, followed by a
     single final newline.

Exit status:
  0 - PASS
  1 - FAIL (mismatch or missing file)

Manual validation command:
  python scripts/check_design_contract.py
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

EXPECTED_HTML_SHA256 = "2362C4D1AEC5D54FA075215D6FDF986416D23D8402FBF33342D29671C5D043A2"


def repo_root(script_path: Path) -> Path:
    """Return the repository root as the parent of the scripts directory."""
    return script_path.resolve().parent.parent


def read_bytes(path: Path) -> bytes:
    if not path.is_file():
        raise FileNotFoundError(f"missing file: {path}")
    return path.read_bytes()


def extract_first_style_block(html_text: str) -> str:
    match = re.search(r"<style[^>]*>(.*?)</style>", html_text, re.DOTALL)
    if match is None:
        raise ValueError("no <style> block found in reference HTML")
    return match.group(1).strip() + "\n"


def main() -> int:
    root = repo_root(Path(__file__))
    html_path = root / "docs" / "design" / "fsp-reference.html"
    css_path = root / "frontend" / "src" / "app" / "globals.css"

    try:
        html_bytes = read_bytes(html_path)
        css_text = css_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"FAIL: {exc}")
        return 1

    actual_digest = hashlib.sha256(html_bytes).hexdigest().upper()
    if actual_digest != EXPECTED_HTML_SHA256:
        print("FAIL: reference HTML checksum mismatch")
        print(f"  expected SHA-256: {EXPECTED_HTML_SHA256}")
        print(f"  actual   SHA-256: {actual_digest}")
        return 1

    try:
        html_text = html_bytes.decode("utf-8")
        expected_css = extract_first_style_block(html_text)
    except (UnicodeDecodeError, ValueError) as exc:
        print(f"FAIL: {exc}")
        return 1

    if css_text != expected_css:
        print("FAIL: globals.css does not match first <style> block in reference HTML")
        print(f"  globals.css length: {len(css_text)}")
        print(f"  expected    length: {len(expected_css)}")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
