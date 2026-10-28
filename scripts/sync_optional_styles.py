"""Package the exact existing frontend CSS for Django OIDC pages; no second theme."""
import sys
from pathlib import Path


def main():
    root=Path(__file__).resolve().parent.parent
    expected="\n\n".join((root/"frontend/src/app"/name).read_text(encoding="utf-8") for name in ["globals.css","app.css"])
    target=root/"backend/apps/extensions/static/extensions/fsp-id.css"
    if "--check" in sys.argv:
        if not target.exists() or target.read_text(encoding="utf-8")!=expected:
            raise SystemExit("FAIL: OIDC CSS differs from the established frontend CSS")
        print("PASS: OIDC CSS reuses the exact existing frontend styles")
    else:
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(expected,encoding="utf-8",newline="\n")


if __name__=="__main__":
    main()
