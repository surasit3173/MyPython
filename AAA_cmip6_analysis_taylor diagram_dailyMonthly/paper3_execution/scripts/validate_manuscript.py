from __future__ import annotations

import csv
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "manuscript" / "Paper3_CMJS_manuscript.md"
OUTPUT = ROOT / "output"
AUDIT = OUTPUT / "manuscript_numerical_audit.csv"


def fmt_response(row: pd.Series) -> str:
    return f"{row.response_pct:.1f} [{row.ci_low_pct:.1f}, {row.ci_high_pct:.1f}]"


def norm(value: str) -> str:
    return value.replace("−", "-").replace("+", "").strip().upper()


def markdown_table(text: str, caption_starts: str) -> list[list[str]]:
    tail = text.split(caption_starts, 1)[1]
    lines = tail.splitlines()
    rows = []
    in_table = False
    for line in lines:
        if line.startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if all(set(cell) <= {"-", ":"} for cell in cells):
                continue
            rows.append(cells)
            in_table = True
        elif in_table:
            break
    return rows


def main() -> None:
    text = MANUSCRIPT.read_text(encoding="utf-8")
    primary = pd.read_csv(OUTPUT / "primary_response_summary.csv")
    preservation = pd.read_csv(OUTPUT / "qdm_enso_signal_preservation.csv")
    asym = pd.read_csv(OUTPUT / "enso_asymmetry_primary.csv")
    audit: list[dict[str, str | bool]] = []

    rows = markdown_table(text, "**Table 2.")
    assert len(rows) == 17, f"Expected header + 16 Table 2 rows; got {len(rows)}"
    for cells in rows[1:]:
        season, metric, phase = cells[:3]
        season_key = "RAINY" if season == "Rainy" else "HOT_DRY"
        metric_key = "wet_day_frequency_pct" if metric == "Wet-day frequency" else metric
        phase_key = "EL_NINO" if phase == "El Niño" else "LA_NINA"
        key = (season_key, metric_key, phase_key)
        found = []
        for source, column in (("OBSERVED", 3), ("RAW", 5), ("QDM", 6)):
            row = primary[(primary.source_type == source) & (primary.season_type == season_key) &
                          (primary.metric == metric_key) & (primary.phase == phase_key)].iloc[0]
            expected = norm(fmt_response(row))
            actual = norm(cells[column])
            ok = actual == expected
            audit.append({"check": f"Table2 {source} {key}", "pass": ok,
                          "expected": expected, "actual": actual})
            found.append(ok)
        row_obs = primary[(primary.source_type == "OBSERVED") &
                          (primary.season_type == season_key) &
                          (primary.metric == metric_key) & (primary.phase == phase_key)].iloc[0]
        expected_q = f"{row_obs.permutation_p_bh_primary:.3f}"
        ok_q = cells[4] == expected_q
        audit.append({"check": f"Table2 q {key}", "pass": ok_q,
                      "expected": expected_q, "actual": cells[4]})
        assert all(found) and ok_q

    rows3 = markdown_table(text, "**Table 3.")
    assert len(rows3) == 9, f"Expected header + 8 Table 3 rows; got {len(rows3)}"
    for cells in rows3[1:]:
        season, metric = cells[:2]
        season_key = "RAINY" if season == "Rainy" else "HOT_DRY"
        metric_key = "wet_day_frequency_pct" if metric == "Wet-day frequency" else metric
        for phase_key, col in (("EL_NINO", 2), ("LA_NINA", 3)):
            row = preservation[(preservation.season_type == season_key) &
                               (preservation.metric == metric_key) &
                               (preservation.phase == phase_key)].iloc[0]
            expected_cat = row.category.replace("INDETERMINATE_RAW_NEAR_ZERO", "INDETERMINATE")
            actual_cat = cells[col].split("(", 1)[0].strip().upper()
            ok = actual_cat == expected_cat
            audit.append({"check": f"Table3 category {(season_key, metric_key, phase_key)}",
                          "pass": ok, "expected": expected_cat, "actual": actual_cat})
            assert ok
        for source, col in (("OBSERVED", 4), ("RAW", 5), ("QDM", 6)):
            row = asym[(asym.source_type == source) & (asym.season_type == season_key) &
                       (asym.metric == metric_key)].iloc[0]
            expected = f"{row.neutral_centered_asymmetry_pct:.1f}"
            actual = norm(cells[col])
            ok = actual == expected
            audit.append({"check": f"Table3 asymmetry {(source, season_key, metric_key)}",
                          "pass": ok, "expected": expected, "actual": actual})
            assert ok

    categories = preservation.category.value_counts().to_dict()
    expected_phrase = "preserved only 2 of 16 signals, attenuated 4, amplified 3, reversed 1"
    phrase_ok = expected_phrase in text.lower()
    counts_ok = categories == {
        "INDETERMINATE_RAW_NEAR_ZERO": 6,
        "ATTENUATED": 4,
        "AMPLIFIED": 3,
        "PRESERVED": 2,
        "REVERSED": 1,
    }
    audit.append({"check": "Abstract preservation counts", "pass": phrase_ok and counts_ok,
                  "expected": str(categories), "actual": expected_phrase})
    assert phrase_ok and counts_ok

    with AUDIT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["check", "pass", "expected", "actual"])
        writer.writeheader()
        writer.writerows(audit)
    assert all(row["pass"] for row in audit)
    print(f"MANUSCRIPT_AUDIT_COMPLETE checks={len(audit)} output={AUDIT}")


if __name__ == "__main__":
    main()
