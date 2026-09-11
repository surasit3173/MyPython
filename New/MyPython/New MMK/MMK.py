#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, glob
import numpy as np
import pandas as pd
from scipy.stats import norm
from datetime import datetime

# ====================== Sen's slope ======================
def sen_slope(x, y):
    slopes = []
    n = len(x)
    for i in range(n):
        for j in range(i+1, n):
            if x[j] != x[i]:
                slopes.append((y[j] - y[i]) / (x[j] - x[i]))
    return np.median(slopes)

# ====================== Standard MK ======================
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

    return S, Z, p, var_S

# ====================== Autocorrelation ======================
def autocorr(x, lag):
    return np.corrcoef(x[:-lag], x[lag:])[0,1]

# ====================== Modified MK ======================
def modified_mk(y):
    n = len(y)

    # lag-1 autocorrelation
    r1 = autocorr(y, 1)

    # effective sample size (Hamed & Rao, 1998)
    ne = n * (1 - r1) / (1 + r1) if (1 + r1) != 0 else n

    S, _, _, var_S = mann_kendall(y)

    var_S_mod = var_S * (n / ne)

    if S > 0:
        Z = (S - 1)/np.sqrt(var_S_mod)
    elif S < 0:
        Z = (S + 1)/np.sqrt(var_S_mod)
    else:
        Z = 0

    p = 2*(1 - norm.cdf(abs(Z)))

    return Z, p, var_S_mod, r1

# ====================== LOAD ======================
def load_data(file):
    df = pd.read_csv(file)
    station_cols = [c for c in df.columns if str(c).isdigit()]
    df['date'] = pd.to_datetime(df[['YEAR','MONTH','DAY']])
    df['year'] = df['date'].dt.year
    return df, station_cols

# ====================== ANNUAL ======================
def annual_series(df, station):
    return df.groupby('year')[station].sum()

# ====================== MAIN ======================
def main():

    files = glob.glob("*.csv")
    out = f"MK_Results_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(out, exist_ok=True)

    writer = pd.ExcelWriter(os.path.join(out, "MK_Station_Analysis.xlsx"), engine='openpyxl')

    summary_rows = []

    for file in files:

        print(f"Processing: {file}")

        df, stations = load_data(file)

        station_results = []

        for st in stations:

            series = annual_series(df, st).dropna()

            if len(series) < 10:
                continue

            years = series.index.values
            values = series.values

            slope = sen_slope(years, values)

            # Standard MK
            S, Z, p, var_S = mann_kendall(values)

            # Modified MK
            Zm, pm, var_mod, r1 = modified_mk(values)

            trend_mk = "Increasing" if Z > 0 else "Decreasing" if Z < 0 else "No trend"
            trend_mmk = "Increasing" if Zm > 0 else "Decreasing" if Zm < 0 else "No trend"

            station_results.append([
                st,
                slope,
                Z, p,
                Zm, pm,
                r1,
                trend_mk,
                trend_mmk
            ])

            summary_rows.append([
                file,
                st,
                slope,
                p,
                pm,
                trend_mk,
                trend_mmk
            ])

        df_station = pd.DataFrame(station_results, columns=[
            'Station',
            "Sen’s slope",
            'Z (MK)', 'p-value (MK)',
            'Z (MMK)', 'p-value (MMK)',
            'Lag-1 autocorrelation',
            'Trend (MK)',
            'Trend (MMK)'
        ])

        sheet_name = os.path.basename(file)[:30]
        df_station.to_excel(writer, sheet_name=sheet_name, index=False)

    # ====================== SUMMARY ======================
    summary_df = pd.DataFrame(summary_rows, columns=[
        'Dataset','Station',"Sen’s slope",
        'p-value (MK)','p-value (MMK)',
        'Trend (MK)','Trend (MMK)'
    ])

    # comparison
    summary_df['Difference'] = summary_df['Trend (MK)'] != summary_df['Trend (MMK)']

    summary_df.to_excel(writer, sheet_name='Summary', index=False)

    writer.close()

    print(f"\n✅ DONE → {out}")

if __name__ == "__main__":
    main()