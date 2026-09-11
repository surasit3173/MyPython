#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import theilslopes
import pymannkendall as mk
from datetime import datetime

# ================= STYLE =================
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.labelsize": 12
})

# ================= SAFE ACCESS =================
def safe_attr(obj, names):
    for n in names:
        if hasattr(obj, n):
            return getattr(obj, n)
    return np.nan

# ================= TREND =================
def trend_analysis(y):

    y = np.array(y, dtype=float)
    y = y[~np.isnan(y)]

    if len(y) < 10 or np.std(y) == 0:
        return None

    x = np.arange(len(y))

    # Theil–Sen
    slope, intercept, lo, hi = theilslopes(y, x, 0.95)

    # MK
    res_mk = mk.original_test(y)

    # MMK
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

# ================= LOAD =================
def load(f):
    df = pd.read_csv(f)
    stations = [c for c in df.columns if str(c).isdigit()]
    df['date'] = pd.to_datetime(df[['YEAR','MONTH','DAY']])
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    return df, stations

# ================= SEASON =================
def get_seasonal(df, st):
    ann = df.groupby('year')[st].sum()
    wet = df[df['month'].isin([5,6,7,8,9,10])].groupby('year')[st].sum()
    dry = df[df['month'].isin([11,12,1,2,3,4])].groupby('year')[st].sum()
    return {"Annual":ann, "Wet":wet, "Dry":dry}

# ================= PLOT =================
def plot_multiseason(st, seasons, out):

    fig, axes = plt.subplots(1, 3, figsize=(15,5), sharey=True)

    for ax,(name,data) in zip(axes, seasons.items()):

        data = data.dropna()

        if len(data) < 10:
            ax.set_title(f"{name}\n(No Data)")
            continue

        y = data.values
        x = np.arange(len(y))
        years = data.index.values

        r = trend_analysis(y)
        if r is None:
            continue

        slope = r['slope']
        yfit = slope*x + (np.median(y) - slope*np.median(x))

        # plot
        ax.plot(years, y, 'o-', lw=1.8, label="Observed")
        ax.plot(years, yfit, '--', lw=2.5, label="Trend")

        ax.fill_between(years,
                        yfit + r['ci_low'],
                        yfit + r['ci_high'],
                        alpha=0.2)

        # significance
        mk_sig = "*" if r['mk_p'] < 0.05 else ""
        mmk_sig = "*" if r['mmk_p'] < 0.05 else ""

        ax.set_title(
            f"{name}\n"
            f"MK p={r['mk_p']:.3f}{mk_sig} | "
            f"MMK p={r['mmk_p']:.3f}{mmk_sig}"
        )

        ax.grid(True, alpha=0.3)

    axes[0].set_ylabel("Rainfall (mm)")
    plt.suptitle(f"Station {st} - Multi-season Trend", fontweight='bold')

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper center', ncol=2)

    plt.tight_layout(rect=[0,0,1,0.92])
    plt.savefig(os.path.join(out, f"{st}_MultiSeason.png"), dpi=400)
    plt.close()

# ================= MAIN =================
def main():

    files = glob.glob("*.csv")
    out = f"MMK_Q2_Output_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(out, exist_ok=True)

    rows = []

    for f in files:

        print("Processing:", f)
        df, stations = load(f)

        for st in stations:

            seasons = get_seasonal(df, st)

            for s_name, data in seasons.items():

                data = data.dropna()
                if len(data) < 10:
                    continue

                r = trend_analysis(data.values)
                if r is None:
                    continue

                rows.append([
                    st, s_name,
                    r['slope'], r['ci_low'], r['ci_high'],
                    r['mk_p'], r['mmk_p'],
                    r['trend_mk'], r['trend_mmk']
                ])

            # plot
            plot_multiseason(st, seasons, out)

    # ================= SAVE =================
    df_out = pd.DataFrame(rows, columns=[
        "Station","Season",
        "Slope","CI_low","CI_high",
        "p_MK","p_MMK",
        "Trend_MK","Trend_MMK"
    ])

    df_out.to_excel(os.path.join(out, "Trend_Summary.xlsx"), index=False)

    print("\n✅ DONE:", out)

# ================= RUN =================
if __name__ == "__main__":
    main()