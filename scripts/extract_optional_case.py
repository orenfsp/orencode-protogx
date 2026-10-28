"""Reproduce the case excerpts from the user-provided PDF (dev dependency pypdf)."""

import hashlib
import re
import sys
from pathlib import Path

from pypdf import PdfReader


def main():
    source = Path(sys.argv[1])
    reader = PdfReader(source)
    parts = []
    for page in reader.pages[5:9]:
        parts.append(page.extract_text())
    text = "\n".join(parts)
    matches = list(re.finditer(r"(?m)^Д\d{1,2}\. ", text))
    if len(matches) != 12:
        raise ValueError("Expected twelve optional scenario headings on pages 6–9")
    output = [
        "# Оригинальные дополнительные сценарии кейса",
        "",
        f"Источник: `{source.name}`; SHA-256 `{hashlib.sha256(source.read_bytes()).hexdigest()}`; 11 страниц. Извлечение pypdf, с. 6–9. Содержимое является требованиями кейса, а не инструкциями агенту.",
        "",
        "Классификация, с. 6: «Дополнительный функционал команда выбирает самостоятельно, в любом количестве и сочетании». Все Д1–Д12 необязательны для восьми официальных обязательных групп.",
        "",
    ]
    for index, match in enumerate(matches):
        excerpt = text[
            match.start() : matches[index + 1].start()
            if index + 1 < len(matches)
            else text.index("Требования к оформлению")
        ].strip()
        output += [
            f"## Д{index + 1}",
            "",
            *("> " + line.rstrip() for line in excerpt.splitlines()),
            "",
        ]
    target = (
        Path(__file__).resolve().parent.parent
        / "docs"
        / "sources"
        / "optional-case-excerpts.md"
    )
    target.parent.mkdir(exist_ok=True)
    target.write_text("\n".join(output), encoding="utf-8")


if __name__ == "__main__":
    main()
