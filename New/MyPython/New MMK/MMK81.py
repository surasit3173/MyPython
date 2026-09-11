# -*- coding: utf-8 -*-
"""
===============================================================================
Q2-Q3 Standard Rainfall Trend Analysis (Full Version)
- แสดงผลทุกสถานี ทุกสเกลเวลา (Annual, Wet, Dry)
- Table 2, Table 3, Table 5 ตามตัวอย่าง
- กราฟ MK vs MMK แยกตามสถานีและฤดู
- รวมผลวิเคราะห์จาก v3
===============================================================================
"""

import os, glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import norm, theilslopes
import pymannkendall as mk
from datetime import datetime

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.labelsize": 12
})

# ========================= CORE =========================
def sen_slope(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    slope, intercept, lo, hi = theilslopes(y, x, alpha=0.05)
    return slope, lo, hi

def standard_mk(y):
    n = len(y)
    S = sum(np.sum(np.sign(y[i+1:] - y[i])) for i in range(n-1))
    var_s = n*(n-1)*(2*n+5)/18.0
    Z = (S-1)/np.sqrt(var_s) if S > 0 else (S+1)/np.sqrt(var_s) if S < 0 else 0
    p = 2*(1 - norm.cdf(abs(Z)))
    return S, var_s, Z, p

def modified_mk(y):
    n = len(y)
    r1 = np.corrcoef(y[:-1], y[1:])[0,1]
    ne = n * (1 - r1) / (1 + r1) if (1 + r1) != 0 else n

    S, var_s, _, _ = standard_mk(y)
    var_mod = var_s * (n / ne)

    Z = (S-1)/np.sqrt(var_mod) if S > 0 else (S+1)/np.sqrt(var_mod) if S < 0 else 0
    p = 2*(1 - norm.cdf(abs(Z)))
    return Z, p, r1, var_mod, ne

# ========================= LOAD =========================
def load(f):
    df = pd.read_csv(f)
    st = [c for c in df.columns if str(c).isdigit()]
    df['date'] = pd.to_datetime(df[['YEAR','MONTH','DAY']])
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    return df, st

def split_season(df, st):
    ann = df.groupby('year')[st].sum()
    wet = df[df['month'].isin([5,6,7,8,9,10])].groupby('year')[st].sum()
    dry = df[df['month'].isin([11,12,1,2,3,4])].groupby('year')[st].sum()
    return {"Annual": ann, "Wet": wet, "Dry": dry}

# ========================= PLOT =========================
def plot_mk(x, y, st, season, out, title):
    slope, lo, hi = sen_slope(x, y)
    Z, p = standard_mk(y)[2:4]

    yfit = slope * x + (np.median(y) - slope * np.median(x))

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x, y, alpha=0.7, edgecolor='black')
    ax.plot(x, yfit, color='darkred', lw=2.8)
    ax.fill_between(x, yfit + lo, yfit + hi, alpha=0.2, color='red')

    text = (f"Standard Mann–Kendall\n"
            f"Z = {Z:.3f}\n"
            f"p = {p:.4f} {'*' if p < 0.05 else ''}\n\n"
            f"Sen’s slope = {slope:.2f} mm yr⁻¹\n"
            f"95% CI = [{lo:.2f}, {hi:.2f}]")

    ax.text(0.02, 0.98, text, transform=ax.transAxes, va='top',
            bbox=dict(facecolor='white', alpha=0.9))

    ax.set_title(title, fontweight='bold')
    ax.set_xlabel("Year")
    ax.set_ylabel("Rainfall (mm)")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(out, f"{st}_{season}_MK.png"), dpi=500)
    plt.close()

def plot_mmk(x, y, st, season, out, title):
    slope, lo, hi = sen_slope(x, y)
    Z, p, r1, _, _ = modified_mk(y)

    yfit = slope * x + (np.median(y) - slope * np.median(x))

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x, y, alpha=0.7, edgecolor='black')
    ax.plot(x, yfit, color='navy', lw=2.8)
    ax.fill_between(x, yfit + lo, yfit + hi, alpha=0.2, color='blue')

    text = (f"Modified Mann–Kendall (MMK)\n"
            f"Z = {Z:.3f}\n"
            f"p = {p:.4f} {'*' if p < 0.05 else ''}\n"
            f"ρ₁ = {r1:.2f}\n\n"
            f"Sen’s slope = {slope:.2f} mm yr⁻¹\n"
            f"95% CI = [{lo:.2f}, {hi:.2f}]")

    ax.text(0.02, 0.98, text, transform=ax.transAxes, va='top',
            bbox=dict(facecolor='white', alpha=0.9))

    ax.set_title(title, fontweight='bold')
    ax.set_xlabel("Year")
    ax.set_ylabel("Rainfall (mm)")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(out, f"{st}_{season}_MMK.png"), dpi=500)
    plt.close()

# ========================= MAIN =========================
def main():
    files = glob.glob("*.csv")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = f"Q2_MK_MMK_Results_{timestamp}"
    os.makedirs(out, exist_ok=True)

    table2 = []
    table3 = []
    table5 = []

    for f in files:
        print(f"Processing: {f}")
        df, stations = load(f)

        for st in stations:
            seasons = split_season(df, st)

            for s_name, series in seasons.items():
                series = series.dropna()
                if len(series) < 10:
                    continue

                years = series.index.values
                values = series.values

                # Sen's Slope + CI
                slope, lo, hi = sen_slope(years, values)

                # Standard MK
                S, var_s, Z, p_mk = standard_mk(values)

                # Modified MK
                Z_mmk, p_mmk, r1, var_mod, neff = modified_mk(values)

                trend_mk = "Increasing" if Z > 0 else "Decreasing" if Z < 0 else "No trend"
                trend_mmk = "Increasing" if Z_mmk > 0 else "Decreasing" if Z_mmk < 0 else "No trend"

                # Table 2: Standard MK
                table2.append([st, s_name, len(years), S, round(var_s, 2), round(Z, 4),
                               round(Z / (len(years)*(len(years)-1)/2), 4),
                               round(p_mk, 6), trend_mk])

                # Table 3: Modified MK
                table3.append([st, s_name, round(var_mod, 2), round(neff, 2), round(r1, 4),
                               round(Z_mmk, 4),
                               round(Z_mmk / (len(years)*(len(years)-1)/2), 4),
                               round(p_mmk, 6), trend_mmk])

                # Table 5: Summary
                table5.append([st, s_name, round(slope, 4), round(p_mmk, 6),
                               "Yes" if p_mmk < 0.05 else "No", trend_mmk])

                # กราฟ MK vs MMK
                name = f"{st}_{s_name}"
                plot_mk(years, values, st, s_name, out,
                        f"Station {st} - {s_name} (Standard MK)")
                plot_mmk(years, values, st, s_name, out,
                        f"Station {st} - {s_name} (Modified MK)")

    # ====================== EXPORT ======================
    df2 = pd.DataFrame(table2, columns=["Station", "Scale", "N", "S", "Var(S)", "Z",
                                        "τ (Kendall)", "p-value", "Trend"])
    df3 = pd.DataFrame(table3, columns=["Station", "Scale", "Var*(S)", "N_eff", "p1",
                                        "Z", "τ (Kendall)", "p-value", "Trend"])
    df5 = pd.DataFrame(table5, columns=["Station", "Scale", "Sen's Slope (mm/yr)",
                                        "p-value", "Significant", "Trend"])

    with pd.ExcelWriter(os.path.join(out, "Trend_Tables.xlsx")) as writer:
        df2.to_excel(writer, sheet_name="Table2_MK", index=False)
        df3.to_excel(writer, sheet_name="Table3_MMK", index=False)
        df5.to_excel(writer, sheet_name="Table5_Summary", index=False)

    print(f"\n✅ DONE → ผลลัพธ์ถูกสร้างในโฟลเดอร์: {out}")
    print("   • Table2_MK     : Standard Mann–Kendall Test Results")
    print("   • Table3_MMK    : Modified Mann–Kendall Test Results")
    print("   • Table5_Summary: Sen’s Slope + Significance")
    print("   • กราฟ MK และ MMK แยกตามสถานีและฤดู (ทุกสถานี)")

if __name__ == "__main__":
    main()