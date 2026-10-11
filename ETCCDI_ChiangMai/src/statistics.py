"""
statistics.py — Descriptive statistics for 11 ETCCDI annual series.

Computes: N, Mean, Median, SD, Min, Max, Q25, Q75, IQR, CV
Produces TABLE_04_DESCRIPTIVE_STATISTICS.xlsx
"""
import sys
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import OUTPUT_ROOT, INDICES, UNITS


def compute_descriptive_stats(df_etccdi: pd.DataFrame) -> pd.DataFrame:
    """
    Compute descriptive statistics for each ETCCDI index.

    Args:
        df_etccdi: DataFrame with columns [Year, PRCPTOT, ..., R99p]

    Returns:
        DataFrame with one row per index and columns:
        Index, Unit, N, Mean, Median, SD, Min, Max, Q25, Q75, IQR, CV_%
    """
    records = []
    for idx in INDICES:
        if idx not in df_etccdi.columns:
            continue
        series = df_etccdi[idx].dropna()
        n = len(series)
        if n == 0:
            records.append({"Index": idx, "Unit": UNITS.get(idx, ""), "N": 0})
            continue

        mean   = float(series.mean())
        median = float(series.median())
        sd     = float(series.std(ddof=1))
        mn     = float(series.min())
        mx     = float(series.max())
        q25    = float(series.quantile(0.25))
        q75    = float(series.quantile(0.75))
        iqr    = q75 - q25
        cv     = (sd / mean * 100) if mean != 0 else np.nan

        records.append({
            "Index":  idx,
            "Unit":   UNITS.get(idx, ""),
            "N":      n,
            "Mean":   round(mean, 2),
            "Median": round(median, 2),
            "SD":     round(sd, 2),
            "Min":    round(mn, 2),
            "Max":    round(mx, 2),
            "Q25":    round(q25, 2),
            "Q75":    round(q75, 2),
            "IQR":    round(iqr, 2),
            "CV_%":   round(cv, 1),
        })
    return pd.DataFrame(records)


def save_descriptive_stats(df_stats: pd.DataFrame) -> None:
    """Write TABLE_04_DESCRIPTIVE_STATISTICS.xlsx."""
    tables_dir = OUTPUT_ROOT / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    out_path = tables_dir / "TABLE_04_DESCRIPTIVE_STATISTICS.xlsx"
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df_stats.to_excel(writer, sheet_name="Descriptive_Stats", index=False)
    print(f"[STATS] TABLE_04_DESCRIPTIVE_STATISTICS.xlsx saved to {out_path}")


def run_statistics(df_etccdi: pd.DataFrame) -> pd.DataFrame:
    """Main entry point. Returns the stats DataFrame."""
    df_stats = compute_descriptive_stats(df_etccdi)
    save_descriptive_stats(df_stats)
    return df_stats
