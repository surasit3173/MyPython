import pandas as pd
import numpy as np

def parse_noaa_oni(oni_html_path, threshold_c=0.5, persistence_windows=5):
    """Parse NOAA CPC ONI HTML table and label persistent ENSO episodes."""
    tables = pd.read_html(oni_html_path)
    selected = None
    for table in tables:
        if table.shape[1] >= 13 and str(table.iloc[0, 0]).strip() == "Year":
            selected = table.copy()
            break
    if selected is None:
        raise ValueError("NOAA ONI table not found in HTML")

    selected.columns = [str(v).strip() for v in selected.iloc[0]]
    selected = selected.iloc[1:].copy()
    selected["Year"] = pd.to_numeric(selected["Year"], errors="coerce")
    selected = selected.dropna(subset=["Year"])
    selected["Year"] = selected["Year"].astype(int)

    seasons_list = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
    rows = []
    for record in selected.itertuples(index=False):
        yr = int(record[0])
        for month, season_name in enumerate(seasons_list, start=1):
            val = pd.to_numeric(record[month], errors="coerce")
            if pd.isna(val): continue
            rows.append({"date": pd.Timestamp(year=yr, month=month, day=1), "season": season_name, "oni_c": float(val)})

    df_oni = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)

    vals = df_oni["oni_c"].to_numpy()
    cand = np.where(vals >= threshold_c, 1, np.where(vals <= -threshold_c, -1, 0))
    ep = np.zeros(len(cand), dtype=int)

    i, n = 0, len(cand)
    while i < n:
        if cand[i] == 0:
            i += 1
            continue
        j = i
        while j < n and cand[j] == cand[i]:
            j += 1
        if (j - i) >= persistence_windows:
            ep[i:j] = cand[i]
        i = j

    df_oni["episode_sign"] = ep
    df_oni["episode_phase"] = df_oni["episode_sign"].map({-1: "LA_NINA", 0: "NEUTRAL", 1: "EL_NINO"})
    return df_oni

def classify_management_seasons(df_oni, date_start=1981, date_end=2014):
    """Classify Rainy (May-Oct) and Hot/Dry (Nov-Apr cross-year) management seasons."""
    windows = []
    for d in df_oni["date"]:
        p = d.to_period("M")
        windows.append(((p - 1).start_time, (p + 1).end_time))

    season_rows = []
    for cy in range(date_start, date_end + 1):
        r_start, r_end = pd.Timestamp(cy, 5, 1), pd.Timestamp(cy, 10, 31)
        hd_start, hd_end = pd.Timestamp(cy, 11, 1), pd.Timestamp(cy + 1, 4, 30)

        for stype, sstart, send in [("RAINY", r_start, r_end), ("HOT_DRY", hd_start, hd_end)]:
            if stype == "HOT_DRY" and cy == date_end:
                continue # Exclude incomplete season

            overlap = [wstart <= send and wend >= sstart for wstart, wend in windows]
            sub = df_oni[overlap]
            n_win = len(sub)
            n_el = (sub["episode_sign"] == 1).sum()
            n_la = (sub["episode_sign"] == -1).sum()
            if n_el > n_win / 2:
                phase = "EL_NINO"
            elif n_la > n_win / 2:
                phase = "LA_NINA"
            elif n_el == 0 and n_la == 0:
                phase = "NEUTRAL"
            else:
                phase = "TRANSITION_UNCLASSIFIED"

            season_rows.append({
                "season_type": stype,
                "climate_year": cy,
                "season_start": sstart.strftime("%Y-%m-%d"),
                "season_end": send.strftime("%Y-%m-%d"),
                "enso_phase": phase,
                "oni_mean_c": float(sub["oni_c"].mean()),
                "n_overlapping_windows": n_win,
                "n_el_nino_windows": int(n_el),
                "n_la_nina_windows": int(n_la),
                "n_neutral_windows": int(n_win - n_el - n_la)
            })
    return pd.DataFrame(season_rows)
