#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import theilslopes, kendalltau, norm
import pymannkendall as mk

# ================= GLOBAL STYLE =================
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11
})

# ================= PREPROCESS =================
def preprocess(x):
    x = np.array(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) < 10:
        return None
    if np.all(x == x[0]):
        return None
    return x

# ================= FDR =================
def fdr_bh(pvals):
    pvals = np.array(pvals)
    n = len(pvals)
    idx = np.argsort(pvals)
    sorted_p = pvals[idx]

    adj = sorted_p * n / (np.arange(1, n+1))
    adj = np.minimum.accumulate(adj[::-1])[::-1]

    out = np.empty(n)
    out[idx] = adj
    return out

# ================= MK =================
def standard_mk(x):
    x = preprocess(x)
    if x is None:
        return None

    n = len(x)
    S = sum(np.sign(x[j]-x[i]) for i in range(n) for j in range(i+1,n))
    var_s = n*(n-1)*(2*n+5)/18

    z = 0 if var_s <= 0 else (
        (S-1)/np.sqrt(var_s) if S>0 else
        (S+1)/np.sqrt(var_s) if S<0 else 0
    )

    p = 2*(1-norm.cdf(abs(z)))
    tau,_ = kendalltau(range(n),x)

    return dict(z=z,p=p,tau=tau,S=S,var_s=var_s)

# ================= MMK =================
def modified_mk(x):
    x = preprocess(x)
    if x is None:
        return None

    try:
        res = mk.hamed_rao_modification_test(x)
    except:
        res = mk.original_test(x)

    z = getattr(res,'z',getattr(res,'Z',np.nan))
    p = getattr(res,'p',getattr(res,'p_value',np.nan))
    tau = getattr(res,'Tau',getattr(res,'tau',np.nan))

    return dict(z=z,p=p,tau=tau)

# ================= SEN =================
def sen_slope(x):
    x = preprocess(x)
    if x is None:
        return None
    t = np.arange(len(x))
    slope, intercept, lo, hi = theilslopes(x,t,0.95)
    return slope, lo, hi

# ================= SEASON =================
def get_season(m):
    return "Wet" if m in [5,6,7,8,9,10] else "Dry"

# ================= AGG =================
def aggregate(df, st):
    d = df[['date',st]].rename(columns={st:'pr'})
    d['year'] = d['date'].dt.year
    d['season'] = d['date'].dt.month.apply(get_season)

    return {
        "Annual": d.groupby('year')['pr'].sum(),
        "Wet": d[d['season']=="Wet"].groupby('year')['pr'].sum(),
        "Dry": d[d['season']=="Dry"].groupby('year')['pr'].sum()
    }

# ================= Q2 PLOT =================
def plot_q2(years, values, slope, lo, hi, mk_res, mmk_res, title, ylabel, out):

    years = np.array(years)
    values = np.array(values)
    x = np.arange(len(values))

    intercept = np.median(values) - slope*np.median(x)
    trend = slope*x + intercept
    ci_l = lo*x + intercept
    ci_u = hi*x + intercept
    mean_val = np.mean(values)

    fig, ax = plt.subplots(figsize=(10,6.5))

    # BAR
    ax.bar(years, values,
           color="#4C72B0", alpha=0.85,
           edgecolor="black", linewidth=0.6)

    # MEAN
    ax.axhline(mean_val, linestyle="--",
               linewidth=1.8, color="#2ca02c")

    # TREND
    ax.plot(years, trend,
            color="#d62728", linewidth=2.6)

    # CI
    ax.fill_between(years, ci_l, ci_u,
                    color="#d62728", alpha=0.18)

    # LABEL
    ax.set_xlabel("Year", fontsize=12.5)
    ax.set_ylabel(ylabel, fontsize=12.5)
    ax.set_title(title, fontsize=14.5, fontweight='bold')

    ax.grid(True, linestyle="--", alpha=0.35)

    # BOX MK
    txt1 = (
        f"Standard MK\nZ={mk_res['z']:.2f}\np={mk_res['p']:.4f}\n\n"
        f"Modified MK\nZ={mmk_res['z']:.2f}\np={mmk_res['p']:.4f}"
    )

    ax.text(0.02,0.98,txt1,transform=ax.transAxes,
            va='top', bbox=dict(facecolor='white',edgecolor='black'))

    # BOX SLOPE
    txt2 = (
        f"Sen’s slope = {slope:.2f} mm/year\n"
        f"95% CI: [{lo:.2f}, {hi:.2f}]"
    )

    ax.text(0.02,0.05,txt2,transform=ax.transAxes,
            va='bottom', bbox=dict(facecolor='white',edgecolor='black'))

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    plt.savefig(out, dpi=400)
    plt.close()

# ================= MAIN =================
def main():

    files = glob.glob("*.csv")
    out = "Q2_FIGURES"
    os.makedirs(out, exist_ok=True)

    rows = []

    for f in files:
        df = pd.read_csv(f)
        stations = [c for c in df.columns if str(c).isdigit()]

        df['date'] = pd.to_datetime(df[['YEAR','MONTH','DAY']])

        for st in stations:
            agg = aggregate(df, st)

            for scale, series in agg.items():

                y = series.values
                yrs = series.index

                mk_res = standard_mk(y)
                mmk_res = modified_mk(y)
                slope, lo, hi = sen_slope(y)

                rows.append([
                    st, scale,
                    slope, lo, hi,
                    mk_res['p'], mmk_res['p']
                ])

                plot_q2(
                    yrs, y,
                    slope, lo, hi,
                    mk_res, mmk_res,
                    f"Station {st} - {scale}",
                    f"{scale} Rainfall (mm)",
                    os.path.join(out,f"{st}_{scale}.png")
                )

    df = pd.DataFrame(rows, columns=[
        "Station","Scale",
        "SenSlope","CI_Lower","CI_Upper",
        "p_MK","p_MMK"
    ])

    df["p_MK_FDR"] = fdr_bh(df["p_MK"])
    df["p_MMK_FDR"] = fdr_bh(df["p_MMK"])

    df.to_excel(os.path.join(out,"Trend_Table.xlsx"), index=False)

    print("✅ DONE — Q2 Standard Figures & Tables Ready")

if __name__ == "__main__":
    main()