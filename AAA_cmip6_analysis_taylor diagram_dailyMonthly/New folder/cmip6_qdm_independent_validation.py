"""
CMIP6 rainfall QDM independent-validation workflow.

This script rewrites the original full-period assessment into a leakage-aware
calibration/validation design:

* QDM transfer functions are estimated only from 1981-2000 observations and
  raw CMIP6 historical simulations.
* The frozen transfer functions are applied to raw CMIP6 data for 2001-2014.
* All principal performance statistics are reported for the independent
  validation period only.

Inputs are daily CSV files with YEAR, MONTH, DAY, and station columns.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    HAS_MATPLOTLIB = True
except ModuleNotFoundError:
    plt = None
    HAS_MATPLOTLIB = False


CAL_START = "1981-01-01"
CAL_END = "2000-12-31"
VAL_START = "2001-01-01"
VAL_END = "2014-12-31"
WET_DAY_THRESHOLD = 1.0
MIN_VALID_PAIRS = 30
MISSING_FLAGS = [-99, -999, -9999, -9.99e20, 9.99e20, 1e20]

MODEL_PALETTE = {
    "ACCESS-ESM1-5": "#0072B2",
    "CanESM5": "#D55E00",
    "CESM2": "#009E73",
    "EC-Earth3": "#CC79A7",
    "MIROC6": "#E69F00",
    "MME": "#000000",
}


@dataclass(frozen=True)
class FileInventory:
    observed: Path
    raw: Dict[str, Path]
    provided_bc: Dict[str, Path]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Independent validation of QDM-corrected CMIP6 rainfall."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path(r"D:\ClaudeWork\AAA_cmip6_analysis_taylor diagram_dailyMonthly"),
        help="Folder containing observed, raw pr_day, and optional bc_pr_day CSV files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "qdm_independent_validation_results",
        help="Folder where outputs will be written.",
    )
    parser.add_argument("--cal-start", default=CAL_START)
    parser.add_argument("--cal-end", default=CAL_END)
    parser.add_argument("--val-start", default=VAL_START)
    parser.add_argument("--val-end", default=VAL_END)
    parser.add_argument(
        "--no-pdf",
        action="store_true",
        help="Write PNG figures only. By default PNG and PDF are both written.",
    )
    return parser.parse_args()


def model_name(path: Path) -> str:
    stem = path.stem
    stem = re.sub(r"^bc_", "", stem, flags=re.IGNORECASE)
    stem = re.sub(r"^pr_day_", "", stem, flags=re.IGNORECASE)
    stem = re.sub(r"^pr_", "", stem, flags=re.IGNORECASE)
    match = re.search(r"(.+?)_historical_", stem, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    parts = stem.split("_")
    return parts[0]


def discover_files(input_dir: Path) -> FileInventory:
    csvs = sorted(input_dir.glob("*.csv"))
    observed = [p for p in csvs if "observed" in p.name.lower()]
    if not observed:
        raise FileNotFoundError(f"No observed CSV found in {input_dir}")
    raw = {}
    provided_bc = {}
    for path in csvs:
        lower = path.name.lower()
        if lower.startswith("pr_day_"):
            raw[model_name(path)] = path
        elif lower.startswith("bc_pr_day_"):
            provided_bc[model_name(path)] = path
    if not raw:
        raise FileNotFoundError(f"No raw pr_day CSV files found in {input_dir}")
    return FileInventory(observed=observed[0], raw=raw, provided_bc=provided_bc)


def load_daily_csv(path: Path, station_filter: Optional[Sequence[str]] = None) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]
    required = {"YEAR", "MONTH", "DAY"}
    if not required.issubset(df.columns):
        missing = ", ".join(sorted(required - set(df.columns)))
        raise ValueError(f"{path.name} is missing required columns: {missing}")

    for flag in MISSING_FLAGS:
        df = df.replace(flag, np.nan)
    dates = pd.to_datetime(
        {"year": df["YEAR"], "month": df["MONTH"], "day": df["DAY"]},
        errors="coerce",
    )
    station_cols = [c for c in df.columns if c not in required]
    if station_filter is not None:
        keep = set(map(str, station_filter))
        station_cols = [c for c in station_cols if c in keep]
    out = df.loc[:, station_cols].apply(pd.to_numeric, errors="coerce")
    out = out.mask(out < 0)
    out.index = dates
    out = out.loc[out.index.notna()].sort_index()
    out = out[~out.index.duplicated(keep="first")]
    return out


def period_slice(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    return df.loc[pd.Timestamp(start) : pd.Timestamp(end)]


def monthly_sum(df: pd.DataFrame, min_fraction: float = 0.8) -> pd.DataFrame:
    def valid_sum(group: pd.DataFrame) -> pd.Series:
        required = int(math.ceil(min_fraction * len(group)))
        return group.sum(axis=0, min_count=required)

    return df.resample("MS").apply(valid_sum)


def empirical_cdf_position(values: np.ndarray, x: float) -> float:
    clean = np.sort(values[np.isfinite(values)])
    if clean.size == 0 or not np.isfinite(x):
        return np.nan
    rank = np.searchsorted(clean, x, side="right")
    return (rank - 0.5) / clean.size if rank > 0 else 0.5 / clean.size


def quantile(values: np.ndarray, p: float) -> float:
    clean = values[np.isfinite(values)]
    if clean.size == 0 or not np.isfinite(p):
        return np.nan
    return float(np.quantile(clean, np.clip(p, 0.001, 0.999), method="linear"))


def qdm_correct_series(
    obs_cal: pd.Series,
    mod_cal: pd.Series,
    mod_target: pd.Series,
    wet_day_threshold: float = WET_DAY_THRESHOLD,
) -> pd.Series:
    """Apply a calibration-only multiplicative QDM transfer to precipitation.

    For each calendar month and station, ratios are estimated from calibration
    distributions only: ratio(p) = Q_obs_cal(p) / Q_mod_cal(p). The validation
    observation series is never used. Very small raw values are kept at zero to
    avoid generating artificial drizzle.
    """
    corrected = pd.Series(np.nan, index=mod_target.index, dtype=float)
    eps = 0.05

    for month in range(1, 13):
        target_idx = mod_target.index.month == month
        obs_vals = obs_cal.loc[obs_cal.index.month == month].to_numpy(dtype=float)
        mod_vals = mod_cal.loc[mod_cal.index.month == month].to_numpy(dtype=float)
        obs_vals = obs_vals[np.isfinite(obs_vals)]
        mod_vals = mod_vals[np.isfinite(mod_vals)]
        if obs_vals.size < MIN_VALID_PAIRS or mod_vals.size < MIN_VALID_PAIRS:
            continue

        for date, raw_value in mod_target.loc[target_idx].items():
            if not np.isfinite(raw_value):
                continue
            if raw_value < wet_day_threshold:
                corrected.loc[date] = 0.0
                continue
            p = empirical_cdf_position(mod_vals, float(raw_value))
            q_obs = quantile(obs_vals, p)
            q_mod = max(quantile(mod_vals, p), eps)
            ratio = np.clip(q_obs / q_mod, 0.0, 10.0)
            corrected.loc[date] = max(0.0, float(raw_value) * ratio)

    return corrected


def apply_qdm(
    obs: pd.DataFrame,
    raw: pd.DataFrame,
    cal_start: str,
    cal_end: str,
    target_start: str,
    target_end: str,
) -> pd.DataFrame:
    common = [c for c in obs.columns if c in raw.columns]
    obs_cal = period_slice(obs[common], cal_start, cal_end)
    raw_cal = period_slice(raw[common], cal_start, cal_end)
    raw_target = period_slice(raw[common], target_start, target_end)
    corrected = {}
    for station in common:
        corrected[station] = qdm_correct_series(
            obs_cal[station], raw_cal[station], raw_target[station]
        )
    return pd.DataFrame(corrected, index=raw_target.index)


def paired_arrays(obs: pd.Series, sim: pd.Series) -> Tuple[np.ndarray, np.ndarray]:
    aligned = pd.concat([obs, sim], axis=1, join="inner").dropna()
    if aligned.empty:
        return np.array([]), np.array([])
    return aligned.iloc[:, 0].to_numpy(dtype=float), aligned.iloc[:, 1].to_numpy(dtype=float)


def compute_metrics(obs: Sequence[float], sim: Sequence[float]) -> Dict[str, float]:
    o = np.asarray(obs, dtype=float)
    s = np.asarray(sim, dtype=float)
    mask = np.isfinite(o) & np.isfinite(s)
    o = o[mask]
    s = s[mask]
    null = {
        "n": float(o.size),
        "RMSE": np.nan,
        "MAE": np.nan,
        "MBE": np.nan,
        "PBIAS": np.nan,
        "r": np.nan,
        "NSE": np.nan,
        "KGE": np.nan,
        "std_obs": np.nan,
        "std_sim": np.nan,
        "mean_obs": np.nan,
        "mean_sim": np.nan,
    }
    if o.size < MIN_VALID_PAIRS:
        return null
    err = s - o
    mean_obs = float(np.mean(o))
    mean_sim = float(np.mean(s))
    std_obs = float(np.std(o, ddof=1))
    std_sim = float(np.std(s, ddof=1))
    rmse = float(np.sqrt(np.mean(err**2)))
    mae = float(np.mean(np.abs(err)))
    mbe = float(np.mean(err))
    pbias = float(100.0 * np.sum(err) / np.sum(o)) if np.sum(o) != 0 else np.nan
    r = float(np.corrcoef(o, s)[0, 1]) if std_obs > 0 and std_sim > 0 else np.nan
    nse_denom = float(np.sum((o - mean_obs) ** 2))
    nse = float(1.0 - np.sum(err**2) / nse_denom) if nse_denom > 0 else np.nan
    alpha = std_sim / std_obs if std_obs > 0 else np.nan
    beta = mean_sim / mean_obs if mean_obs != 0 else np.nan
    kge = (
        float(1.0 - np.sqrt((r - 1.0) ** 2 + (alpha - 1.0) ** 2 + (beta - 1.0) ** 2))
        if np.isfinite(r) and np.isfinite(alpha) and np.isfinite(beta)
        else np.nan
    )
    return {
        "n": float(o.size),
        "RMSE": rmse,
        "MAE": mae,
        "MBE": mbe,
        "PBIAS": pbias,
        "r": r,
        "NSE": nse,
        "KGE": kge,
        "std_obs": std_obs,
        "std_sim": std_sim,
        "mean_obs": mean_obs,
        "mean_sim": mean_sim,
    }


def metric_table(
    obs: pd.DataFrame,
    sims: Mapping[str, pd.DataFrame],
    period: str,
    scale: str,
    product: str,
) -> pd.DataFrame:
    rows = []
    for model, sim_df in sims.items():
        for station in [c for c in obs.columns if c in sim_df.columns]:
            o, s = paired_arrays(obs[station], sim_df[station])
            metrics = compute_metrics(o, s)
            rows.append(
                {
                    "period": period,
                    "scale": scale,
                    "product": product,
                    "model": model,
                    "station": station,
                    **metrics,
                }
            )
    return pd.DataFrame(rows)


def ensemble_mean(sims: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    models = list(sims)
    if not models:
        raise ValueError("No simulations supplied for ensemble.")
    common_index = sims[models[0]].index
    common_cols = list(sims[models[0]].columns)
    for model in models[1:]:
        common_index = common_index.intersection(sims[model].index)
        common_cols = [c for c in common_cols if c in sims[model].columns]
    stack = np.stack(
        [sims[m].loc[common_index, common_cols].to_numpy(dtype=float) for m in models],
        axis=0,
    )
    return pd.DataFrame(np.nanmean(stack, axis=0), index=common_index, columns=common_cols)


def build_improvement(raw_metrics: pd.DataFrame, qdm_metrics: pd.DataFrame) -> pd.DataFrame:
    keys = ["scale", "model", "station"]
    raw = raw_metrics[keys + ["RMSE", "MAE", "PBIAS", "r", "NSE", "KGE"]].rename(
        columns={c: f"{c}_raw" for c in ["RMSE", "MAE", "PBIAS", "r", "NSE", "KGE"]}
    )
    qdm = qdm_metrics[keys + ["RMSE", "MAE", "PBIAS", "r", "NSE", "KGE"]].rename(
        columns={c: f"{c}_qdm" for c in ["RMSE", "MAE", "PBIAS", "r", "NSE", "KGE"]}
    )
    out = raw.merge(qdm, on=keys, how="inner")
    for metric in ["RMSE", "MAE"]:
        out[f"{metric}_delta"] = out[f"{metric}_qdm"] - out[f"{metric}_raw"]
        out[f"{metric}_improvement_pct"] = (
            100.0 * (out[f"{metric}_raw"] - out[f"{metric}_qdm"]) / out[f"{metric}_raw"]
        )
    out["abs_PBIAS_delta"] = out["PBIAS_qdm"].abs() - out["PBIAS_raw"].abs()
    for metric in ["r", "NSE", "KGE"]:
        out[f"{metric}_delta"] = out[f"{metric}_qdm"] - out[f"{metric}_raw"]
    return out.replace([np.inf, -np.inf], np.nan)


def wilcoxon_summary(improvement: pd.DataFrame) -> pd.DataFrame:
    rows = []
    metric_specs = [
        ("RMSE", "lower"),
        ("MAE", "lower"),
        ("abs_PBIAS", "lower"),
        ("r", "higher"),
        ("NSE", "higher"),
        ("KGE", "higher"),
    ]
    for scale in sorted(improvement["scale"].unique()):
        sub_scale = improvement[improvement["scale"] == scale]
        for metric, direction in metric_specs:
            if metric == "abs_PBIAS":
                diff_by_station = (
                    sub_scale.assign(diff=sub_scale["PBIAS_qdm"].abs() - sub_scale["PBIAS_raw"].abs())
                    .groupby("station")["diff"]
                    .median()
                    .dropna()
                )
            elif direction == "lower":
                diff_by_station = (
                    sub_scale.groupby("station")[f"{metric}_delta"].median().dropna()
                )
            else:
                diff_by_station = (
                    sub_scale.groupby("station")[f"{metric}_delta"].median().dropna()
                )
            values = diff_by_station.to_numpy(dtype=float)
            if values.size < 6 or np.allclose(values, 0):
                stat = np.nan
                p_value = np.nan
            else:
                alternative = "less" if direction == "lower" else "greater"
                stat, p_value = wilcoxon_signed_rank_approx(values, alternative)
            rows.append(
                {
                    "scale": scale,
                    "metric": metric,
                    "preferred_direction": direction,
                    "n_stations": int(values.size),
                    "median_station_delta": float(np.nanmedian(values)) if values.size else np.nan,
                    "wilcoxon_statistic": float(stat) if np.isfinite(stat) else np.nan,
                    "p_value_one_sided": float(p_value) if np.isfinite(p_value) else np.nan,
                    "interpretation": (
                        "improved" if (
                            np.isfinite(p_value)
                            and p_value < 0.05
                            and ((direction == "lower" and np.nanmedian(values) < 0)
                                 or (direction == "higher" and np.nanmedian(values) > 0))
                        )
                        else "not significant"
                    ),
                }
            )
    return pd.DataFrame(rows)


def wilcoxon_signed_rank_approx(values: np.ndarray, alternative: str) -> Tuple[float, float]:
    """One-sample Wilcoxon signed-rank test using a normal approximation.

    This avoids a SciPy dependency while retaining the intended station-level
    paired non-parametric comparison. For n=12 the p-values should be reported
    as approximate and interpreted with the median difference/effect direction.
    """
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x) & (x != 0)]
    n = x.size
    if n == 0:
        return np.nan, np.nan
    abs_x = np.abs(x)
    order = np.argsort(abs_x)
    ranks = np.empty(n, dtype=float)
    sorted_abs = abs_x[order]
    i = 0
    while i < n:
        j = i + 1
        while j < n and sorted_abs[j] == sorted_abs[i]:
            j += 1
        avg_rank = (i + 1 + j) / 2.0
        ranks[order[i:j]] = avg_rank
        i = j
    w_plus = float(ranks[x > 0].sum())
    mean_w = n * (n + 1) / 4.0
    sd_w = math.sqrt(n * (n + 1) * (2 * n + 1) / 24.0)
    if sd_w == 0:
        return w_plus, np.nan
    z = (w_plus - mean_w) / sd_w
    cdf = 0.5 * math.erfc(-z / math.sqrt(2.0))
    if alternative == "greater":
        p_value = 1.0 - cdf
    elif alternative == "less":
        p_value = cdf
    else:
        p_value = 2.0 * min(cdf, 1.0 - cdf)
    return w_plus, float(np.clip(p_value, 0.0, 1.0))


def station_completeness(obs: pd.DataFrame, cal: pd.DataFrame, val: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for station in obs.columns:
        rows.append(
            {
                "station": station,
                "n_total_days": int(obs[station].shape[0]),
                "n_total_valid": int(obs[station].notna().sum()),
                "total_completeness_pct": 100.0 * obs[station].notna().mean(),
                "calibration_valid_days": int(cal[station].notna().sum()),
                "calibration_completeness_pct": 100.0 * cal[station].notna().mean(),
                "validation_valid_days": int(val[station].notna().sum()),
                "validation_completeness_pct": 100.0 * val[station].notna().mean(),
                "calibration_mean_mm_day": float(cal[station].mean()),
                "validation_mean_mm_day": float(val[station].mean()),
                "calibration_wet_day_pct": 100.0 * (cal[station] >= WET_DAY_THRESHOLD).mean(),
                "validation_wet_day_pct": 100.0 * (val[station] >= WET_DAY_THRESHOLD).mean(),
            }
        )
    return pd.DataFrame(rows)


def write_table(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig")


def pil_font(size: int = 18, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\calibrib.ttf" if bold else r"C:\Windows\Fonts\calibri.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def pil_canvas(title: str, width: int = 1800, height: int = 1050) -> Tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    draw.text((60, 40), title, fill="#111111", font=pil_font(34, bold=True))
    draw.line((60, 92, width - 60, 92), fill="#999999", width=2)
    return img, draw


def pil_save(img: Image.Image, output_dir: Path, stem: str, save_pdf: bool) -> None:
    png = output_dir / f"{stem}.png"
    img.save(png)
    if save_pdf:
        img.save(output_dir / f"{stem}.pdf", "PDF", resolution=300)


def pil_bar_chart(
    title: str,
    labels: Sequence[str],
    values: Sequence[float],
    output_dir: Path,
    stem: str,
    ylabel: str,
    save_pdf: bool,
    color: str = "#0072B2",
) -> None:
    img, draw = pil_canvas(title)
    font = pil_font(20)
    small = pil_font(16)
    left, top, right, bottom = 140, 180, 1700, 850
    draw.rectangle((left, top, right, bottom), outline="#333333", width=2)
    vals = np.asarray(values, dtype=float)
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        draw.text((left + 40, top + 80), "No finite values available.", fill="#A00000", font=font)
        pil_save(img, output_dir, stem, save_pdf)
        return
    ymin = min(0.0, float(np.nanmin(values)))
    ymax = max(0.0, float(np.nanmax(values)))
    if math.isclose(ymin, ymax):
        ymax = ymin + 1.0
    scale = (bottom - top - 40) / (ymax - ymin)
    zero_y = bottom - 20 - (0 - ymin) * scale
    draw.line((left, zero_y, right, zero_y), fill="#666666", width=2)
    n = len(labels)
    bar_w = max(12, int((right - left - 80) / max(n, 1) * 0.65))
    for i, (label, value) in enumerate(zip(labels, values)):
        if not np.isfinite(value):
            continue
        cx = left + 50 + i * (right - left - 100) / max(n - 1, 1)
        y = bottom - 20 - (float(value) - ymin) * scale
        x0, x1 = int(cx - bar_w / 2), int(cx + bar_w / 2)
        draw.rectangle((x0, min(y, zero_y), x1, max(y, zero_y)), fill=color, outline="#333333")
        draw.text((x0 - 10, bottom + 16), str(label), fill="#111111", font=small)
    draw.text((60, 500), ylabel, fill="#111111", font=font)
    draw.text((left, 120), f"Range: {ymin:.2f} to {ymax:.2f}", fill="#555555", font=small)
    pil_save(img, output_dir, stem, save_pdf)


def pil_lines_figure(title: str, lines: Sequence[str], output_dir: Path, stem: str, save_pdf: bool) -> None:
    img, draw = pil_canvas(title)
    font = pil_font(23)
    y = 150
    for line in lines:
        draw.text((80, y), line, fill="#111111", font=font)
        y += 42
    pil_save(img, output_dir, stem, save_pdf)


def save_figure(fig: plt.Figure, output_dir: Path, stem: str, save_pdf: bool = True) -> None:
    png = output_dir / f"{stem}.png"
    fig.savefig(png, dpi=300, bbox_inches="tight")
    if save_pdf:
        fig.savefig(output_dir / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)


def figure_framework(output_dir: Path, save_pdf: bool) -> None:
    if not HAS_MATPLOTLIB:
        pil_lines_figure(
            "Calibration-Validation Framework",
            [
                "1981-2000: calibration period.",
                "QDM transfer functions are fitted for each model, station, and calendar month.",
                "2001-2014: independent validation period.",
                "The frozen QDM transfer functions are applied to raw CMIP6 rainfall.",
                "Validation observations are not used to refit, update, or optimize QDM.",
            ],
            output_dir,
            "Fig2_calibration_validation_framework",
            save_pdf,
        )
        return
    fig, ax = plt.subplots(figsize=(10, 3.2))
    ax.axis("off")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 24)
    ax.plot([5, 95], [12, 12], color="#333333", lw=2)
    ax.axvspan(5, 57, ymin=0.42, ymax=0.58, color="#DDEBF7")
    ax.axvspan(57, 95, ymin=0.42, ymax=0.58, color="#E2F0D9")
    ax.plot([57, 57], [8, 16], color="#333333", lw=1.5)
    ax.text(31, 16, "Calibration: 1981-2000", ha="center", va="center", weight="bold")
    ax.text(31, 8, "Fit QDM transfer functions", ha="center", va="center")
    ax.text(76, 16, "Independent validation: 2001-2014", ha="center", va="center", weight="bold")
    ax.text(76, 8, "Apply frozen QDM; compute metrics", ha="center", va="center")
    ax.text(57, 20, "No validation observations used for QDM fitting", ha="center", color="#A00000")
    ax.text(5, 4, "1981", ha="center")
    ax.text(57, 4, "2000/2001", ha="center")
    ax.text(95, 4, "2014", ha="center")
    save_figure(fig, output_dir, "Fig2_calibration_validation_framework", save_pdf)


def figure_observed_characteristics(
    obs_cal: pd.DataFrame, obs_val: pd.DataFrame, output_dir: Path, save_pdf: bool
) -> None:
    cal_month = obs_cal.groupby(obs_cal.index.month).mean().mean(axis=1)
    val_month = obs_val.groupby(obs_val.index.month).mean().mean(axis=1)
    station_means = pd.DataFrame(
        {
            "Calibration": obs_cal.mean(axis=0),
            "Validation": obs_val.mean(axis=0),
        }
    )
    if not HAS_MATPLOTLIB:
        diff = station_means["Validation"] - station_means["Calibration"]
        pil_bar_chart(
            "Observed Rainfall: Validation Minus Calibration Mean",
            list(diff.index),
            list(diff.values),
            output_dir,
            "Fig3_observed_calibration_validation_characteristics",
            "Mean rainfall difference (mm/day)",
            save_pdf,
            color="#59A14F",
        )
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    axes[0].plot(cal_month.index, cal_month.values, marker="o", label="1981-2000")
    axes[0].plot(val_month.index, val_month.values, marker="s", label="2001-2014")
    axes[0].set_xticks(range(1, 13))
    axes[0].set_xlabel("Month")
    axes[0].set_ylabel("Mean rainfall (mm day$^{-1}$)")
    axes[0].set_title("Regional Monthly Cycle")
    axes[0].legend(frameon=False)
    station_means.plot(kind="bar", ax=axes[1], color=["#4E79A7", "#59A14F"])
    axes[1].set_xlabel("Station")
    axes[1].set_ylabel("Mean rainfall (mm day$^{-1}$)")
    axes[1].set_title("Station Mean Rainfall")
    axes[1].tick_params(axis="x", rotation=45)
    fig.suptitle("Observed Rainfall Characteristics by Analysis Period", weight="bold")
    save_figure(fig, output_dir, "Fig3_observed_calibration_validation_characteristics", save_pdf)


def figure_validation_performance(
    improvement: pd.DataFrame, output_dir: Path, save_pdf: bool
) -> None:
    daily = improvement[improvement["scale"] == "daily"]
    summary = (
        daily.groupby("model")[["RMSE_raw", "RMSE_qdm", "KGE_raw", "KGE_qdm"]]
        .median()
        .sort_index()
    )
    if not HAS_MATPLOTLIB:
        vals = summary["RMSE_qdm"] - summary["RMSE_raw"]
        pil_bar_chart(
            "Raw vs QDM Validation Performance: RMSE Change",
            list(summary.index),
            list(vals.values),
            output_dir,
            "Fig4_raw_vs_qdm_validation_performance",
            "RMSE QDM - Raw (mm/day)",
            save_pdf,
            color="#0072B2",
        )
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    x = np.arange(len(summary.index))
    width = 0.38
    axes[0].bar(x - width / 2, summary["RMSE_raw"], width, label="Raw", color="#D55E00")
    axes[0].bar(x + width / 2, summary["RMSE_qdm"], width, label="QDM", color="#0072B2")
    axes[0].set_xticks(x, summary.index, rotation=35, ha="right")
    axes[0].set_ylabel("Median station RMSE (mm day$^{-1}$)")
    axes[0].set_title("Error")
    axes[0].legend(frameon=False)
    axes[1].bar(x - width / 2, summary["KGE_raw"], width, label="Raw", color="#D55E00")
    axes[1].bar(x + width / 2, summary["KGE_qdm"], width, label="QDM", color="#0072B2")
    axes[1].axhline(0, color="#555555", lw=0.8)
    axes[1].set_xticks(x, summary.index, rotation=35, ha="right")
    axes[1].set_ylabel("Median station KGE")
    axes[1].set_title("Hydrological Performance")
    axes[1].legend(frameon=False)
    fig.suptitle("Raw vs QDM Validation Performance Across Individual Models", weight="bold")
    save_figure(fig, output_dir, "Fig4_raw_vs_qdm_validation_performance", save_pdf)


def figure_spatial_improvement(
    improvement: pd.DataFrame, output_dir: Path, save_pdf: bool
) -> None:
    daily = improvement[improvement["scale"] == "daily"]
    station = daily.groupby("station")[["RMSE_improvement_pct", "KGE_delta"]].median()
    if not HAS_MATPLOTLIB:
        pil_bar_chart(
            "Station-Level QDM Improvement During Validation",
            list(station.index),
            list(station["RMSE_improvement_pct"].values),
            output_dir,
            "Fig5_station_level_qdm_improvement",
            "Median RMSE improvement (%)",
            save_pdf,
            color="#0072B2",
        )
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    station["RMSE_improvement_pct"].plot(kind="bar", ax=axes[0], color="#0072B2")
    axes[0].axhline(0, color="#333333", lw=0.8)
    axes[0].set_ylabel("Median RMSE improvement (%)")
    axes[0].set_xlabel("Station")
    axes[0].set_title("Error Reduction")
    station["KGE_delta"].plot(kind="bar", ax=axes[1], color="#59A14F")
    axes[1].axhline(0, color="#333333", lw=0.8)
    axes[1].set_ylabel("Median KGE change")
    axes[1].set_xlabel("Station")
    axes[1].set_title("KGE Change")
    for ax in axes:
        ax.tick_params(axis="x", rotation=45)
    fig.suptitle("Spatial Variation in QDM Performance During Validation", weight="bold")
    save_figure(fig, output_dir, "Fig5_station_level_qdm_improvement", save_pdf)


def figure_mme_vs_models(
    qdm_metrics: pd.DataFrame, mme_metrics: pd.DataFrame, output_dir: Path, save_pdf: bool
) -> None:
    daily = qdm_metrics[qdm_metrics["scale"] == "daily"]
    mme_daily = mme_metrics[mme_metrics["scale"] == "daily"]
    if not HAS_MATPLOTLIB:
        model_median = daily.groupby("model")["KGE"].median().sort_index()
        mme_kge = float(mme_daily["KGE"].median())
        labels = list(model_median.index) + ["MME"]
        values = list(model_median.values) + [mme_kge]
        pil_bar_chart(
            "Individual QDM-Corrected Models Versus Unweighted MME",
            labels,
            values,
            output_dir,
            "Fig6_individual_models_vs_unweighted_mme",
            "Median daily validation KGE",
            save_pdf,
            color="#59A14F",
        )
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    daily.boxplot(column="RMSE", by="model", ax=axes[0], grid=False, rot=35)
    axes[0].axhline(mme_daily["RMSE"].median(), color="#000000", lw=2, label="MME median")
    axes[0].set_title("RMSE Distribution")
    axes[0].set_ylabel("RMSE (mm day$^{-1}$)")
    axes[0].legend(frameon=False)
    daily.boxplot(column="KGE", by="model", ax=axes[1], grid=False, rot=35)
    axes[1].axhline(mme_daily["KGE"].median(), color="#000000", lw=2, label="MME median")
    axes[1].set_title("KGE Distribution")
    axes[1].set_ylabel("KGE")
    axes[1].legend(frameon=False)
    fig.suptitle("Individual QDM-Corrected Models Versus Unweighted MME", weight="bold")
    save_figure(fig, output_dir, "Fig6_individual_models_vs_unweighted_mme", save_pdf)


def figure_taylor_daily(
    obs_val: pd.DataFrame,
    raw_val: Mapping[str, pd.DataFrame],
    qdm_val: Mapping[str, pd.DataFrame],
    output_dir: Path,
    save_pdf: bool,
) -> None:
    if not HAS_MATPLOTLIB:
        rows = []
        for model in sorted(raw_val):
            raw_vals = []
            qdm_vals = []
            for station in obs_val.columns:
                o, s_raw = paired_arrays(obs_val[station], raw_val[model][station])
                _, s_qdm = paired_arrays(obs_val[station], qdm_val[model][station])
                raw_vals.append(compute_metrics(o, s_raw)["r"])
                qdm_vals.append(compute_metrics(o, s_qdm)["r"])
            rows.append(
                f"{model}: median r Raw={np.nanmedian(raw_vals):.3f}, "
                f"QDM={np.nanmedian(qdm_vals):.3f}"
            )
        pil_lines_figure(
            "Taylor-Diagram Summary, Daily Validation Period",
            [
                "Matplotlib is unavailable in this runtime, so this fallback figure",
                "reports the Taylor-diagram correlation component by model.",
                "Full Taylor coordinates are still encoded in Table3 via r and std_sim.",
                "",
                *rows,
            ],
            output_dir,
            "Fig1_taylor_diagram_daily_validation",
            save_pdf,
        )
        return
    fig, ax = plt.subplots(figsize=(7, 6.5))
    obs_std = np.nanmean([obs_val[c].std(ddof=1) for c in obs_val.columns])
    max_std = obs_std * 2.0
    theta = np.linspace(0, np.pi / 2, 200)
    for r in [0.5, 1.0, 1.5, 2.0]:
        ax.plot(obs_std * r * np.cos(theta), obs_std * r * np.sin(theta), color="#DDDDDD", lw=0.8)
    for corr in [0.2, 0.4, 0.6, 0.8, 0.9, 0.95, 0.99]:
        angle = math.acos(corr)
        ax.plot([0, max_std * math.cos(angle)], [0, max_std * math.sin(angle)], color="#EEEEEE", lw=0.8)
        ax.text(max_std * 1.03 * math.cos(angle), max_std * 1.03 * math.sin(angle), f"{corr:.2f}", fontsize=8)
    ax.plot(obs_std, 0, marker="*", ms=14, color="black", label="Observed")
    for model in sorted(raw_val):
        for label, sims, marker in [("Raw", raw_val, "^"), ("QDM", qdm_val, "o")]:
            xs = []
            ys = []
            for station in obs_val.columns:
                o, s = paired_arrays(obs_val[station], sims[model][station])
                met = compute_metrics(o, s)
                if np.isfinite(met["r"]) and np.isfinite(met["std_sim"]):
                    angle = math.acos(np.clip(met["r"], 0, 1))
                    xs.append(met["std_sim"] * math.cos(angle))
                    ys.append(met["std_sim"] * math.sin(angle))
            if xs:
                ax.scatter(
                    xs,
                    ys,
                    s=28,
                    marker=marker,
                    alpha=0.75,
                    color=MODEL_PALETTE.get(model, "#666666"),
                    label=f"{model} {label}",
                )
    ax.set_xlim(0, max_std)
    ax.set_ylim(0, max_std)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Standard deviation (mm day$^{-1}$)")
    ax.set_ylabel("Standard deviation (mm day$^{-1}$)")
    ax.set_title("Taylor Diagram, Daily Validation Period", weight="bold")
    handles, labels = ax.get_legend_handles_labels()
    dedup = dict(zip(labels, handles))
    ax.legend(dedup.values(), dedup.keys(), fontsize=7, frameon=False, ncol=2, loc="upper right")
    save_figure(fig, output_dir, "Fig1_taylor_diagram_daily_validation", save_pdf)


def write_excel_workbook(tables: Mapping[str, pd.DataFrame], path: Path) -> None:
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet, df in tables.items():
            clean = re.sub(r"[^A-Za-z0-9_ ]", "", sheet)[:31]
            df.to_excel(writer, sheet_name=clean, index=False)


def main() -> None:
    args = parse_args()
    input_dir = args.input_dir
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    save_pdf = not args.no_pdf

    inventory = discover_files(input_dir)
    obs = load_daily_csv(inventory.observed)
    stations = list(obs.columns)
    raw = {
        model: load_daily_csv(path, stations)
        for model, path in sorted(inventory.raw.items())
    }
    common_models = sorted(raw)
    common_stations = [
        station
        for station in stations
        if all(station in raw[model].columns for model in common_models)
    ]
    obs = obs[common_stations]
    raw = {model: df[common_stations] for model, df in raw.items()}

    obs_cal = period_slice(obs, args.cal_start, args.cal_end)
    obs_val = period_slice(obs, args.val_start, args.val_end)
    raw_cal = {
        model: period_slice(df, args.cal_start, args.cal_end)
        for model, df in raw.items()
    }
    raw_val = {
        model: period_slice(df, args.val_start, args.val_end)
        for model, df in raw.items()
    }
    qdm_val = {
        model: apply_qdm(obs, df, args.cal_start, args.cal_end, args.val_start, args.val_end)
        for model, df in raw.items()
    }

    raw_val_m = {model: monthly_sum(df) for model, df in raw_val.items()}
    qdm_val_m = {model: monthly_sum(df) for model, df in qdm_val.items()}
    obs_val_m = monthly_sum(obs_val)

    raw_metrics_d = metric_table(obs_val, raw_val, "validation_2001_2014", "daily", "raw")
    qdm_metrics_d = metric_table(obs_val, qdm_val, "validation_2001_2014", "daily", "qdm_refit_free")
    raw_metrics_m = metric_table(obs_val_m, raw_val_m, "validation_2001_2014", "monthly", "raw")
    qdm_metrics_m = metric_table(obs_val_m, qdm_val_m, "validation_2001_2014", "monthly", "qdm_refit_free")
    raw_metrics = pd.concat([raw_metrics_d, raw_metrics_m], ignore_index=True)
    qdm_metrics = pd.concat([qdm_metrics_d, qdm_metrics_m], ignore_index=True)
    improvement = build_improvement(raw_metrics, qdm_metrics)

    mme_raw = {"MME": ensemble_mean(raw_val)}
    mme_qdm = {"MME": ensemble_mean(qdm_val)}
    mme_raw_m = {"MME": monthly_sum(mme_raw["MME"])}
    mme_qdm_m = {"MME": monthly_sum(mme_qdm["MME"])}
    mme_metrics = pd.concat(
        [
            metric_table(obs_val, mme_raw, "validation_2001_2014", "daily", "raw_mme"),
            metric_table(obs_val, mme_qdm, "validation_2001_2014", "daily", "qdm_mme"),
            metric_table(obs_val_m, mme_raw_m, "validation_2001_2014", "monthly", "raw_mme"),
            metric_table(obs_val_m, mme_qdm_m, "validation_2001_2014", "monthly", "qdm_mme"),
        ],
        ignore_index=True,
    )
    tests = wilcoxon_summary(improvement)
    completeness = station_completeness(obs, obs_cal, obs_val)

    model_inventory = pd.DataFrame(
        {
            "model": common_models,
            "raw_file": [str(inventory.raw[m]) for m in common_models],
            "provided_bc_file_not_used_for_principal_validation": [
                str(inventory.provided_bc.get(m, "")) for m in common_models
            ],
            "principal_qdm_source": "recomputed from calibration period only",
        }
    )

    all_validation_metrics = pd.concat([raw_metrics, qdm_metrics, mme_metrics], ignore_index=True)
    summary = (
        all_validation_metrics.groupby(["scale", "product", "model"])[
            ["RMSE", "MAE", "PBIAS", "r", "NSE", "KGE"]
        ]
        .median()
        .reset_index()
    )

    tables = {
        "Table1_station_completeness": completeness,
        "Table2_model_inventory": model_inventory,
        "Table3_validation_metrics": all_validation_metrics,
        "Table4_qdm_changes": improvement,
        "Table5_mme_comparison": summary,
        "Statistical_tests": tests,
    }
    for name, df in tables.items():
        write_table(df, output_dir / f"{name}.csv")
    write_excel_workbook(tables, output_dir / "CMIP6_QDM_independent_validation_tables.xlsx")

    figure_taylor_daily(obs_val, raw_val, qdm_val, output_dir, save_pdf)
    figure_framework(output_dir, save_pdf)
    figure_observed_characteristics(obs_cal, obs_val, output_dir, save_pdf)
    figure_validation_performance(improvement, output_dir, save_pdf)
    figure_spatial_improvement(improvement, output_dir, save_pdf)
    figure_mme_vs_models(qdm_metrics, mme_metrics[mme_metrics["product"] == "qdm_mme"], output_dir, save_pdf)

    metadata = {
        "input_dir": str(input_dir),
        "observed_file": str(inventory.observed),
        "calibration_period": [args.cal_start, args.cal_end],
        "validation_period": [args.val_start, args.val_end],
        "models": common_models,
        "stations": common_stations,
        "qdm_note": (
            "Principal QDM series were recomputed from observed and raw CMIP6 "
            "calibration data only. Provided bc_pr_day files were inventoried "
            "but not used for principal independent-validation metrics."
        ),
    }
    (output_dir / "analysis_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("Independent-validation workflow complete.")
    print(f"Outputs written to: {output_dir}")
    print("Median validation summary:")
    print(summary.to_string(index=False, max_rows=30))


if __name__ == "__main__":
    main()
