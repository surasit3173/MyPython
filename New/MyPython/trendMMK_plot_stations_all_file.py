"""
===============================================================================
  Multi-File Rainfall Trend Analysis – Modified Mann–Kendall (Hamed & Rao 1998)
  เป้าหมาย: ประมวลผลทุกไฟล์ CSV ในโฟลเดอร์, สร้างรูปภาพ และตารางสรุปผล Excel
  มาตรฐานวารสาร: Q2-Q3 / TCI1
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

# ตรวจสอบและนำเข้า pymannkendall
try:
    import pymannkendall as pmk
except ImportError:
    sys.exit("\n ✗ ไม่พบไลบรารี pymannkendall\n โปรดติดตั้งด้วยคำสั่ง: python -m pip install pymannkendall pandas openpyxl")

warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════════════════════════════════════
# [1] GRAPHIC STYLE & COLOURS (คงเดิมตามมาตรฐานวารสาร)
# ═══════════════════════════════════════════════════════════════════════════
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 10, "axes.grid": True, "grid.linestyle": "--", "figure.dpi": 300
})

COL = {
    "bar_inc": "#4393C3", "bar_dec": "#D6604D", "bar_no": "#74ADD1",
    "edge": "#1A1A2E", "trend_inc": "#B22222", "trend_dec": "#1565C0",
    "trend_ns": "#555555", "band_inc": "#FFCCCC", "band_dec": "#CCE5FF",
    "band_ns": "#E0E0E0", "mean": "#2E7D32", "annot_bg": "#FAFAFA"
}

# ═══════════════════════════════════════════════════════════════════════════
# [2] STATISTICAL FUNCTIONS (Modified Mann-Kendall)
# ═══════════════════════════════════════════════════════════════════════════

def modified_mann_kendall(x: np.ndarray, alpha: float = 0.05) -> dict:
    """การทดสอบ Modified Mann-Kendall (Hamed & Rao 1998)"""
    res = pmk.hamed_rao_modification_test(x, alpha=alpha)
    trend_str = "Increasing" if res.trend == 'increasing' else ("Decreasing" if res.trend == 'decreasing' else "No trend")
    return dict(n=len(x), S=res.s, var_S=res.var_s, Z=res.z, p=res.p, tau=res.Tau, trend=trend_str, significant=res.h)

def sens_slope_ci(x: np.ndarray, alpha: float = 0.05):
    """Sen's slope + 95% CI (Gilbert 1987)"""
    n = len(x)
    t = np.arange(1, n + 1)
    Q = np.sort([(x[j] - x[i]) / (t[j] - t[i]) for i in range(n - 1) for j in range(i + 1, n)])
    b = float(np.median(Q))
    var_S = (n * (n - 1) * (2 * n + 5)) / 18.0
    Ca = stats.norm.ppf(1 - alpha / 2) * math.sqrt(var_S)
    idx_l = max(0, int(round((len(Q) - Ca) / 2)))
    idx_u = min(len(Q) - 1, int(round((len(Q) + Ca) / 2)))
    return b, Q[idx_l], Q[idx_u]

def p_stars(p: float) -> str:
    if p <= 0.001: return "***"
    if p <= 0.01:  return "**"
    if p <= 0.05:  return "*"
    return "ns"

# ═══════════════════════════════════════════════════════════════════════════
# [3] PLOTTING FUNCTION (แก้ไขให้ระบุวิธี Hamed & Rao)
# ═══════════════════════════════════════════════════════════════════════════

def plot_station(stn, years, rain, mk, slope, ci_lo, ci_hi, out_path, period_label):
    n = len(rain)
    t_idx = np.arange(1, n + 1)
    mean_r = np.mean(rain)
    
    # Trend line calculations
    t_cont = np.linspace(1, n, 200)
    intercept = np.median(rain - slope * t_idx)
    trend_y = slope * t_cont + intercept
    ci_lo_y = ci_lo * t_cont + intercept
    ci_hi_y = ci_hi * t_cont + intercept

    # Plot setup
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bar_col = COL["bar_inc"] if mk["trend"] == "Increasing" and mk["significant"] else (COL["bar_dec"] if mk["trend"] == "Decreasing" and mk["significant"] else COL["bar_no"])
    line_col = COL["trend_inc"] if mk["significant"] and mk["trend"]=="Increasing" else (COL["trend_dec"] if mk["significant"] else COL["trend_ns"])
    
    ax.bar(years, rain, color=bar_col, alpha=0.7, edgecolor=COL["edge"], label="Annual Rainfall")
    ax.fill_between(np.linspace(years[0], years[-1], 200), ci_lo_y, ci_hi_y, color="#E0E0E0", alpha=0.5, label="95% CI")
    ax.plot(np.linspace(years[0], years[-1], 200), trend_y, color=line_col, lw=2, label="Sen's Slope")
    ax.axhline(mean_r, color=COL["mean"], ls="--", label="Mean")

    # Annotations
    stars = p_stars(mk["p"])
    info = (f"Modified MK (Hamed & Rao 1998)\n"
            f"Z: {mk['Z']:.3f} ({stars})\np: {mk['p']:.4f}\n"
            f"Slope: {slope:.2f} mm/yr\nTrend: {mk['trend']}")
    ax.text(0.02, 0.95, info, transform=ax.transAxes, va='top', bbox=dict(facecolor='white', alpha=0.8), fontsize=8, family='monospace')
    
    ax.set_title(f"Station: {stn} ({period_label})", fontweight='bold')
    ax.set_ylabel("Rainfall (mm)")
    plt.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)

# ═══════════════════════════════════════════════════════════════════════════
# [4] MAIN ENGINE (Batch Processing)
# ═══════════════════════════════════════════════════════════════════════════

def get_all_csv_files():
    """รวบรวมไฟล์ CSV ทั้งหมดจากโฟลเดอร์ปัจจุบัน"""
    return sorted(list(Path(os.getcwd()).glob("*.csv")))

def main():
    print("=" * 60)
    print("  Modified Mann-Kendall Batch Analysis (Hamed & Rao 1998)")
    print("=" * 60)

    csv_files = get_all_csv_files()
    if not csv_files:
        print("✗ ไม่พบไฟล์ CSV ในโฟลเดอร์ปัจจุบัน")
        return

    all_summary = [] # สำหรับรวมผลลัพธ์ทุกสถานีจากทุกไฟล์

    for csv_path in csv_files:
        print(f"\n▶ กำลังประมวลผลไฟล์: {csv_path.name}")
        
        # สร้างโฟลเดอร์ผลลัพธ์แยกตามไฟล์
        fig_dir = Path(os.getcwd()) / f"Results_{csv_path.stem}"
        fig_dir.mkdir(exist_ok=True)

        # โหลดข้อมูล
        df = pd.read_csv(csv_path)
        # กรองเฉพาะสถานี (คอลัมน์ที่ไม่ใช่ YEAR, MONTH, DAY)
        stns = [c for c in df.columns if c.upper() not in ("YEAR", "MONTH", "DAY")]
        
        # จัดการข้อมูลรายปี
        annual = df.groupby("YEAR")[stns].sum()
        years = annual.index.values
        period_label = f"{years[0]}-{years[-1]}"

        for stn in stns:
            data = annual[stn].dropna().values
            if len(data) < 10: continue # ข้อมูลน้อยไปไม่วิเคราะห์

            # คำนวณสถิติ
            mk = modified_mann_kendall(data)
            slope, ci_l, ci_u = sens_slope_ci(data)

            # บันทึกข้อมูลลง Summary List
            all_summary.append({
                "Source_File": csv_path.name,
                "Station": stn,
                "Period": period_label,
                "Z_Stat": round(mk["Z"], 3),
                "p_value": round(mk["p"], 4),
                "Tau": round(mk["tau"], 3),
                "Sen_Slope": round(slope, 3),
                "Significant": "Yes" if mk["significant"] else "No",
                "Trend": mk["trend"]
            })

            # วาดรูป
            out_img = fig_dir / f"Plot_{stn}.png"
            plot_station(stn, years, data, mk, slope, ci_l, ci_u, out_img, period_label)
            print(f"  ✓ บันทึกรูป: {stn}")

    # ── ส่งออกไฟล์ Excel สรุปผลรวม ──
    if all_summary:
        summary_df = pd.DataFrame(all_summary)
        excel_name = "Overall_Trend_Summary.xlsx"
        summary_df.to_excel(excel_name, index=False)
        print("\n" + "=" * 60)
        print(f"✔ เสร็จสมบูรณ์!")
        print(f"✔ ไฟล์สรุปผล Excel: {excel_name}")
        print(f"✔ รูปภาพถูกบันทึกแยกในโฟลเดอร์ Results_...")
        print("=" * 60)

if __name__ == "__main__":
    main()