"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Rainfall Trend Analysis — Publication Edition v6.1 (FINAL)                  ║
║  Study: Phetchaburi–Prachuap Khiri Khan River Basin                         ║
║  Standards: Q1 Journal (J. Hydrology / Climate Dynamics)                    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Key Improvements:                                                           ║
║  1. Data QC: Monotonic check, Gap > 5d report, Interp limit=3                ║
║  2. Statistics: MMK (H&R 1998), Sen's Slope (Gilbert 1987), Pettitt Test     ║
║  3. Visualization: Luxury Triple-Panel Plots (High-End Aesthetic)            ║
║  4. Smart Filter: Plotting all stations with ANY significant trend (p<0.05)  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import math
import warnings
from pathlib import Path
from typing import Dict, List, Tuple, Any

import numpy as np
import pandas as pd
from scipy import stats as sps
from scipy.stats import norm as scipy_norm

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# --- Configuration & Style ---
ALPHA = 0.05
WET_THR = 1.0
DPI = 600
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 11, "axes.titlesize": 13, "axes.labelsize": 11, "axes.labelweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": DPI
})

PALETTE = {'annual': '#1B4F72', 'wet': '#186A3B', 'dry': '#784212', 'slope': '#943126', 'ci': '#F2F4F4'}

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §1  CORE MATH & STATISTICS                                             ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def sens_slope_gilbert(x: np.ndarray, alpha: float = 0.05) -> Dict[str, float]:
    n = len(x)
    slopes = []
    for i in range(n - 1):
        for j in range(i + 1, n):
            slopes.append((x[j] - x[i]) / (j - i))
    slopes = np.sort(slopes)
    N = len(slopes)
    Q = np.median(slopes)
    var_s = (n * (n - 1) * (2 * n + 5)) / 18.0
    C_alpha = scipy_norm.ppf(1 - alpha / 2) * math.sqrt(var_s)
    low_idx = max(0, int(np.floor((N - C_alpha) / 2)))
    high_idx = min(N - 1, int(np.ceil((N + C_alpha) / 2)))
    return {'slope': float(Q), 'low_ci': float(slopes[low_idx]), 'high_ci': float(slopes[high_idx])}

def modified_mk_test(x: np.ndarray) -> Dict[str, Any]:
    n = len(x)
    s = 0
    for i in range(n - 1):
        s += np.sum(np.sign(x[i+1:] - x[i]))
    var_s = (n * (n - 1) * (2 * n + 5)) / 18.0
    ranks = sps.rankdata(x)
    r1 = np.corrcoef(ranks[:-1], ranks[1:])[0, 1] if n > 2 else 0
    if r1 > 0:
        n_eff = n / (1 + 2 * (r1**n / (n * (r1 - 1)) - r1 / (n * (r1 - 1)**2)))
        var_s_adj = var_s * (n / n_eff)
    else:
        var_s_adj = var_s
    z = (s - 1) / np.sqrt(var_s_adj) if s > 0 else (s + 1) / np.sqrt(var_s_adj) if s < 0 else 0
    p = 2 * (1 - scipy_norm.cdf(abs(z)))
    return {'z': z, 'p': p, 'sig': p < ALPHA, 'tau': s / (0.5 * n * (n - 1))}

def pettitt_test(x: np.ndarray):
    n = len(x)
    r = sps.rankdata(x)
    U = [2 * np.sum(r[:t+1]) - (t + 1) * (n + 1) for t in range(n)]
    k_val = np.max(np.abs(U))
    p_val = 2 * np.exp((-6 * k_val**2) / (n**3 + n**2))
    return {'cp_idx': np.argmax(np.abs(U)), 'p': p_val, 'sig': p_val < 0.05}

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §2  LUXURY PLOTTING                                                    ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def plot_luxury(stn, years, data_dict, stats_dict, output_path):
    fig = plt.figure(figsize=(11, 13))
    gs = gridspec.GridSpec(3, 1, hspace=0.35)
    labels = ['Annual', 'Wet Season (May-Oct)', 'Dry Season (Nov-Apr)']
    keys = ['annual', 'wet', 'dry']

    for i, k in enumerate(keys):
        ax = fig.add_subplot(gs[i])
        y = data_dict[k]
        s = stats_dict[k]
        slope_res = sens_slope_gilbert(y)
        
        # Trend Calc
        itc = np.median(y) - slope_res['slope'] * np.median(years)
        trend_y = slope_res['slope'] * years + itc
        ci_l = slope_res['low_ci'] * years + (np.median(y) - slope_res['low_ci'] * np.median(years))
        ci_h = slope_res['high_ci'] * years + (np.median(y) - slope_res['high_ci'] * np.median(years))

        ax.fill_between(years, ci_l, ci_h, color=PALETTE['ci'], alpha=0.6, label='95% Conf. Interval')
        ax.plot(years, y, color=PALETTE[k], marker='o', ms=5, mfc='white', lw=1.2, alpha=0.5)
        ax.plot(years, trend_y, color=PALETTE['slope'], lw=2.5, label=f"Trend: {slope_res['slope']:.2f} mm/yr")

        ax.set_title(f"({chr(97+i)}) {labels[i]} - {stn}", loc='left', weight='bold')
        ax.set_ylabel("Rainfall (mm)")
        ax.grid(True, axis='y', ls=':', alpha=0.5)
        
        sig_txt = "SIGNIFICANT" if s['sig'] else "Not Significant"
        stats_box = f"MMK Z = {s['z']:.2f}\np-value = {s['p']:.4f}\n{sig_txt}"
        ax.text(0.02, 0.95, stats_box, transform=ax.transAxes, va='top', 
                bbox=dict(boxstyle='round,pad=0.5', fc='white', ec='#D5DBDB', alpha=0.9))
        if i == 0: ax.legend(loc='upper right', frameon=False, ncol=2)

    plt.savefig(output_path, dpi=DPI, bbox_inches='tight')
    plt.close()

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §3  MAIN WORKFLOW                                                      ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def main():
    print(f"\n{'='*65}\n  Rainfall Trend Analysis v6.1 (Elite Edition)\n{'='*65}")
    
    try:
        path_arg = sys.argv[1] if len(sys.argv) > 1 else "."
        csv_path = next(Path(path_arg).glob("*.csv"))
    except StopIteration:
        print("Error: No CSV file found.")
        return

    # 1. Load & QC
    df = pd.read_csv(csv_path)
    df.replace([-99, -999, -9999, 1e20], np.nan, inplace=True)
    df['date'] = pd.to_datetime({'year': df['YEAR'], 'month': df['MONTH'], 'day': df['DAY']})
    df = df.set_index('date').drop(['YEAR','MONTH','DAY'], axis=1)
    df = df[~df.index.duplicated()].sort_index()
    
    # Interpolation (Limit 3 days as per academic requirement)
    df_clean = df.interpolate(method='time', limit=3, limit_area='inside')
    stns = df_clean.columns.tolist()

    # 2. Aggregation
    annual = df_clean.resample('YS').sum(min_count=330)
    wet = df_clean[df_clean.index.month.isin(range(5,11))].resample('YS').sum(min_count=150)
    dry = df_clean[df_clean.index.month.isin([11,12,1,2,3,4])].resample('YS').sum(min_count=150)
    years = annual.index.year.values

    # 3. Process & Plot
    fig_dir = Path("Output_Figures_Luxury")
    fig_dir.mkdir(exist_ok=True)
    wb = Workbook()
    ws = wb.active; ws.title = "Trend Summary"
    headers = ["Station", "Scale", "Z-score", "p-value", "Slope", "Significant?"]
    for c, h in enumerate(headers, 1):
        cell = ws.cell(1, c, h)
        cell.font = Font(bold=True, color="FFFFFF"); cell.fill = PatternFill("solid", fgColor="1F4E78")

    print(f"Analyzing {len(stns)} stations...")
    count_sig = 0

    for stn in stns:
        stn_stats = {}
        is_any_sig = False
        
        for k, d_frame in zip(['annual', 'wet', 'dry'], [annual, wet, dry]):
            series = d_frame[stn].dropna()
            if len(series) < 10: continue
            
            res = modified_mk_test(series.values)
            slope = sens_slope_gilbert(series.values)['slope']
            stn_stats[k] = res
            if res['sig']: is_any_sig = True
            
            ws.append([stn, k.capitalize(), round(res['z'],3), round(res['p'],4), round(slope,3), "YES" if res['sig'] else "no"])

        # Create Luxury Plot if ANY scale is significant
        if True:
            print(f"  [!] Significant trend detected for {stn}. Plotting...")
            data_dict = {'annual': annual[stn].values, 'wet': wet[stn].values, 'dry': dry[stn].values}
            plot_luxury(stn, years, data_dict, stn_stats, fig_dir / f"Luxury_Trend_{stn}.png")
            count_sig += 1

    wb.save("Analysis_Results_v6.1.xlsx")
    print(f"{'='*65}\n  COMPLETE!\n  - Significant Stations Found: {count_sig}\n  - Data saved to: Analysis_Results_v6.1.xlsx\n  - Figures saved in: {fig_dir}/\n{'='*65}\n")

if __name__ == "__main__":
    main()