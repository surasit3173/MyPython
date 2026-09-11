#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import norm
from datetime import datetime

# ===================== STYLE =====================
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10
})

# ===================== HELPERS =====================
def safe_corr(x, y):
    if len(x) < 3:
        return np.nan
    if np.std(x) == 0 or np.std(y) == 0:
        return np.nan
    return np.corrcoef(x, y)[0, 1]

def autocorr(x, lag):
    if len(x) <= lag:
        return np.nan
    return safe_corr(x[:-lag], x[lag:])

# ===================== SEN + MK =====================
def sen_slope(x, y):
    slopes = []
    for i in range(len(x)):
        for j in range(i+1, len(x)):
            if x[j] != x[i]:
                slopes.append((y[j] - y[i]) / (x[j] - x[i]))
    return np.median(slopes) if slopes else np.nan

def mann_kendall(y):
    n = len(y)
    S = 0
    for i in range(n-1):
        S += np.sum(np.sign(y[i+1:] - y[i]))
    var_S = n*(n-1)*(2*n+5)/18
    if S > 0:
        Z = (S - 1)/np.sqrt(var_S)
    elif S < 0:
        Z = (S + 1)/np.sqrt(var_S)
    else:
        Z = 0
    p = 2*(1 - norm.cdf(abs(Z)))
    return Z, p

def bootstrap_ci(x, y, n=300):
    slopes = []
    for _ in range(n):
        idx = np.random.choice(len(x), len(x), replace=True)
        slopes.append(sen_slope(x[idx], y[idx]))
    return np.percentile(slopes, [2.5, 97.5])

# ===================== FDR =====================
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

# ===================== PETTITT =====================
def pettitt_test(x):
    x = np.array(x)
    n = len(x)
    U = np.zeros(n)
    for t in range(n):
        for i in range(t):
            for j in range(t, n):
                U[t] += np.sign(x[j] - x[i])
    K = np.max(np.abs(U))
    t_idx = np.argmax(np.abs(U))
    p = 2*np.exp((-6*K**2)/(n**3 + n**2))
    return t_idx, p

# ===================== LOAD =====================
def load(file):
    df = pd.read_csv(file)
    stations = [c for c in df.columns if str(c).isdigit()]
    df['date'] = pd.to_datetime(df[['YEAR','MONTH','DAY']])
    return df, stations

# ===================== AGG =====================
def annual(df, st):
    df['year'] = df['date'].dt.year
    return df.groupby('year')[st].sum()

def seasonal(df, st):
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    wet = df[df['month'].isin([5,6,7,8,9,10])].groupby('year')[st].sum()
    dry = df[df['month'].isin([11,12,1,2,3,4])].groupby('year')[st].sum()
    return wet, dry

# ===================== MAIN =====================
def main():

    files = glob.glob("*.csv")
    out = f"Q2_Results_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(out, exist_ok=True)

    writer = pd.ExcelWriter(os.path.join(out, "Results.xlsx"), engine='openpyxl')

    T2_rows, T3_rows, T4_rows, T5_rows = [], [], [], []

    for file in files:

        df, stations = load(file)

        for st in stations:

            series = df[st]

            # ===================== T2 =====================
            T2_rows.append([
                st,
                np.nanmean(series),
                np.nanstd(series),
                np.nanmin(series),
                np.nanmax(series),
                np.mean(pd.isna(series))*100
            ])

            # ===================== TIME SERIES =====================
            ann = annual(df.copy(), st).dropna()
            wet, dry = seasonal(df.copy(), st)

            for label, data in zip(['Annual','Wet','Dry'], [ann, wet, dry]):

                if len(data) < 10:
                    continue

                x = data.index.values
                y = data.values

                slope = sen_slope(x, y)
                Z, p = mann_kendall(y)
                ci = bootstrap_ci(x, y)

                change = (y[-1] - y[0]) / y[0] * 100 if y[0] != 0 else np.nan
                trend = "Increasing" if slope > 0 else "Decreasing"

                T3_rows.append([
                    st, "1981–2014", label,
                    slope, ci[0], ci[1], p, trend, change
                ])

                # ===================== T4 =====================
                idx, p_cp = pettitt_test(y)
                T4_rows.append([st, label, x[idx], p_cp])

                # ===================== T5 =====================
                rho1 = autocorr(y, 1)
                sig_lags = []
                for lag in range(1,6):
                    r = autocorr(y, lag)
                    if abs(r) > 0.3:
                        sig_lags.append(lag)
                T5_rows.append([st, rho1, sig_lags])

                # ===================== F1 =====================
                fig, ax = plt.subplots(figsize=(6,4))
                ax.plot(x, y, 'o-')
                yfit = slope*x + (np.median(y)-slope*np.median(x))
                ax.plot(x, yfit, '--')

                ax.fill_between(x, yfit+ci[0], yfit+ci[1], alpha=0.2)

                ax.set_title(f"{st} - {label}")
                ax.set_xlabel("Year")
                ax.set_ylabel("Rainfall (mm)")
                ax.grid(True, alpha=0.3)

                plt.tight_layout()
                plt.savefig(os.path.join(out, f"F1_{st}_{label}.png"), dpi=400)
                plt.close()

                # ===================== F4 =====================
                fig, ax = plt.subplots()
                lags = range(1,6)
                vals = [autocorr(y, l) for l in lags]
                ax.bar(lags, vals)
                ax.set_title(f"ACF {st}")
                plt.savefig(os.path.join(out, f"F4_{st}.png"), dpi=400)
                plt.close()

                # ===================== F5 =====================
                fig, ax = plt.subplots()
                ax.plot(x, y)
                ax.axvline(x[idx], color='r')
                ax.set_title(f"Change Point {st}")
                plt.savefig(os.path.join(out, f"F5_{st}.png"), dpi=400)
                plt.close()

    # ===================== SAVE =====================
    pd.DataFrame(T2_rows, columns=['Station','Mean','Std','Min','Max','%Missing']).to_excel(writer, sheet_name='T2', index=False)
    df_T3 = pd.DataFrame(T3_rows, columns=['Station','Period','Season','Slope','CI_low','CI_high','p','Trend','%Change'])
    df_T3['P_Value_FDR'] = fdr_bh(df_T3['p'])
    df_T3.to_excel(writer, sheet_name='T3', index=False)

    pd.DataFrame(T4_rows, columns=['Station','Season','ChangePoint','p']).to_excel(writer, sheet_name='T4', index=False)
    pd.DataFrame(T5_rows, columns=['Station','Rho1','SignificantLags']).to_excel(writer, sheet_name='T5', index=False)

    writer.close()

    print(f"✅ DONE → {out}")

if __name__ == "__main__":
    main()