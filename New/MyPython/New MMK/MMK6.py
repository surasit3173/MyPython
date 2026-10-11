#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, glob
import numpy as np
import pandas as pd
from datetime import datetime
from scipy.stats import theilslopes, norm
import pymannkendall as mk

# =========================================================
# ====================== SETTINGS ==========================
# =========================================================
ALPHA = 0.05
MIN_N = 10

# =========================================================
# ===================== UTILITIES ==========================
# =========================================================
def safe_attr(obj, names, default=np.nan):
    for n in names:
        if hasattr(obj, n):
            return getattr(obj, n)
    return default

def preprocess_series(y):
    y = np.array(y, dtype=float)
    y = y[~np.isnan(y)]
    return y

# =========================================================
# ================== CORE STATISTICS =======================
# =========================================================

def mann_kendall_stats(y):
    """
    Compute S, Var(S), tau, Z, p-value (Standard MK)
    """
    n = len(y)
    S = 0
    for i in range(n-1):
        S += np.sum(np.sign(y[i+1:] - y[i]))

    # variance (no tie correction for simplicity, acceptable for rainfall)
    var_s = n*(n-1)*(2*n+5)/18

    if S > 0:
        Z = (S - 1)/np.sqrt(var_s)
    elif S < 0:
        Z = (S + 1)/np.sqrt(var_s)
    else:
        Z = 0.0

    p = 2*(1 - norm.cdf(abs(Z)))
    tau = S / (0.5 * n * (n-1))

    return S, var_s, Z, p, tau

def modified_mk_stats(y):
    """
    Hamed & Rao (1998) variance correction
    """
    n = len(y)

    # lag-1 autocorrelation
    if n < 3:
        return np.nan, np.nan, np.nan, np.nan, np.nan

    r1 = np.corrcoef(y[:-1], y[1:])[0,1]

    # effective sample size
    neff = n * (1 - r1) / (1 + r1) if (1 + r1) != 0 else n

    S, var_s, _, _, tau = mann_kendall_stats(y)

    var_s_star = var_s * (n / neff)

    if S > 0:
        Z = (S - 1)/np.sqrt(var_s_star)
    elif S < 0:
        Z = (S + 1)/np.sqrt(var_s_star)
    else:
        Z = 0.0

    p = 2*(1 - norm.cdf(abs(Z)))

    return var_s_star, neff, Z, p, tau

def theil_sen(y):
    x = np.arange(len(y))
    slope, intercept, lo, hi = theilslopes(y, x, 0.95)
    return slope, lo, hi

def classify_trend(p, slope):
    if np.isnan(p):
        return "NA"
    if p < ALPHA:
        return "Increasing" if slope > 0 else "Decreasing"
    return "No Trend"

def significance_label(p):
    if np.isnan(p):
        return "NA"
    return "Significant" if p < ALPHA else "Not Significant"

# =========================================================
# ====================== DATA ==============================
# =========================================================
def load_data(file):
    df = pd.read_csv(file)
    stations = [c for c in df.columns if str(c).isdigit()]
    df['date'] = pd.to_datetime(df[['YEAR','MONTH','DAY']])
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    return df, stations

def get_seasonal(df, st):
    ann = df.groupby('year')[st].sum()
    wet = df[df['month'].isin([5,6,7,8,9,10])].groupby('year')[st].sum()
    dry = df[df['month'].isin([11,12,1,2,3,4])].groupby('year')[st].sum()
    return {"Annual":ann, "Wet":wet, "Dry":dry}

# =========================================================
# ====================== MAIN ==============================
# =========================================================
def main():

    files = glob.glob("*.csv")
    out = f"Q2_Table_Output_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(out, exist_ok=True)

    table2 = []
    table3 = []
    table5 = []

    for f in files:
        print("Processing:", f)
        df, stations = load_data(f)

        for st in stations:

            seasons = get_seasonal(df, st)

            t5_row = [st]

            for scale, series in seasons.items():

                y = preprocess_series(series.values)

                if len(y) < MIN_N or np.std(y) == 0:
                    continue

                # ---------- Standard MK ----------
                S, var_s, Z, p, tau = mann_kendall_stats(y)

                table2.append([
                    st, scale, var_s, len(y), p, Z, tau, p,
                    classify_trend(p, np.nan)
                ])

                # ---------- Modified MK ----------
                var_star, neff, Zm, pm, taum = modified_mk_stats(y)

                table3.append([
                    st, scale, var_star, neff, pm, Zm, taum, pm,
                    classify_trend(pm, np.nan)
                ])

                # ---------- Sen slope ----------
                slope, lo, hi = theil_sen(y)

                t5_row.extend([
                    slope,
                    pm,
                    significance_label(pm),
                    classify_trend(pm, slope)
                ])

            if len(t5_row) > 1:
                table5.append(t5_row)

    # =====================================================
    # ================= EXPORT EXCEL =======================
    # =====================================================

    writer = pd.ExcelWriter(os.path.join(out, "Trend_Tables.xlsx"),
                            engine='openpyxl')

    # Table 2
    df2 = pd.DataFrame(table2, columns=[
        "Station","Scale","Var*(S)","N",
        "p1","Z","Tau","p-value","Trend"
    ])
    df2.to_excel(writer, sheet_name="Table2_MK", index=False)

    # Table 3
    df3 = pd.DataFrame(table3, columns=[
        "Station","Scale","Var*(S)","NEff",
        "p1","Z","Tau","p-value","Trend"
    ])
    df3.to_excel(writer, sheet_name="Table3_MMK", index=False)

    # Table 5
    df5 = pd.DataFrame(table5, columns=[
        "Station",
        "Annual_Slope","Annual_p","Annual_Sig","Annual_Trend",
        "Wet_Slope","Wet_p","Wet_Sig","Wet_Trend",
        "Dry_Slope","Dry_p","Dry_Sig","Dry_Trend"
    ])
    df5.to_excel(writer, sheet_name="Table5_Summary", index=False)

    writer.close()

    print("\n✅ DONE (Q2 Tables Ready)")
    print("📁 Output:", out)

# =========================================================
if __name__ == "__main__":
    main()