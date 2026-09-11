#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import norm

# ================= STYLE (สำคัญมาก) =================
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 12,
    "axes.titlesize": 16,
    "axes.labelsize": 13,
    "legend.fontsize": 11
})

# ================= SEN =================
def sen_slope(x, y):
    slopes = [(y[j]-y[i])/(x[j]-x[i]) for i in range(len(x)) for j in range(i+1,len(x))]
    return np.median(slopes)

# ================= MK =================
def mk_test(y):
    n = len(y)
    S = sum(np.sum(np.sign(y[i+1:] - y[i])) for i in range(n-1))
    var = n*(n-1)*(2*n+5)/18

    if S > 0:
        Z = (S - 1)/np.sqrt(var)
    elif S < 0:
        Z = (S + 1)/np.sqrt(var)
    else:
        Z = 0

    p = 2*(1-norm.cdf(abs(Z)))
    return S, Z, p

# ================= MMK =================
def modified_mk(y):
    n = len(y)
    r1 = np.corrcoef(y[:-1], y[1:])[0,1]

    ne = n*(1-r1)/(1+r1) if (1+r1)!=0 else n

    S, _, _ = mk_test(y)
    var = n*(n-1)*(2*n+5)/18
    var_mod = var*(n/ne)

    if S > 0:
        Z = (S - 1)/np.sqrt(var_mod)
    elif S < 0:
        Z = (S + 1)/np.sqrt(var_mod)
    else:
        Z = 0

    p = 2*(1-norm.cdf(abs(Z)))
    return Z, p, r1

# ================= CI =================
def bootstrap_ci(x, y, n=500):
    slopes=[]
    for _ in range(n):
        idx=np.random.choice(len(x),len(x),True)
        slopes.append(sen_slope(x[idx],y[idx]))
    return np.percentile(slopes,[2.5,97.5])

# ================= LOAD =================
def load(file):
    df = pd.read_csv(file)
    stations = [c for c in df.columns if str(c).isdigit()]
    df['date'] = pd.to_datetime(df[['YEAR','MONTH','DAY']])
    df['year'] = df['date'].dt.year
    return df, stations

def annual(df, st):
    return df.groupby('year')[st].sum()

# ================= PLOT =================
def plot_station(st, years, values, out):

    slope = sen_slope(years, values)
    ci = bootstrap_ci(years, values)

    S, Z, p = mk_test(values)
    Zm, pm, r1 = modified_mk(values)

    mean = np.mean(values)
    cv = np.std(values)/mean*100

    # ===== trend line =====
    intercept = np.median(values) - slope*np.median(years)
    yfit = slope*years + intercept

    # ===== figure =====
    fig, ax = plt.subplots(figsize=(11,6.5))

    # bar (annual rainfall)
    ax.bar(years, values, width=0.8, alpha=0.75,
           edgecolor='black', linewidth=0.5)

    # mean line
    ax.axhline(mean, linestyle='--', linewidth=2)

    # trend
    ax.plot(years, yfit, color='darkred', linewidth=3)

    # confidence band
    ax.fill_between(years,
                    yfit + ci[0],
                    yfit + ci[1],
                    color='red', alpha=0.15)

    # ===== TEXT BOX (ULTRA IMPORTANT) =====
    sig = "*" if p < 0.05 else ""
    sig_m = "*" if pm < 0.05 else ""

    text = (
        f"Mann–Kendall Test (Standard)\n"
        f"Z = {Z:.3f}, p = {p:.4f} {sig}\n\n"
        f"Modified Mann–Kendall (MMK)\n"
        f"Z = {Zm:.3f}, p = {pm:.4f} {sig_m}\n"
        f"ρ₁ = {r1:.2f}\n\n"
        f"Sen’s slope = {slope:.2f} mm yr⁻¹\n"
        f"95% CI = [{ci[0]:.2f}, {ci[1]:.2f}]\n\n"
        f"Mean = {mean:.1f} mm\n"
        f"CV = {cv:.1f}%"
    )

    ax.text(0.02, 0.98, text,
            transform=ax.transAxes,
            va='top', ha='left',
            bbox=dict(facecolor='white', alpha=0.9, edgecolor='black'))

    # ===== TITLE =====
    ax.set_title(f"Station {st}\nAnnual Rainfall Trend (1981–2014)",
                 fontweight='bold')

    ax.set_xlabel("Year")
    ax.set_ylabel("Annual Rainfall (mm)")

    ax.grid(True, linestyle='--', alpha=0.3)

    # remove top/right
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()

    plt.savefig(os.path.join(out, f"Trend_{st}.png"),
                dpi=500, bbox_inches='tight')
    plt.close()

# ================= MAIN =================
def main():

    files = glob.glob("*.csv")
    out = "Q2_Plots"
    os.makedirs(out, exist_ok=True)

    for f in files:
        df, stations = load(f)

        for st in stations:
            series = annual(df, st).dropna()

            if len(series) < 10:
                continue

            plot_station(st,
                         series.index.values,
                         series.values,
                         out)

    print("✅ DONE: All station plots generated")

if __name__ == "__main__":
    main()