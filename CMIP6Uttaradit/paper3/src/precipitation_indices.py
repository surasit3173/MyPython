import pandas as pd
import numpy as np

def compute_seasonal_indices(df_daily, df_seasons, stations):
    """Compute seasonal climate & extreme precipitation indices for requested stations."""
    if "date" not in df_daily.columns:
        df_daily["date"] = pd.to_datetime(df_daily[["YEAR", "MONTH", "DAY"]])
    df_daily = df_daily.set_index("date").sort_index()

    # Filter stations to only those present in df_daily
    available_stations = [s for s in stations if s in df_daily.columns]

    p95_dict = {}
    p99_dict = {}
    for s in available_stations:
        wet = df_daily[s][df_daily[s] >= 1.0]
        p95_dict[s] = wet.quantile(0.95) if len(wet) > 0 else 0.0
        p99_dict[s] = wet.quantile(0.99) if len(wet) > 0 else 0.0

    results = []
    for _, srow in df_seasons.iterrows():
        stype = srow["season_type"]
        cy = srow["climate_year"]
        phase = srow["enso_phase"]
        sstart = pd.Timestamp(srow["season_start"])
        send = pd.Timestamp(srow["season_end"])

        sub = df_daily.loc[sstart:send]
        if sub.empty: continue

        for sta in available_stations:
            vals = sub[sta].to_numpy(dtype=float)

            prcptot = np.sum(vals)
            rx1day = np.max(vals) if len(vals) > 0 else 0.0
            rx5day = np.max(pd.Series(vals).rolling(5).sum().dropna().to_numpy()) if len(vals) >= 5 else rx1day

            wet_vals = vals[vals >= 1.0]
            sdii = np.mean(wet_vals) if len(wet_vals) > 0 else 0.0

            r95p = np.sum(vals[vals > p95_dict[sta]])
            r99p = np.sum(vals[vals > p99_dict[sta]])

            wet_mask = (vals >= 1.0).astype(int)
            cwd, cdd = 0, 0
            curr_w, curr_d = 0, 0
            for w in wet_mask:
                if w == 1:
                    curr_w += 1
                    curr_d = 0
                    if curr_w > cwd: cwd = curr_w
                else:
                    curr_d += 1
                    curr_w = 0
                    if curr_d > cdd: cdd = curr_d

            results.append({
                "season_type": stype,
                "climate_year": cy,
                "enso_phase": phase,
                "station": sta,
                "PRCPTOT": prcptot,
                "Rx1day": rx1day,
                "Rx5day": rx5day,
                "SDII": sdii,
                "R95p": r95p,
                "R99p": r99p,
                "CWD": cwd,
                "CDD": cdd
            })

    return pd.DataFrame(results)
