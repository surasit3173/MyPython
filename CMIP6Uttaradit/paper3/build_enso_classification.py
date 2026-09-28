import os
import sys
import json
import hashlib
import requests
import datetime
import pandas as pd
import numpy as np

def build_enso():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    paper3_dir = os.path.join(repo_root, "CMIP6Uttaradit", "paper3")

    # 1. Download & Pin NOAA PSL ONI Data
    oni_url = "https://psl.noaa.gov/data/correlation/oni.data"
    raw_path = os.path.join(paper3_dir, "oni.data")

    response = requests.get(oni_url, timeout=15)
    if response.status_code == 200:
        oni_content = response.text
        with open(raw_path, "w") as f:
            f.write(oni_content)
    else:
        with open(raw_path, "r") as f:
            oni_content = f.read()

    sha256_hash = hashlib.sha256(oni_content.encode('utf-8')).hexdigest()
    access_date = datetime.date.today().isoformat()

    # Save ONI provenance
    provenance = {
        "source": "NOAA Physical Sciences Laboratory (PSL) ONI Mirror",
        "url": oni_url,
        "access_date": access_date,
        "sha256": sha256_hash,
        "local_file": "oni.data",
        "threshold_c": 0.5,
        "persistence_seasons": 5
    }
    with open(os.path.join(paper3_dir, "oni_provenance.json"), "w") as f:
        json.dump(provenance, f, indent=2)

    # 2. Parse ONI Data into pandas DataFrame
    # Format of oni.data:
    # Header line with start_year end_year
    # Year JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC
    lines = oni_content.strip().split('\n')
    data_lines = []
    for line in lines:
        parts = line.strip().split()
        if len(parts) == 13 and parts[0].isdigit() and len(parts[0]) == 4:
            year = int(parts[0])
            if 1950 <= year <= 2026:
                vals = [float(p) for p in parts[1:]]
                data_lines.append([year] + vals)

    months = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
    # In ONI monthly table columns 1-12 correspond to 3-month running periods ending in each month:
    # Col 1 (Jan) = DJF, Col 2 (Feb) = JFM, ..., Col 12 (Dec) = NDJ.
    oni_df = pd.DataFrame(data_lines, columns=["YEAR"] + list(range(1, 13)))

    # Save long format monthly ONI
    records = []
    for idx, row in oni_df.iterrows():
        yr = int(row["YEAR"])
        for m in range(1, 13):
            val = row[m]
            if val != -99.99 and val != -99.90:
                records.append({
                    "YEAR": yr,
                    "MONTH": m,
                    "SEASON_LABEL": months[m-1],
                    "ONI": val
                })
    oni_long = pd.DataFrame(records)
    oni_long.to_csv(os.path.join(paper3_dir, "enso_raw_source.csv"), index=False)

    # 3. Identify Official ENSO Episodes (5 consecutive overlapping seasons >= +0.5 or <= -0.5)
    # Sort chronologically
    oni_long['TIME_IDX'] = oni_long['YEAR'] * 12 + oni_long['MONTH']
    oni_long = oni_long.sort_values('TIME_IDX').reset_index(drop=True)

    episodes = []
    curr_phase = None
    curr_start_idx = None
    count = 0

    for i, row in oni_long.iterrows():
        val = row['ONI']
        if val >= 0.5:
            phase = "EL_NINO"
        elif val <= -0.5:
            phase = "LA_NINA"
        else:
            phase = "NEUTRAL"

        if phase == curr_phase and phase != "NEUTRAL":
            count += 1
        else:
            if curr_phase in ["EL_NINO", "LA_NINA"] and count >= 5:
                episodes.append({
                    "episode_id": f"EP_{len(episodes)+1:03d}_{curr_phase}",
                    "phase": curr_phase,
                    "start_year": oni_long.loc[curr_start_idx, "YEAR"],
                    "start_month": oni_long.loc[curr_start_idx, "MONTH"],
                    "start_season": oni_long.loc[curr_start_idx, "SEASON_LABEL"],
                    "end_year": oni_long.loc[i-1, "YEAR"],
                    "end_month": oni_long.loc[i-1, "MONTH"],
                    "end_season": oni_long.loc[i-1, "SEASON_LABEL"],
                    "duration_seasons": count,
                    "threshold": 0.5,
                    "persistence_rule": 5,
                    "ONI_version": "NOAA_PSL_2026",
                    "source_url": oni_url,
                    "source_hash": sha256_hash
                })
            curr_phase = phase
            curr_start_idx = i
            count = 1 if phase != "NEUTRAL" else 0

    if curr_phase in ["EL_NINO", "LA_NINA"] and count >= 5:
        episodes.append({
            "episode_id": f"EP_{len(episodes)+1:03d}_{curr_phase}",
            "phase": curr_phase,
            "start_year": oni_long.loc[curr_start_idx, "YEAR"],
            "start_month": oni_long.loc[curr_start_idx, "MONTH"],
            "start_season": oni_long.loc[curr_start_idx, "SEASON_LABEL"],
            "end_year": oni_long.loc[len(oni_long)-1, "YEAR"],
            "end_month": oni_long.loc[len(oni_long)-1, "MONTH"],
            "end_season": oni_long.loc[len(oni_long)-1, "SEASON_LABEL"],
            "duration_seasons": count,
            "threshold": 0.5,
            "persistence_rule": 5,
            "ONI_version": "NOAA_PSL_2026",
            "source_url": oni_url,
            "source_hash": sha256_hash
        })

    ep_df = pd.DataFrame(episodes)
    ep_df.to_csv(os.path.join(paper3_dir, "enso_episode_catalog.csv"), index=False)

    # 4. Classify Management-Oriented Seasons (1995–2014)
    # Seasons:
    # Rainy: May-October (months 5,6,7,8,9,10)
    # Hot/Dry: November-April (months 11,12 of yr t, 1,2,3,4 of yr t+1)

    season_classifications = []
    sensitivity_classifications = []

    # Common overlap period: 1995 to 2014 (20 rainy seasons, 20 hot/dry seasons)
    years = list(range(1995, 2015))

    for yr in years:
        # A. Rainy Season (May - Oct of yr)
        # Months in ONI dataframe corresponding to May-Oct (months 5 to 10)
        r_oni = oni_long[(oni_long['YEAR'] == yr) & (oni_long['MONTH'].isin([5,6,7,8,9,10]))]['ONI'].values
        r_mean_oni = float(np.mean(r_oni))
        r_min_oni = float(np.min(r_oni))
        r_max_oni = float(np.max(r_oni))

        # Check episode overlap: how many months of May-Oct are in an official El Nino / La Nina episode?
        el_nino_count = 0
        la_nina_count = 0
        for m in [5,6,7,8,9,10]:
            # check if (yr, m) is inside any episode
            for _, ep in ep_df.iterrows():
                s_idx = ep['start_year'] * 12 + ep['start_month']
                e_idx = ep['end_year'] * 12 + ep['end_month']
                curr_idx = yr * 12 + m
                if s_idx <= curr_idx <= e_idx:
                    if ep['phase'] == 'EL_NINO':
                        el_nino_count += 1
                    elif ep['phase'] == 'LA_NINA':
                        la_nina_count += 1

        if el_nino_count >= 4 and la_nina_count == 0:
            primary_phase = "EL_NINO"
        elif la_nina_count >= 4 and el_nino_count == 0:
            primary_phase = "LA_NINA"
        elif el_nino_count == 0 and la_nina_count == 0 and abs(r_mean_oni) < 0.5:
            primary_phase = "NEUTRAL"
        else:
            primary_phase = "TRANSITION_UNCLASSIFIED"

        # Sensitivity rule: mean ONI threshold >= +0.5 -> EL_NINO, <= -0.5 -> LA_NINA, else NEUTRAL
        if r_mean_oni >= 0.5:
            sens_phase = "EL_NINO"
        elif r_mean_oni <= -0.5:
            sens_phase = "LA_NINA"
        else:
            sens_phase = "NEUTRAL"

        season_classifications.append({
            "season_id": f"{yr}_RAIN",
            "climate_year": yr,
            "season_type": "RAINY",
            "season_start": f"{yr}-05-01",
            "season_end": f"{yr}-10-31",
            "ENSO_phase": primary_phase,
            "ONI_mean": round(r_mean_oni, 3),
            "ONI_min": round(r_min_oni, 3),
            "ONI_max": round(r_max_oni, 3),
            "n_months": len(r_oni),
            "el_nino_months": el_nino_count,
            "la_nina_months": la_nina_count,
            "classification_rule": "Episode_Overlap_>=4_months"
        })

        sensitivity_classifications.append({
            "season_id": f"{yr}_RAIN",
            "primary_phase": primary_phase,
            "sensitivity_phase": sens_phase,
            "changed": (primary_phase != sens_phase)
        })

        # B. Hot/Dry Season (Nov of yr to Apr of yr+1)
        # Note: 2014_2015_HOT_DRY ends on 2015-04-30, exceeding 2014-12-31 observed data end date.
        # To satisfy D1 seasonal completeness, incomplete Hot/Dry 2014/15 is excluded from classification.
        if yr == 2014:
            continue
        # Nov, Dec of yr; Jan, Feb, Mar, Apr of yr+1
        hd_oni_records = []
        for m in [11, 12]:
            sub = oni_long[(oni_long['YEAR'] == yr) & (oni_long['MONTH'] == m)]
            if len(sub) > 0:
                hd_oni_records.append(sub.iloc[0])
        for m in [1, 2, 3, 4]:
            sub = oni_long[(oni_long['YEAR'] == yr + 1) & (oni_long['MONTH'] == m)]
            if len(sub) > 0:
                hd_oni_records.append(sub.iloc[0])

        hd_oni_df = pd.DataFrame(hd_oni_records)
        hd_oni = hd_oni_df['ONI'].values
        hd_mean_oni = float(np.mean(hd_oni))
        hd_min_oni = float(np.min(hd_oni))
        hd_max_oni = float(np.max(hd_oni))

        el_nino_count = 0
        la_nina_count = 0
        for _, row in hd_oni_df.iterrows():
            c_yr = int(row['YEAR'])
            c_m = int(row['MONTH'])
            curr_idx = c_yr * 12 + c_m
            for _, ep in ep_df.iterrows():
                s_idx = ep['start_year'] * 12 + ep['start_month']
                e_idx = ep['end_year'] * 12 + ep['end_month']
                if s_idx <= curr_idx <= e_idx:
                    if ep['phase'] == 'EL_NINO':
                        el_nino_count += 1
                    elif ep['phase'] == 'LA_NINA':
                        la_nina_count += 1

        if el_nino_count >= 4 and la_nina_count == 0:
            primary_phase = "EL_NINO"
        elif la_nina_count >= 4 and el_nino_count == 0:
            primary_phase = "LA_NINA"
        elif el_nino_count == 0 and la_nina_count == 0 and abs(hd_mean_oni) < 0.5:
            primary_phase = "NEUTRAL"
        else:
            primary_phase = "TRANSITION_UNCLASSIFIED"

        if hd_mean_oni >= 0.5:
            sens_phase = "EL_NINO"
        elif hd_mean_oni <= -0.5:
            sens_phase = "LA_NINA"
        else:
            sens_phase = "NEUTRAL"

        season_classifications.append({
            "season_id": f"{yr}_{yr+1:02d}_HOT_DRY",
            "climate_year": yr,
            "season_type": "HOT_DRY",
            "season_start": f"{yr}-11-01",
            "season_end": f"{yr+1}-04-30",
            "ENSO_phase": primary_phase,
            "ONI_mean": round(hd_mean_oni, 3),
            "ONI_min": round(hd_min_oni, 3),
            "ONI_max": round(hd_max_oni, 3),
            "n_months": len(hd_oni),
            "el_nino_months": el_nino_count,
            "la_nina_months": la_nina_count,
            "classification_rule": "Episode_Overlap_>=4_months"
        })

        sensitivity_classifications.append({
            "season_id": f"{yr}_{yr+1:02d}_HOT_DRY",
            "primary_phase": primary_phase,
            "sensitivity_phase": sens_phase,
            "changed": (primary_phase != sens_phase)
        })

    class_df = pd.DataFrame(season_classifications)
    class_df.to_csv(os.path.join(paper3_dir, "enso_season_classification.csv"), index=False)

    sens_df = pd.DataFrame(sensitivity_classifications)
    sens_df.to_csv(os.path.join(paper3_dir, "enso_classification_sensitivity.csv"), index=False)

    # 5. Build Sample Sizes Summary
    sample_sizes = class_df.groupby(['season_type', 'ENSO_phase']).size().reset_index(name='n_seasons')
    sample_sizes.to_csv(os.path.join(paper3_dir, "enso_sample_sizes.csv"), index=False)

    print("ENSO classification completed successfully.")
    print("Sample sizes summary:")
    print(sample_sizes)

if __name__ == "__main__":
    build_enso()
