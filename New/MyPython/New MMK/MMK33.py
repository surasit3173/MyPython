# -*- coding: utf-8 -*-
"""
===============================================================================
Q2-Q3 Standard Rainfall Trend Analysis
- Standard MK + Modified MK (Hamed & Rao)
- Theil–Sen slope + 95% CI
- Seasonal (Annual / Wet / Dry)
- Table 2, Table 3, Table 5 (ตามที่ต้องการ)
===============================================================================
"""

import os, glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import norm, theilslopes
import pymannkendall as mk

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.labelsize": 12
})

# ========================= CORE =========================
def sen_slope(x, y):
    """Theil-Sen Estimator"""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    slope, intercept, lo, hi = theilslopes(y, x, alpha=0.05)
    return slope, lo, hi

def standard_mk(y):
    """Standard Mann-Kendall"""
    n = len(y)
    S = sum(np.sum(np.sign(y[i+1:] - y[i])) for i in range(n-1))
    var_s = n*(n-1)*(2*n+5)/18.0
    Z = (S-1)/np.sqrt(var_s) if S > 0 else (S+1)/np.sqrt(var_s) if S < 0 else 0
    p = 2*(1 - norm.cdf(abs(Z)))
    return S, var_s, Z, p

def modified_mk(y):
    """Modified MK with Hamed & Rao"""
    n = len(y)
    r1 = np.corrcoef(y[:-1], y[1:])[0,1]
    ne = n * (1 - r1) / (1 + r1) if (1 + r1) != 0 else n

    S, var_s, _, _ = standard_mk(y)
    var_mod = var_s * (n / ne)

    Z = (S-1)/np.sqrt(var_mod) if S > 0 else (S+1)/np.sqrt(var_mod) if S < 0 else 0
    p = 2*(1 - norm.cdf(abs(Z)))
    return Z, p, r1, var_mod, ne

# ========================= LOAD =========================
def load(f):
    df = pd.read_csv(f)
    st = [c for c in df.columns if str(c).isdigit()]
    df['date'] = pd.to_datetime(df[['YEAR','MONTH','DAY']])
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    return df, st

def split_season(df, st):
    ann = df.groupby('year')[st].sum()
    wet = df[df['month'].isin([5,6,7,8,9,10])].groupby('year')[st].sum()
    dry = df[df['month'].isin([11,12,1,2,3,4])].groupby('year')[st].sum()
    return {"Annual": ann, "Wet": wet, "Dry": dry}

# ========================= MAIN =========================
def main():
    files = glob.glob("*.csv")
    out = "Q2_MK_MMK_Results"
    os.makedirs(out, exist_ok=True)

    table2 = []
    table3 = []
    table5 = []

    for f in files:
        print(f"Processing: {f}")
        df, stations = load(f)

        for st in stations:
            seasons = split_season(df, st)

            for s_name, series in seasons.items():
                series = series.dropna()
                if len(series) < 10:
                    continue

                years = series.index.values
                values = series.values

                # Sen's Slope + CI
                slope, lo, hi = sen_slope(years, values)

                # Standard MK
                S, var_s, Z, p_mk = standard_mk(values)

                # Modified MK
                Z_mmk, p_mmk, r1, var_mod, neff = modified_mk(values)

                trend_mk = "Increasing" if Z > 0 else "Decreasing" if Z < 0 else "No trend"
                trend_mmk = "Increasing" if Z_mmk > 0 else "Decreasing" if Z_mmk < 0 else "No trend"

                # Table 2: Standard MK
                table2.append([st, s_name, len(years), S, var_s, Z, round(Z/ (len(years)*(len(years)-1)/2), 4), p_mk, trend_mk])

                # Table 3: Modified MK
                table3.append([st, s_name, var_mod, round(neff, 2), r1, Z_mmk, round(Z_mmk / (len(years)*(len(years)-1)/2), 4), p_mmk, trend_mmk])

                # Table 5: Summary
                table5.append([st, s_name, slope, p_mmk, "Yes" if p_mmk < 0.05 else "No", trend_mmk])

    # ====================== EXPORT ======================
    df2 = pd.DataFrame(table2, columns=["Station", "Scale", "N", "S", "Var(S)", "Z", "τ (Kendall)", "p-value", "Trend"])
    df3 = pd.DataFrame(table3, columns=["Station", "Scale", "Var*(S)", "N_eff", "p1", "Z", "τ (Kendall)", "p-value", "Trend"])
    df5 = pd.DataFrame(table5, columns=["Station", "Scale", "Sen's Slope (mm/yr)", "p-value", "Significant", "Trend"])

    with pd.ExcelWriter(os.path.join(out, "Trend_Tables.xlsx")) as writer:
        df2.to_excel(writer, sheet_name="Table2_MK", index=False)
        df3.to_excel(writer, sheet_name="Table3_MMK", index=False)
        df5.to_excel(writer, sheet_name="Table5_Summary", index=False)

    print(f"\n✅ DONE → Results saved in folder: {out}")
    print("   • Table2_MK: Standard Mann-Kendall")
    print("   • Table3_MMK: Modified Mann-Kendall")
    print("   • Table5_Summary: Sen’s Slope + Significance")

if __name__ == "__main__":
    main()