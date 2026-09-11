"""
qdm_parametric_nonparametric.py

Publication-oriented comparison of parametric and non-parametric QDM.

The script estimates every transfer function on the calibration period only,
then applies it to calibration and validation blocks without using validation
observations in any fitted threshold, distribution, or quantile function.

Outputs
-------
out/qdm_p_np/
    corrected/*.csv
    QDM_parametric_nonparametric_results.xlsx
    station_metrics.csv
    fit_diagnostics.csv
    summary.csv
    figures/Figure_QDM_method_comparison.{png,pdf}
    figures/Figure_QDM_metric_heatmap.{png,pdf}
"""
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("MPLCONFIGDIR", str(_WORKSPACE_ROOT / ".matplotlib_cache"))

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only on incomplete envs
    yaml = None

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:  # pragma: no cover - exercised only on incomplete envs
    matplotlib = None
    plt = None

try:
    from scipy import stats
except ImportError:  # pragma: no cover - exercised only on incomplete envs
    stats = None

io_layer = None
M = None
Provenance = None


METHODS = ("QDM_NP_annual", "QDM_NP_monthly", "QDM_P_annual", "QDM_P_monthly")
DISTS = ("gamma", "genextreme", "weibull_min", "lognorm", "pearson3")
MM = 1 / 25.4
MAX_PARAMETRIC_FIT_N = 2000


@dataclass
class FittedDist:
    name: str
    params: tuple[float, ...]
    aic: float
    ks_d: float
    ks_p: float
    n: int
    n_params: int

    @property
    def scipy_dist(self):
        return getattr(stats, self.name)

    def cdf(self, x: np.ndarray) -> np.ndarray:
        return self.scipy_dist.cdf(x, *self.params)

    def ppf(self, p: np.ndarray) -> np.ndarray:
        return self.scipy_dist.ppf(p, *self.params)


@dataclass
class Transfer:
    model: str
    station: str
    family: str
    grouping: str
    group: str
    wet_threshold_obs: float
    wet_threshold_model: float
    obs_sorted: np.ndarray
    mod_sorted: np.ndarray
    obs_fit: FittedDist | None
    mod_fit: FittedDist | None
    usable: bool
    note: str


def plotting_positions(n: int) -> np.ndarray:
    return (np.arange(1, n + 1) - 0.5) / n


def ecdf_prob(sorted_ref: np.ndarray, x: np.ndarray) -> np.ndarray:
    pp = plotting_positions(sorted_ref.size)
    return np.interp(x, sorted_ref, pp, left=pp[0], right=pp[-1])


def inv_ecdf(sorted_ref: np.ndarray, p: np.ndarray) -> np.ndarray:
    pp = plotting_positions(sorted_ref.size)
    return np.interp(np.clip(p, pp[0], pp[-1]), pp, sorted_ref)


def group_keys(index: pd.DatetimeIndex, grouping: str) -> np.ndarray:
    if grouping == "monthly":
        return np.array([f"{m:02d}" for m in index.month])
    if grouping == "annual":
        return np.full(len(index), "all")
    raise ValueError(f"unknown grouping {grouping!r}; use annual or monthly")


def period_mask(index: pd.DatetimeIndex, years: list[int]) -> np.ndarray:
    return (index.year >= int(years[0])) & (index.year <= int(years[1]))


def finite_positive(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    return x[np.isfinite(x) & (x > 0)]


def fit_distribution(x: np.ndarray, min_n: int,
                     max_n: int = MAX_PARAMETRIC_FIT_N) -> FittedDist | None:
    x = finite_positive(x)
    if x.size < min_n or np.nanstd(x) <= 0:
        return None
    if x.size > max_n:
        sx = np.sort(x)
        pos = np.linspace(0, sx.size - 1, max_n).round().astype(int)
        x_fit = sx[pos]
    else:
        x_fit = x

    best: FittedDist | None = None
    for name in DISTS:
        dist = getattr(stats, name)
        try:
            if name in {"gamma", "weibull_min", "lognorm"}:
                params = dist.fit(x_fit, floc=0)
                n_params = len(params) - 1
            else:
                params = dist.fit(x_fit)
                n_params = len(params)
            logpdf = dist.logpdf(x, *params)
            if not np.all(np.isfinite(logpdf)):
                continue
            aic = float(2 * n_params - 2 * np.sum(logpdf))
            ks = stats.kstest(x, name, args=params)
            fit = FittedDist(
                name=name,
                params=tuple(float(p) for p in params),
                aic=aic,
                ks_d=float(ks.statistic),
                ks_p=float(ks.pvalue),
                n=int(x.size),
                n_params=n_params,
            )
            if best is None or (fit.aic, fit.n_params, fit.name) < (
                best.aic, best.n_params, best.name
            ):
                best = fit
        except Exception:
            continue
    return best


def wet_arrays(obs_cal: np.ndarray, mod_cal: np.ndarray, wet_thr: float,
               min_wet: int, frequency_adaptation: bool) -> tuple[float, np.ndarray, np.ndarray, bool, str]:
    o = obs_cal[np.isfinite(obs_cal)]
    m = mod_cal[np.isfinite(mod_cal)]
    if o.size == 0 or m.size == 0:
        return wet_thr, np.array([]), np.array([]), False, "empty calibration block"

    obs_wet = np.sort(o[o >= wet_thr])
    obs_wet_fraction = float(obs_wet.size / o.size)
    note = ""

    if frequency_adaptation and np.isfinite(obs_wet_fraction):
        t_model = float(np.quantile(m, 1.0 - obs_wet_fraction))
        t_model = max(t_model, 0.0)
        if float(np.mean(m > 0.0)) < obs_wet_fraction:
            t_model = 0.0
            note = "model has fewer non-zero days than observed wet days"
    else:
        t_model = wet_thr
        note = "frequency adaptation disabled"

    # Values at or below the frozen model threshold are dry. This makes the
    # adapted model wet-day count no larger than the observed count when ties
    # occur at the empirical threshold.
    mod_wet = np.sort(m[m > t_model])
    usable = obs_wet.size >= min_wet and mod_wet.size >= min_wet
    if not usable:
        note = (note + "; " if note else "") + (
            f"insufficient wet days obs={obs_wet.size}, model={mod_wet.size}"
        )
    return t_model, obs_wet, mod_wet, usable, note


def fit_transfer(obs_cal: np.ndarray, mod_cal: np.ndarray, cfg: dict,
                 model: str, station: str, family: str, grouping: str,
                 group: str) -> Transfer:
    wet_thr = float(cfg["data"]["wet_threshold_mm"])
    min_wet = int(cfg["qdm"].get("min_wet_days_calibration", 30))
    t_model, obs_wet, mod_wet, usable, note = wet_arrays(
        obs_cal, mod_cal, wet_thr, min_wet,
        bool(cfg["qdm"].get("frequency_adaptation", True)),
    )

    obs_fit = mod_fit = None
    if usable and family == "parametric":
        max_n = int(cfg.get("qdm_parametric", {}).get(
            "max_fit_sample", MAX_PARAMETRIC_FIT_N
        ))
        obs_fit = fit_distribution(obs_wet, min_wet, max_n)
        mod_fit = fit_distribution(mod_wet, min_wet, max_n)
        usable = obs_fit is not None and mod_fit is not None
        if not usable:
            note = (note + "; " if note else "") + "parametric fit failed"

    return Transfer(
        model=model,
        station=station,
        family=family,
        grouping=grouping,
        group=group,
        wet_threshold_obs=wet_thr,
        wet_threshold_model=t_model,
        obs_sorted=obs_wet,
        mod_sorted=mod_wet,
        obs_fit=obs_fit,
        mod_fit=mod_fit,
        usable=usable,
        note=note,
    )


def _safe_probs(p: np.ndarray) -> np.ndarray:
    eps = 1e-6
    return np.clip(np.asarray(p, dtype=float), eps, 1.0 - eps)


def apply_transfer(tf: Transfer, target_values: np.ndarray, cfg: dict) -> tuple[np.ndarray, dict]:
    x = np.asarray(target_values, dtype=float)
    out = np.zeros_like(x, dtype=float)
    out[~np.isfinite(x)] = np.nan
    stats_row = {
        "n_input": int(np.isfinite(x).sum()),
        "n_wet_target": 0,
        "n_delta_clipped_low": 0,
        "n_delta_clipped_high": 0,
        "n_output_capped": 0,
        "output_cap_mm": np.nan,
        "max_output_mm": np.nan,
    }
    if not tf.usable:
        return out, stats_row

    thr = tf.wet_threshold_model
    wet = np.isfinite(x) & (x > thr)
    xw = x[wet]
    stats_row["n_wet_target"] = int(xw.size)
    if xw.size == 0:
        return out, stats_row

    if tf.family == "nonparametric":
        target_sorted = np.sort(xw)
        tau = ecdf_prob(target_sorted, xw)
        obs_q = inv_ecdf(tf.obs_sorted, tau)
        mod_hist_q = inv_ecdf(tf.mod_sorted, tau)
    else:
        target_fit = fit_distribution(
            xw,
            int(cfg["qdm"].get("min_wet_days_calibration", 30)),
            int(cfg.get("qdm_parametric", {}).get(
                "max_fit_sample", MAX_PARAMETRIC_FIT_N
            )),
        )
        if target_fit is None or tf.obs_fit is None or tf.mod_fit is None:
            return out, stats_row
        tau = _safe_probs(target_fit.cdf(xw))
        obs_q = tf.obs_fit.ppf(tau)
        mod_hist_q = tf.mod_fit.ppf(tau)

    with np.errstate(divide="ignore", invalid="ignore"):
        delta = np.where(mod_hist_q > 0, xw / mod_hist_q, 1.0)
    lo = float(cfg["qdm"].get("min_delta_ratio", 0.2))
    hi = float(cfg["qdm"].get("max_delta_ratio", 5.0))
    stats_row["n_delta_clipped_low"] = int(np.sum(delta < lo))
    stats_row["n_delta_clipped_high"] = int(np.sum(delta > hi))
    corrected = obs_q * np.clip(delta, lo, hi)
    corrected = np.where(np.isfinite(corrected), corrected, np.nan)
    corrected = np.clip(corrected, 0.0, None)

    cap_factor = cfg["qdm"].get("upper_tail_cap_factor")
    if cap_factor is None and tf.family == "parametric":
        cap_factor = cfg.get("qdm_parametric", {}).get(
            "upper_tail_cap_factor", 5.0
        )
    if cap_factor is not None and tf.obs_sorted.size:
        cap = float(cap_factor) * float(tf.obs_sorted[-1])
        stats_row["n_output_capped"] = int(np.sum(corrected > cap))
        stats_row["output_cap_mm"] = cap
        corrected = np.minimum(corrected, cap)

    out[wet] = corrected
    out[np.isfinite(out) & (out < tf.wet_threshold_obs)] = 0.0
    stats_row["max_output_mm"] = float(np.nanmax(corrected)) if corrected.size else np.nan
    return out, stats_row


def method_parts(method: str) -> tuple[str, str]:
    _, family_code, grouping = method.split("_")
    return ("parametric" if family_code == "P" else "nonparametric", grouping)


def correct_method(obs: pd.DataFrame, mod: pd.DataFrame, cfg: dict,
                   model: str, method: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    family, grouping = method_parts(method)
    cal = cfg["periods"]["calibration"]
    val = cfg["periods"]["validation"]

    idx = obs.index.intersection(mod.index)
    obs_a = obs.loc[idx]
    mod_a = mod.loc[idx]
    is_cal = period_mask(idx, cal)
    is_val = period_mask(idx, val)
    keys = group_keys(idx, grouping)

    out = pd.DataFrame(np.nan, index=idx, columns=obs_a.columns)
    diag_rows: list[dict] = []

    for station in obs_a.columns:
        o = obs_a[station].to_numpy(dtype=float)
        m = mod_a[station].to_numpy(dtype=float)
        fallback = None
        if grouping == "monthly":
            fallback = fit_transfer(
                o[is_cal], m[is_cal], cfg, model, station, family,
                "annual", "all",
            )
        for group in np.unique(keys):
            gm = keys == group
            tf = fit_transfer(o[gm & is_cal], m[gm & is_cal], cfg, model,
                              station, family, grouping, str(group))
            applied_tf = tf
            fallback_used = False
            if not tf.usable and fallback is not None and fallback.usable:
                applied_tf = fallback
                fallback_used = True

            for period, mask in (("calibration", is_cal), ("validation", is_val)):
                sel = gm & mask
                if not sel.any():
                    continue
                corrected, st = apply_transfer(applied_tf, m[sel], cfg)
                out.loc[idx[sel], station] = corrected

                row = {
                    "method": method,
                    "model": model,
                    "station": station,
                    "family": family,
                    "grouping": grouping,
                    "group": str(group),
                    "period": period,
                    "usable": tf.usable,
                    "note": tf.note,
                    "fallback_used": fallback_used,
                    "applied_grouping": applied_tf.grouping,
                    "applied_group": applied_tf.group,
                    "wet_threshold_obs_mm": tf.wet_threshold_obs,
                    "wet_threshold_model_mm": tf.wet_threshold_model,
                    "n_obs_wet_cal": int(tf.obs_sorted.size),
                    "n_mod_wet_cal": int(tf.mod_sorted.size),
                    **st,
                }
                if tf.obs_fit is not None:
                    row.update({
                        "obs_dist": tf.obs_fit.name,
                        "obs_aic": tf.obs_fit.aic,
                        "obs_ks_d": tf.obs_fit.ks_d,
                        "obs_ks_p": tf.obs_fit.ks_p,
                        "obs_n_params": tf.obs_fit.n_params,
                    })
                if tf.mod_fit is not None:
                    row.update({
                        "mod_dist": tf.mod_fit.name,
                        "mod_aic": tf.mod_fit.aic,
                        "mod_ks_d": tf.mod_fit.ks_d,
                        "mod_ks_p": tf.mod_fit.ks_p,
                        "mod_n_params": tf.mod_fit.n_params,
                    })
                diag_rows.append(row)

    return out, pd.DataFrame(diag_rows)


def to_wide_csv(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    t = cfg["time"]
    out = df.copy()
    out.insert(0, t["day_col"], out.index.day)
    out.insert(0, t["month_col"], out.index.month)
    out.insert(0, t["year_col"], out.index.year)
    return out.reset_index(drop=True)


def evaluate_outputs(ds: io_layer.Dataset, outputs: dict[str, dict[str, pd.DataFrame]],
                     cfg: dict) -> pd.DataFrame:
    rows: list[dict] = []
    wet_thr = float(cfg["data"]["wet_threshold_mm"])
    cal = cfg["periods"]["calibration"]
    val = cfg["periods"]["validation"]
    qs = tuple(cfg["evaluate"].get("quantiles_reported", [0.5, 0.9, 0.95, 0.99]))

    for model, bundle in ds.raw.items():
        datasets: dict[str, pd.DataFrame] = {"raw": bundle.df}
        for method in METHODS:
            datasets[method] = outputs[method][model]
        for station in ds.stations:
            obs_series = ds.observed.df[station]
            hist_max = float(np.nanmax(obs_series.to_numpy(dtype=float)))
            for dataset_name, df in datasets.items():
                for period, years in (("calibration", cal), ("validation", val)):
                    ix = df.index[period_mask(df.index, years)]
                    met = M.full_metrics(obs_series, df.loc[ix, station],
                                         wet_thr, hist_max, qs)
                    rows.append({
                        "model": model,
                        "station": station,
                        "dataset": dataset_name,
                        "period": period,
                        **met,
                    })
    return pd.DataFrame(rows)


def summarise(metrics_df: pd.DataFrame) -> pd.DataFrame:
    selected = ["PBIAS", "KS_D", "q95_relbias_pct", "q99_relbias_pct",
                "mRMSE", "mMAE", "mNSE", "mKGE", "mr", "clim_r",
                "annual_r", "Rx1day_relbias_pct"]
    lower = {"KS_D", "mRMSE", "mMAE"}
    absolute = {"PBIAS", "q95_relbias_pct", "q99_relbias_pct", "Rx1day_relbias_pct"}

    rows: list[dict] = []
    for period in ("calibration", "validation"):
        raw = metrics_df[(metrics_df.dataset == "raw") & (metrics_df.period == period)]
        raw = raw.set_index(["model", "station"])
        for method in METHODS:
            d = metrics_df[(metrics_df.dataset == method) & (metrics_df.period == period)]
            d = d.set_index(["model", "station"])
            ix = raw.index.intersection(d.index)
            for metric in selected:
                if metric not in raw or metric not in d:
                    continue
                a = raw.loc[ix, metric].to_numpy(dtype=float)
                b = d.loc[ix, metric].to_numpy(dtype=float)
                ok = np.isfinite(a) & np.isfinite(b)
                if ok.sum() == 0:
                    continue
                av = np.abs(a[ok]) if metric in absolute else a[ok]
                bv = np.abs(b[ok]) if metric in absolute else b[ok]
                improved = bv < av if metric in lower or metric in absolute else bv > av
                rows.append({
                    "period": period,
                    "method": method,
                    "metric": metric,
                    "group": M.METRIC_GROUP.get(metric, "-"),
                    "raw_mean": float(np.nanmean(av)),
                    "corrected_mean": float(np.nanmean(bv)),
                    "delta_mean": float(np.nanmean(bv - av)),
                    "n_improved": int(np.sum(improved)),
                    "n_total": int(improved.size),
                    "pct_improved": float(100 * np.mean(improved)),
                })
    return pd.DataFrame(rows)


def apply_figure_style(cfg: dict) -> None:
    fig_cfg = cfg.get("figures", {})
    fams = list(fig_cfg.get("font_family", ["Cordia New", "Garuda", "DejaVu Sans"]))
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": fams + ["DejaVu Sans"],
        "font.size": float(fig_cfg.get("base_font_pt", 11.0)),
        "axes.labelsize": 9.5,
        "axes.titlesize": 10.0,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "legend.fontsize": 8.0,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.unicode_minus": False,
        "axes.grid": True,
        "grid.linestyle": ":",
        "grid.linewidth": 0.55,
        "grid.alpha": 0.55,
        "savefig.dpi": int(fig_cfg.get("dpi", 600)),
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.03,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def save_figure(fig, fig_dir: Path, stem: str) -> None:
    fig_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_dir / f"{stem}.png")
    fig.savefig(fig_dir / f"{stem}.pdf")
    plt.close(fig)


def method_label(method: str) -> str:
    return {
        "QDM_NP_annual": "NP annual",
        "QDM_NP_monthly": "NP monthly",
        "QDM_P_annual": "P annual",
        "QDM_P_monthly": "P monthly",
    }[method]


def metric_label(metric: str) -> str:
    return {
        "PBIAS": "PBIAS",
        "KS_D": "KS statistic D",
        "q99_relbias_pct": "q99 bias",
        "mRMSE": "Monthly RMSE",
        "mKGE": "Monthly KGE",
        "mr": "Monthly r",
    }.get(metric, metric)


def make_figures(metrics_df: pd.DataFrame, summary: pd.DataFrame,
                 cfg: dict, fig_dir: Path) -> None:
    apply_figure_style(cfg)
    width = float(cfg.get("figures", {}).get("width_mm", 160)) * MM
    palette = {
        "raw": "#4D4D4D",
        "QDM_NP_annual": "#0072B2",
        "QDM_NP_monthly": "#009E73",
        "QDM_P_annual": "#D55E00",
        "QDM_P_monthly": "#CC79A7",
    }

    val = metrics_df[metrics_df.period == "validation"].copy()
    fig, axes = plt.subplots(2, 2, figsize=(width, width * 0.72), layout="constrained")
    panels = [
        ("mRMSE", "Monthly RMSE", "Monthly RMSE (mm)", False),
        ("KS_D", "Distribution distance", "KS statistic D", False),
        ("q99_relbias_pct", "Upper-tail bias", "|q99 bias| (%)", True),
        ("mKGE", "Monthly KGE", "Monthly KGE", False),
    ]
    order = ["raw", *METHODS]
    labels = ["Raw", *(method_label(m) for m in METHODS)]
    for panel_tag, (ax, (metric, title, ylabel, absval)) in zip("abcd", zip(axes.ravel(), panels)):
        data = []
        for name in order:
            y = pd.to_numeric(val.loc[val.dataset == name, metric], errors="coerce")
            if absval:
                y = y.abs()
            data.append(y.dropna().to_numpy(dtype=float))
        try:
            bp = ax.boxplot(data, patch_artist=True, tick_labels=labels,
                            showfliers=False)
        except TypeError:
            bp = ax.boxplot(data, patch_artist=True, labels=labels,
                            showfliers=False)
        for patch, name in zip(bp["boxes"], order):
            patch.set_facecolor(palette[name])
            patch.set_alpha(0.80)
            patch.set_edgecolor("#333333")
            patch.set_linewidth(0.8)
        for item in bp["medians"]:
            item.set_color("white")
            item.set_linewidth(1.2)
        ax.set_ylabel(ylabel)
        ax.tick_params(axis="x", rotation=25)
        ax.set_title(f"({panel_tag}) {title}", loc="left", fontweight="bold")
    save_figure(fig, fig_dir, "Figure_QDM_method_comparison")

    heat_metrics = ["PBIAS", "KS_D", "q99_relbias_pct", "mRMSE", "mKGE", "mr"]
    h = summary[(summary.period == "validation") & (summary.metric.isin(heat_metrics))]
    mat = h.pivot(index="metric", columns="method", values="pct_improved").reindex(
        heat_metrics
    )[list(METHODS)]
    fig, ax = plt.subplots(figsize=(width, width * 0.46), layout="constrained")
    im = ax.imshow(mat.to_numpy(dtype=float), vmin=0, vmax=100, cmap="YlGnBu")
    ax.set_xticks(np.arange(len(METHODS)))
    ax.set_xticklabels([method_label(m) for m in METHODS], rotation=20, ha="right")
    ax.set_yticks(np.arange(len(mat.index)))
    ax.set_yticklabels([metric_label(m) for m in mat.index])
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = mat.iloc[i, j]
            ax.text(j, i, f"{v:.0f}", ha="center", va="center",
                    color="white" if v >= 62 else "#1A1A1A", fontsize=8.5)
    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label("Improved over raw (%)")
    ax.set_title("Independent validation improvement rate", loc="left",
                 fontweight="bold")
    save_figure(fig, fig_dir, "Figure_QDM_metric_heatmap")


def write_excel(out_path: Path, summary: pd.DataFrame, metrics_df: pd.DataFrame,
                diag_df: pd.DataFrame) -> None:
    with pd.ExcelWriter(out_path, engine="openpyxl") as w:
        summary.to_excel(w, sheet_name="S01_summary", index=False)
        metrics_df.to_excel(w, sheet_name="S02_station_metrics", index=False)
        diag_df.to_excel(w, sheet_name="S03_fit_diagnostics", index=False)
        pd.DataFrame({"method": METHODS, "description": [
            "Non-parametric empirical QDM, annual pooled calibration",
            "Non-parametric empirical QDM, month-wise calibration",
            "Parametric QDM with AIC-selected distribution, annual pooled calibration; numerical upper-tail cap recorded in diagnostics",
            "Parametric QDM with AIC-selected distribution, month-wise calibration; numerical upper-tail cap recorded in diagnostics",
        ]}).to_excel(w, sheet_name="S04_method_key", index=False)

    from openpyxl import load_workbook
    from openpyxl.styles import Font
    wb = load_workbook(out_path)
    for ws in wb.worksheets:
        ws.freeze_panes = "A2"
        for row in ws.iter_rows():
            for cell in row:
                cell.font = Font(name="Times New Roman", size=10, bold=(cell.row == 1))
    wb.save(out_path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument(
        "--out-dir",
        default=None,
        help=("output directory; default is a workspace-level "
              "qdm_p_np_publication_out folder"),
    )
    ap.add_argument(
        "--figures-only",
        action="store_true",
        help="regenerate figures from existing station_metrics.csv and summary.csv",
    )
    ap.add_argument(
        "--parametric-cap-factor",
        default=None,
        help=("override the parametric cap factor for sensitivity analysis; "
              "use 'none' for an uncapped run"),
    )
    args = ap.parse_args()

    missing = []
    if yaml is None:
        missing.append("PyYAML")
    if stats is None:
        missing.append("scipy")
    if plt is None:
        missing.append("matplotlib")
    if missing:
        print("Missing required packages: " + ", ".join(missing))
        print("Install them in the project environment with:")
        print("  pip install -r requirements.txt")
        return 2

    global io_layer, M, Provenance
    import io_layer as _io_layer
    import metrics as _metrics
    from provenance import Provenance as _Provenance
    io_layer = _io_layer
    M = _metrics
    Provenance = _Provenance

    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))
    if args.parametric_cap_factor is not None:
        value = args.parametric_cap_factor.strip().lower()
        cfg.setdefault("qdm_parametric", {})["upper_tail_cap_factor"] = (
            None if value == "none" else float(value)
        )
    out_root = Path(args.out_dir) if args.out_dir else (
        _WORKSPACE_ROOT / "qdm_p_np_publication_out"
    )
    corrected_dir = out_root / "corrected"
    fig_dir = out_root / "figures"
    corrected_dir.mkdir(parents=True, exist_ok=True)

    if args.figures_only:
        metrics_path = out_root / "station_metrics.csv"
        summary_path = out_root / "summary.csv"
        if not metrics_path.is_file() or not summary_path.is_file():
            print(f"Missing cached results under {out_root}; run without --figures-only first.")
            return 1
        make_figures(pd.read_csv(metrics_path), pd.read_csv(summary_path), cfg, fig_dir)
        print(f"figures regenerated -> {fig_dir}", flush=True)
        return 0

    print("=" * 78, flush=True)
    print("  Parametric vs non-parametric QDM", flush=True)
    print("=" * 78, flush=True)
    ds = io_layer.build_dataset(cfg, Provenance(cfg, args.config))

    outputs: dict[str, dict[str, pd.DataFrame]] = {m: {} for m in METHODS}
    diag_parts: list[pd.DataFrame] = []

    for model, bundle in ds.raw.items():
        print(f"\n  model: {model}", flush=True)
        for method in METHODS:
            print(f"    {method}", flush=True)
            corrected, diag = correct_method(ds.observed.df, bundle.df, cfg, model, method)
            outputs[method][model] = corrected
            diag_parts.append(diag)
            to_wide_csv(corrected, cfg).to_csv(
                corrected_dir / f"bc_{model}_{method}.csv",
                index=False,
                float_format="%.3f",
            )

    diag_df = pd.concat(diag_parts, ignore_index=True)
    metrics_df = evaluate_outputs(ds, outputs, cfg)
    summary = summarise(metrics_df)

    diag_df.to_csv(out_root / "fit_diagnostics.csv", index=False)
    metrics_df.to_csv(out_root / "station_metrics.csv", index=False)
    summary.to_csv(out_root / "summary.csv", index=False)
    write_excel(out_root / "QDM_parametric_nonparametric_results.xlsx",
                summary, metrics_df, diag_df)
    make_figures(metrics_df, summary, cfg, fig_dir)

    print("\n" + "=" * 78, flush=True)
    print(f"  done -> {out_root}", flush=True)
    print("=" * 78, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
