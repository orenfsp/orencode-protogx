#!/usr/bin/env python3
"""Fail if the committed OpenAPI schema differs from warning-free generation."""
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory() as directory:
        generated = Path(directory) / "openapi.yaml"
        command = [sys.executable, "manage.py", "spectacular", "--validate", "--fail-on-warn", "--file", str(generated)]
        subprocess.run(command, cwd=root / "backend", check=True)
        actual = yaml.safe_load(generated.read_text(encoding="utf-8"))
        committed = yaml.safe_load((root / "docs" / "openapi.yaml").read_text(encoding="utf-8"))
    if actual != committed:
        print("FAIL: docs/openapi.yaml differs from fresh generation", file=sys.stderr)
        return 1
    print("PASS: docs/openapi.yaml matches warning-free generation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
