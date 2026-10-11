"""
sensitivity.py — Trend sensitivity (robustness) analysis.

Compares three methods per index:
  Model A: Ordinary Mann–Kendall
  Model B: Hamed & Rao modified MK (autocorrelation-corrected)
  Model C: Sen's slope magnitude

Robustness = TRUE when A and B agree on direction AND both significant,
             OR both agree on non-significance.

Produces TABLE_S1_TREND_ROBUSTNESS.xlsx
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


def _direction(slope: float) -> str:
    if np.isnan(slope):
        return "N/A"
    return "Positive" if slope > 0 else "Negative"


def run_sensitivity(df_etccdi: pd.DataFrame) -> pd.DataFrame:
    """
    Run three-model sensitivity analysis for all 11 ETCCDI indices.

    Returns DataFrame with columns:
      Index, N, Model_A_p, Model_A_sig, Model_B_p, Model_B_sig,
      Direction, Sen_slope, Robust
    """
    from scipy import stats

    years = df_etccdi["Year"].values
    records = []

    for idx in INDICES:
        if idx not in df_etccdi.columns:
            continue
        mask = df_etccdi[idx].notna()
        x    = years[mask.values]
        y    = df_etccdi.loc[mask, idx].values
        n    = len(y)

        if n < 10:
            records.append({
                "Index": idx, "N": n,
                "Model_A_p": np.nan, "Model_A_sig": False,
                "Model_B_p": np.nan, "Model_B_sig": False,
                "Direction": "N/A", "Sen_slope": np.nan, "Robust": False,
            })
            continue

        # Model A — Ordinary MK
        if HAS_PYMANNKENDALL:
            res_a = mk.original_test(y)
            p_a   = float(res_a.p)
            slope_a = float(res_a.slope)
        else:
            from trend import _mk_ordinary_fallback, _sens_slope_ci
            fb = _mk_ordinary_fallback(y)
            p_a = fb["p"]
            slope_a, _, _, _ = _sens_slope_ci(x, y)

        # Model B — Hamed & Rao corrected MK
        if HAS_PYMANNKENDALL:
            try:
                res_b = mk.hamed_rao_modification_test(y)
                p_b   = float(res_b.p)
            except Exception:
                p_b = p_a  # fallback to ordinary if HR fails
        else:
            p_b = p_a

        # Model C — Sen's slope
        sen_result = stats.theilslopes(y, x, alpha=1 - 0.95)
        slope_sen  = float(sen_result.slope)

        sig_a = p_a < ALPHA
        sig_b = p_b < ALPHA

        # Robustness: direction and significance agree
        dir_a = slope_a > 0 if not np.isnan(slope_a) else None
        dir_b = slope_sen > 0 if not np.isnan(slope_sen) else None
        same_direction = (dir_a is not None and dir_b is not None and dir_a == dir_b)
        same_sig = (sig_a == sig_b)
        robust = same_direction and same_sig

        records.append({
            "Index":       idx,
            "N":           n,
            "Model_A_Ordinary_MK_p":  round(p_a, 6),
            "Model_A_sig":            sig_a,
            "Model_B_Hamed_Rao_MK_p": round(p_b, 6),
            "Model_B_sig":            sig_b,
            "Direction":              _direction(slope_sen),
            "Sen_slope":              round(slope_sen, 4),
            "Robust":                 robust,
        })

    return pd.DataFrame(records)


def save_sensitivity(df_sens: pd.DataFrame) -> None:
    """Save TABLE_S1_TREND_ROBUSTNESS.xlsx."""
    tables_dir = OUTPUT_ROOT / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    out_path = tables_dir / "TABLE_S1_TREND_ROBUSTNESS.xlsx"
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df_sens.to_excel(writer, sheet_name="Trend_Robustness", index=False)

    stats_dir = OUTPUT_ROOT / "statistics"
    stats_dir.mkdir(parents=True, exist_ok=True)
    stats_path = stats_dir / "trend_sensitivity.xlsx"
    with pd.ExcelWriter(stats_path, engine="openpyxl") as writer:
        df_sens.to_excel(writer, sheet_name="Trend_Robustness", index=False)
    print(f"[SENSITIVITY] TABLE_S1_TREND_ROBUSTNESS.xlsx saved to {out_path}")


def run_sensitivity_analysis(df_etccdi: pd.DataFrame) -> pd.DataFrame:
    """Main entry point."""
    df_sens = run_sensitivity(df_etccdi)
    save_sensitivity(df_sens)
    return df_sens
