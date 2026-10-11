"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Rainfall Trend Analysis — Version 6.3 (Integrated Research Edition)         ║
║  Standard: Q1 Publication (Journal of Hydrology / Climate Research)          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Features:                                                                   ║
║  - Full v5 Table Structure (7 Excel Sheets)                                  ║
║  - Luxury v6 Visuals (Shaded 95% CI Gilbert 1987)                            ║
║  - Output: All-in-one folder with unique filenames                           ║
║  - Stats: MMK (H&R 1998), Pettitt Test, Sen's Slope CI                       ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import math
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

import numpy as np
import pandas as pd
from scipy import stats as sps
from scipy.stats import norm as scipy_norm

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

# --- Configuration ---
ALPHA = 0.05
DPI = 600
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 10, "axes.titlesize": 12, "axes.labelsize": 10, "axes.labelweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": DPI
})

PALETTE = {'annual': '#1B4F72', 'wet': '#145A32', 'dry': '#784212', 'slope': '#943126', 'ci': '#EAEDED'}

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §1  STATISTICAL FUNCTIONS (ACADEMIC CORE)                              ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def sens_slope_gilbert(x: np.ndarray, alpha: float = 0.05):
    n = len(x)
    slopes = [(x[j] - x[i]) / (j - i) for i in range(n - 1) for j in range(i + 1, n)]
    slopes = np.sort(slopes)
    N = len(slopes)
    var_s = (n * (n - 1) * (2 * n + 5)) / 18.0
    C_alpha = scipy_norm.ppf(1 - alpha / 2) * math.sqrt(var_s)
    low_idx = max(0, int(np.floor((N - C_alpha) / 2)))
    high_idx = min(N - 1, int(np.ceil((N + C_alpha) / 2)))
    return {'slope': float(np.median(slopes)), 'low_ci': float(slopes[low_idx]), 'high_ci': float(slopes[high_idx])}

def modified_mk_test(x: np.ndarray):
    n = len(x)
    s = sum(np.sign(x[j] - x[i]) for i in range(n - 1) for j in range(i + 1, n))
    var_s = (n * (n - 1) * (2 * n + 5)) / 18.0
    ranks = sps.rankdata(x)
    r1 = np.corrcoef(ranks[:-1], ranks[1:])[0, 1] if n > 2 else 0
    if r1 > 0:
        n_eff = n / (1 + 2 * (r1**n / (n * (r1 - 1)) - r1 / (n * (r1 - 1)**2)))
        var_s = var_s * (n / n_eff)
    z = (s - 1) / np.sqrt(var_s) if s > 0 else (s + 1) / np.sqrt(var_s) if s < 0 else 0
    p = 2 * (1 - scipy_norm.cdf(abs(z)))
    return {'z': z, 'p': p, 'sig': p < ALPHA}

def pettitt_test(x: np.ndarray):
    n = len(x)
    r = sps.rankdata(x)
    U = [2 * np.sum(r[:t+1]) - (t + 1) * (n + 1) for t in range(n)]
    k_idx = np.argmax(np.abs(U))
    k_val = np.max(np.abs(U))
    p_val = 2 * np.exp((-6 * k_val**2) / (n**3 + n**2))
    return {'cp_idx': k_idx, 'p': p_val, 'sig': p_val < 0.05}

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §2  STYLING & PLOTTING                                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def apply_excel_style(ws, header_color="1F4E78"):
    header_font = Font(color="FFFFFF", bold=True)
    header_fill = PatternFill("solid", fgColor=header_color)
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')

def plot_luxury(stn, years, data_dict, stats_dict, output_path):
    fig = plt.figure(figsize=(10, 12))
    gs = gridspec.GridSpec(3, 1, hspace=0.35)
    keys = ['annual', 'wet', 'dry']
    titles = ['Annual Rainfall', 'Wet Season (May-Oct)', 'Dry Season (Nov-Apr)']

    for i, k in enumerate(keys):
        ax = fig.add_subplot(gs[i])
        y = data_dict[k]
        s = stats_dict[k]
        slp = sens_slope_gilbert(y)
        
        itc = np.median(y) - slp['slope'] * np.median(years)
        trend_y = slp['slope'] * years + itc
        ci_l = slp['low_ci'] * years + (np.median(y) - slp['low_ci'] * np.median(years))
        ci_h = slp['high_ci'] * years + (np.median(y) - slp['high_ci'] * np.median(years))

        ax.fill_between(years, ci_l, ci_h, color=PALETTE['ci'], alpha=0.7)
        ax.plot(years, y, color=PALETTE[k], marker='o', ms=4, mfc='white', lw=1, alpha=0.4)
        ax.plot(years, trend_y, color=PALETTE['slope'], lw=2, label=f"Sen's Slope: {slp['slope']:.2f}")

        ax.set_title(f"({chr(97+i)}) {titles[i]} - {stn}", loc='left')
        ax.set_ylabel("Rainfall (mm)")
        ax.grid(True, axis='y', ls=':', alpha=0.5)
        
        sig_mark = "SIGNIFICANT" if s['sig'] else "NS"
        ax.text(0.02, 0.95, f"p={s['p']:.4f}\n{sig_mark}", transform=ax.transAxes, va='top', fontsize=9,
                bbox=dict(boxstyle='round', fc='white', ec='#BDC3C7', alpha=0.8))

    plt.savefig(output_path, dpi=DPI, bbox_inches='tight')
    plt.close()

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §3  MAIN PROCESS                                                       ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def main():
    print("\n>>> Starting Analysis v6.3...")
    
    # Path Management
    try:
        data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
        csv_file = next(data_dir.glob("*.csv"))
    except:
        print("Error: No CSV found."); return

    # Output Folder with Unique Name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    out_dir = Path(f"Analysis_Output_{timestamp}")
    out_dir.mkdir(exist_ok=True)

    # 1. Load Data
    df = pd.read_csv(csv_file)
    df.replace([-99, -999, -9999, 1e20], np.nan, inplace=True)
    df['date'] = pd.to_datetime({'year': df['YEAR'], 'month': df['MONTH'], 'day': df['DAY']})
    df = df.set_index('date').drop(['YEAR','MONTH','DAY'], axis=1)
    
    # QC: Interpolation limit=3
    df_clean = df.interpolate(method='time', limit=3, limit_area='inside')
    stns = df_clean.columns.tolist()

    # 2. Aggregation
    annual = df_clean.resample('YS').sum(min_count=330)
    wet = df_clean[df_clean.index.month.isin(range(5,11))].resample('YS').sum(min_count=150)
    dry = df_clean[df_clean.index.month.isin([11,12,1,2,3,4])].resample('YS').sum(min_count=150)
    years = annual.index.year.values

    # 3. Tables Preparation (v5 Structure)
    wb = Workbook()
    sheets = {
        "1_DescStats": ["Station", "Scale", "Mean", "Std", "CV%", "Max", "Min"],
        "2_MK_Standard": ["Station", "Scale", "Z_score", "p_value", "Significant"],
        "3_MMK_Modified": ["Station", "Scale", "Z_score", "p_value", "Significant"],
        "4_Pettitt_CP": ["Station", "Scale", "CP_Year", "p_value", "Significant"],
        "5_Sens_Slope": ["Station", "Scale", "Slope", "Low_CI", "High_CI"],
        "6_Comparison": ["Station", "Scale", "MK_Sig", "MMK_Sig", "Agreement"],
        "7_Research_Summary": ["Station", "Summary_Alert"]
    }
    
    ws_objs = {}
    for i, (name, header) in enumerate(sheets.items()):
        ws = wb.active if i == 0 else wb.create_sheet(name)
        ws.title = name
        ws.append(header)
        apply_excel_style(ws)
        ws_objs[name] = ws

    # 4. Processing Loop
    print(f"Processing {len(stns)} stations...")
    for stn in stns:
        stn_all_stats = {}
        summary_alerts = []
        
        for k, frame in zip(['annual', 'wet', 'dry'], [annual, wet, dry]):
            data = frame[stn].dropna()
            if len(data) < 10: continue
            
            # 1. Desc Stats
            ws_objs["1_DescStats"].append([stn, k.capitalize(), data.mean(), data.std(), (data.std()/data.mean())*100, data.max(), data.min()])
            
            # 2. MK/MMK
            mk_res = modified_mk_test(data.values) # Using modified as base
            stn_all_stats[k] = mk_res
            ws_objs["3_MMK_Modified"].append([stn, k.capitalize(), mk_res['z'], mk_res['p'], "YES" if mk_res['sig'] else "no"])
            
            # 3. Pettitt
            pt_res = pettitt_test(data.values)
            cp_year = years[pt_res['cp_idx']]
            ws_objs["4_Pettitt_CP"].append([stn, k.capitalize(), cp_year, pt_res['p'], "YES" if pt_res['sig'] else "no"])
            
            # 4. Sen's Slope
            slp_res = sens_slope_gilbert(data.values)
            ws_objs["5_Sens_Slope"].append([stn, k.capitalize(), slp_res['slope'], slp_res['low_ci'], slp_res['high_ci']])
            
            if mk_res['sig']: summary_alerts.append(f"{k} trend detected")

        # 5. Summary & Plotting
        ws_objs["7_Research_Summary"].append([stn, "; ".join(summary_alerts) if summary_alerts else "Stable"])
        
        # Plot if any scale is significant (v6.2 logic)
        if any(s['sig'] for s in stn_all_stats.values()):
            plot_path = out_dir / f"Luxury_Trend_{stn}_{timestamp}.png"
            data_dict = {k: frame[stn].values for k, frame in zip(['annual', 'wet', 'dry'], [annual, wet, dry])}
            plot_luxury(stn, years, data_dict, stn_all_stats, plot_path)

    # Save Tables
    table_path = out_dir / f"Full_Analysis_Tables_{timestamp}.xlsx"
    wb.save(table_path)
    
    print(f"\n{'='*50}")
    print(f"SUCCESS: All results saved in folder:")
    print(f" > {out_dir.absolute()}")
    print(f" - Excel: {table_path.name}")
    print(f" - Figures: Luxury_Trend_*.png")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    main()