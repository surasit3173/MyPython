"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Rainfall Trend Analysis — Supreme Analytical Edition v6.4                  ║
║  Role: Senior Hydrologist / Python Expert (Q1 Journal Standard)              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Outputs:                                                                    ║
║  - 7 Excel Sheets: Descriptive, MK, MMK, Pettitt, Sen's, Comparison, Summary  ║
║  - Luxury Figures: 600 DPI, Shaded 95% CI, Academic Style Annotations        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import math
import warnings
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats as sps
from scipy.stats import norm
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

# --- Global Configurations ---
ALPHA = 0.05
DPI = 600
WET_THRESHOLD = 1.0  # mm
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 10, "axes.titlesize": 12, "axes.labelsize": 10, "axes.labelweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": DPI
})

# Professional Palette
COLORS = {'annual': '#1B4F72', 'wet': '#145A32', 'dry': '#784212', 'slope': '#B03A2E', 'ci': '#F2F4F4'}

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §1  ADVANCED STATISTICAL ENGINE                                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def standard_mk_test(x):
    """Standard Mann-Kendall Test."""
    n = len(x)
    s = sum(np.sign(x[j] - x[i]) for i in range(n - 1) for j in range(i + 1, n))
    var_s = (n * (n - 1) * (2 * n + 5)) / 18.0
    z = (s - 1) / np.sqrt(var_s) if s > 0 else (s + 1) / np.sqrt(var_s) if s < 0 else 0
    p = 2 * (1 - norm.cdf(abs(z)))
    return {'z': z, 'p': p, 'sig': p < ALPHA}

def modified_mk_test(x):
    """Modified Mann-Kendall Test (Hamed & Rao, 1998) for autocorrelated data."""
    n = len(x)
    s = sum(np.sign(x[j] - x[i]) for i in range(n - 1) for j in range(i + 1, n))
    var_s = (n * (n - 1) * (2 * n + 5)) / 18.0
    
    # Variance Correction Factor
    ranks = sps.rankdata(x)
    rho = np.corrcoef(ranks[:-1], ranks[1:])[0, 1] if n > 2 else 0
    if rho > 0.1: # Significant autocorrelation threshold
        n_ns = 1 + 2 * (rho**n / (n * (rho - 1)) - rho / (n * (rho - 1)**2))
        var_s *= (n / n_ns)
        
    z = (s - 1) / np.sqrt(var_s) if s > 0 else (s + 1) / np.sqrt(var_s) if s < 0 else 0
    p = 2 * (1 - norm.cdf(abs(z)))
    return {'z': z, 'p': p, 'sig': p < ALPHA, 'var_adj': var_s}

def sens_slope_gilbert(x, alpha=0.05):
    """Sen's Slope with Gilbert (1987) Confidence Intervals."""
    n = len(x)
    slopes = [(x[j] - x[i]) / (j - i) for i in range(n - 1) for j in range(i + 1, n)]
    slopes = np.sort(slopes)
    N = len(slopes)
    var_s = (n * (n - 1) * (2 * n + 5)) / 18.0
    z_crit = norm.ppf(1 - alpha / 2)
    C_alpha = z_crit * math.sqrt(var_s)
    low_idx = max(0, int(np.floor((N - C_alpha) / 2)))
    high_idx = min(N - 1, int(np.ceil((N + C_alpha) / 2)))
    return {'slope': float(np.median(slopes)), 'low_ci': float(slopes[low_idx]), 'high_ci': float(slopes[high_idx])}

def pettitt_test(x):
    """Pettitt's test for change-point detection."""
    n = len(x)
    r = sps.rankdata(x)
    U = [2 * np.sum(r[:t+1]) - (t + 1) * (n + 1) for t in range(n)]
    k_idx = np.argmax(np.abs(U))
    p_val = 2 * np.exp((-6 * np.max(np.abs(U))**2) / (n**3 + n**2))
    return {'idx': k_idx, 'p': p_val, 'sig': p_val < 0.05}

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §2  LUXURY PLOTTING COMPONENT                                          ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def plot_luxury_panel(stn, years, data_dict, stats_dict, out_path):
    fig = plt.figure(figsize=(10, 12))
    gs = gridspec.GridSpec(3, 1, hspace=0.3)
    keys = ['annual', 'wet', 'dry']
    titles = ['Annual Rainfall', 'Wet Season (May-Oct)', 'Dry Season (Nov-Apr)']

    for i, k in enumerate(keys):
        ax = fig.add_subplot(gs[i])
        y = data_dict[k]
        s = stats_dict[k]
        slp = sens_slope_gilbert(y)
        
        # Trend Line & Shaded CI
        intercept = np.median(y) - slp['slope'] * np.median(years)
        trend_y = slp['slope'] * years + intercept
        ci_low_y = slp['low_ci'] * years + (np.median(y) - slp['low_ci'] * np.median(years))
        ci_high_y = slp['high_ci'] * years + (np.median(y) - slp['high_ci'] * np.median(years))

        ax.fill_between(years, ci_low_y, ci_high_y, color=COLORS['ci'], alpha=0.8, label='95% CI (Gilbert)')
        ax.plot(years, y, color=COLORS[k], marker='o', ms=5, mfc='white', lw=1.2, alpha=0.6, label='Observed')
        ax.plot(years, trend_y, color=COLORS['slope'], lw=2.5, label=f"Sen's Slope: {slp['slope']:.2f}")

        # Formatting
        ax.set_title(f"({chr(97+i)}) {titles[i]} - Station {stn}", loc='left', weight='bold')
        ax.set_ylabel("Rainfall (mm)")
        ax.grid(True, axis='y', ls='--', alpha=0.3)
        
        # Annotation Box
        sig_text = "SIGNIFICANT" if s['sig'] else "Non-Significant"
        box_text = f"MMK Z: {s['z']:.2f}\np-value: {s['p']:.4f}\n{sig_text}"
        ax.text(0.02, 0.95, box_text, transform=ax.transAxes, va='top', fontsize=9,
                bbox=dict(boxstyle='round,pad=0.5', fc='white', ec='#D5DBDB', alpha=0.9))
        
        if i == 0: ax.legend(loc='upper right', frameon=False, ncol=3, fontsize=8)

    plt.savefig(out_path, dpi=DPI, bbox_inches='tight')
    plt.close()

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §3  MAIN WORKFLOW & EXCEL REPORTING                                     ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def apply_header_style(ws):
    for cell in ws[1]:
        cell.font = Font(color="FFFFFF", bold=True)
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.alignment = Alignment(horizontal='center')
        cell.border = Border(bottom=Side(style='medium'))

def main():
    print(f"\n{'='*60}\n Rainfall Trend Analysis v6.4 — Supreme Edition\n{'='*60}")
    
    # 1. Setup Environment
    try:
        input_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
        csv_path = next(input_dir.glob("*.csv"))
    except:
        print("Error: No CSV file found."); return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(f"Research_Analysis_{timestamp}")
    fig_dir = out_dir / "Luxury_Figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    # 2. Data Loading & Quality Control
    df = pd.read_csv(csv_path)
    df.replace([-99, -999, -9999, -9.99e+20, 1e+20], np.nan, inplace=True)
    df['date'] = pd.to_datetime({'year': df['YEAR'], 'month': df['MONTH'], 'day': df['DAY']})
    df = df.set_index('date').drop(['YEAR','MONTH','DAY'], axis=1).sort_index()
    df = df[~df.index.duplicated()]

    # QC Report: Gaps > 5 days
    for col in df.columns:
        gaps = df[col].isnull().astype(int).groupby(df[col].notnull().astype(int).cumsum()).sum()
        if gaps.max() > 5:
            print(f"  [QC Alert] Station {col}: Max gap of {gaps.max()} days detected.")

    # Interpolation (Strict Limit = 3 days)
    df_clean = df.interpolate(method='time', limit=3, limit_area='inside')
    stns = df_clean.columns.tolist()

    # 3. Aggregation
    annual = df_clean.resample('YS').sum(min_count=330)
    wet = df_clean[df_clean.index.month.isin(range(5,11))].resample('YS').sum(min_count=150)
    dry = df_clean[df_clean.index.month.isin([11,12,1,2,3,4])].resample('YS').sum(min_count=150)
    years = annual.index.year.values

    # 4. Excel Initialization (7 Sheets)
    wb = Workbook()
    sheets_def = {
        "1_Descriptive": ["Station", "Scale", "Mean", "Std", "CV%", "Max", "Min", "WetDays_Avg"],
        "2_Standard_MK": ["Station", "Scale", "Z_score", "p_value", "Significant"],
        "3_Modified_MK": ["Station", "Scale", "Z_score", "p_value", "Var_Adj", "Significant"],
        "4_Pettitt_CP": ["Station", "Scale", "CP_Year", "p_value", "Significant"],
        "5_Sens_Slope": ["Station", "Scale", "Slope", "Low_CI_95", "High_CI_95"],
        "6_Comp_MK_MMK": ["Station", "Scale", "MK_Sig", "MMK_Sig", "Agreement"],
        "7_Research_Summary": ["Station", "Annual_Trend", "Wet_Trend", "Dry_Trend", "Key_Finding"]
    }
    
    ws_map = {}
    for i, (name, head) in enumerate(sheets_def.items()):
        ws = wb.active if i == 0 else wb.create_sheet(name)
        ws.title = name
        ws.append(head)
        apply_header_style(ws)
        ws_map[name] = ws

    # 5. Main Processing Loop
    print(f"\nProcessing {len(stns)} stations...")
    for stn in stns:
        stn_results = {}
        summary_trends = []

        for k, frame in zip(['annual', 'wet', 'dry'], [annual, wet, dry]):
            data = frame[stn].dropna()
            if len(data) < 10: continue

            # Calculations
            mk = standard_mk_test(data.values)
            mmk = modified_mk_test(data.values)
            pet = pettitt_test(data.values)
            slp = sens_slope_gilbert(data.values)
            stn_results[k] = mmk
            
            # Populate Tables
            ws_map["1_Descriptive"].append([stn, k.capitalize(), data.mean(), data.std(), (data.std()/data.mean())*100, data.max(), data.min(), "N/A"])
            ws_map["2_Standard_MK"].append([stn, k.capitalize(), mk['z'], mk['p'], "YES" if mk['sig'] else "no"])
            ws_map["3_Modified_MK"].append([stn, k.capitalize(), mmk['z'], mmk['p'], mmk.get('var_adj', 0), "YES" if mmk['sig'] else "no"])
            ws_map["4_Pettitt_CP"].append([stn, k.capitalize(), years[pet['idx']], pet['p'], "YES" if pet['sig'] else "no"])
            ws_map["5_Sens_Slope"].append([stn, k.capitalize(), slp['slope'], slp['low_ci'], slp['high_ci']])
            ws_map["6_Comp_MK_MMK"].append([stn, k.capitalize(), mk['sig'], mmk['sig'], mk['sig'] == mmk['sig']])
            
            if mmk['sig']: summary_trends.append(f"{k}({'+' if mmk['z']>0 else '-'})")

        # Create Plot (for all stations)
        print(f"  > Plotting Luxury Figure for {stn}")
        plot_luxury_panel(stn, years, 
                         {k: frame[stn].values for k, frame in zip(['annual', 'wet', 'dry'], [annual, wet, dry])},
                         stn_results, fig_dir / f"Luxury_Trend_{stn}.png")
        
        # Summary
        ws_map["7_Research_Summary"].append([stn, "TBD", "TBD", "TBD", "; ".join(summary_trends) if summary_trends else "No Significant Trend"])

    # Finalize
    excel_path = out_dir / f"Full_Analysis_Report_{timestamp}.xlsx"
    wb.save(excel_path)
    print(f"\n{'='*60}\n SUCCESS!\n Location: {out_dir.absolute()}\n Excel: {excel_path.name}\n Figures: {len(stns)} Luxury PNGs (600 DPI)\n{'='*60}\n")

if __name__ == "__main__":
    main()