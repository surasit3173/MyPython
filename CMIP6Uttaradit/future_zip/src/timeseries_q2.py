"""
timeseries_q2.py
================
AR6-period rainfall time-series figures + per-GCM/MME station tables, built on
the yearly index cube produced by future_q1.compute_yearly_index_cube.

Products (publication set, split across two manuscripts by design):
  TS-1  Regional annual PRCPTOT 1981-2100: observed, QDM bc-historical ensemble
        band, SSP245/SSP585 ensemble bands; AR6 assessment periods shaded.
  TS-2  Station small-multiples (4x4): anomaly (%) vs AR6 observed baseline,
        observed + SSP5-8.5 MME mean with model IQR; regional panel; legend panel.
  TS-3  Monthly seasonal cycle: observed vs bc-historical ensemble vs AR6
        periods per scenario (regional mean, with ensemble spread).
  TABLE_10  Historical per-station annual rainfall: observed vs each GCM (QDM
        bc-historical) vs MME + residual bias.
  TABLE_11  Future per-station annual rainfall by AR6 period x scenario:
        each GCM, MME mean/median/min/max, delta% vs AR6 baseline, agreement.

No historical->SSP splice: lines from different experiments never connect
across the 2014/2015 boundary.
"""
from __future__ import annotations

import logging

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import config as C
from .future_q1 import (AR6_BASELINE, AR6_ORDER, AR6_WINDOWS, MapStyle,
                        SCENARIO_ORDER, _save, _sign_agreement)

log = logging.getLogger("timeseries_q2")

C_OBS = "#000000"
C_HIST = "#009E73"      # QDM bc-historical ensemble (Okabe-Ito green)
C_245 = "#0072B2"       # SSP2-4.5 (Okabe-Ito blue)
C_585 = "#D55E00"       # SSP5-8.5 (Okabe-Ito vermillion)
SCEN_COLOR = {"ssp245": C_245, "ssp585": C_585}
SCEN_LABEL = {"ssp245": "SSP2-4.5", "ssp585": "SSP5-8.5"}


# --------------------------------------------------------------------------- #
# Data shaping
# --------------------------------------------------------------------------- #
def _prcptot(yearly: pd.DataFrame) -> pd.DataFrame:
    out = yearly[yearly["index"] == "PRCPTOT"].copy()
    out["year"] = out["year"].astype(int)
    return out


def regional_annual(yearly: pd.DataFrame) -> dict:
    """Regional (station-mean) annual PRCPTOT series per dataset."""
    pr = _prcptot(yearly)
    reg = (pr.groupby(["dataset", "model", "scenario", "year"], as_index=False)
           ["value"].mean().rename(columns={"value": "annual"}))
    obs = reg[reg.dataset == "Observed"].set_index("year")["annual"].sort_index()

    def ens(df):
        g = df.groupby("year")["annual"]
        return pd.DataFrame({"mean": g.mean(), "q25": g.quantile(0.25),
                             "q75": g.quantile(0.75), "min": g.min(),
                             "max": g.max()}).sort_index()

    hist = ens(reg[reg.dataset == "BC_HIST"])
    fut = {s: ens(reg[(reg.dataset == "BC") & (reg.scenario == s)])
           for s in SCENARIO_ORDER}
    return {"obs": obs, "hist": hist, "future": fut, "per_model": reg}


def station_annual(yearly: pd.DataFrame) -> pd.DataFrame:
    pr = _prcptot(yearly)
    return pr[["station", "dataset", "model", "scenario", "year", "value"]] \
        .rename(columns={"value": "annual"})


def _window_mean(df: pd.DataFrame, lo: int, hi: int, col="annual") -> pd.Series:
    sub = df[(df["year"] >= lo) & (df["year"] <= hi)]
    return sub[col]


# --------------------------------------------------------------------------- #
# TS-1: regional annual series with AR6 shading
# --------------------------------------------------------------------------- #
def fig_ts1_regional(yearly: pd.DataFrame, area_name: str):
    MapStyle().apply()
    r = regional_annual(yearly)
    fig, ax = plt.subplots(figsize=(11.4, 5.6))

    # AR6 shading (baseline + three future periods)
    shade = [("Baseline", AR6_BASELINE, "#f0f0f0")] + \
            [(k, AR6_WINDOWS[k], "#f5ede2" if i % 2 == 0 else "#e9f0f5")
             for i, k in enumerate(AR6_ORDER)]
    ymax_note = []
    for label, (lo, hi), colr in shade:
        ax.axvspan(lo, hi + 1, color=colr, zorder=0)
    # observed
    ax.plot(r["obs"].index, r["obs"].values, color=C_OBS, lw=1.4, zorder=6,
            label="Observed")
    # bc-historical ensemble (QDM): mean + min-max band
    h = r["hist"]
    if not h.empty:
        ax.fill_between(h.index, h["min"], h["max"], color=C_HIST, alpha=0.18,
                        lw=0, zorder=2, label="QDM historical (7-GCM range)")
        ax.plot(h.index, h["mean"], color=C_HIST, lw=1.1, zorder=4,
                label="QDM historical (ensemble mean)")
    # futures: mean + IQR band, per scenario (no splice across 2014/2015)
    for s in SCENARIO_ORDER:
        f = r["future"][s]
        if f.empty:
            continue
        ax.fill_between(f.index, f["q25"], f["q75"], color=SCEN_COLOR[s],
                        alpha=0.20, lw=0, zorder=2,
                        label=f"{SCEN_LABEL[s]} (model IQR)")
        ax.plot(f.index, f["mean"], color=SCEN_COLOR[s], lw=1.3, zorder=5,
                label=f"{SCEN_LABEL[s]} (ensemble mean)")

    # per-period annotation boxes: ensemble mean +/- sd over the window
    ylim_hint = ax.get_ylim()
    ytop = ylim_hint[1]
    for label, (lo, hi), _ in shade:
        if label == "Baseline":
            vals = _window_mean(r["obs"].rename("annual").reset_index(), lo, hi)
            txt = f"{label}\n{lo}\u2013{hi}\nobs {vals.mean():.0f} mm"
        else:
            parts = []
            for s in SCENARIO_ORDER:
                pm = r["per_model"]
                pm = pm[(pm.dataset == "BC") & (pm.scenario == s)
                        & pm.year.between(lo, hi)]
                m = pm.groupby("model")["annual"].mean()
                parts.append(f"{SCEN_LABEL[s]} {m.mean():.0f}\u00b1{m.std():.0f}")
            txt = f"{label}\n{lo}\u2013{hi}\n" + "\n".join(parts)
        ax.text(0.5 * (lo + hi + 1), ytop * 0.995, txt, ha="center", va="top",
                fontsize=7.6, zorder=8,
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#999",
                          lw=0.5, alpha=0.9))
    ax.set_xlim(1980, 2101)
    ax.set_xlabel("Year")
    ax.set_ylabel("Regional annual rainfall (mm)")
    ax.set_title(f"{area_name}: regional annual rainfall \u2014 observed, QDM "
                 f"bias-corrected historical, and CMIP6 ensemble projections\n"
                 f"Shaded: IPCC AR6 assessment periods; no historical\u2013SSP "
                 f"splice across 2014/2015", fontsize=12)
    ax.legend(loc="lower left", fontsize=8, ncol=2, framealpha=0.9)
    ax.grid(True, lw=0.35, ls=":", color="#cccccc")
    fig.tight_layout()
    _save(fig, "FUTURE_Q1_FIGURE_15_ts_regional_annual_ar6")


# --------------------------------------------------------------------------- #
# TS-2: station small multiples, anomaly % vs AR6 baseline (SSP5-8.5)
# --------------------------------------------------------------------------- #
def fig_ts2_station_smallmultiples(yearly: pd.DataFrame, area_name: str,
                                   scenario: str = "ssp585"):
    MapStyle().apply()
    sa = station_annual(yearly)
    stations = sorted(sa[sa.dataset == "Observed"]["station"].unique())
    lo, hi = AR6_BASELINE
    base = (sa[(sa.dataset == "Observed") & sa.year.between(lo, hi)]
            .groupby("station")["annual"].mean())

    def anom(df):
        b = df["station"].map(base)
        return (df["annual"] - b) / b * 100.0

    obs = sa[sa.dataset == "Observed"].copy()
    obs["anom"] = anom(obs)
    fut = sa[(sa.dataset == "BC") & (sa.scenario == scenario)].copy()
    fut["anom"] = anom(fut)
    fens = (fut.groupby(["station", "year"])["anom"]
            .agg(mean="mean", q25=lambda s: s.quantile(0.25),
                 q75=lambda s: s.quantile(0.75)).reset_index())

    # regional series for the highlighted panel
    robs = obs.groupby("year")["anom"].mean()
    rens = fens.groupby("year")[["mean", "q25", "q75"]].mean()

    n = len(stations)
    ncol = 4
    nrow = int(np.ceil((n + 2) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(12.6, 2.7 * nrow),
                             sharex=True, sharey=True)
    axes = axes.ravel()

    def draw(ax, o_year, o_anom, e, title, bold=False):
        for label, (wlo, whi) in AR6_WINDOWS.items():
            ax.axvspan(wlo, whi + 1, color="#f2f2f2", zorder=0)
        ax.axhline(0, color="#888", lw=0.6, ls="--", zorder=1)
        ax.plot(o_year, o_anom, color=C_OBS, lw=0.55, alpha=0.5, zorder=3)
        ax.plot(o_year, pd.Series(o_anom, index=o_year).rolling(5, center=True)
                .mean().values, color=C_OBS, lw=1.3, zorder=4)
        ax.fill_between(e.index, e["q25"], e["q75"], color=SCEN_COLOR[scenario],
                        alpha=0.22, lw=0, zorder=2)
        ax.plot(e.index, e["mean"].rolling(5, center=True, min_periods=1).mean(),
                color=SCEN_COLOR[scenario], lw=1.3, zorder=4)
        ax.set_title(title, fontsize=9.5,
                     fontweight="bold" if bold else "normal")
        if bold:
            for s in ax.spines.values():
                s.set_linewidth(1.6)
        ax.tick_params(labelsize=8)

    for i, st in enumerate(stations):
        o = obs[obs.station == st].sort_values("year")
        e = fens[fens.station == st].set_index("year").sort_index()
        draw(axes[i], o["year"].values, o["anom"].values, e, st)
    draw(axes[n], robs.index.values, robs.values, rens,
         f"Regional mean ({n} gauges)", bold=True)
    # legend panel
    lax = axes[n + 1]
    lax.axis("off")
    handles = [
        plt.Line2D([0], [0], color=C_OBS, lw=1.3,
                   label="Observed (5-yr mean; thin = annual)"),
        plt.matplotlib.patches.Patch(color=SCEN_COLOR[scenario], alpha=0.22,
                                     label=f"{SCEN_LABEL[scenario]} model IQR"),
        plt.Line2D([0], [0], color=SCEN_COLOR[scenario], lw=1.3,
                   label=f"{SCEN_LABEL[scenario]} MME mean (5-yr)"),
        plt.matplotlib.patches.Patch(color="#f2f2f2",
                                     label="AR6 periods (2021\u201340, 2041\u201360, "
                                           "2081\u2013\u2009 2100)"),
    ]
    lax.legend(handles=handles, loc="center", fontsize=9, frameon=False)
    for ax in axes[n + 2:]:
        ax.axis("off")
    for i in range(len(axes)):
        if i % ncol == 0 and axes[i].axison:
            axes[i].set_ylabel("Anomaly (%)", fontsize=9)
    fig.suptitle(f"{area_name}: station-scale annual rainfall anomaly vs AR6 "
                 f"baseline {AR6_BASELINE[0]}\u2013{AR6_BASELINE[1]} "
                 f"({SCEN_LABEL[scenario]})", fontsize=13)
    fig.supxlabel("Year", fontsize=10)
    fig.tight_layout(rect=(0, 0.015, 1, 0.965))
    _save(fig, "FUTURE_Q1_FIGURE_16_ts_station_smallmultiples_ar6")


# --------------------------------------------------------------------------- #
# TS-3: monthly seasonal cycle by AR6 period
# --------------------------------------------------------------------------- #
def fig_ts3_seasonal_cycle(monthly: pd.DataFrame, area_name: str):
    MapStyle().apply()
    mm = monthly.copy()
    mm["year"] = mm["year"].astype(int)

    def clim(df):
        """Ensemble of per-model monthly climatologies -> mean/min/max."""
        per = df.groupby(["model", "month"])["monthly_total"].mean().reset_index()
        g = per.groupby("month")["monthly_total"]
        return pd.DataFrame({"mean": g.mean(), "min": g.min(), "max": g.max()})

    obs_clim = (mm[(mm.dataset == "Observed")
                   & mm.year.between(*AR6_BASELINE)]
                .groupby("month")["monthly_total"].mean())
    hist_clim = clim(mm[(mm.dataset == "BC_HIST")
                        & mm.year.between(*AR6_BASELINE)])

    fig, axes = plt.subplots(1, 2, figsize=(12.6, 4.9), sharey=True)
    months = np.arange(1, 13)
    mlab = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
    period_style = {k: ls for k, ls in zip(AR6_ORDER, ["--", "-.", "-"])}
    for ax, s in zip(axes, SCENARIO_ORDER):
        ax.plot(months, obs_clim.reindex(months), color=C_OBS, lw=1.8,
                marker="o", ms=3.5, zorder=6,
                label=f"Observed {AR6_BASELINE[0]}\u2013{AR6_BASELINE[1]}")
        if not hist_clim.empty:
            ax.fill_between(months, hist_clim["min"].reindex(months),
                            hist_clim["max"].reindex(months), color=C_HIST,
                            alpha=0.18, lw=0, zorder=1)
            ax.plot(months, hist_clim["mean"].reindex(months), color=C_HIST,
                    lw=1.2, zorder=4, label="QDM historical (mean, range)")
        for k in AR6_ORDER:
            lo, hi = AR6_WINDOWS[k]
            cl = clim(mm[(mm.dataset == "BC") & (mm.scenario == s)
                         & mm.year.between(lo, hi)])
            if cl.empty:
                continue
            ax.plot(months, cl["mean"].reindex(months), color=SCEN_COLOR[s],
                    lw=1.4, ls=period_style[k], zorder=5,
                    label=f"{k} {lo}\u2013{hi}")
        ax.set_xticks(months)
        ax.set_xticklabels(mlab)
        ax.set_title(SCEN_LABEL[s], fontsize=11)
        ax.grid(True, lw=0.35, ls=":", color="#cccccc")
        ax.legend(fontsize=7.6, loc="upper left")
        ax.set_xlabel("Month")
    axes[0].set_ylabel("Regional mean monthly rainfall (mm)")
    fig.suptitle(f"{area_name}: monthly rainfall regime \u2014 observed baseline "
                 f"vs QDM historical vs AR6 future periods", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    _save(fig, "FUTURE_Q1_FIGURE_17_ts_seasonal_cycle_ar6")


# --------------------------------------------------------------------------- #
# TABLE_10 / TABLE_11
# --------------------------------------------------------------------------- #
def table10_station_historical(yearly: pd.DataFrame) -> pd.DataFrame:
    sa = station_annual(yearly)
    lo, hi = AR6_BASELINE
    rows = []
    obs = sa[sa.dataset == "Observed"]
    hist = sa[sa.dataset == "BC_HIST"]
    models = sorted(hist["model"].unique())
    for st, og in obs.groupby("station"):
        row = {"station": st,
               "obs_mean_full": og["annual"].mean(),
               "obs_mean_AR6base": og[og.year.between(lo, hi)]["annual"].mean()}
        mm = []
        for m in models:
            v = hist[(hist.station == st) & (hist.model == m)]
            v = v[v.year.between(lo, hi)]["annual"].mean()
            row[f"{m}"] = v
            row[f"{m}_bias_pct"] = ((v - row["obs_mean_AR6base"])
                                    / row["obs_mean_AR6base"] * 100.0)
            mm.append(v)
        row["MME_mean"] = float(np.nanmean(mm)) if mm else np.nan
        row["MME_bias_pct"] = ((row["MME_mean"] - row["obs_mean_AR6base"])
                               / row["obs_mean_AR6base"] * 100.0)
        rows.append(row)
    out = pd.DataFrame(rows).sort_values("station").reset_index(drop=True)
    out.insert(1, "period", f"AR6 baseline {lo}-{hi} (obs_mean_full = 1981-2014)")
    out.insert(2, "unit", "mm/yr")
    return out


def table11_station_future_ar6(yearly: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    sa = station_annual(yearly)
    lo, hi = AR6_BASELINE
    base = (sa[(sa.dataset == "Observed") & sa.year.between(lo, hi)]
            .groupby("station")["annual"].mean())
    fut = sa[sa.dataset == "BC"]
    models = sorted(fut["model"].unique())
    rows = []
    for (st, s, k), _ in fut.groupby(["station", "scenario", "window"]) \
            if False else []:
        pass
    for k in AR6_ORDER:
        wlo, whi = AR6_WINDOWS[k]
        sub = fut[fut.year.between(wlo, whi)]
        for (st, s), g in sub.groupby(["station", "scenario"]):
            pm = g.groupby("model")["annual"].mean()
            row = {"station": st, "scenario": s, "period": k,
                   "period_years": f"{wlo}-{whi}", "unit": "mm/yr",
                   "obs_AR6base": base.get(st, np.nan)}
            for m in models:
                row[m] = pm.get(m, np.nan)
            row["MME_mean"] = pm.mean()
            row["MME_median"] = pm.median()
            row["MME_min"] = pm.min()
            row["MME_max"] = pm.max()
            row["delta_pct_vs_AR6base"] = ((pm.mean() - row["obs_AR6base"])
                                           / row["obs_AR6base"] * 100.0)
            row["sign_agreement"] = _sign_agreement(pm - row["obs_AR6base"])
            rows.append(row)
    tab = pd.DataFrame(rows).sort_values(
        ["scenario", "period", "station"]).reset_index(drop=True)
    wide = tab.pivot_table(index="station", columns=["scenario", "period"],
                           values="delta_pct_vs_AR6base").round(1)
    wide.columns = [f"{s}_{p}_dpct" for s, p in wide.columns]
    return tab, wide.reset_index()


def build_timeseries_q2_outputs(cube: dict, area_name: str,
                                write_workbook, info_fn) -> None:
    """Generate TS-1..3 + TABLE_10/11 from an existing cube dict."""
    yearly = cube["yearly"]
    fig_ts1_regional(yearly, area_name)
    fig_ts2_station_smallmultiples(yearly, area_name)
    fig_ts3_seasonal_cycle(cube["monthly_regional"], area_name)

    t10 = table10_station_historical(yearly)
    write_workbook(C.FUTURE_Q1_TAB / "FUTURE_Q1_TABLE_10_STATION_RAIN_HISTORICAL_GCM_MME.xlsx",
                   info_fn({"Table": "Per-station annual rainfall: observed vs "
                            "each GCM (QDM bc-historical) vs MME, AR6 baseline",
                            "AR6 baseline": f"{AR6_BASELINE[0]}-{AR6_BASELINE[1]}"}),
                   t10)
    t11, wide = table11_station_future_ar6(yearly)
    import pandas as _pd
    from .future_q1 import _write_workbook as _ww  # reuse writer for extra sheet
    path = C.FUTURE_Q1_TAB / "FUTURE_Q1_TABLE_11_STATION_RAIN_FUTURE_AR6_GCM_MME.xlsx"
    with _pd.ExcelWriter(path, engine="xlsxwriter") as w:
        info_fn({"Table": "Per-station annual rainfall by AR6 period x scenario: "
                 "each GCM, MME summary, delta% vs AR6 observed baseline",
                 "AR6 periods": ", ".join(f"{k}:{v[0]}-{v[1]}"
                                          for k, v in AR6_WINDOWS.items())}) \
            .to_excel(w, index=False, sheet_name="Info")
        t11.to_excel(w, index=False, sheet_name="results")
        wide.to_excel(w, index=False, sheet_name="MME_Summary")
        sig = t11[t11["sign_agreement"] >= 6 / 7 - 1e-9]
        (sig if len(sig) else _pd.DataFrame(
            {"note": ["no station-period with >=6/7 sign agreement"]})) \
            .to_excel(w, index=False, sheet_name="Significant")
    log.info("saved %s", path.name)
