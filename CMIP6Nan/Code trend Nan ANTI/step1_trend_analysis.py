#!/usr/bin/env python3
"""
Rainfall Trend Analysis for Nan Province, Thailand
Full analysis: 1981-2100 (Observed + CMIP6 historical + future)
Methods: Mann-Kendall, Sen's Slope, Spearman's Rho, ITA
Seasons: Wet (May-Oct), Dry (Nov-Apr of following year)
Author: Surasit Punyawansiri
"""

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from pathlib import Path
import pymannkendall as mk
from scipy import stats
import json

# ─── Paths ──────────────────────────────────────────────────────────────────
BASE   = Path(r'C:\MyPython\CMIP6Nan')
OBS_F  = BASE / 'cmip6_framework' / 'data' / 'observed' / 'Observed_Rain_daily_198101_201412_Nan.csv'
CMIP6  = BASE / 'CMIP6'
STA_F  = BASE / 'Station_latitude_longitude.csv'
OUT    = BASE / 'trend_analysis_output'
OUT.mkdir(exist_ok=True)

# ─── Station list ────────────────────────────────────────────────────────────
sta_df   = pd.read_csv(STA_F)
NAN_STA  = [str(s) for s in sta_df['Station_ID'].tolist()]
print(f"Nan stations ({len(NAN_STA)}): {NAN_STA}")

# ─── Models and scenarios ─────────────────────────────────────────────────
MODELS   = ['ACCESS-ESM1-5','CESM2','CanESM5','EC-Earth3',
            'FGOALS-g3','MIROC6','MRI-ESM2-0']
SCENARIOS= ['ssp245','ssp585']

# ─── Season helper ──────────────────────────────────────────────────────────
def assign_season(month, year):
    """Wet: May-Oct; Dry: Nov(year N)-Apr(year N+1) -> assigned to year N."""
    if 5 <= month <= 10:
        return year, 'Wet'
    elif month >= 11:
        return year, 'Dry'
    else:  # Jan-Apr -> belongs to previous Dry season (year-1)
        return year - 1, 'Dry'

def add_season_cols(df_daily):
    """Add season_year and season columns to a daily DataFrame with YEAR/MONTH/DAY."""
    rows = []
    for _, r in df_daily[['YEAR','MONTH']].iterrows():
        sy, sn = assign_season(int(r['MONTH']), int(r['YEAR']))
        rows.append({'season_year': sy, 'season': sn})
    return pd.concat([df_daily.reset_index(drop=True),
                      pd.DataFrame(rows)], axis=1)

# ─── Load observed data ──────────────────────────────────────────────────────
print("\n=== Loading Observed Data ===")
obs_raw = pd.read_csv(OBS_F)
obs_cols = [c for c in obs_raw.columns if c in NAN_STA]
obs_raw  = obs_raw[['YEAR','MONTH','DAY'] + obs_cols].copy()
obs_raw  = add_season_cols(obs_raw)

# Annual sum per station
obs_annual = (obs_raw.groupby('YEAR')[obs_cols]
              .sum().reset_index().rename(columns={'YEAR':'year'}))
obs_annual['type'] = 'observed'

# Seasonal sum
obs_wet = (obs_raw[obs_raw['season']=='Wet']
           .groupby('season_year')[obs_cols].sum().reset_index()
           .rename(columns={'season_year':'year'}))
obs_dry = (obs_raw[obs_raw['season']=='Dry']
           .groupby('season_year')[obs_cols].sum().reset_index()
           .rename(columns={'season_year':'year'}))

# Trim dry season to valid years (need full Nov-Apr)
obs_dry = obs_dry[(obs_dry['year'] >= 1981) & (obs_dry['year'] <= 2013)]

print(f"  Obs annual: {obs_annual['year'].min()}–{obs_annual['year'].max()}, n={len(obs_annual)}")

# ─── Load CMIP6 bias-corrected data ─────────────────────────────────────────
def load_bc_model(model, scenario):
    """Load historical + scenario BC data, return daily DataFrame."""
    hist_pat = list((CMIP6 / model).glob(f'bc_pr_day_{model}_historical_*.csv'))
    futr_pat = list((CMIP6 / model).glob(f'bc_pr_day_{model}_{scenario}_*.csv'))
    if not hist_pat or not futr_pat:
        print(f"  MISSING: {model} {scenario}")
        return None
    dh = pd.read_csv(hist_pat[0])
    df = pd.read_csv(futr_pat[0])
    # Keep only Nan stations present in file
    h_cols = [c for c in dh.columns if c in NAN_STA]
    f_cols = [c for c in df.columns if c in NAN_STA]
    use_cols = sorted(set(h_cols) & set(f_cols))
    dh = dh[['YEAR','MONTH','DAY'] + use_cols]
    df = df[['YEAR','MONTH','DAY'] + use_cols]
    out = pd.concat([dh, df], ignore_index=True)
    out = out.drop_duplicates(subset=['YEAR','MONTH','DAY'])
    out = add_season_cols(out)
    return out, use_cols

print("\n=== Loading CMIP6 Data ===")
model_annual = {}   # {model: {ssp: annual_df}}
model_wet    = {}
model_dry    = {}

for model in MODELS:
    model_annual[model] = {}
    model_wet[model]    = {}
    model_dry[model]    = {}
    for ssp in SCENARIOS:
        data = load_bc_model(model, ssp)
        if data is None:
            continue
        d, cols = data
        # Annual
        ann = (d.groupby('YEAR')[cols].sum().reset_index()
               .rename(columns={'YEAR':'year'}))
        ann['model'] = model
        ann['scenario'] = ssp
        # Wet
        wet = (d[d['season']=='Wet'].groupby('season_year')[cols].sum()
               .reset_index().rename(columns={'season_year':'year'}))
        wet['model'] = model; wet['scenario'] = ssp
        # Dry (trim)
        dry = (d[d['season']=='Dry'].groupby('season_year')[cols].sum()
               .reset_index().rename(columns={'season_year':'year'}))
        dry = dry[(dry['year'] >= 1981) & (dry['year'] <= 2099)]
        dry['model'] = model; dry['scenario'] = ssp

        model_annual[model][ssp] = ann
        model_wet[model][ssp]    = wet
        model_dry[model][ssp]    = dry
        print(f"  {model}/{ssp}: annual {ann['year'].min()}–{ann['year'].max()}")

# ─── Trend Analysis Functions ─────────────────────────────────────────────
def run_mk(series, alpha=0.05):
    """Mann-Kendall test. Returns dict."""
    s = series.dropna()
    if len(s) < 10:
        return dict(trend='insufficient', p_value=np.nan, slope=np.nan,
                    intercept=np.nan, z=np.nan, tau=np.nan)
    res = mk.original_test(s, alpha=alpha)
    slope, intercept, _, _ = stats.theilslopes(s, np.arange(len(s)))
    return dict(trend=res.trend, p_value=res.p, slope=slope,
                intercept=intercept, z=res.z, tau=res.Tau,
                s_stat=res.s, n=len(s))

def run_spearman(series, years=None):
    """Spearman's Rho test."""
    s = series.dropna()
    if len(s) < 10:
        return dict(rho=np.nan, p_value=np.nan, trend='insufficient')
    x = np.arange(len(s)) if years is None else years[:len(s)]
    rho, p = stats.spearmanr(x, s.values)
    trend = ('increasing' if rho > 0 else 'decreasing') if p < 0.05 else 'no trend'
    return dict(rho=rho, p_value=p, trend=trend)

def run_trend_all(series_dict, label_map):
    """
    Run MK + Spearman for each station.
    series_dict: {station_id: pd.Series}
    Returns DataFrame of results.
    """
    records = []
    for sta, ser in series_dict.items():
        mk_res   = run_mk(ser)
        sp_res   = run_spearman(ser)
        rec = {'station': sta}
        rec.update({f'mk_{k}': v for k, v in mk_res.items()})
        rec.update({f'sp_{k}': v for k, v in sp_res.items()})
        rec.update(label_map)
        records.append(rec)
    return pd.DataFrame(records)

# ─── Compute Trends ──────────────────────────────────────────────────────────
print("\n=== Computing Trends ===")
all_trend_rows = []

# Helper: compute regional mean series
def regional_mean(df, sta_cols):
    """Compute spatial average across stations."""
    valid = [c for c in sta_cols if c in df.columns]
    df2 = df.copy()
    df2['regional_mean'] = df2[valid].mean(axis=1)
    return df2[['year','regional_mean']].set_index('year')['regional_mean']

# --- Observed trends (1981-2014) ---
for scale, df_scale in [('annual', obs_annual),
                         ('wet', obs_wet),
                         ('dry', obs_dry)]:
    obs_sta_cols = [c for c in obs_cols if c in df_scale.columns]
    for sta in obs_sta_cols:
        ser = df_scale.set_index('year')[sta]
        mk_r  = run_mk(ser)
        sp_r  = run_spearman(ser, years=ser.index.values)
        row = {'station': sta, 'model': 'observed', 'scenario': 'observed',
               'scale': scale, 'period': '1981-2014'}
        row.update({f'mk_{k}': v for k, v in mk_r.items()})
        row.update({f'sp_{k}': v for k, v in sp_r.items()})
        all_trend_rows.append(row)

# Regional mean observed
for scale, df_scale in [('annual', obs_annual),
                         ('wet', obs_wet),
                         ('dry', obs_dry)]:
    obs_sta_cols = [c for c in obs_cols if c in df_scale.columns]
    ser = regional_mean(df_scale, obs_sta_cols)
    mk_r = run_mk(ser)
    sp_r = run_spearman(ser, years=ser.index.values)
    row = {'station': 'REGIONAL_MEAN', 'model': 'observed',
           'scenario': 'observed', 'scale': scale, 'period': '1981-2014'}
    row.update({f'mk_{k}': v for k, v in mk_r.items()})
    row.update({f'sp_{k}': v for k, v in sp_r.items()})
    all_trend_rows.append(row)

# --- CMIP6 model trends: multiple periods ---
PERIODS = {
    'historical': (1981, 2014),
    'near_future': (2021, 2050),
    'mid_future':  (2051, 2080),
    'far_future':  (2081, 2100),
    'full':        (1981, 2100),
}

for model in MODELS:
    for ssp in SCENARIOS:
        if ssp not in model_annual[model]:
            continue
        for scale, model_dict in [('annual', model_annual),
                                   ('wet', model_wet),
                                   ('dry', model_dry)]:
            df_m = model_dict[model][ssp]
            sta_cols = [c for c in df_m.columns if c in NAN_STA]
            for pname, (py1, py2) in PERIODS.items():
                df_p = df_m[(df_m['year'] >= py1) & (df_m['year'] <= py2)]
                if len(df_p) < 10:
                    continue
                # Per station
                for sta in sta_cols:
                    ser = df_p.set_index('year')[sta]
                    mk_r = run_mk(ser)
                    sp_r = run_spearman(ser, years=df_p['year'].values)
                    row = {'station': sta, 'model': model, 'scenario': ssp,
                           'scale': scale, 'period': pname}
                    row.update({f'mk_{k}': v for k, v in mk_r.items()})
                    row.update({f'sp_{k}': v for k, v in sp_r.items()})
                    all_trend_rows.append(row)
                # Regional mean
                ser_r = regional_mean(df_p, sta_cols)
                mk_r  = run_mk(ser_r)
                sp_r  = run_spearman(ser_r, years=df_p['year'].values)
                row = {'station': 'REGIONAL_MEAN', 'model': model,
                       'scenario': ssp, 'scale': scale, 'period': pname}
                row.update({f'mk_{k}': v for k, v in mk_r.items()})
                row.update({f'sp_{k}': v for k, v in sp_r.items()})
                all_trend_rows.append(row)

trend_df = pd.DataFrame(all_trend_rows)
trend_df.to_csv(OUT / 'trend_results_all.csv', index=False)
print(f"Trend results saved: {len(trend_df)} rows")

# ─── MME (Multi-Model Ensemble) annual series ─────────────────────────────
print("\n=== Computing MME ===")
mme_records = []
for ssp in SCENARIOS:
    for scale, mdict in [('annual', model_annual),
                          ('wet', model_wet),
                          ('dry', model_dry)]:
        frames = []
        for model in MODELS:
            if ssp not in mdict[model]:
                continue
            df_m = mdict[model][ssp]
            sta_cols = [c for c in df_m.columns if c in NAN_STA]
            rm = df_m[['year']].copy()
            rm['regional_mean'] = df_m[sta_cols].mean(axis=1)
            rm['model'] = model
            frames.append(rm)
        if not frames:
            continue
        merged = pd.concat(frames)
        mme = (merged.groupby('year')['regional_mean']
               .agg(['mean','median',
                     lambda x: np.percentile(x, 25),
                     lambda x: np.percentile(x, 75),
                     'min','max','std'])
               .reset_index())
        mme.columns = ['year','mme_mean','mme_median','q25','q75','mme_min','mme_max','mme_std']
        mme['scenario'] = ssp
        mme['scale']    = scale
        mme_records.append(mme)

mme_df = pd.concat(mme_records, ignore_index=True)
mme_df.to_csv(OUT / 'mme_series.csv', index=False)
print(f"MME series saved: {len(mme_df)} rows")

# ─── ITA data (Innovative Trend Analysis) ─────────────────────────────────
print("\n=== Computing ITA ===")
ita_records = []

def compute_ita(ser, label):
    """Split series into two halves, sort each, return for scatter."""
    s = ser.dropna().values
    n = len(s)
    half = n // 2
    first = np.sort(s[:half])
    second = np.sort(s[half:2*half])
    return {'x': first.tolist(), 'y': second.tolist(), **label}

# Observed ITA
obs_sta_cols = [c for c in obs_cols if c in obs_annual.columns]
ser_obs_r = regional_mean(obs_annual, obs_sta_cols)
rec = compute_ita(ser_obs_r, {'model':'observed','scenario':'observed','scale':'annual'})
ita_records.append(rec)

for ssp in SCENARIOS:
    for scale, mdict in [('annual', model_annual),('wet', model_wet),('dry', model_dry)]:
        frames = []
        for model in MODELS:
            if ssp not in mdict[model]: continue
            df_m = mdict[model][ssp]
            sta_cols = [c for c in df_m.columns if c in NAN_STA]
            rm = df_m[['year']].copy()
            rm['regional_mean'] = df_m[sta_cols].mean(axis=1)
            rm['model'] = model
            frames.append(rm)
        if not frames: continue
        merged = pd.concat(frames)
        mme_ser = merged.groupby('year')['regional_mean'].median()
        rec = compute_ita(mme_ser, {'model':'MME','scenario':ssp,'scale':scale})
        ita_records.append(rec)

with open(OUT / 'ita_data.json', 'w') as f:
    json.dump(ita_records, f)
print("ITA data saved")

# ─── Save model annual series for timeline plots ──────────────────────────
print("\n=== Saving Timeline Data ===")
timeline_records = []

# Observed (regional mean)
obs_sta_cols = [c for c in obs_cols if c in obs_annual.columns]
for scale, df_s in [('annual', obs_annual), ('wet', obs_wet), ('dry', obs_dry)]:
    obs_s_c = [c for c in obs_sta_cols if c in df_s.columns]
    ser = df_s.copy()
    ser['regional_mean'] = ser[obs_s_c].mean(axis=1)
    for _, row in ser.iterrows():
        timeline_records.append({'year': row['year'], 'model': 'Observed',
                                  'scenario': 'observed', 'scale': scale,
                                  'regional_mean': row['regional_mean']})

# CMIP6 models
for model in MODELS:
    for ssp in SCENARIOS:
        for scale, mdict in [('annual', model_annual),
                              ('wet', model_wet),
                              ('dry', model_dry)]:
            if ssp not in mdict[model]: continue
            df_m = mdict[model][ssp]
            sta_cols = [c for c in df_m.columns if c in NAN_STA]
            for _, row in df_m.iterrows():
                rm = np.mean([row[s] for s in sta_cols if s in row.index])
                timeline_records.append({'year': row['year'], 'model': model,
                                          'scenario': ssp, 'scale': scale,
                                          'regional_mean': rm})

timeline_df = pd.DataFrame(timeline_records)
timeline_df.to_csv(OUT / 'timeline_series.csv', index=False)
print(f"Timeline data saved: {len(timeline_df)} rows")

print("\n=== DONE: Data Analysis Complete ===")
print(f"Output directory: {OUT}")
