"""ENSO episode and management-season classification."""

from __future__ import annotations

import numpy as np
import pandas as pd


def parse_noaa_oni_html(path) -> pd.DataFrame:
    """Parse the frozen CPC ERSSTv6 ONI table into centred monthly windows."""
    selected = None
    for table in pd.read_html(path):
        if table.shape[1] >= 13 and str(table.iloc[0, 0]).strip() == "Year":
            selected = table.copy()
            break
    if selected is None:
        raise ValueError("NOAA ONI table was not found in the frozen HTML")
    selected.columns = [str(value).strip() for value in selected.iloc[0]]
    selected = selected.iloc[1:].copy()
    selected["Year"] = pd.to_numeric(selected["Year"], errors="coerce")
    selected = selected.dropna(subset=["Year"])
    selected["Year"] = selected["Year"].astype(int)
    seasons = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
    rows = []
    for record in selected.itertuples(index=False):
        year = int(record[0])
        for month, season in enumerate(seasons, start=1):
            value = pd.to_numeric(record[month], errors="coerce")
            if pd.isna(value):
                continue
            rows.append(
                {"date": pd.Timestamp(year=year, month=month, day=1),
                 "season": season, "oni_c": float(value)}
            )
    output = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    output["episode_sign"] = persistent_episode_sign(
        output.set_index("date")["oni_c"], threshold=0.5, minimum_run=5
    ).to_numpy(dtype="int8")
    output["episode_phase"] = output["episode_sign"].map(
        {-1: "LA_NINA", 0: "NO_PERSISTENT_EPISODE", 1: "EL_NINO"}
    )
    return output


def persistent_episode_sign(
    index: pd.Series, *, threshold: float = 0.5, minimum_run: int = 5
) -> pd.Series:
    """Label only threshold runs satisfying the overlapping-season duration rule."""
    values = index.astype(float)
    candidate = pd.Series(
        np.where(values >= threshold, 1, np.where(values <= -threshold, -1, 0)),
        index=values.index,
        dtype="int8",
    )
    episode = pd.Series(0, index=values.index, dtype="int8")
    groups = candidate.ne(candidate.shift()).cumsum()
    for _, positions in candidate.groupby(groups).groups.items():
        locs = list(positions)
        sign = int(candidate.loc[locs[0]])
        if sign != 0 and len(locs) >= minimum_run:
            episode.loc[locs] = sign
    return episode


def classify_management_seasons(
    index: pd.DataFrame, *, climate_years, index_column: str = "index_c"
) -> pd.DataFrame:
    """Classify management seasons by strict-majority persistent membership."""
    required = {index_column, "episode_sign"}
    missing = required.difference(index.columns)
    if missing:
        raise KeyError(f"ENSO index is missing columns: {sorted(missing)}")
    if not isinstance(index.index, pd.DatetimeIndex):
        raise TypeError("ENSO index must use a DatetimeIndex at 3-month-window centres")

    rows = []
    windows = []
    for date in index.index:
        period = date.to_period("M")
        windows.append(((period - 1).start_time, (period + 1).end_time))

    for climate_year in climate_years:
        definitions = (
            ("RAINY", pd.Timestamp(climate_year, 5, 1), pd.Timestamp(climate_year, 10, 31)),
            ("HOT_DRY", pd.Timestamp(climate_year, 11, 1), pd.Timestamp(climate_year + 1, 4, 30)),
        )
        for season_type, season_start, season_end in definitions:
            overlap = np.array(
                [start <= season_end and end >= season_start for start, end in windows],
                dtype=bool,
            )
            evidence = index.loc[overlap]
            n = int(len(evidence))
            n_el = int((evidence["episode_sign"] == 1).sum())
            n_la = int((evidence["episode_sign"] == -1).sum())
            if n_el > n / 2:
                phase = "EL_NINO"
            elif n_la > n / 2:
                phase = "LA_NINA"
            elif n_el == 0 and n_la == 0 and n > 0:
                phase = "NEUTRAL"
            else:
                phase = "TRANSITION_UNCLASSIFIED"
            values = evidence[index_column].astype(float)
            rows.append(
                {
                    "season_type": season_type,
                    "climate_year": int(climate_year),
                    "season_start": season_start,
                    "season_end": season_end,
                    "enso_phase": phase,
                    "index_mean_c": float(values.mean()) if n else np.nan,
                    "index_min_c": float(values.min()) if n else np.nan,
                    "index_max_c": float(values.max()) if n else np.nan,
                    "n_overlapping_windows": n,
                    "n_el_nino_windows": n_el,
                    "n_la_nina_windows": n_la,
                    "n_neutral_windows": int(n - n_el - n_la),
                    "classification_rule": "strict majority of overlapping persistent episode windows",
                }
            )
    return pd.DataFrame(rows)


def episode_catalog(
    index: pd.DataFrame,
    *,
    source_name: str,
    index_column: str,
    threshold_c: float,
    persistence_seasons: int,
) -> pd.DataFrame:
    """Collapse persistent monthly-window membership into traceable episodes."""
    if not isinstance(index.index, pd.DatetimeIndex):
        raise TypeError("ENSO index must use a DatetimeIndex")
    if "episode_sign" not in index or index_column not in index:
        raise KeyError("ENSO index needs episode_sign and the requested index column")
    ordered = index.sort_index()
    groups = ordered["episode_sign"].ne(ordered["episode_sign"].shift()).cumsum()
    rows = []
    counter = {1: 0, -1: 0}
    for _, group in ordered.groupby(groups):
        sign = int(group["episode_sign"].iloc[0])
        if sign == 0:
            continue
        counter[sign] += 1
        phase = "EL_NINO" if sign == 1 else "LA_NINA"
        prefix = "EN" if sign == 1 else "LN"
        rows.append(
            {
                "episode_id": f"{prefix}_{counter[sign]:02d}",
                "phase": phase,
                "start_center_month": group.index.min(),
                "end_center_month": group.index.max(),
                "n_consecutive_overlapping_seasons": int(len(group)),
                "index_mean_c": float(group[index_column].mean()),
                "index_min_c": float(group[index_column].min()),
                "index_max_c": float(group[index_column].max()),
                "threshold_c": float(threshold_c),
                "persistence_seasons": int(persistence_seasons),
                "source": source_name,
            }
        )
    return pd.DataFrame(rows)
