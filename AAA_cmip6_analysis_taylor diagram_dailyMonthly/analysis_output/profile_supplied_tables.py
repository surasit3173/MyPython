"""Profile the CSV/XLSX result tables supplied in the nested framework ZIP."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = (
    Path(__file__).resolve().parent
    / "source_archive"
    / "framework_extracted"
    / "paper1_framework"
)
OUT = Path(__file__).resolve().parent / "supplied_table_profile.csv"


def profile_frame(path: Path, frame: pd.DataFrame, sheet: str = "") -> dict:
    cells = max(frame.shape[0] * frame.shape[1], 1)
    duplicate_rows = int(frame.duplicated().sum()) if len(frame) else 0
    date_cols = [c for c in frame.columns if "date" in str(c).lower()]
    date_summary = ""
    if date_cols:
        values = pd.to_datetime(frame[date_cols[0]], errors="coerce").dropna()
        if len(values):
            date_summary = f"{values.min().date()}..{values.max().date()}"
    return {
        "relative_path": str(path.relative_to(ROOT)),
        "sheet": sheet,
        "rows": int(frame.shape[0]),
        "columns": int(frame.shape[1]),
        "missing_cells": int(frame.isna().sum().sum()),
        "missing_pct": round(100 * frame.isna().sum().sum() / cells, 3),
        "duplicate_rows": duplicate_rows,
        "date_range": date_summary,
        "column_names": " | ".join(map(str, frame.columns)),
    }


records = []
for path in sorted(ROOT.rglob("*.csv")):
    records.append(profile_frame(path, pd.read_csv(path)))
for path in sorted(ROOT.rglob("*.xlsx")):
    book = pd.ExcelFile(path)
    for sheet in book.sheet_names:
        records.append(profile_frame(path, pd.read_excel(path, sheet_name=sheet), sheet))

pd.DataFrame(records).to_csv(OUT, index=False, encoding="utf-8-sig")
print(f"wrote={OUT}")
print(f"profiled_objects={len(records)}")
print(f"csv_files={sum(1 for p in ROOT.rglob('*.csv'))}")
print(f"xlsx_files={sum(1 for p in ROOT.rglob('*.xlsx'))}")
