"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  Rainfall Trend Analysis — Publication Grade v6.7 (Final Fixed)             ║
║  Standard: Q1 Journal (Journal of Hydrology / Atmospheric Research)          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Core Fixes:                                                                 ║
║  - Fixed Imports (scipy.stats, math)                                         ║
║  - Harmonized Field Names (Slope, Slope_LCL, Slope_UCL, p_value)             ║
║  - Synchronized Function Returns (QC, MK Variance)                           ║
║  - Unified Excel Engine (Openpyxl) & Proper Dataframe Construction           ║
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
from scipy import stats
from scipy.stats import norm
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

# --- Global Constants (Fixed Consistency) ---
ALPHA = 0.05
DPI = 600
MIN_YEARS = 10  # เดิมใน v4
WET_THRESHOLD = 1.0 
MISS_FLAGS = [-99, -999, -9999, 1e20, -9.99e+20]

# Publication Palette (Color-blind friendly)
COLOR_MAIN = "#1f77b4"
COLOR_CI   = "#9ecae1"
COLOR_INC  = '#006D2C' # Option A: Classic Green
COLOR_DEC  = '#A50F15' # Option A: Classic Red
COLOR_NS   = '#525252' # Dark Grey

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman"],
    "font.size": 10, "axes.titlesize": 12, "axes.labelsize": 10,
    "axes.spines.top": False, "axes.spines.right": False
})

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §1  CORE ANALYTICAL FUNCTIONS (Fixed Names & Logic)                    ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def mk_variance(x):
    """Calculates the variance of S, handling ties (Standard & Consistent Name)."""
    n = len(x)
    var_s = (n * (n - 1) * (2 * n + 5)) / 18.0
    _, ties = np.unique(x, return_counts=True)
    for t in ties[ties > 1]:
        var_s -= (t * (t - 1) * (2 * t + 5)) / 18.0
    return var_s

def modified_mk_test(x):
    """Modified MK (H&R 1998) with fixed import and consistent math."""
    n = len(x)
    if n < MIN_YEARS: return {'z': 0, 'p': 1.0, 'sig': False, 'var_adj': 0}
    
    s = sum(np.sign(x[j] - x[i]) for i in range(n - 1) for j in range(i + 1, n))
    var_s = mk_variance(x)
    
    ranks = stats.rankdata(x)
    rho = np.corrcoef(ranks[:-1], ranks[1:])[0, 1] if n > 2 else 0
    var_adj = var_s
    if rho > 0.1:
        n_ns = 1 + 2 * (rho**n / (n * (rho - 1)) - rho / (n * (rho - 1)**2))
        var_adj *= (n / n_ns)
        
    z = (s - 1) / math.sqrt(var_adj) if s > 0 else (s + 1) / math.sqrt(var_adj) if s < 0 else 0
    p = 2 * (1 - norm.cdf(abs(z)))
    return {'z': z, 'p': p, 'sig': p < ALPHA, 'var_adj': var_adj}

def sens_slope_gilbert(x, years):
    """Sen's Slope with Gilbert (1987) CI - Fixed scipy_norm error."""
    n = len(x)
    slopes = [(x[j] - x[i]) / (j - i) for i in range(n - 1) for j in range(i + 1, n)]
    slopes = np.sort(slopes)
    N = len(slopes)
    var_s = mk_variance(x)
    
    z_crit = norm.ppf(1 - ALPHA / 2)
    C_alpha = z_crit * math.sqrt(var_s)
    
    low_idx = max(0, int(np.floor((N - C_alpha) / 2)))
    high_idx = min(N - 1, int(np.ceil((N + C_alpha) / 2)))
    
    lo, hi = slopes[low_idx], slopes[high_idx]
    lo, hi = sorted([lo, hi]) # Fix 12: CI lines flipping
    
    return {'slope': float(np.median(slopes)), 'slope_lo': lo, 'slope_hi': hi}

def pettitt_test(x, years):
    """Pettitt change point with fixed year conversion."""
    n = len(x)
    r = stats.rankdata(x)
    U = [2 * np.sum(r[:t+1]) - (t + 1) * (n + 1) for t in range(n)]
    k_idx = np.argmax(np.abs(U))
    p_val = 2 * np.exp((-6 * np.max(np.abs(U))**2) / (n**3 + n**2))
    return {'cp_year': years[k_idx], 'p': p_val, 'sig': p_val < 0.05}

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §2  DATA MANAGEMENT (QC & Aggregation)                                 ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def quality_control(df):
    """Refined QC with return signature fix (Fix 9 & 10)."""
    # Ensure DatetimeIndex
    if not pd.api.types.is_datetime64_any_dtype(df.index):
        df.index = pd.to_datetime(df.index)
        
    qc_results = {}
    df_clean = df.copy()
    
    for stn in df.columns:
        # Report Gaps > 5 days
        gaps = df[stn].isnull().astype(int).groupby(df[stn].notnull().astype(int).cumsum()).sum()
        max_gap = gaps.max()
        qc_results[stn] = {"Max_Gap": max_gap}
        
        # Interpolation Limit=3 (Fix 10: time-weighted)
        df_clean[stn] = df_clean[stn].interpolate(method='time', limit=3, limit_area='inside')
        
    return df_clean, qc_results

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §3  LUXURY FIGURES (Consistency Fix)                                   ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def plot_luxury_panel(stn, years, data_dict, stats_dict, out_path):
    fig = plt.figure(figsize=(10, 12))
    gs = gridspec.GridSpec(3, 1, hspace=0.35)
    keys = ['annual', 'wet', 'dry']
    titles = ['Annual Rainfall', 'Wet Season (May-Oct)', 'Dry Season (Nov-Apr)']

    for i, k in enumerate(keys):
        ax = fig.add_subplot(gs[i])
        y = data_dict[k]
        s = stats_dict[k]
        slp = sens_slope_gilbert(y, years)
        
        # Fixed 15: Color Accessibility & 4: Field Consistency
        current_color = COLOR_INC if (s['sig'] and s['z'] > 0) else (COLOR_DEC if (s['sig'] and s['z'] < 0) else COLOR_NS)
        
        intercept = np.median(y) - slp['slope'] * np.median(years)
        ax.fill_between(years, slp['slope_lo']*years + (np.median(y) - slp['slope_lo']*np.median(years)), 
                        slp['slope_hi']*years + (np.median(y) - slp['slope_hi']*np.median(years)), 
                        color=COLOR_CI, alpha=0.5)
        
        ax.plot(years, y, color=current_color, marker='o', ms=4, mfc='white', alpha=0.3)
        ax.plot(years, slp['slope']*years + intercept, color=current_color, lw=2.5)

        ax.set_title(f"({chr(97+i)}) {titles[i]} - {stn}", loc='left', weight='bold')
        ax.set_ylabel("Rainfall (mm)")
        ax.grid(True, axis='y', ls=':', alpha=0.5)
        
    plt.savefig(out_path, dpi=DPI, bbox_inches='tight')
    plt.close()

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §4  MAIN WORKFLOW                                                      ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def main():
    # 1. Setup & Load
    try:
        input_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
        csv_path = next(input_dir.glob("*.csv"))
    except:
        print("Error: No CSV file found."); return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    out_dir = Path(f"Analysis_v6_7_{timestamp}")
    out_dir.mkdir(exist_ok=True)

    df = pd.read_csv(csv_path)
    df.replace(MISS_FLAGS, np.nan, inplace=True)
    df['date'] = pd.to_datetime({'year': df['YEAR'], 'month': df['MONTH'], 'day': df['DAY']})
    df = df.set_index('date').drop(['YEAR','MONTH','DAY'], axis=1).sort_index()

    # 2. QC & Aggregate (Fix 9, 13)
    daily_clean, qc_info = quality_control(df)
    stns = daily_clean.columns.tolist()
    
    annual = daily_clean.resample('YS').sum(min_count=330)
    wet = daily_clean[daily_clean.index.month.isin(range(5,11))].resample('YS').sum(min_count=150)
    dry = daily_clean[daily_clean.index.month.isin([11,12,1,2,3,4])].resample('YS').sum(min_count=150)
    years = annual.index.year.values

    # 3. Processing & Results Construction (Fix 4, 5, 7, 11)
    results_list = []
    
    for stn in stns:
        stn_stats = {}
        for k, frame in zip(['Annual', 'Wet', 'Dry'], [annual, wet, dry]):
            data = frame[stn].dropna()
            if len(data) < MIN_YEARS: continue
            
            mmk = modified_mk_test(data.values)
            slp = sens_slope_gilbert(data.values, years)
            pet = pettitt_test(data.values, years)
            
            # Master Results Dict (Fix 4: Consistent Naming)
            results_list.append({
                "Station": stn, "Scale": k,
                "Mean": data.mean(), "Z_score": mmk['z'], "p_value": mmk['p'],
                "Significant": "YES" if mmk['sig'] else "no",
                "Slope": slp['slope'], "Slope_LCL": slp['slope_lo'], "Slope_UCL": slp['slope_hi'],
                "CP_Year": pet['cp_year']
            })
            stn_stats[k.lower()] = mmk

        # Luxury Figure (Fix 6: Use stn list)
        plot_luxury_panel(stn, years, 
                         {k: frame[stn].values for k, frame in zip(['annual', 'wet', 'dry'], [annual, wet, dry])},
                         stn_stats, out_dir / f"Luxury_Trend_{stn}.png")

    # 4. Final Export (Fix 7, 8)
    master_df = pd.DataFrame(results_list)
    
    # Fix 7: Methodology Table
    methods_df = pd.DataFrame([
        ["Mann-Kendall", "Mann (1945); Kendall (1975)"],
        ["Modified MK", "Hamed & Rao (1998)"],
        ["Sen's Slope", "Sen (1968); Gilbert (1987)"],
        ["Pettitt", "Pettitt (1979)"]
    ], columns=["Method", "Reference"])

    # Fix 8: Excel Engine - Use openpyxl via pandas writer
    excel_path = out_dir / f"Full_Report_{timestamp}.xlsx"
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        master_df.to_excel(writer, sheet_name="Trend_Analysis", index=False)
        methods_df.to_excel(writer, sheet_name="Methodology", index=False)
        
        # Apply Styles
        wb = writer.book
        for sheet_name in writer.sheets:
            ws = writer.sheets[sheet_name]
            for cell in ws[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="1F4E78")

    print(f"\nSUCCESS: Publication-ready files saved in: {out_dir.name}")

if __name__ == "__main__":
    main()