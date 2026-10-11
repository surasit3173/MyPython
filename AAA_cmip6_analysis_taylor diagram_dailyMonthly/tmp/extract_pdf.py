import argparse
from pathlib import Path

import pdfplumber


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("out")
    args = ap.parse_args()
    lines = []
    with pdfplumber.open(args.pdf) as pdf:
        for index, page in enumerate(pdf.pages, 1):
            lines.append(f"\n===== PAGE {index} =====\n")
            lines.append(page.extract_text(x_tolerance=1.5, y_tolerance=3, layout=True) or "")
    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    print(f"pages={len(pdf.pages)} out={args.out}")


if __name__ == "__main__":
    main()
