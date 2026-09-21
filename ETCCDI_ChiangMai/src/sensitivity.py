"""
sensitivity.py — Trend sensitivity comparison (Ordinary MK vs Hamed-Rao Modified MK).

Compares Ordinary MK and Hamed-Rao Modified MK across all 11 indices per Master Spec Section 21.
Saves TABLE_05_TREND_SENSITIVITY.xlsx and TREND_SENSITIVITY.xlsx.
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import OUTPUT_ROOT, INDICES, ALPHA

try:
    import pymannkendall as mk
    HAS_PYMANNKENDALL = True
except ImportError:
    HAS_PYMANNKENDALL = False


def run_sensitivity_analysis(df_etccdi: pd.DataFrame) -> pd.DataFrame:
    years = df_etccdi["Year"].values
    records = []

    for idx in INDICES:
        if idx not in df_etccdi.columns:
            continue
        mask = df_etccdi[idx].notna()
        x = years[mask.values]
        y = df_etccdi.loc[mask, idx].values
        n = len(y)

        if n < 10:
            continue

        if HAS_PYMANNKENDALL:
            res_ord = mk.original_test(y)
            p_ord = round(float(res_ord.p), 6)
            inf_ord = "Significant" if p_ord < ALPHA else "Non-significant"

            try:
                res_mod = mk.hamed_rao_modification_test(y)
                p_mod = round(float(res_mod.p), 6)
                inf_mod = "Significant" if p_mod < ALPHA else "Non-significant"
            except Exception as e:
                p_mod = p_ord
                inf_mod = inf_ord
        else:
            p_ord = np.nan
            p_mod = np.nan
            inf_ord = "N/A"
            inf_mod = "N/A"

        same_inf = (inf_ord == inf_mod)
        if same_inf:
            comment = f"Consistent inference ({inf_ord.lower()})"
        else:
            comment = f"Inference shift: Ordinary={inf_ord}, Modified={inf_mod}"

        rec = {
            "Index": idx,
            "N": n,
            "P_ordinary": p_ord,
            "P_modified": p_mod,
            "Inference_ordinary": inf_ord,
            "Inference_modified": inf_mod,
            "Same_inference": same_inf,
            "Comment": comment,
        }
        records.append(rec)

    df_sens = pd.DataFrame(records)

    stats_dir = OUTPUT_ROOT / "statistics"
    tables_dir = OUTPUT_ROOT / "tables"
    stats_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    out_stats = stats_dir / "TREND_SENSITIVITY.xlsx"
    out_table = tables_dir / "TABLE_05_TREND_SENSITIVITY.xlsx"

    with pd.ExcelWriter(out_stats, engine="openpyxl") as writer:
        df_sens.to_excel(writer, sheet_name="Trend_Sensitivity", index=False)
    with pd.ExcelWriter(out_table, engine="openpyxl") as writer:
        df_sens.to_excel(writer, sheet_name="Trend_Sensitivity", index=False)

    print(f"[SENSITIVITY] Saved trend sensitivity to {out_stats} and {out_table}")
    return df_sens
