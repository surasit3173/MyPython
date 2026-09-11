#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import theilslopes
import pymannkendall as mk
from datetime import datetime

# ================= GLOBAL STYLE (Q2) =================
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.titlesize": 16,
    "axes.labelsize": 13
})

# ================= SAFE ACCESS =================
def safe_attr(obj, names, default=np.nan):
    for n in names:
        if hasattr(obj, n):
            return getattr(obj, n)
    return default

# ================= TREND ANALYSIS =================
def trend_analysis(y):

    y = np.array(y, dtype=float)
    y = y[~np.isnan(y)]

    # ---- Data quality check ----
    if len(y) < 10 or np.std(y) == 0:
        return None

    x = np.arange(len(y))

    # ---- Theil–Sen slope + CI ----
    slope, intercept, lo, hi = theilslopes(y, x, 0.95)

    # ---- Standard MK ----
    res_mk = mk.original_test(y)

    # ---- Modified MK (Hamed & Rao) ----
    res_mmk = mk.hamed_rao_modification_test(y)

    return {
        "slope": slope,
        "ci_low": lo,
        "ci_high": hi,
        "mk_p": safe_attr(res_mk, ["p", "p_value"]),
        "mk_z": safe_attr(res_mk, ["z", "Z"]),
        "mmk_p": safe_attr(res_mmk, ["p", "p_value"]),
        "mmk_z": safe_attr(res_mmk, ["z", "Z"]),
        "trend_mk": str(safe_attr(res_mk, ["trend"])).title(),
        "trend_mmk": str(safe_attr(res_mmk, ["trend"])).title()
    }

# ================= LOAD DATA =================
def load_data(file):
    df = pd.read_csv(file)
    stations = [c for c in df.columns if str(c).isdigit()]

    df['date'] = pd.to_datetime(df[['YEAR','MONTH','DAY']])
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month

    return df, stations

# ================= SEASON SPLIT =================
def get_seasonal(df, st):

    ann = df.groupby('year')[st].sum()

    wet = df[df['month'].isin([5,6,7,8,9,10])].groupby('year')[st].sum()
    dry = df[df['month'].isin([11,12,1,2,3,4])].groupby('year')[st].sum()

    return {"Annual":ann, "Wet":wet, "Dry":dry}

# ================= PLOT FUNCTION =================
def plot_q2(st, years, values, result, method, outpath):

    slope = result['slope']
    lo = result['ci_low']
    hi = result['ci_high']

    p = result['mk_p'] if method == "MK" else result['mmk_p']
    z = result['mk_z'] if method == "MK" else result['mmk_z']

    # ---- Trend line ----
    x = np.arange(len(values))
    intercept = np.median(values) - slope*np.median(x)
    yfit = slope*x + intercept

    mean_val = np.mean(values)

    fig, ax = plt.subplots(figsize=(12,7))

    # ---- Bars ----
    ax.bar(years, values,
           color='#5b8db8',
           edgecolor='#2f2f2f',
           linewidth=1.0,
           alpha=0.9)

    # ---- Trend ----
    ax.plot(years, yfit,
            color='#8b0000',
            linewidth=3.0,
            label="Sen’s Slope")

    # ---- CI band ----
    if not (np.isnan(lo) or np.isnan(hi)):
        ax.fill_between(years,
                        yfit + lo,
                        yfit + hi,
                        color='#c0392b',
                        alpha=0.18,
                        label='95% Confidence Band')

    # ---- Mean ----
    ax.axhline(mean_val,
               linestyle='--',
               linewidth=2,
               color='#2e7d32',
               label=f"Mean ({mean_val:.1f} mm)")

    sig = "*" if p < 0.05 else ""

    # ---- Box 1 (MK/MMK) ----
    text1 = (
        f"{'Standard' if method=='MK' else 'Modified'} Mann–Kendall\n"
        f"Z = {z:.3f}\n"
        f"p = {p:.4f} {sig}"
    )

    ax.text(0.02, 0.96, text1,
            transform=ax.transAxes,
            va='top',
            bbox=dict(facecolor='white', edgecolor='black', alpha=0.9))

    # ---- Box 2 (Slope) ----
    text2 = (
        f"Sen’s slope = {slope:.2f} mm yr⁻¹\n"
        f"95% CI = [{lo:.2f}, {hi:.2f}]"
    )

    ax.text(0.02, 0.72, text2,
            transform=ax.transAxes,
            va='top',
            bbox=dict(facecolor='white', edgecolor='black', alpha=0.9))

    # ---- Titles ----
    ax.set_title(
        f"Station {st}\n"
        f"{'Standard' if method=='MK' else 'Modified'} Mann–Kendall Trend",
        fontweight='bold'
    )

    ax.set_xlabel("Year")
    ax.set_ylabel("Rainfall (mm)")

    ax.grid(True, linestyle='--', alpha=0.4)
    ax.legend(loc='upper right')

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    plt.savefig(outpath, dpi=400, bbox_inches='tight')
    plt.close()

# ================= MAIN =================
def main():

    files = glob.glob("*.csv")
    out = f"Q2_Output_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(out, exist_ok=True)

    rows = []

    for f in files:

        print("Processing:", f)

        df, stations = load_data(f)

        for st in stations:

            seasons = get_seasonal(df, st)

            for s_name, series in seasons.items():

                series = series.dropna()
                if len(series) < 10:
                    continue

                years = series.index.values
                values = series.values

                result = trend_analysis(values)
                if result is None:
                    continue

                # ---- Plot MK ----
                plot_q2(st, years, values, result, "MK",
                        os.path.join(out, f"{st}_{s_name}_MK.png"))

                # ---- Plot MMK ----
                plot_q2(st, years, values, result, "MMK",
                        os.path.join(out, f"{st}_{s_name}_MMK.png"))

                # ---- Save table ----
                rows.append([
                    st, s_name,
                    result['slope'],
                    result['ci_low'],
                    result['ci_high'],
                    result['mk_p'],
                    result['mmk_p'],
                    result['trend_mk'],
                    result['trend_mmk']
                ])

    # ---- Export Excel ----
    df_out = pd.DataFrame(rows, columns=[
        "Station","Season",
        "Slope","CI_low","CI_high",
        "p_MK","p_MMK",
        "Trend_MK","Trend_MMK"
    ])

    df_out.to_excel(os.path.join(out, "Trend_Summary.xlsx"),
                    index=False,
                    engine='openpyxl')

    print("\n✅ Analysis completed successfully")
    print("📁 Output folder:", out)

# ================= RUN =================
if __name__ == "__main__":
    main()