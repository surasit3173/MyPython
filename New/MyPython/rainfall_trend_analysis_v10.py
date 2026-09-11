import os
import sys
import math
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

# --- Configuration: Option A: Classic (Journal of Hydrology) ---
ALPHA = 0.05
DPI = 600
WET_THRESHOLD = 1.0  # mm (นิยามวันฝนตก)

# สีตามคำขอของคุณ
COLOR_INC = '#006D2C' # เขียวเข้ม (Increasing)
COLOR_DEC = '#A50F15' # แดงเข้ม (Decreasing)
COLOR_NS  = '#525252' # เทาเข้ม (Non-Significant)
COLOR_CI  = '#F7F7F7' # พื้นหลัง CI

plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman"],
    "font.size": 10, "axes.titlesize": 12, "axes.labelsize": 10,
    "axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": DPI
})

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §1  ADVANCED STATISTICAL ENGINE                                        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def standard_mk_test(x):
    n = len(x)
    s = sum(np.sign(x[j] - x[i]) for i in range(n - 1) for j in range(i + 1, n))
    var_s = (n * (n - 1) * (2 * n + 5)) / 18.0
    z = (s - 1) / np.sqrt(var_s) if s > 0 else (s + 1) / np.sqrt(var_s) if s < 0 else 0
    p = 2 * (1 - norm.cdf(abs(z)))
    return {'z': z, 'p': p, 'sig': p < ALPHA}

def modified_mk_test(x):
    """Modified Mann-Kendall (Hamed & Rao, 1998)"""
    n = len(x)
    s = sum(np.sign(x[j] - x[i]) for i in range(n - 1) for j in range(i + 1, n))
    var_s = (n * (n - 1) * (2 * n + 5)) / 18.0
    ranks = sps.rankdata(x)
    rho = np.corrcoef(ranks[:-1], ranks[1:])[0, 1] if n > 2 else 0
    var_adj = var_s
    if rho > 0.1:
        n_ns = 1 + 2 * (rho**n / (n * (rho - 1)) - rho / (n * (rho - 1)**2))
        var_adj *= (n / n_ns)
    z = (s - 1) / np.sqrt(var_adj) if s > 0 else (s + 1) / np.sqrt(var_adj) if s < 0 else 0
    p = 2 * (1 - norm.cdf(abs(z)))
    return {'z': z, 'p': p, 'sig': p < ALPHA, 'var_adj': var_adj}

def sens_slope_gilbert(x, alpha=0.05):
    n = len(x)
    slopes = [(x[j] - x[i]) / (j - i) for i in range(n - 1) for j in range(i + 1, n)]
    slopes = np.sort(slopes)
    N = len(slopes)
    var_s = (n * (n - 1) * (2 * n + 5)) / 18.0
    C_alpha = norm.ppf(1 - alpha / 2) * math.sqrt(var_s)
    low_idx = max(0, int(np.floor((N - C_alpha) / 2)))
    high_idx = min(N - 1, int(np.ceil((N + C_alpha) / 2)))
    return {'slope': float(np.median(slopes)), 'low_ci': float(slopes[low_idx]), 'high_ci': float(slopes[high_idx])}

def pettitt_test(x):
    n = len(x)
    r = sps.rankdata(x)
    U = [2 * np.sum(r[:t+1]) - (t + 1) * (n + 1) for t in range(n)]
    k_idx = np.argmax(np.abs(U))
    p_val = 2 * np.exp((-6 * np.max(np.abs(U))**2) / (n**3 + n**2))
    return {'idx': k_idx, 'p': p_val, 'sig': p_val < 0.05}

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §2  DYNAMIC LUXURY PLOTTING                                            ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def plot_luxury_final(stn, years, data_dict, stats_dict, out_path):
    fig = plt.figure(figsize=(10, 12))
    gs = gridspec.GridSpec(3, 1, hspace=0.32)
    keys = ['annual', 'wet', 'dry']
    titles = ['Annual Rainfall', 'Wet Season (May-Oct)', 'Dry Season (Nov-Apr)']

    for i, k in enumerate(keys):
        ax = fig.add_subplot(gs[i])
        y = data_dict[k]
        s = stats_dict[k]
        slp = sens_slope_gilbert(y)
        
        # Determine Color Logic
        if s['sig']:
            color = COLOR_INC if s['z'] > 0 else COLOR_DEC
            lbl = "SIGNIFICANT"
        else:
            color = COLOR_NS
            lbl = "NS"

        itc = np.median(y) - slp['slope'] * np.median(years)
        trend_y = slp['slope'] * years + itc
        ci_l = slp['low_ci'] * years + (np.median(y) - slp['low_ci'] * np.median(years))
        ci_h = slp['high_ci'] * years + (np.median(y) - slp['high_ci'] * np.median(years))

        ax.fill_between(years, ci_l, ci_h, color=COLOR_CI, alpha=0.9, label='95% CI (Gilbert)')
        ax.plot(years, y, color=color, marker='o', ms=5, mfc='white', alpha=0.4, lw=1)
        ax.plot(years, trend_y, color=color, lw=2.5, label=f"Trend: {slp['slope']:.2f} mm/yr")

        ax.set_title(f"({chr(97+i)}) {titles[i]} - {stn}", loc='left', weight='bold')
        ax.set_ylabel("Rainfall (mm)")
        ax.grid(True, axis='y', ls=':', alpha=0.6)
        
        box = f"MMK Z: {s['z']:.2f}\np-value: {s['p']:.4f}\n{lbl}"
        ax.text(0.02, 0.95, box, transform=ax.transAxes, va='top', fontsize=9,
                bbox=dict(boxstyle='round', fc='white', ec='#D5DBDB', alpha=0.9))
        if i == 0: ax.legend(loc='upper right', frameon=False, ncol=3, fontsize=8)

    plt.savefig(out_path, dpi=DPI, bbox_inches='tight')
    plt.close()

# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  §3  MAIN EXECUTION                                                     ║
# ╚══════════════════════════════════════════════════════════════════════════╝

def main():
    print(f"\nRainfall Trend Analysis v6.6 (Final Integrated)\n{'='*55}")
    
    try:
        data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
        csv_file = next(data_dir.glob("*.csv"))
    except:
        print("Error: No CSV file found."); return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    out_dir = Path(f"Research_Full_Report_{timestamp}")
    fig_dir = out_dir / "Figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load & QC
    df = pd.read_csv(csv_file)
    df.replace([-99, -999, -9999, 1e20], np.nan, inplace=True)
    df['date'] = pd.to_datetime({'year': df['YEAR'], 'month': df['MONTH'], 'day': df['DAY']})
    df = df.set_index('date').drop(['YEAR','MONTH','DAY'], axis=1).sort_index()
    df_clean = df.interpolate(method='time', limit=3, limit_area='inside')
    
    stns = df_clean.columns.tolist()
    annual = df_clean.resample('YS').sum(min_count=330)
    wet = df_clean[df_clean.index.month.isin(range(5,11))].resample('YS').sum(min_count=150)
    dry = df_clean[df_clean.index.month.isin([11,12,1,2,3,4])].resample('YS').sum(min_count=150)
    wet_days = (df_clean >= WET_THRESHOLD).resample('YS').sum()
    years = annual.index.year.values

    # 2. Excel Setup (7 Sheets)
    wb = Workbook()
    sheets = {
        "1_Descriptive": ["Station", "Scale", "Mean", "Std", "CV%", "Max", "Min", "Avg_WetDays"],
        "2_Standard_MK": ["Station", "Scale", "Z", "p_value", "Significant"],
        "3_Modified_MK": ["Station", "Scale", "Z", "p_value", "Var_Adj", "Significant"],
        "4_Pettitt_CP": ["Station", "Scale", "CP_Year", "p_value", "Significant"],
        "5_Sens_Slope": ["Station", "Scale", "Slope", "Low_CI", "High_CI"],
        "6_Comparison": ["Station", "Scale", "MK_Sig", "MMK_Sig", "Agreement"],
        "7_Research_Summary": ["Station", "Annual", "Wet", "Dry", "Overall_Trend"]
    }
    
    ws_map = {}
    for i, (name, head) in enumerate(sheets.items()):
        ws = wb.active if i == 0 else wb.create_sheet(name)
        ws.title = name
        ws.append(head)
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="1F4E78")
        ws_map[name] = ws

    # 3. Processing Loop
    for stn in stns:
        stn_stats = {}
        row_summary = [stn]
        all_findings = []

        for k, frame in zip(['annual', 'wet', 'dry'], [annual, wet, dry]):
            data = frame[stn].dropna()
            if len(data) < 10: continue
            
            mk = standard_mk_test(data.values)
            mmk = modified_mk_test(data.values)
            pet = pettitt_test(data.values)
            slp = sens_slope_gilbert(data.values)
            stn_stats[k] = mmk
            
            # Fill Sheets
            ws_map["1_Descriptive"].append([stn, k, data.mean(), data.std(), (data.std()/data.mean())*100, data.max(), data.min(), wet_days[stn].mean()])
            ws_map["2_Standard_MK"].append([stn, k, mk['z'], mk['p'], "YES" if mk['sig'] else "no"])
            ws_map["3_Modified_MK"].append([stn, k, mmk['z'], mmk['p'], mmk.get('var_adj'), "YES" if mmk['sig'] else "no"])
            ws_map["4_Pettitt_CP"].append([stn, k, years[pet['idx']], pet['p'], "YES" if pet['sig'] else "no"])
            ws_map["5_Sens_Slope"].append([stn, k, slp['slope'], slp['low_ci'], slp['high_ci']])
            ws_map["6_Comparison"].append([stn, k, mk['sig'], mmk['sig'], mk['sig']==mmk['sig']])
            
            trend_desc = f"{'Up' if mmk['z']>0 else 'Down'} (p={mmk['p']:.3f})" if mmk['sig'] else "Stable"
            row_summary.append(trend_desc)
            if mmk['sig']: all_findings.append(f"{k} {trend_desc}")

        # Summary & Plot
        row_summary.append("; ".join(all_findings) if all_findings else "No Change")
        ws_map["7_Research_Summary"].append(row_summary)
        
        print(f"  > Processing: {stn}")
        plot_luxury_final(stn, years, {k: f[stn].values for k, f in zip(['annual', 'wet', 'dry'], [annual, wet, dry])},
                          stn_stats, fig_dir / f"Luxury_Trend_{stn}.png")

    wb.save(out_dir / f"Full_Analysis_Report_{timestamp}.xlsx")
    print(f"\n{'='*55}\nCOMPLETE: Results in {out_dir}\n{'='*55}\n")

if __name__ == "__main__":
    main()