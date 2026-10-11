"""
===============================================================================
  Time Series Comparison: Observed vs Raw CMIP6 vs Bias-Corrected (QDM)
  Annual / Monthly Rainfall – Per Station + All-Station Overview
  มาตรฐานวารสาร Q2-Q3 / TCI1
-------------------------------------------------------------------------------
  ไฟล์ Input (ในโฟลเดอร์เดียวกับ script):
    • Observed     → ชื่อไฟล์มีคำว่า  "Observed"  (case-insensitive)
    • Raw CMIP6    → ชื่อไฟล์ขึ้นต้นด้วย  "pr"
    • Bias-Corrected → ชื่อไฟล์ขึ้นต้นด้วย "bc"
  โครงสร้าง CSV : YEAR, MONTH, DAY, <station_id>, ...

  อ้างอิง:
    Cannon et al. (2015) QDM – J. Climate 28:6938–6959
    Maraun (2016) Bias Correcting Climate Change Simulations – Curr. Clim. Chang. Rep.
    Teutschbein & Seibert (2012) Hydrol. Earth Syst. Sci. 16:3391–3314
===============================================================================
"""

import os, sys, glob, warnings, math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
from matplotlib.gridspec import GridSpec

warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════════════════════════════════════
# 0.  JOURNAL-GRADE STYLE
# ═══════════════════════════════════════════════════════════════════════════
plt.rcParams.update({
    "font.family":          "serif",
    "font.serif":           ["Times New Roman", "DejaVu Serif"],
    "font.size":            10,
    "axes.titlesize":       10,
    "axes.labelsize":       9.5,
    "xtick.labelsize":      8.5,
    "ytick.labelsize":      8.5,
    "legend.fontsize":      8,
    "figure.titlesize":     12,
    "lines.linewidth":      1.3,
    "axes.linewidth":       0.8,
    "axes.spines.top":      False,
    "axes.spines.right":    False,
    "axes.grid":            True,
    "grid.linestyle":       "--",
    "grid.linewidth":       0.35,
    "grid.alpha":           0.45,
    "grid.color":           "#AAAAAA",
    "figure.dpi":           150,
    "savefig.dpi":          300,
    "savefig.bbox":         "tight",
    "savefig.pad_inches":   0.10,
    "mathtext.fontset":     "stix",
})

# ── Colour palette (colour-blind–safe) ────────────────────────────────────
C = {
    "obs":       "#1A1A2E",   # near-black  – Observed
    "raw":       "#E63946",   # vivid red   – Raw CMIP6
    "bc":        "#2196F3",   # blue        – Bias-Corrected
    "obs_fill":  "#CCCCCC",   # light grey  – Observed band/fill
    "raw_fill":  "#FFCCCC",   # pink fill
    "bc_fill":   "#BBDEFB",   # light blue fill
    "mean_obs":  "#333333",
    "mean_raw":  "#C62828",
    "mean_bc":   "#0D47A1",
    "ref_line":  "#2E7D32",
    "grid":      "#DDDDDD",
}

ALPHA_LINE  = 0.85
ALPHA_FILL  = 0.20
ALPHA_SHADE = 0.30

# ═══════════════════════════════════════════════════════════════════════════
# 1.  HELPER: STATISTICS
# ═══════════════════════════════════════════════════════════════════════════

def bias_metrics(obs, sim):
    """Compute bias statistics; aligns Series on common index automatically."""
    if isinstance(obs, pd.Series) and isinstance(sim, pd.Series):
        common = obs.index.intersection(sim.index)
        o = obs.reindex(common).values.astype(float)
        s = sim.reindex(common).values.astype(float)
    else:
        obs = np.asarray(obs, dtype=float)
        sim = np.asarray(sim, dtype=float)
        n   = min(len(obs), len(sim))
        o, s = obs[:n], sim[:n]
    mask = ~np.isnan(o) & ~np.isnan(s)
    o, s = o[mask], s[mask]
    if len(o) < 2:
        return dict(pbias=np.nan, rmse=np.nan, corr=np.nan, ratio=np.nan)
    pbias = 100 * (np.mean(s) - np.mean(o)) / np.mean(o)
    rmse  = np.sqrt(np.mean((s - o) ** 2))
    corr  = float(np.corrcoef(o, s)[0, 1])
    ratio = np.mean(s) / np.mean(o) if np.mean(o) != 0 else np.nan
    return dict(pbias=pbias, rmse=rmse, corr=corr, ratio=ratio)


def rolling_annual(monthly: pd.Series, window: int = 12) -> pd.Series:
    """12-month centred rolling mean (smoothed annual cycle view)."""
    return monthly.rolling(window=window, center=True, min_periods=6).mean()

# ═══════════════════════════════════════════════════════════════════════════
# 2.  FILE DISCOVERY & LOADING
# ═══════════════════════════════════════════════════════════════════════════

def find_csv_files(folder: str):
    """
    Scan folder for the three CSV datasets.
    Returns paths: (obs_path, raw_path, bc_path)
    Matching rules (case-insensitive):
      Observed  → filename contains 'observed'
      Raw CMIP6 → filename starts with 'pr'
      BC        → filename starts with 'bc'
    """
    all_csv = [f for f in Path(folder).glob("*.csv")]
    obs_files = [f for f in all_csv if "observed" in f.name.lower()]
    raw_files = [f for f in all_csv if f.name.lower().startswith("pr")]
    bc_files  = [f for f in all_csv if f.name.lower().startswith("bc")]

    def pick(lst, label):
        if not lst:
            return None
        if len(lst) > 1:
            print(f"  ⚠  พบไฟล์ {label} มากกว่า 1 ไฟล์ – ใช้: {lst[0].name}")
        return str(lst[0])

    return pick(obs_files, "Observed"), pick(raw_files, "Raw CMIP6"), pick(bc_files, "BC")


def load_monthly(csv_path: str, label: str):
    """
    Read daily CSV → aggregate to monthly totals.
    Returns DataFrame: index=DatetimeIndex(monthly), columns=station_ids
    """
    if csv_path is None or not os.path.isfile(csv_path):
        print(f"  ✗  ไม่พบไฟล์ {label}: {csv_path}")
        return None, []

    df = pd.read_csv(csv_path)
    for mv in [-99, -999, -9999, -9.99e+20, 1e+20]:
        df.replace(mv, np.nan, inplace=True)
    num_cols = df.select_dtypes(include=[np.number]).columns
    df[num_cols] = df[num_cols].where(df[num_cols] >= 0)

    stns = [c for c in df.columns if c not in ("YEAR", "MONTH", "DAY")]

    # Build datetime index from YEAR+MONTH (use day=1)
    df["date"] = pd.to_datetime(
        df["YEAR"].astype(str) + "-" + df["MONTH"].astype(str).str.zfill(2),
        format="%Y-%m", errors="coerce")

    monthly = (df.groupby("date")[stns]
                 .sum(min_count=15))          # need ≥15 days per month
    monthly.index = pd.DatetimeIndex(monthly.index)
    monthly.index.freq = None
    return monthly, stns


def load_annual(csv_path: str):
    """Daily CSV → annual totals."""
    if csv_path is None or not os.path.isfile(csv_path):
        return None, []
    df = pd.read_csv(csv_path)
    for mv in [-99, -999, -9999]:
        df.replace(mv, np.nan, inplace=True)
    num_cols = df.select_dtypes(include=[np.number]).columns
    df[num_cols] = df[num_cols].where(df[num_cols] >= 0)
    stns = [c for c in df.columns if c not in ("YEAR", "MONTH", "DAY")]
    annual = df.groupby("YEAR")[stns].apply(
        lambda g: g.sum(min_count=int(0.8 * len(g))))
    annual.index.name = "YEAR"
    return annual, stns

# ═══════════════════════════════════════════════════════════════════════════
# 3.  SINGLE-STATION PLOT  (3-panel layout)
# ═══════════════════════════════════════════════════════════════════════════

def plot_station(stn: str,
                 obs_m: pd.Series, raw_m: pd.Series, bc_m: pd.Series,
                 obs_a: pd.Series, raw_a: pd.Series, bc_a: pd.Series,
                 out_path: str, fig_num: int, total_figs: int,
                 period_obs: str, period_sim: str,
                 base_name: str):
    """
    3-panel figure per station:
      Panel A – Monthly time series (Observed / Raw / BC)
      Panel B – 12-month rolling mean (smoothed)
      Panel C – Annual totals bar chart with trend lines
    """

    # ── align monthly to common date range ────────────────────────────
    def align(s1, s2, s3):
        idx = s1.index.union(s2.index).union(s3.index) \
              if s2 is not None and s3 is not None else s1.index
        s1r = s1.reindex(idx)
        s2r = s2.reindex(idx) if s2 is not None else pd.Series(np.nan, index=idx)
        s3r = s3.reindex(idx) if s3 is not None else pd.Series(np.nan, index=idx)
        return s1r, s2r, s3r

    om, rm, bm = align(obs_m, raw_m, bc_m)
    roll_o = rolling_annual(om)
    roll_r = rolling_annual(rm)
    roll_b = rolling_annual(bm)

    # ── bias metrics ──────────────────────────────────────────────────
    met_raw = bias_metrics(om.values, rm.values)
    met_bc  = bias_metrics(om.values, bm.values)

    # ── annual series ─────────────────────────────────────────────────
    # use pre-computed annual where available; fallback to monthly resample
    def safe_annual(s_ann, s_mon):
        if s_ann is not None and len(s_ann.dropna()) > 2:
            return s_ann
        if s_mon is not None:
            return s_mon.resample("YE").sum(min_count=10)
        return None

    oa = safe_annual(obs_a, obs_m)
    ra = safe_annual(raw_a, raw_m)
    ba = safe_annual(bc_a, bc_m)

    # ── figure ─────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(13, 10))
    gs  = GridSpec(3, 1, figure=fig,
                   hspace=0.38, top=0.91, bottom=0.08,
                   left=0.07, right=0.97)
    axA = fig.add_subplot(gs[0])
    axB = fig.add_subplot(gs[1])
    axC = fig.add_subplot(gs[2])

    # ─────────────────── PANEL A: Monthly time series ─────────────────
    axA.fill_between(om.index, 0, om.values,
                     color=C["obs_fill"], alpha=0.45, zorder=1)
    axA.plot(om.index,  om.values,  color=C["obs"],
             lw=0.7, alpha=0.75, zorder=3, label="Observed")
    axA.plot(rm.index,  rm.values,  color=C["raw"],
             lw=0.7, alpha=0.65, zorder=4, label="Raw CMIP6")
    axA.plot(bm.index,  bm.values,  color=C["bc"],
             lw=0.7, alpha=0.65, zorder=5, label="Bias-Corrected (QDM)")

    # mean lines
    axA.axhline(om.mean(), color=C["obs"], lw=1.0,
                ls=(0,(6,4)), alpha=0.8)
    axA.axhline(rm.mean(), color=C["raw"], lw=1.0,
                ls=(0,(6,4)), alpha=0.8)
    axA.axhline(bm.mean(), color=C["bc"],  lw=1.0,
                ls=(0,(6,4)), alpha=0.8)

    # bias annotation
    annA = (
        f"Pbias (Raw)  = {met_raw['pbias']:+.1f}%   "
        f"RMSE = {met_raw['rmse']:.1f} mm   r = {met_raw['corr']:.3f}\n"
        f"Pbias (QDM) = {met_bc['pbias']:+.1f}%   "
        f"RMSE = {met_bc['rmse']:.1f} mm   r = {met_bc['corr']:.3f}"
    )
    axA.text(0.01, 0.97, annA, transform=axA.transAxes,
             va="top", ha="left", fontsize=7.5, family="monospace",
             bbox=dict(boxstyle="round,pad=0.4", facecolor="#FAFAFA",
                       edgecolor="#BBBBBB", lw=0.6, alpha=0.93), zorder=9)
    axA.set_title(f"(a)  Monthly Rainfall — Station {stn}",
                  loc="left", fontsize=9.5, fontweight="bold", pad=4)
    axA.set_ylabel("Monthly Rainfall (mm)", labelpad=4)
    axA.xaxis.set_major_locator(mdates.YearLocator(5))
    axA.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axA.xaxis.set_minor_locator(mdates.YearLocator(1))
    _style_ax(axA)

    # ─────────────────── PANEL B: 12-month rolling mean ───────────────
    axB.fill_between(roll_o.index, roll_o.values, alpha=0.18,
                     color=C["obs_fill"], zorder=1)
    axB.plot(roll_o.index, roll_o.values, color=C["obs"],
             lw=1.6, alpha=ALPHA_LINE, zorder=3, label="Observed (12-mo rolling)")
    axB.plot(roll_r.index, roll_r.values, color=C["raw"],
             lw=1.5, alpha=ALPHA_LINE, zorder=4,
             label="Raw CMIP6 (12-mo rolling)")
    axB.plot(roll_b.index, roll_b.values, color=C["bc"],
             lw=1.5, alpha=ALPHA_LINE, zorder=5,
             label="Bias-Corrected / QDM (12-mo rolling)")

    # shaded bias gap  (Raw – Obs)
    axB.fill_between(roll_o.index, roll_o.values, roll_r.values,
                     where=~np.isnan(roll_r.values),
                     color=C["raw"], alpha=0.12, zorder=2,
                     label="Raw model bias region")

    axB.set_title("(b)  12-Month Centred Rolling Mean  "
                  "(emphasises systematic bias & trend)",
                  loc="left", fontsize=9.5, fontweight="bold", pad=4)
    axB.set_ylabel("Rainfall (mm)", labelpad=4)
    axB.xaxis.set_major_locator(mdates.YearLocator(5))
    axB.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axB.xaxis.set_minor_locator(mdates.YearLocator(1))
    leg_B = axB.legend(loc="upper right", frameon=True, framealpha=0.92,
                        edgecolor="#AAAAAA", fontsize=7.5, ncol=2,
                        handlelength=2.0, columnspacing=1.0)
    leg_B.get_frame().set_linewidth(0.6)
    _style_ax(axB)

    # ─────────────────── PANEL C: Annual totals bar + trend ───────────
    def plot_annual_bars(ax, s_ann, color, label, offset=0.0, width=0.28):
        if s_ann is None or s_ann.dropna().empty:
            return
        vals = s_ann.dropna()
        yrs  = vals.index.astype(float) if hasattr(vals.index[0], 'year') \
               else vals.index.astype(float)
        # For DatetimeIndex convert to year float
        if hasattr(vals.index, 'year'):
            yrs = np.array([d.year for d in vals.index], dtype=float)
        ax.bar(yrs + offset, vals.values, width=width, color=color,
               edgecolor=C["obs"] if color == C["obs"] else color,
               linewidth=0.3, alpha=0.75, label=label, zorder=2)
        # OLS trend
        mask = ~np.isnan(vals.values)
        if mask.sum() > 3:
            slope, intercept, r, p, _ = stats.linregress(
                yrs[mask], vals.values[mask])
            x_fit = np.linspace(yrs[mask].min(), yrs[mask].max(), 200)
            ax.plot(x_fit, slope * x_fit + intercept,
                    color=color, lw=1.8, ls="--", zorder=5, alpha=0.9)

    # bars side-by-side  (obs centre, raw left, bc right)
    plot_annual_bars(axC, oa, C["obs"], "Observed",            offset=-0.28)
    plot_annual_bars(axC, ra, C["raw"], "Raw CMIP6",           offset= 0.0)
    plot_annual_bars(axC, ba, C["bc"],  "Bias-Corrected (QDM)",offset= 0.28)

    axC.set_title("(c)  Annual Rainfall with Linear Trend Lines (dashed)",
                  loc="left", fontsize=9.5, fontweight="bold", pad=4)
    axC.set_ylabel("Annual Rainfall (mm)", labelpad=4)
    axC.set_xlabel("Year", labelpad=4)
    axC.xaxis.set_major_locator(ticker.MultipleLocator(5))
    axC.xaxis.set_minor_locator(ticker.MultipleLocator(1))
    axC.yaxis.set_major_locator(ticker.MultipleLocator(500))
    axC.yaxis.set_minor_locator(ticker.MultipleLocator(100))
    leg_C = axC.legend(loc="upper right", frameon=True, framealpha=0.92,
                        edgecolor="#AAAAAA", fontsize=7.5, ncol=3,
                        handlelength=1.8)
    leg_C.get_frame().set_linewidth(0.6)
    _style_ax(axC)

    # ── Main title ─────────────────────────────────────────────────────
    fig.suptitle(
        f"Observed vs Raw CMIP6 vs Bias-Corrected Rainfall — Station {stn}\n"
        f"Prachuap Khiri Khan Province, Thailand  "
        f"│  Obs: {period_obs}  │  Sim: {period_sim}",
        fontsize=11, fontweight="bold", y=0.995)

    # ── Footnote ───────────────────────────────────────────────────────
    fig.text(0.01, 0.005,
             "Bias correction: Quantile Delta Mapping (QDM).  "
             "Pbias = percent bias; RMSE = root mean square error; "
             "r = Pearson correlation.  "
             "Ref: Cannon et al. (2015); Teutschbein & Seibert (2012).",
             ha="left", fontsize=6.5, color="#777777", style="italic")
    fig.text(0.99, 0.005,
             f"Fig. {fig_num} of {total_figs}",
             ha="right", fontsize=7, color="#AAAAAA")

    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}")


# ═══════════════════════════════════════════════════════════════════════════
# 4.  ALL-STATION OVERVIEW  (2-row panel × n_stn/2 cols)
# ═══════════════════════════════════════════════════════════════════════════

def plot_overview(all_data: list, period_obs: str, period_sim: str,
                  out_path: str):
    """
    Compact overview: rolling mean per station (2 rows × ceil(n/2) cols).
    Each mini-panel shows Obs / Raw / BC rolling mean + metric annotation.
    """
    n  = len(all_data)
    nc = min(4, math.ceil(n / 2))
    nr = math.ceil(n / nc)

    fig_w = nc * 4.5
    fig_h = nr * 3.6

    fig, axes = plt.subplots(nr, nc, figsize=(fig_w, fig_h),
                             sharex=False, sharey=False)
    axes_flat = axes.flatten() if hasattr(axes, "flatten") else [axes]

    for idx, d in enumerate(all_data):
        ax  = axes_flat[idx]
        stn = d["stn"]
        om  = d["obs_m"];  rm  = d["raw_m"];  bm  = d["bc_m"]

        ro  = rolling_annual(om)
        rr  = rolling_annual(rm)
        rb  = rolling_annual(bm)

        met_r = bias_metrics(om.values, rm.values)
        met_b = bias_metrics(om.values, bm.values)

        ax.fill_between(ro.index, ro.values, alpha=0.18,
                        color=C["obs_fill"], zorder=1)
        # align all rolling series to obs index before fill_between
        common_idx = ro.dropna().index
        ro_c = ro.reindex(common_idx)
        rr_c = rr.reindex(common_idx)
        rb_c = rb.reindex(common_idx)
        valid_r = ~np.isnan(rr_c.values)
        ax.fill_between(ro_c.index, ro_c.values, rr_c.values,
                        where=valid_r,
                        color=C["raw"], alpha=0.12, zorder=2)
        ax.plot(ro_c.index, ro_c.values, color=C["obs"],
                lw=1.4, alpha=0.90, label="Obs")
        ax.plot(rr.index, rr.values, color=C["raw"],
                lw=1.2, alpha=0.85, label="Raw")
        ax.plot(rb.index, rb.values, color=C["bc"],
                lw=1.2, alpha=0.85, ls="-", label="QDM")

        ax.set_title(f"Station {stn}", fontsize=8.5, fontweight="bold", pad=2)
        ann = (f"Raw  Pb={met_r['pbias']:+.1f}%  r={met_r['corr']:.2f}\n"
               f"QDM Pb={met_b['pbias']:+.1f}%  r={met_b['corr']:.2f}")
        ax.text(0.03, 0.97, ann,
                transform=ax.transAxes, va="top", fontsize=6.8,
                family="monospace",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#FAFAFA",
                          edgecolor="#CCCCCC", lw=0.5, alpha=0.93))
        ax.xaxis.set_major_locator(mdates.YearLocator(10))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.tick_params(labelsize=7)
        ax.set_ylabel("RF (mm)", fontsize=7, labelpad=2)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(True, lw=0.3, ls="--", alpha=0.45)

    for ax in axes_flat[n:]:
        ax.set_visible(False)

    # shared legend
    handles = [
        Line2D([0],[0], color=C["obs"], lw=1.6,
               label="Observed (12-mo rolling)"),
        Line2D([0],[0], color=C["raw"], lw=1.4,
               label="Raw CMIP6 (12-mo rolling)"),
        Line2D([0],[0], color=C["bc"],  lw=1.4,
               label="Bias-Corrected / QDM (12-mo rolling)"),
        mpatches.Patch(color=C["raw"], alpha=0.20,
                       label="Raw model bias region"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=4,
               fontsize=8, frameon=True, edgecolor="#AAAAAA",
               bbox_to_anchor=(0.5, -0.02))

    fig.suptitle(
        "Overview: Observed vs Raw CMIP6 vs Bias-Corrected (QDM) Rainfall\n"
        f"Prachuap Khiri Khan Province, Thailand  "
        f"│  Obs: {period_obs}  │  Sim: {period_sim}\n"
        "12-Month Centred Rolling Mean",
        fontsize=10.5, fontweight="bold", y=1.01)

    fig.text(0.99, -0.015,
             "Pb = percent bias; r = Pearson correlation.  "
             "Ref: Cannon et al. (2015); Teutschbein & Seibert (2012).",
             ha="right", fontsize=6.5, color="#777777", style="italic")

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"    ✓  {Path(out_path).name}  [ALL-STATION OVERVIEW]")


# ═══════════════════════════════════════════════════════════════════════════
# 5.  UTILITY
# ═══════════════════════════════════════════════════════════════════════════

def _style_ax(ax):
    ax.tick_params(axis="x", which="major", length=4, width=0.7)
    ax.tick_params(axis="x", which="minor", length=2, width=0.5)
    ax.tick_params(axis="y", which="both",  length=3, width=0.7)
    ax.set_ylim(bottom=0)


def period_str(df):
    """Return 'YYYY–YYYY' from a monthly DatetimeIndex."""
    if df is None or df.empty:
        return "N/A"
    yrs = sorted({d.year for d in df.index})
    return f"{yrs[0]}–{yrs[-1]}"


# ═══════════════════════════════════════════════════════════════════════════
# 6.  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def find_script_folder():
    """Return folder of script (CWD if running interactively)."""
    try:
        return str(Path(os.path.abspath(__file__)).parent)
    except NameError:
        return os.getcwd()


def main():
    print("=" * 70)
    print("  Time Series: Observed vs Raw CMIP6 vs Bias-Corrected (QDM)")
    print("  มาตรฐานวารสาร Q2-Q3 / TCI1")
    print("=" * 70)

    # ── โฟลเดอร์ทำงาน ─────────────────────────────────────────────────
    if len(sys.argv) > 1:
        work_dir = sys.argv[1].strip('"').strip("'")
    else:
        work_dir = find_script_folder()

    print(f"  โฟลเดอร์ : {work_dir}")

    # ── ค้นหาไฟล์ ─────────────────────────────────────────────────────
    obs_path, raw_path, bc_path = find_csv_files(work_dir)

    if obs_path is None:
        sys.exit("  ✗  ไม่พบไฟล์ Observed (ชื่อต้องมีคำว่า 'Observed')")
    if raw_path is None:
        print("  ⚠  ไม่พบไฟล์ Raw CMIP6 (ชื่อต้องขึ้นต้นด้วย 'pr')")
    if bc_path is None:
        print("  ⚠  ไม่พบไฟล์ Bias-Corrected (ชื่อต้องขึ้นต้นด้วย 'bc')")

    print(f"  Observed : {Path(obs_path).name}")
    print(f"  Raw CMIP6: {Path(raw_path).name if raw_path else 'ไม่พบ'}")
    print(f"  BC (QDM) : {Path(bc_path).name  if bc_path  else 'ไม่พบ'}")
    print("-" * 70)

    # ── โหลดข้อมูล ────────────────────────────────────────────────────
    print("  กำลังโหลดข้อมูล ...")
    obs_m, obs_stns = load_monthly(obs_path, "Observed")
    raw_m, raw_stns = load_monthly(raw_path, "Raw CMIP6")
    bc_m,  bc_stns  = load_monthly(bc_path,  "BC")

    obs_a, _ = load_annual(obs_path)
    raw_a, _ = load_annual(raw_path)
    bc_a,  _ = load_annual(bc_path)

    stns = obs_stns   # master station list from Observed

    period_obs = period_str(obs_m)
    period_sim = period_str(raw_m) if raw_m is not None else period_str(bc_m)

    print(f"  สถานี {len(stns)} สถานี  │  Obs: {period_obs}  │  Sim: {period_sim}")

    # ── สร้างโฟลเดอร์ output ──────────────────────────────────────────
    base_name = Path(obs_path).stem
    fig_dir   = Path(work_dir) / f"Output_TimeSeries_{base_name}"
    fig_dir.mkdir(exist_ok=True)
    print(f"  Output   : {fig_dir}")
    print("-" * 70)
    print("  กำลังสร้างรูปภาพ ...")
    print()

    # ── loop รายสถานี ─────────────────────────────────────────────────
    all_data   = []
    total_figs = len(stns) + 1   # +1 for overview

    for fig_num, stn in enumerate(stns, 1):
        stn = str(stn)

        def get_series(df, s):
            if df is None or s not in df.columns:
                return pd.Series(dtype=float)
            return df[s].dropna()

        def get_annual(df, s):
            if df is None or s not in df.columns:
                return None
            return df[s].dropna()

        om  = get_series(obs_m, stn)
        rm  = get_series(raw_m, stn)
        bm  = get_series(bc_m,  stn)

        oa  = get_annual(obs_a, stn)
        ra  = get_annual(raw_a, stn)
        ba  = get_annual(bc_a,  stn)

        if len(om) < 6:
            print(f"  ⚠  Station {stn}: Observed ไม่เพียงพอ – ข้ามไป")
            continue

        all_data.append(dict(stn=stn, obs_m=om, raw_m=rm, bc_m=bm))

        out_png = fig_dir / f"Output_TimeSeries_{base_name}_Stn{stn}.png"
        plot_station(stn, om, rm, bm, oa, ra, ba,
                     str(out_png), fig_num, total_figs,
                     period_obs, period_sim, base_name)

    # ── overview ──────────────────────────────────────────────────────
    if all_data:
        print()
        print("  กำลังสร้าง All-Station Overview ...")
        ov_png = fig_dir / f"Output_TimeSeries_{base_name}_ALL_Overview.png"
        plot_overview(all_data, period_obs, period_sim, str(ov_png))

    print()
    print("=" * 70)
    print(f"  เสร็จสิ้น – {len(all_data) + 1} ไฟล์รูปภาพ")
    print(f"  บันทึกใน: {fig_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
