"""
===============================================================================
  Annual Rainfall Trend Plots – Mann–Kendall + Sen's Slope
  รูปภาพแสดง trend รายสถานี พร้อม Uncertainty Band
  มาตรฐานวารสาร Q2-Q3 / TCI1
-------------------------------------------------------------------------------
  อ้างอิง:
    Mann (1945), Kendall (1975), Sen (1968), Gilbert (1987)
===============================================================================
"""

import os, sys, math, warnings
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
from matplotlib.lines import Line2D
from pathlib import Path

warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════════════════════════════════════
# 0.  JOURNAL-GRADE MATPLOTLIB STYLE
# ═══════════════════════════════════════════════════════════════════════════
plt.rcParams.update({
    # Font
    "font.family":          "serif",
    "font.serif":           ["Times New Roman", "DejaVu Serif"],
    "font.size":            10,
    "axes.titlesize":       11,
    "axes.labelsize":       10,
    "xtick.labelsize":      9,
    "ytick.labelsize":      9,
    "legend.fontsize":      8.5,
    "figure.titlesize":     12,
    # Lines / markers
    "lines.linewidth":      1.4,
    "lines.markersize":     5,
    "patch.linewidth":      0.8,
    # Axes
    "axes.linewidth":       0.8,
    "axes.spines.top":      False,
    "axes.spines.right":    False,
    "axes.grid":            True,
    "grid.linestyle":       "--",
    "grid.linewidth":       0.4,
    "grid.alpha":           0.5,
    "grid.color":           "#AAAAAA",
    # Figure
    "figure.dpi":           300,
    "savefig.dpi":          300,
    "savefig.bbox":         "tight",
    "savefig.pad_inches":   0.08,
    # Math
    "mathtext.fontset":     "stix",
})

# ═══════════════════════════════════════════════════════════════════════════
# 1.  COLOUR PALETTE  (colour-blind–safe, print-friendly)
# ═══════════════════════════════════════════════════════════════════════════
COL = {
    "bar_inc":   "#4393C3",   # blue  – bars (increasing or neutral)
    "bar_dec":   "#D6604D",   # red   – bars (decreasing)
    "bar_no":    "#74ADD1",   # light blue
    "edge":      "#1A1A2E",   # dark edge
    "trend_inc": "#B22222",   # dark red trend line  (increasing, sig)
    "trend_dec": "#1565C0",   # dark blue trend line (decreasing, sig)
    "trend_ns":  "#555555",   # grey trend line      (no trend)
    "band_inc":  "#FFCCCC",   # uncertainty band fill (sig+)
    "band_dec":  "#CCE5FF",   # uncertainty band fill (sig-)
    "band_ns":   "#E0E0E0",   # uncertainty band fill (ns)
    "mean":      "#2E7D32",   # mean line
    "annot_bg":  "#FAFAFA",   # annotation box background
}

# ═══════════════════════════════════════════════════════════════════════════
# 2.  STATISTICAL FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def mann_kendall(x: np.ndarray, alpha: float = 0.05) -> dict:
    """Two-tailed MK test with tied-group variance correction."""
    n = len(x)
    S = int(sum(int(np.sign(x[j] - x[i]))
                for i in range(n - 1) for j in range(i + 1, n)))
    u, c  = np.unique(x, return_counts=True)
    tied  = np.sum(c * (c - 1) * (2 * c + 5))
    var_S = (n * (n - 1) * (2 * n + 5) - tied) / 18.0
    if S > 0:
        Z = (S - 1) / math.sqrt(var_S)
    elif S < 0:
        Z = (S + 1) / math.sqrt(var_S)
    else:
        Z = 0.0
    p   = 2 * (1 - stats.norm.cdf(abs(Z)))
    tau = S / (0.5 * n * (n - 1))
    if p <= alpha:
        trend = "Increasing" if Z > 0 else "Decreasing"
    else:
        trend = "No trend"
    return dict(n=n, S=S, var_S=var_S, Z=Z, p=p, tau=tau, trend=trend,
                significant=(p <= alpha))


def sens_slope_ci(x: np.ndarray, alpha: float = 0.05):
    """Sen's slope + rank-based 95 % CI (Gilbert 1987)."""
    n  = len(x)
    t  = np.arange(1, n + 1, dtype=float)
    Q  = np.sort([(x[j] - x[i]) / (t[j] - t[i])
                  for i in range(n - 1) for j in range(i + 1, n)])
    N  = len(Q)
    b  = float(np.median(Q))
    u, c   = np.unique(x, return_counts=True)
    var_S  = (n * (n - 1) * (2 * n + 5) - np.sum(c*(c-1)*(2*c+5))) / 18.0
    Ca     = stats.norm.ppf(1 - alpha / 2) * math.sqrt(var_S)
    M1     = max(0, min(int(round((N - Ca) / 2)),     N - 1))
    M2     = max(0, min(int(round((N + Ca) / 2)),     N - 1))
    return b, Q[M1], Q[M2]


def p_stars(p: float) -> str:
    if p <= 0.001: return "***"
    if p <= 0.01:  return "**"
    if p <= 0.05:  return "*"
    return "ns"

# ═══════════════════════════════════════════════════════════════════════════
# 3.  DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════

def load_annual(csv_path: str):
    df = pd.read_csv(csv_path)
    for mv in [-99, -999, -9999]:
        df.replace(mv, np.nan, inplace=True)
    df[df.select_dtypes(include=[np.number]).columns] = \
        df.select_dtypes(include=[np.number]).where(
            df.select_dtypes(include=[np.number]) >= 0)
    stns = [c for c in df.columns if c not in ("YEAR", "MONTH", "DAY")]
    annual = (df.groupby("YEAR")[stns]
                .apply(lambda g: g.sum(min_count=int(0.8 * len(g)))))
    annual.index.name = "YEAR"
    return annual, stns

# ═══════════════════════════════════════════════════════════════════════════
# 4.  SINGLE-STATION PLOT
# ═══════════════════════════════════════════════════════════════════════════

def plot_station(stn: str, years: np.ndarray, rain: np.ndarray,
                 mk: dict, slope: float, ci_lo: float, ci_hi: float,
                 out_path: str, figure_num: int, total_figs: int,
                 period_label: str):
    """
    One figure per station:
      – bar chart of annual rainfall
      – Sen's slope trend line
      – 95 % uncertainty band (shaded)
      – long-term mean line
      – full statistical annotation box
    """
    # ── Derived quantities ─────────────────────────────────────────────
    n      = len(rain)
    t_idx  = np.arange(1, n + 1, dtype=float)   # 1-based time index
    mean_r = np.mean(rain)
    std_r  = np.std(rain, ddof=1)
    cv     = std_r / mean_r * 100

    # Trend-line over continuous time axis
    t_cont = np.linspace(1, n, 300)
    # intercept via median of (y_i - slope * t_i)
    intercept = np.median(rain - slope * t_idx)
    trend_y   = slope * t_cont + intercept
    ci_lo_y   = ci_lo * t_cont + intercept
    ci_hi_y   = ci_hi * t_cont + intercept

    # ── Colour selection ───────────────────────────────────────────────
    if mk["trend"] == "Increasing" and mk["significant"]:
        bar_col   = COL["bar_inc"]
        line_col  = COL["trend_inc"]
        band_col  = COL["band_inc"]
    elif mk["trend"] == "Decreasing" and mk["significant"]:
        bar_col   = COL["bar_dec"]
        line_col  = COL["trend_dec"]
        band_col  = COL["band_dec"]
    else:
        bar_col   = COL["bar_no"]
        line_col  = COL["trend_ns"]
        band_col  = COL["band_ns"]

    # ── Figure layout ──────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(8.5, 4.5))

    # ── 1. Bars ────────────────────────────────────────────────────────
    bars = ax.bar(years, rain,
                  width=0.75, color=bar_col, edgecolor=COL["edge"],
                  linewidth=0.4, alpha=0.82, zorder=2, label="Annual Rainfall")

    # colour bars above / below mean differently (subtle)
    for bar, val in zip(bars, rain):
        bar.set_facecolor(bar_col if val >= mean_r
                          else matplotlib.colors.to_rgba(bar_col, 0.55))

    # ── 2. Uncertainty band ────────────────────────────────────────────
    x_cont = np.linspace(years[0], years[-1], 300)
    ax.fill_between(x_cont, ci_lo_y, ci_hi_y,
                    color=band_col, alpha=0.55,
                    label="95% CI (Sen's slope)", zorder=3)

    # ── 3. Trend line ──────────────────────────────────────────────────
    ls_trend = "-" if mk["significant"] else "--"
    ax.plot(x_cont, trend_y,
            color=line_col, linewidth=2.0, linestyle=ls_trend,
            zorder=4, label=f"Sen's slope ({slope:+.2f} mm yr⁻¹)")

    # ── 4. Long-term mean ──────────────────────────────────────────────
    ax.axhline(mean_r, color=COL["mean"], linewidth=1.1,
               linestyle=(0, (5, 3)), zorder=3,
               label=f"Long-term mean ({mean_r:.1f} mm)")

    # ── 5. Statistical annotation box ─────────────────────────────────
    stars = p_stars(mk["p"])
    sig_txt = f"{mk['p']:.4f}{' ' + stars if stars != 'ns' else ' ns'}"
    z_sign  = "+" if mk["Z"] >= 0 else ""

    annot_lines = [
        f"Mann–Kendall trend test",
        f"Period : {period_label}   N = {n} years",
        r"$\tau$" + f" = {mk['tau']:+.4f}     S = {mk['S']:,}",
        f"Z  = {z_sign}{mk['Z']:.3f}     p = {sig_txt}",
        r"$\hat{\beta}$" + f" = {slope:+.2f} mm yr⁻¹"
          f"   [95% CI: {ci_lo:+.2f}, {ci_hi:+.2f}]",
        f"Mean = {mean_r:.1f} mm   CV = {cv:.1f}%",
        f"Trend : {mk['trend'].upper()}",
    ]
    annot_txt = "\n".join(annot_lines)

    ax.text(0.013, 0.975, annot_txt,
            transform=ax.transAxes,
            va="top", ha="left",
            fontsize=8, family="monospace",
            linespacing=1.55,
            bbox=dict(boxstyle="round,pad=0.45",
                      facecolor=COL["annot_bg"],
                      edgecolor="#AAAAAA",
                      linewidth=0.7, alpha=0.93),
            zorder=6)

    # ── 6. Significance stamp ──────────────────────────────────────────
    if mk["significant"]:
        stamp_col = COL["trend_inc"] if mk["trend"] == "Increasing" \
                    else COL["trend_dec"]
        arrow = "↑" if mk["trend"] == "Increasing" else "↓"
        ax.text(0.987, 0.975,
                f"{arrow} Significant\n{stars} (α = 0.05)",
                transform=ax.transAxes,
                va="top", ha="right",
                fontsize=8.5, fontweight="bold", color=stamp_col,
                bbox=dict(boxstyle="round,pad=0.35",
                          facecolor="white",
                          edgecolor=stamp_col, linewidth=1.0,
                          alpha=0.92),
                zorder=6)
    else:
        ax.text(0.987, 0.975,
                "No Significant Trend\nns (α = 0.05)",
                transform=ax.transAxes,
                va="top", ha="right",
                fontsize=8, color="#555555",
                bbox=dict(boxstyle="round,pad=0.35",
                          facecolor="white",
                          edgecolor="#999999", linewidth=0.7,
                          alpha=0.90),
                zorder=6)

    # ── 7. Axes formatting ─────────────────────────────────────────────
    ax.set_xlim(years[0] - 0.8, years[-1] + 0.8)
    ymax = max(rain) * 1.18
    ymin = max(0, min(rain) * 0.88 - 50)
    ax.set_ylim(ymin, ymax)

    ax.xaxis.set_major_locator(ticker.MultipleLocator(5))
    ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
    ax.yaxis.set_major_locator(ticker.MultipleLocator(200))
    ax.yaxis.set_minor_locator(ticker.MultipleLocator(100))

    ax.tick_params(axis="x", which="major", length=4, width=0.7,
                   rotation=0, top=False)
    ax.tick_params(axis="x", which="minor", length=2, width=0.5)
    ax.tick_params(axis="y", which="both",  length=3, width=0.7)

    ax.set_xlabel("Year", labelpad=5)
    ax.set_ylabel("Annual Rainfall (mm)", labelpad=5)

    # ── 8. Title ───────────────────────────────────────────────────────
    fig.suptitle(
        f"Annual Rainfall Trend — Station {stn}   ({period_label})",
        fontsize=11, fontweight="bold", y=1.01)
    ax.set_title(
        "Prachuap Khiri Khan Province, Thailand",
        fontsize=9, color="#444444", pad=3)

    # ── 9. Legend ──────────────────────────────────────────────────────
    handles = [
        mpatches.Patch(facecolor=bar_col, edgecolor=COL["edge"],
                       linewidth=0.4, alpha=0.82, label="Annual Rainfall"),
        Line2D([0], [0], color=line_col, linewidth=2.0, linestyle=ls_trend,
               label=f"Sen's Slope ({slope:+.2f} mm yr⁻¹)"),
        mpatches.Patch(facecolor=band_col, alpha=0.55, edgecolor="none",
                       label="95% Confidence Band"),
        Line2D([0], [0], color=COL["mean"], linewidth=1.1,
               linestyle=(0, (5, 3)),
               label=f"Long-term Mean ({mean_r:.1f} mm)"),
    ]
    leg = ax.legend(handles=handles, loc="lower right",
                    frameon=True, framealpha=0.92,
                    edgecolor="#AAAAAA", fontsize=8,
                    ncol=2, columnspacing=1.0,
                    handlelength=2.2, handletextpad=0.5)
    leg.get_frame().set_linewidth(0.6)

    # ── 10. Figure counter watermark ───────────────────────────────────
    fig.text(0.99, 0.01,
             f"Fig. {figure_num} of {total_figs}",
             ha="right", va="bottom",
             fontsize=7, color="#AAAAAA")

    # ── 11. Reference footnote ─────────────────────────────────────────
    fig.text(0.01, 0.01,
             "Mann–Kendall (1975); Sen (1968); Gilbert (1987). "
             "Two-tailed test, α = 0.05. 95% CI: rank-based method.",
             ha="left", va="bottom",
             fontsize=6.5, color="#777777", style="italic")

    plt.tight_layout(rect=[0, 0.03, 1, 1])
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"    ✓  {os.path.basename(out_path)}")


# ═══════════════════════════════════════════════════════════════════════════
# 5.  COMBINED MULTI-PANEL OVERVIEW (all stations, 3×4 grid)
# ═══════════════════════════════════════════════════════════════════════════

def plot_overview(all_data: list, period_label: str, out_path: str):
    """3×4 subplot overview – all stations on one page (journal figure)."""
    n_stn = len(all_data)
    ncols = 3
    nrows = math.ceil(n_stn / ncols)

    fig, axes = plt.subplots(nrows, ncols,
                             figsize=(7.5 * ncols / 3 * ncols,
                                      4.2 * nrows / 4 * nrows),
                             sharex=False, sharey=False)
    axes_flat = axes.flatten() if hasattr(axes, "flatten") else [axes]

    for idx, d in enumerate(all_data):
        ax   = axes_flat[idx]
        stn  = d["stn"]
        yrs  = d["years"]
        rain = d["rain"]
        mk   = d["mk"]
        slope, ci_lo, ci_hi = d["slope"], d["ci_lo"], d["ci_hi"]

        n       = len(rain)
        t_idx   = np.arange(1, n + 1, dtype=float)
        mean_r  = np.mean(rain)
        cv      = np.std(rain, ddof=1) / mean_r * 100
        intercept = np.median(rain - slope * t_idx)

        x_cont  = np.linspace(yrs[0], yrs[-1], 200)
        t_cont  = np.linspace(1, n, 200)
        trend_y = slope * t_cont + intercept
        ci_lo_y = ci_lo * t_cont + intercept
        ci_hi_y = ci_hi * t_cont + intercept

        if mk["trend"] == "Increasing" and mk["significant"]:
            bar_col, line_col, band_col = \
                COL["bar_inc"], COL["trend_inc"], COL["band_inc"]
        elif mk["trend"] == "Decreasing" and mk["significant"]:
            bar_col, line_col, band_col = \
                COL["bar_dec"], COL["trend_dec"], COL["band_dec"]
        else:
            bar_col, line_col, band_col = \
                COL["bar_no"], COL["trend_ns"], COL["band_ns"]

        ax.bar(yrs, rain, width=0.75, color=bar_col,
               edgecolor=COL["edge"], linewidth=0.25, alpha=0.80, zorder=2)
        ax.fill_between(x_cont, ci_lo_y, ci_hi_y,
                        color=band_col, alpha=0.50, zorder=3)
        ls = "-" if mk["significant"] else "--"
        ax.plot(x_cont, trend_y, color=line_col, lw=1.6,
                linestyle=ls, zorder=4)
        ax.axhline(mean_r, color=COL["mean"], lw=0.9,
                   linestyle=(0, (5, 3)), zorder=3)

        # mini annotation
        stars = p_stars(mk["p"])
        sig   = stars if stars != "ns" else "ns"
        arrow = ("↑" if mk["trend"] == "Increasing"
                 else ("↓" if mk["trend"] == "Decreasing" else "–"))
        ax.set_title(f"Station {stn}", fontsize=9, fontweight="bold", pad=2)
        ax.text(0.03, 0.97,
                f"Z={mk['Z']:+.2f}  p={mk['p']:.3f} {sig}\n"
                f"β={slope:+.2f} mm yr⁻¹  {arrow}",
                transform=ax.transAxes, va="top", ha="left",
                fontsize=7, family="monospace",
                bbox=dict(boxstyle="round,pad=0.3",
                          facecolor=COL["annot_bg"],
                          edgecolor="#BBBBBB", lw=0.5, alpha=0.92),
                zorder=6)
        ax.tick_params(labelsize=7)
        ax.xaxis.set_major_locator(ticker.MultipleLocator(10))
        ax.yaxis.set_major_locator(ticker.MultipleLocator(400))
        ax.set_ylabel("RF (mm)", fontsize=7, labelpad=2)
        ax.grid(True, linestyle="--", linewidth=0.3, alpha=0.5)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    # hide unused subplots
    for ax in axes_flat[n_stn:]:
        ax.set_visible(False)

    fig.suptitle(
        "Annual Rainfall Trends — Prachuap Khiri Khan Province, Thailand\n"
        f"Mann–Kendall Test + Sen's Slope Estimator   ({period_label})",
        fontsize=11, fontweight="bold", y=1.01)

    # shared legend
    leg_handles = [
        mpatches.Patch(facecolor=COL["bar_inc"], edgecolor=COL["edge"],
                       alpha=0.82, label="Annual Rainfall (Increasing*)"),
        mpatches.Patch(facecolor=COL["bar_dec"], edgecolor=COL["edge"],
                       alpha=0.82, label="Annual Rainfall (Decreasing*)"),
        mpatches.Patch(facecolor=COL["bar_no"],  edgecolor=COL["edge"],
                       alpha=0.82, label="Annual Rainfall (No trend)"),
        Line2D([0],[0], color=COL["trend_inc"], lw=1.8,
               label="Sen's Slope (sig, +)"),
        Line2D([0],[0], color=COL["trend_dec"], lw=1.8,
               label="Sen's Slope (sig, -)"),
        Line2D([0],[0], color=COL["trend_ns"],  lw=1.4, ls="--",
               label="Sen's Slope (ns)"),
        mpatches.Patch(facecolor=COL["band_ns"], alpha=0.50, edgecolor="none",
                       label="95% Confidence Band"),
        Line2D([0],[0], color=COL["mean"], lw=1.0, ls=(0,(5,3)),
               label="Long-term Mean"),
    ]
    fig.legend(handles=leg_handles, loc="lower center",
               ncol=4, fontsize=7.5, frameon=True,
               edgecolor="#AAAAAA", framealpha=0.95,
               bbox_to_anchor=(0.5, -0.02))

    fig.text(0.99, -0.03,
             "Mann–Kendall (1975); Sen (1968); Gilbert (1987). "
             "Two-tailed, α = 0.05. * significant.",
             ha="right", fontsize=6.5, color="#777777", style="italic")

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    print(f"    ✓  {os.path.basename(out_path)}  [overview]")


# ═══════════════════════════════════════════════════════════════════════════
# 6.  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def find_csv() -> str:
    """ค้นหา CSV อัตโนมัติ 4 ขั้น"""
    # ขั้น 1: CLI argument
    if len(sys.argv) > 1:
        p = sys.argv[1].strip('"').strip("'")
        if os.path.isfile(p):
            return p
    # ขั้น 2: current working directory
    for f in sorted(Path(os.getcwd()).glob("*.csv")):
        return str(f)
    # ขั้น 3: โฟลเดอร์ script
    script_dir = Path(os.path.abspath(__file__)).parent
    for f in sorted(script_dir.glob("*.csv")):
        return str(f)
    # ขั้น 4: default path
    default = r"C:\Prachuap Khiri Khan\Observed_Rain_daily_198101_201412_Prachuap_Khiri_Khan.csv"
    if os.path.isfile(default):
        return default
    return None


def main():
    print("=" * 68)
    print("  Annual Rainfall Trend Plots – Mann–Kendall + Sen's Slope")
    print("  มาตรฐานวารสาร Q2-Q3 / TCI1")
    print("=" * 68)

    # ── ค้นหา CSV ──────────────────────────────────────────────────────
    csv_path = find_csv()
    if csv_path is None:
        sys.exit(
            "\n  ✗  ไม่พบไฟล์ CSV\n"
            "  วิธีแก้ไข:\n"
            "    [1] วาง CSV ในโฟลเดอร์เดียวกับ script แล้วรัน\n"
            r'    [2] > trend_plot_stations.py "C:\path\to\file.csv"'
        )

    base_name  = Path(csv_path).stem
    output_dir = Path(csv_path).parent
    # โฟลเดอร์เก็บรูปภาพ : Output_Figures_<ชื่อไฟล์>
    fig_dir    = output_dir / f"Output_Figures_{base_name}"
    fig_dir.mkdir(exist_ok=True)

    print(f"  Input  : {csv_path}")
    print(f"  Output : {fig_dir}")
    print("-" * 68)

    # ── โหลดและรวมข้อมูลรายปี ─────────────────────────────────────────
    annual, stns = load_annual(csv_path)
    years_all    = annual.index.values.astype(int)
    period_label = f"{years_all[0]}–{years_all[-1]}"
    n_stns       = len(stns)
    print(f"  สถานี {n_stns} สถานี  |  ช่วง {period_label}")
    print("-" * 68)
    print("  กำลังสร้างรูปภาพ ...")
    print()

    # ── วิเคราะห์และพล็อตรายสถานี ─────────────────────────────────────
    all_data = []
    for fig_num, stn in enumerate(stns, 1):
        series = annual[stn].dropna()
        if len(series) < 4:
            print(f"  ⚠  Station {stn}: ข้อมูลไม่เพียงพอ ({len(series)} ปี) – ข้ามไป")
            continue

        yrs  = series.index.values.astype(int)
        rain = series.values.astype(float)

        mk                = mann_kendall(rain)
        slope, ci_lo, ci_hi = sens_slope_ci(rain)

        all_data.append(dict(stn=stn, years=yrs, rain=rain,
                             mk=mk, slope=slope,
                             ci_lo=ci_lo, ci_hi=ci_hi))

        out_png = fig_dir / f"Output_{base_name}_Stn{stn}.png"
        plot_station(stn, yrs, rain, mk, slope, ci_lo, ci_hi,
                     str(out_png), fig_num, n_stns, period_label)

    # ── Overview (all-station panel) ────────────────────────────────────
    print()
    print("  กำลังสร้าง overview figure (all stations) ...")
    ov_png = fig_dir / f"Output_{base_name}_ALL_Overview.png"
    plot_overview(all_data, period_label, str(ov_png))

    print()
    print("=" * 68)
    print(f"  เสร็จสิ้น – รูปภาพทั้งหมด {len(all_data) + 1} ไฟล์")
    print(f"  บันทึกใน: {fig_dir}")
    print("=" * 68)


if __name__ == "__main__":
    main()
