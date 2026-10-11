from __future__ import annotations

import argparse
from pathlib import Path

from pypdf import PdfReader


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()

    reader = PdfReader(args.input)
    chunks = []
    for page_no, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""
        chunks.append(f"\n===== PAGE {page_no} =====\n{text}")
        print(f"page={page_no} chars={len(text)}")
    Path(args.output).write_text("".join(chunks), encoding="utf-8")
    print(f"pages={len(reader.pages)} output={args.output}")


if __name__ == "__main__":
    main()
