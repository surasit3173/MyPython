"""
qdm_q1.py
=========
Dedicated QDM-only Q1 outputs, isolated from the core rainfall pipeline.

This module reads the existing QDM evaluation workbook, extracts tidy tables,
and generates a separate publication-style figure/table set in output/qdm_q1.
"""
from __future__ import annotations

import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import config as C
from . import figures as FIG

log = logging.getLogger("qdm_q1")


def _save(fig, name: str):
    for ext in ("png", "pdf"):
        fig.savefig(C.QDM_Q1_FIG / f"{name}.{ext}", dpi=C.DPI, bbox_inches="tight")
    plt.close(fig)
    log.info("saved %s.{png,pdf}", name)


def _detect_header_row(workbook: Path, sheet_name: str, required_terms: tuple[str, ...]) -> int:
    raw = pd.read_excel(workbook, sheet_name=sheet_name, header=None)
    for idx, row in raw.iterrows():
        cells = [str(v).strip() for v in row.tolist() if pd.notna(v)]
        if all(term in cells for term in required_terms):
            return int(idx)
    raise ValueError(f"Could not detect header row for sheet '{sheet_name}'.")


def _read_sheet(workbook: Path, sheet_name: str, required_terms: tuple[str, ...]) -> pd.DataFrame:
    header_row = _detect_header_row(workbook, sheet_name, required_terms)
    df = pd.read_excel(workbook, sheet_name=sheet_name, header=header_row)
    df = df.dropna(how="all").copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, ~pd.Index(df.columns).str.startswith("Unnamed:")]
    return df.reset_index(drop=True)


def _to_float(series: pd.Series) -> pd.Series:
    cleaned = (series.astype(str)
               .str.replace(",", "", regex=False)
               .str.replace("%", "", regex=False)
               .str.replace(r"[^\d\.\-eE]", "", regex=True))
    cleaned = cleaned.str.replace(r"(?<=\d)-$", "", regex=True)
    return pd.to_numeric(cleaned, errors="coerce")


def _normalise_code(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip()


def discover_qdm_workbook(source_dir: Path | None = None) -> Path:
    source_dir = Path(source_dir or C.QDM_SOURCE_DIR)
    candidates = sorted(source_dir.glob("*ComprehensiveAnalysis.xlsx"))
    if not candidates:
        raise FileNotFoundError(f"No QDM workbook found in {source_dir}")
    preferred = [p for p in candidates if "Observed_Rain_daily_198101_201412_28sta_" in p.name]
    return preferred[-1] if preferred else candidates[-1]


def discover_qdm_extreme_workbook(source_dir: Path | None = None) -> Path | None:
    source_dir = Path(source_dir or C.QDM_SOURCE_DIR)
    candidates = sorted(source_dir.glob("*etccdi_extreme_indices*_ComprehensiveAnalysis.xlsx"))
    if not candidates:
        return None
    refined = [p for p in candidates if "refined" in p.name.lower()]
    return refined[-1] if refined else candidates[-1]


def load_qdm_tables(source_dir: Path | None = None) -> dict[str, pd.DataFrame]:
    workbook = discover_qdm_workbook(source_dir)
    extreme_workbook = discover_qdm_extreme_workbook(source_dir)
    daily = _read_sheet(workbook, "S1 Metrics-Daily", ("Dataset", "Station", "Code"))
    monthly = _read_sheet(workbook, "S2 Metrics-Monthly", ("Dataset", "Station", "Code"))
    improv = _read_sheet(workbook, "S3 Improvement Summary", ("Station", "Code", "Scale"))
    wilcox = _read_sheet(workbook, "S4 Wilcoxon Test", ("Station", "Code", "N (pairs)"))
    ks = _read_sheet(workbook, "S5 KS-Test", ("Station", "Code", "D (Raw)"))
    seasonal = _read_sheet(workbook, "S6 Seasonal Analysis", ("Season", "Station", "Code"))
    wetday = _read_sheet(workbook, "S9 Wet-Day Diagnostics", ("Dataset", "Station", "Code"))
    trend = _read_sheet(workbook, "S10 Trend Analysis", ("Dataset", "Station", "Code"))

    for df in (daily, monthly, improv, wilcox, ks, seasonal, wetday, trend):
        if "Code" in df.columns:
            df["Code"] = _normalise_code(df["Code"])

    for col in ("RMSE", "MAE", "MBE", "Pbias", "RSR", "r", "r_sq", "NSE", "KGE", "d",
                "sigma_r", "beta", "RMSE_pct", "Pbias_abs"):
        if col in daily.columns:
            daily[col] = _to_float(daily[col])
        if col in monthly.columns:
            monthly[col] = _to_float(monthly[col])

    improv = improv.rename(columns={
        "RMSE reduction (mm)": "rmse_reduction_mm",
        "RMSE reduction (%)": "rmse_reduction_pct",
        "|Pbias| reduction (%)": "pbias_reduction_pct",
        "-r": "delta_r",
        "-NSE": "delta_nse",
        "-KGE": "delta_kge",
        "-d": "delta_d",
        "KGE Raw": "kge_raw",
        "KGE BC": "kge_bc",
    })
    seasonal = seasonal.rename(columns={
        "KGE Raw": "kge_raw",
        "KGE BC": "kge_bc",
        "-KGE": "delta_kge",
        "RMSE Raw (mm)": "rmse_raw_mm",
        "RMSE BC (mm)": "rmse_bc_mm",
        "-RMSE (mm)": "delta_rmse_mm",
    })
    wilcox = wilcox.rename(columns={
        "N (pairs)": "n_pairs",
        "Median|err| Raw": "median_abs_err_raw",
        "Median|err| BC": "median_abs_err_bc",
        "Reduction (%)": "reduction_pct",
        "p (two-tail)": "p_two_tail",
        "p (one-tail)": "p_one_tail",
        "Effect r": "effect_r",
        "FDR q<0.05": "fdr_significant",
    })
    ks = ks.rename(columns={
        "D (Raw)": "d_raw",
        "p (Raw)": "p_raw",
        "Sig (Raw)": "sig_raw",
        "D (BC)": "d_bc",
        "p (BC)": "p_bc",
        "Sig (BC)": "sig_bc",
        "D Improvement (D_raw - D_bc)": "d_improvement",
    })
    wetday = wetday.rename(columns={
        "N_years": "n_years",
        "Mean": "mean_value",
        "SD": "sd_value",
        "Min": "min_value",
        "Max": "max_value",
    })
    trend = trend.rename(columns={
        "N_years": "n_years",
        "Lag_k": "lag_k",
        "N_eff": "n_eff",
        "Rho_lag1": "rho_lag1",
        "Sen_slope_per_year": "sen_slope_per_year",
        "MK_tau": "mk_tau",
        "Z": "z_value",
        "P_value": "p_value",
    })

    for df, cols in (
        (improv, ("rmse_reduction_mm", "rmse_reduction_pct", "pbias_reduction_pct",
                  "delta_r", "delta_nse", "delta_kge", "delta_d", "kge_raw", "kge_bc")),
        (seasonal, ("kge_raw", "kge_bc", "delta_kge", "rmse_raw_mm", "rmse_bc_mm", "delta_rmse_mm")),
        (wilcox, ("n_pairs", "median_abs_err_raw", "median_abs_err_bc", "reduction_pct",
                  "W-statistic", "p_two_tail", "p_one_tail", "effect_r")),
        (ks, ("d_raw", "p_raw", "d_bc", "p_bc", "d_improvement")),
        (wetday, ("n_years", "mean_value", "sd_value", "min_value", "max_value")),
        (trend, ("n_years", "lag_k", "n_eff", "rho_lag1", "sen_slope_per_year",
                 "mk_tau", "z_value", "p_value")),
    ):
        for col in cols:
            if col in df.columns:
                df[col] = _to_float(df[col])

    station_daily = daily[daily["Dataset"].isin(["Raw CMIP6", "BC (QDM)"])].copy()
    station_monthly = monthly[monthly["Dataset"].isin(["Raw CMIP6", "BC (QDM)"])].copy()
    tables = {
        "workbook": pd.DataFrame([{"source_workbook": str(workbook)}]),
        "daily_metrics": station_daily,
        "monthly_metrics": station_monthly,
        "improvement": improv,
        "wilcoxon": wilcox,
        "ks": ks,
        "seasonal": seasonal,
        "wetday": wetday,
        "trend": trend,
    }
    if extreme_workbook is not None:
        etccdi_thresholds = _read_sheet(
            extreme_workbook,
            "S12 ETCCDI Thresholds",
            ("Station", "Station_Code", "WetDay_Threshold_mm"),
        )
        etccdi_bias = _read_sheet(
            extreme_workbook,
            "S14 ETCCDI Bias",
            ("Station", "Station_Code", "Index"),
        )
        etccdi_trend = _read_sheet(
            extreme_workbook,
            "S15 ETCCDI Trend",
            ("Dataset", "Dataset_Type", "Station", "Station_Code", "Index"),
        )
        for df in (etccdi_thresholds, etccdi_bias, etccdi_trend):
            for col in ("Station_Code", "Index", "Dataset", "Dataset_Type", "Description", "Unit", "Trend"):
                if col in df.columns:
                    df[col] = df[col].astype(str).str.strip()
        for df, cols in (
            (etccdi_thresholds, ("WetDay_Threshold_mm", "P95_threshold_mm", "P99_threshold_mm", "Baseline_Wet_Days")),
            (etccdi_bias, ("Observed_Mean", "Raw_Mean", "BC_QDM_Mean", "Raw_Bias", "BC_QDM_Bias",
                           "Raw_Abs_Bias", "BC_QDM_Abs_Bias", "Bias_Reduction_percent")),
            (etccdi_trend, ("N", "Sen_Slope_per_year", "MK_Z", "MK_p", "Kendall_tau",
                            "N_effective", "Lag_k", "Lag1_autocorrelation")),
        ):
            for col in cols:
                if col in df.columns:
                    df[col] = _to_float(df[col])

        etccdi_bias["abs_bias_change"] = etccdi_bias["Raw_Abs_Bias"] - etccdi_bias["BC_QDM_Abs_Bias"]
        etccdi_bias["relative_bias_ratio"] = np.where(
            etccdi_bias["Raw_Abs_Bias"] > 0,
            etccdi_bias["BC_QDM_Abs_Bias"] / etccdi_bias["Raw_Abs_Bias"],
            np.nan,
        )
        stable_threshold = etccdi_bias.groupby("Index")["Raw_Abs_Bias"].transform(
            lambda s: float(s[s > 0].quantile(0.25)) if (s > 0).any() else np.nan
        )
        etccdi_bias["percent_metric_flag"] = np.where(
            etccdi_bias["Raw_Abs_Bias"] <= stable_threshold,
            "Low raw bias; use abs_bias_change for interpretation",
            "Stable percent metric",
        )

        tables["extreme_workbook"] = pd.DataFrame([{"source_workbook": str(extreme_workbook)}])
        tables["etccdi_thresholds"] = etccdi_thresholds
        tables["etccdi_bias"] = etccdi_bias
        tables["etccdi_trend"] = etccdi_trend
    return tables


def build_publication_tables(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    improvement = tables["improvement"].copy()
    significance = tables["wilcoxon"].merge(
        tables["ks"], on=["Station", "Code"], how="outer", suffixes=("_wilcox", "_ks")
    )
    seasonal = tables["seasonal"].copy()
    hydro = tables["wetday"].merge(
        tables["trend"][["Dataset", "Station", "Code", "Metric", "sen_slope_per_year",
                         "z_value", "p_value", "Trend"]],
        on=["Dataset", "Station", "Code", "Metric"],
        how="left",
    )

    summary_rows = []
    for scale, sub in improvement.groupby("Scale"):
        summary_rows.append({
            "section": f"Improvement - {scale}",
            "n_stations": len(sub),
            "median_rmse_reduction_pct": round(sub["rmse_reduction_pct"].median(), 2),
            "median_pbias_reduction_pct": round(sub["pbias_reduction_pct"].median(), 2),
            "median_delta_kge": round(sub["delta_kge"].median(), 3),
            "share_kge_improved_pct": round((sub["delta_kge"] > 0).mean() * 100, 1),
        })
    summary_rows.append({
        "section": "Wilcoxon significance",
        "n_stations": len(tables["wilcoxon"]),
        "median_rmse_reduction_pct": round(tables["wilcoxon"]["reduction_pct"].median(), 2),
        "median_pbias_reduction_pct": np.nan,
        "median_delta_kge": round(tables["wilcoxon"]["effect_r"].median(), 3),
        "share_kge_improved_pct": round(
            tables["wilcoxon"]["fdr_significant"].astype(str).str.lower().eq("yes").mean() * 100, 1
        ),
    })
    summary = pd.DataFrame(summary_rows)

    out = {
        "QDM_Q1_TABLE_01_IMPROVEMENT_TIDY.xlsx": improvement,
        "QDM_Q1_TABLE_02_SIGNIFICANCE_TIDY.xlsx": significance,
        "QDM_Q1_TABLE_03_SEASONAL_SKILL_TIDY.xlsx": seasonal,
        "QDM_Q1_TABLE_04_HYDROCLIMATE_DIAGNOSTICS_TIDY.xlsx": hydro,
        "QDM_Q1_TABLE_05_EXECUTIVE_SUMMARY.xlsx": summary,
    }
    if "etccdi_thresholds" in tables:
        out["QDM_Q1_TABLE_06_ETCCDI_THRESHOLDS.xlsx"] = tables["etccdi_thresholds"]
        out["QDM_Q1_TABLE_07_ETCCDI_BIAS_BY_STATION.xlsx"] = tables["etccdi_bias"]
        out["QDM_Q1_TABLE_08_ETCCDI_TREND_BY_STATION.xlsx"] = tables["etccdi_trend"]
    return out


def fig_qdm_improvement_heatmap(improvement: pd.DataFrame):
    metrics = ["rmse_reduction_pct", "pbias_reduction_pct", "delta_r", "delta_nse", "delta_kge", "delta_d"]
    labels = ["RMSE %", "|Pbias| %", "Delta r", "Delta NSE", "Delta KGE", "Delta d"]
    fig, axes = plt.subplots(1, 2, figsize=(14.6, 10.8), sharey=True)
    for ax, scale in zip(axes, ["Daily", "Monthly"]):
        sub = improvement[improvement["Scale"].astype(str).str.lower() == scale.lower()].copy()
        sub = sub.sort_values(["delta_kge", "rmse_reduction_pct"], ascending=[False, False])
        mat = sub[metrics].to_numpy(dtype=float)
        denom = np.nanmax(np.abs(mat), axis=0)
        denom = np.where(np.isfinite(denom) & (denom > 0), denom, 1.0)
        mat_scaled = mat / denom
        im = ax.imshow(mat_scaled, aspect="auto", cmap="RdYlBu_r", vmin=-1, vmax=1)
        ax.set_title(
            f"{scale}: median Delta KGE={sub['delta_kge'].median():+.2f}, "
            f"median RMSE gain={sub['rmse_reduction_pct'].median():+.1f}%"
        )
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=25, ha="right")
        ax.set_yticks(range(len(sub)))
        ax.set_yticklabels(sub["Code"])
        ax.set_xlabel("Improvement metric")
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                val = mat[i, j]
                if not np.isfinite(val):
                    continue
                text = f"{val:.1f}" if j < 2 else f"{val:.2f}"
                ax.text(j, i, text, ha="center", va="center", fontsize=5.7, color="#1A1A1A")
    axes[0].set_ylabel("Station code")
    cbar = fig.colorbar(im, ax=axes, fraction=0.025, pad=0.02)
    cbar.set_label("Column-scaled improvement sign and intensity")
    fig.suptitle("QDM Skill Improvement Matrix Across 28 Stations", fontsize=14)
    fig.subplots_adjust(left=0.08, right=0.93, bottom=0.10, top=0.92, wspace=0.16)
    _save(fig, "QDM_Q1_FIGURE_01_improvement_heatmap")


def fig_qdm_significance_dashboard(wilcox: pd.DataFrame, ks: pd.DataFrame):
    left = wilcox.sort_values("reduction_pct", ascending=True).copy()
    right = ks.set_index("Code").loc[left["Code"]].reset_index()
    y = np.arange(len(left))
    fig, axes = plt.subplots(1, 2, figsize=(14.5, 10.8), sharey=True)

    colors = np.where(left["fdr_significant"].astype(str).str.lower().eq("yes"), C.C_ACCENT, C.C_NEUTRAL)
    axes[0].barh(y, left["reduction_pct"], color=colors, edgecolor="#333333", linewidth=0.4)
    axes[0].scatter(left["effect_r"], y, color=C.C_ELNINO, s=26, zorder=3)
    axes[0].set_title("Wilcoxon daily absolute-error reduction")
    axes[0].set_xlabel("Reduction in median |error| (%)")
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(left["Code"])
    axes[0].axvline(0, color="black", lw=0.8, ls="--")

    ks_colors = np.where(right["d_improvement"] >= 0, C.C_ACCENT, C.C_ELNINO)
    axes[1].barh(y, right["d_improvement"], color=ks_colors, edgecolor="#333333", linewidth=0.4)
    axes[1].scatter(right["d_bc"], y, color=C.C_MAIN, s=16, zorder=3)
    axes[1].set_title("Wet-day KS distribution improvement")
    axes[1].set_xlabel("D_raw - D_bc (positive = QDM closer to observed)")
    axes[1].axvline(0, color="black", lw=0.8, ls="--")

    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], color=C.C_ACCENT, lw=8, label="FDR-significant improvement"),
        Line2D([0], [0], color=C.C_NEUTRAL, lw=8, label="Not FDR-significant"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=C.C_ELNINO,
               markeredgecolor=C.C_ELNINO, label="Effect size r / BC KS D"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=3, bbox_to_anchor=(0.5, 0.01))
    fig.suptitle("QDM Statistical Evidence Across Stations", fontsize=14)
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    _save(fig, "QDM_Q1_FIGURE_02_significance_dashboard")


def fig_qdm_seasonal_skill_shift(seasonal: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(14.2, 10.2), sharey=True)
    for ax, season in zip(axes, ["Wet (May-Oct)", "Dry (Nov-Apr)"]):
        sub = seasonal[seasonal["Season"] == season].copy()
        sub = sub.sort_values("delta_kge", ascending=True).reset_index(drop=True)
        y = np.arange(len(sub))
        for yi, (_, row) in enumerate(sub.iterrows()):
            col = C.C_ACCENT if row["delta_kge"] >= 0 else C.C_ELNINO
            ax.plot([row["kge_raw"], row["kge_bc"]], [yi, yi], color=col, lw=1.6, alpha=0.9)
            ax.plot(row["kge_raw"], yi, "o", color="white", mec="#555555", mew=0.9, ms=5)
            ax.plot(
                row["kge_bc"],
                yi,
                "o",
                color=col,
                mec="black",
                mew=0.4,
                ms=5 + max(row["delta_rmse_mm"], 0) / 35.0,
            )
        ax.axvline(0, color="#888888", lw=0.8, ls=":")
        ax.set_title(
            f"{season}\nmedian Delta KGE={sub['delta_kge'].median():+.2f}, "
            f"median Delta RMSE={sub['delta_rmse_mm'].median():+.1f} mm"
        )
        ax.set_xlabel("KGE (raw open circle -> QDM filled circle)")
        ax.set_yticks(y)
        ax.set_yticklabels(sub["Code"])
    axes[0].set_ylabel("Station code")
    fig.suptitle("Seasonal Skill Shift After QDM Bias Correction", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    _save(fig, "QDM_Q1_FIGURE_03_seasonal_skill_shift")


def fig_qdm_hydroclimate_fidelity(wetday: pd.DataFrame, trend: pd.DataFrame):
    metrics = ["Annual rainfall", "Wet-day count", "Wet-day frequency"]
    dataset_order = ["Observed", "Raw ensemble", "BC-QDM ensemble"]
    dataset_colors = {"Observed": C.C_MAIN, "Raw ensemble": C.C_ELNINO, "BC-QDM ensemble": C.C_LANINA}
    fig, axes = plt.subplots(2, 3, figsize=(15.5, 8.8))

    wetday_plot = wetday[wetday["Metric"].isin(metrics)].copy()
    trend_plot = trend[trend["Metric"].isin(metrics)].copy()

    for col_idx, metric in enumerate(metrics):
        ax = axes[0, col_idx]
        sub = wetday_plot[wetday_plot["Metric"] == metric]
        grouped = (sub.groupby("Dataset")[["mean_value", "sd_value"]]
                   .median()
                   .reindex(dataset_order))
        x = np.arange(len(dataset_order))
        ax.errorbar(
            x,
            grouped["mean_value"],
            yerr=grouped["sd_value"],
            fmt="o",
            color=C.C_MAIN,
            ecolor="#777777",
            elinewidth=1.0,
            capsize=3,
        )
        for xi, ds in enumerate(dataset_order):
            ax.scatter(
                xi,
                grouped.loc[ds, "mean_value"],
                s=65,
                color=dataset_colors[ds],
                edgecolor="black",
                linewidths=0.4,
                zorder=3,
            )
        ax.set_xticks(x)
        ax.set_xticklabels(["Obs", "Raw", "QDM"])
        ax.set_title(metric)
        ax.set_ylabel("Median station mean +/- station SD")

        ax2 = axes[1, col_idx]
        sub_t = trend_plot[trend_plot["Metric"] == metric]
        grouped_t = (sub_t.groupby("Dataset")[["sen_slope_per_year", "p_value"]]
                     .median()
                     .reindex(dataset_order))
        for xi, ds in enumerate(dataset_order):
            ax2.scatter(
                xi,
                grouped_t.loc[ds, "sen_slope_per_year"],
                s=90 if grouped_t.loc[ds, "p_value"] < C.ALPHA else 50,
                color=dataset_colors[ds],
                edgecolor="black",
                linewidths=0.4,
            )
        ax2.axhline(0, color="#777777", lw=0.8, ls="--")
        ax2.set_xticks(x)
        ax2.set_xticklabels(["Obs", "Raw", "QDM"])
        ax2.set_ylabel("Median Sen slope per year")
        ax2.set_title(f"{metric} trend conservation")

    fig.suptitle("QDM Hydroclimate Fidelity and Trend Conservation", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    _save(fig, "QDM_Q1_FIGURE_04_hydroclimate_fidelity")


def fig_qdm_etccdi_bias_matrix(etccdi_bias: pd.DataFrame):
    selected = ["PRCPTOT", "R10mm", "R20mm", "Rx1day", "Rx5day", "R95p", "R99p"]
    sub = etccdi_bias[etccdi_bias["Index"].isin(selected)].copy()
    codes = list(dict.fromkeys(sub["Station_Code"]))
    mat = np.full((len(codes), len(selected)), np.nan)
    for i, code in enumerate(codes):
        for j, idx in enumerate(selected):
            row = sub[(sub["Station_Code"] == code) & (sub["Index"] == idx)]
            if not row.empty:
                mat[i, j] = row["abs_bias_change"].iloc[0]
    denom = np.nanpercentile(np.abs(mat), 90, axis=0) if np.isfinite(mat).any() else np.ones(len(selected))
    denom = np.where(np.isfinite(denom) & (denom > 0), denom, 1.0)
    mat_scaled = mat / denom

    fig, ax = plt.subplots(figsize=(12.6, 10.2))
    im = ax.imshow(mat_scaled, aspect="auto", cmap="RdYlBu_r", vmin=-1.0, vmax=1.0)
    ax.set_xticks(range(len(selected)))
    ax.set_xticklabels(selected, rotation=25, ha="right")
    ax.set_yticks(range(len(codes)))
    ax.set_yticklabels(codes)
    ax.set_xlabel("Extreme precipitation index")
    ax.set_ylabel("Station code")
    ax.set_title(
        "QDM Absolute-Bias Change for Article-Aligned Extreme Indices\n"
        "Positive values = raw absolute bias - QDM absolute bias; colors are scaled within each index"
    )
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            val = mat[i, j]
            if np.isfinite(val):
                ax.text(j, i, f"{val:.1f}", ha="center", va="center", fontsize=6.0)
    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label("Within-index scaled absolute-bias change")
    fig.tight_layout()
    _save(fig, "QDM_Q1_FIGURE_05_etccdi_bias_matrix")


def fig_qdm_etccdi_trend_significance(etccdi_trend: pd.DataFrame):
    selected = ["PRCPTOT", "R10mm", "R20mm", "Rx1day", "Rx5day", "R95p", "R99p", "R50mm"]
    sub = etccdi_trend[
        (etccdi_trend["Dataset"] == "BC-QDM ensemble") &
        (etccdi_trend["Index"].isin(selected))
    ].copy()
    codes = list(dict.fromkeys(sub["Station_Code"]))
    mat = np.full((len(selected), len(codes)), np.nan)
    pmat = np.full_like(mat, np.nan, dtype=float)
    for i, idx in enumerate(selected):
        for j, code in enumerate(codes):
            row = sub[(sub["Index"] == idx) & (sub["Station_Code"] == code)]
            if not row.empty:
                mat[i, j] = row["Sen_Slope_per_year"].iloc[0]
                pmat[i, j] = row["MK_p"].iloc[0]
    vmax = float(np.nanpercentile(np.abs(mat), 95)) if np.isfinite(mat).any() else 1.0
    vmax = vmax if np.isfinite(vmax) and vmax > 0 else 1.0

    fig, ax = plt.subplots(figsize=(14.5, 6.8))
    im = ax.imshow(mat, aspect="auto", cmap="RdBu_r", vmin=-vmax, vmax=vmax)
    ax.set_xticks(range(len(codes)))
    ax.set_xticklabels(codes, rotation=90, fontsize=8)
    ax.set_yticks(range(len(selected)))
    ax.set_yticklabels(selected)
    ax.set_xlabel("Station code")
    ax.set_ylabel("Extreme precipitation index")
    significant_n = int(np.sum(np.isfinite(pmat) & (pmat < C.ALPHA)))
    subtitle = (
        "Star = Mann-Kendall p < 0.05 after lag-k autocorrelation adjustment"
        if significant_n > 0
        else "No station reaches p < 0.05 after lag-k autocorrelation adjustment; colors show Sen slope"
    )
    ax.set_title(f"BC-QDM ETCCDI Trend Significance Matrix\n{subtitle}")
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            if np.isfinite(pmat[i, j]) and pmat[i, j] < C.ALPHA:
                ax.text(j, i, "*", ha="center", va="center", fontsize=10, fontweight="bold")
    cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label("Sen slope per year")
    fig.tight_layout()
    _save(fig, "QDM_Q1_FIGURE_06_etccdi_trend_significance")


def write_tables(table_map: dict[str, pd.DataFrame], source_dir: Path, source_workbook: str):
    for fname, df in table_map.items():
        out = C.QDM_Q1_TAB / fname
        with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
            info = pd.DataFrame({
                "Field": ["Source directory", "Source workbook", "Output standard", "Generated UTC"],
                "Value": [
                    str(source_dir),
                    source_workbook,
                    "Q1 isolated QDM-only output",
                    pd.Timestamp.utcnow().isoformat(timespec="seconds"),
                ],
            })
            info.to_excel(writer, index=False, sheet_name="Info")
            df.to_excel(writer, index=False, sheet_name="results")
        log.info("saved %s", out.name)


def build_qdm_q1_outputs(source_dir: Path | None = None) -> dict[str, str]:
    source_dir = Path(source_dir or C.QDM_SOURCE_DIR)
    if not source_dir.exists():
        raise FileNotFoundError(f"QDM source directory not found: {source_dir}")

    FIG.init()
    tables = load_qdm_tables(source_dir)
    publication_tables = build_publication_tables(tables)
    write_tables(publication_tables, source_dir, tables["workbook"]["source_workbook"].iloc[0])

    fig_qdm_improvement_heatmap(tables["improvement"])
    fig_qdm_significance_dashboard(tables["wilcoxon"], tables["ks"])
    fig_qdm_seasonal_skill_shift(tables["seasonal"])
    fig_qdm_hydroclimate_fidelity(tables["wetday"], tables["trend"])
    if "etccdi_bias" in tables:
        fig_qdm_etccdi_bias_matrix(tables["etccdi_bias"])
        fig_qdm_etccdi_trend_significance(tables["etccdi_trend"])

    return {
        "source_dir": str(source_dir),
        "source_workbook": tables["workbook"]["source_workbook"].iloc[0],
        "table_dir": str(C.QDM_Q1_TAB),
        "figure_dir": str(C.QDM_Q1_FIG),
    }
