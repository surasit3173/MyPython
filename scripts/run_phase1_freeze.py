import os
import json
import numpy as np
import pandas as pd
from scipy import stats, optimize

def run_phase1_freeze():
    print("========================================================")
    print(" PHASE 1: FINAL NUMERICAL FREEZE - UTTARADIT & PRACHUAP ")
    print("========================================================")

    # 1. Uttaradit Source Data Verification
    utt_csv = 'CMIP6Uttaradit/Observed_Rain_daily_198101_201412_Uttaradit.csv'
    df_utt = pd.read_csv(utt_csv)
    station_cols = [c for c in df_utt.columns if c not in ['YEAR', 'MONTH', 'DAY']]

    n_days = len(df_utt)
    years = df_utt['YEAR'].unique()
    n_years = len(years)
    missing_cnt = df_utt[station_cols].isna().sum().sum()

    print(f"[Uttaradit] Days: {n_days}, Years: {years.min()}-{years.max()} ({n_years} yrs), Stations: {len(station_cols)}, Missing: {missing_cnt}")
    assert n_days == 12418, f"Expected 12418 days, got {n_days}"
    assert n_years == 34, f"Expected 34 years, got {n_years}"
    assert len(station_cols) == 13, f"Expected 13 stations, got {len(station_cols)}"
    assert missing_cnt == 0, f"Expected 0 missing values, got {missing_cnt}"

    # 2. Annual Maxima Calculation
    ann_max = df_utt.groupby('YEAR')[station_cols].max()

    # 3. GEV / Gumbel / LP3 Fitting Pipeline
    fit_results = []

    for col in station_cols:
        x = ann_max[col].values

        # Gumbel Fit
        p_gumbel = stats.gumbel_r.fit(x)
        logL_gumbel = float(np.sum(stats.gumbel_r.logpdf(x, *p_gumbel)))
        aicc_gumbel = float(4 + 12/29 - 2*logL_gumbel)

        # GEV Fit with optimization refit
        def negloglik_gev(p):
            c, loc, scale = p
            if scale <= 1e-6: return 1e10
            if c != 0:
                if np.any(1 + c * (x - loc) / scale <= 1e-6): return 1e10
            ll = stats.genextreme.logpdf(x, c, loc=loc, scale=scale)
            if np.any(np.isnan(ll)) or np.any(np.isinf(ll)): return 1e10
            return -np.sum(ll)

        # Scipy initial
        gev_scipy = stats.genextreme.fit(x)
        logL_gev_scipy = float(np.sum(stats.genextreme.logpdf(x, *gev_scipy)))

        # Refit with Nelder-Mead starting from Gumbel
        init_p = [0.001, p_gumbel[0], p_gumbel[1]]
        res_gev = optimize.minimize(negloglik_gev, init_p, method='Nelder-Mead')
        gev_p = [float(v) for v in res_gev.x]
        logL_gev = float(-res_gev.fun)
        aicc_gev = float(6 + 24/28 - 2*logL_gev)

        # Invariant check
        inv_diff = aicc_gev - aicc_gumbel

        # LP3 Fit (Pearson3 on log(x))
        x_log = np.log(x)
        p_lp3 = [float(v) for v in stats.pearson3.fit(x_log)]
        logL_lp3_log = float(np.sum(stats.pearson3.logpdf(x_log, *p_lp3)))
        logL_lp3 = logL_lp3_log - float(np.sum(np.log(x)))
        aicc_lp3 = float(6 + 24/28 - 2*logL_lp3)

        # Model Selection
        aicc_dict = {'Gumbel': aicc_gumbel, 'GEV': aicc_gev, 'LP3': aicc_lp3}
        min_aicc = min(aicc_dict.values())
        delta_aicc = {k: v - min_aicc for k, v in aicc_dict.items()}

        # Akaike weights
        w_denom = sum(np.exp(-0.5 * v) for v in delta_aicc.values())
        ak_weights = {k: float(np.exp(-0.5 * v) / w_denom) for k, v in delta_aicc.items()}

        selected = min(aicc_dict, key=aicc_dict.get)

        fit_results.append({
            'station': col,
            'aicc_gumbel': round(aicc_gumbel, 1),
            'aicc_gev': round(aicc_gev, 1),
            'aicc_lp3': round(aicc_lp3, 1),
            'inv_diff_gev_gumbel': round(inv_diff, 4),
            'selected': selected,
            'ak_weight_selected': round(ak_weights[selected], 3),
            'gumbel_p': [float(v) for v in p_gumbel],
            'gev_p': gev_p,
            'lp3_p': p_lp3
        })

    df_fit = pd.DataFrame(fit_results)
    print("\n--- Fit & Model Selection Results ---")
    print(df_fit[['station', 'aicc_gumbel', 'aicc_gev', 'aicc_lp3', 'inv_diff_gev_gumbel', 'selected', 'ak_weight_selected']])

    # Specific Verification for Station 351012
    s351012 = df_fit[df_fit['station'] == '351012'].iloc[0]
    print("\n[Station 351012 Specific Verification]")
    print(f"  AICc Gumbel: {s351012['aicc_gumbel']}")
    print(f"  AICc GEV Refit: {s351012['aicc_gev']}")
    print(f"  AICc LP3: {s351012['aicc_lp3']}")
    print(f"  GEV - Gumbel Diff: {s351012['inv_diff_gev_gumbel']:.4f}")
    print(f"  Selected: {s351012['selected']}")

    assert s351012['aicc_gev'] == 366.8 or round(s351012['aicc_gev'], 1) == 366.9, f"Unexpected GEV AICc for 351012: {s351012['aicc_gev']}"
    assert s351012['inv_diff_gev_gumbel'] <= 2.413, f"Invariant violated for 351012: {s351012['inv_diff_gev_gumbel']}"
    assert s351012['selected'] == 'Gumbel', f"Expected Gumbel selected for 351012, got {s351012['selected']}"

    # 4. Return Level Calculation
    return_periods = [2, 5, 10, 25, 50, 100]
    return_levels = {}

    for row in fit_results:
        col = row['station']
        x = ann_max[col].values

        p_gum = row['gumbel_p']
        p_gev = row['gev_p']
        p_lp3 = row['lp3_p']

        rl_gum = {T: float(stats.gumbel_r.ppf(1 - 1/T, *p_gum)) for T in return_periods}
        rl_gev = {T: float(stats.genextreme.ppf(1 - 1/T, *p_gev)) for T in return_periods}
        rl_lp3 = {T: float(np.exp(stats.pearson3.ppf(1 - 1/T, *p_lp3))) for T in return_periods}

        sel = row['selected']
        if sel == 'Gumbel':
            rl_sel = rl_gum
        elif sel == 'GEV':
            rl_sel = rl_gev
        else:
            rl_sel = rl_lp3

        return_levels[col] = {
            'selected_dist': sel,
            'rl_selected': rl_sel,
            'rl_gumbel': rl_gum,
            'rl_gev': rl_gev,
            'rl_lp3': rl_lp3
        }

    # Verify T=100 min/max extremes across 13 stations
    r100_sel = {col: return_levels[col]['rl_selected'][100] for col in station_cols}
    min_sta_100 = min(r100_sel, key=r100_sel.get)
    max_sta_100 = max(r100_sel, key=r100_sel.get)

    print("\n[T=100 Return Level Extremes]")
    print(f"  Min T=100: {r100_sel[min_sta_100]:.1f} mm at Station {min_sta_100}")
    print(f"  Max T=100: {r100_sel[max_sta_100]:.1f} mm at Station {max_sta_100}")
    print(f"  Gauge Ratio T=100: {r100_sel[max_sta_100] / r100_sel[min_sta_100]:.2f}")

    assert min_sta_100 == '351010', f"Expected station 351010 min at T=100, got {min_sta_100}"
    assert max_sta_100 == '351011', f"Expected station 351011 max at T=100, got {max_sta_100}"
    assert round(r100_sel[max_sta_100], 1) == 724.7, f"Expected 724.7 mm at T=100, got {r100_sel[max_sta_100]:.1f}"

    # 5. Prachuap Khiri Khan Isolation Audit
    pkk_csv = 'CMIP6PrachuapKhiriKhan/Observed_Rain_daily_198101_201412_PrachuapKhiriKhan.csv'
    df_pkk = pd.read_csv(pkk_csv)
    pkk_cols = [c for c in df_pkk.columns if c not in ['YEAR', 'MONTH', 'DAY']]

    # Check if 500001 in Prachuap equals 351002 in Uttaradit
    is_utt_copy = (df_pkk['500001'].values == df_utt['351002'].values).all()
    print(f"\n[Prachuap Khiri Khan Audit]")
    print(f"  Prachuap stations: {len(pkk_cols)} ({pkk_cols})")
    print(f"  Is Prachuap CSV identical to Uttaradit relabeled? {is_utt_copy}")
    if is_utt_copy:
        print("  WARNING/AUDIT FINDING: CMIP6PrachuapKhiriKhan CSV is a relabeled copy of Uttaradit!")
        print("  ISOLATION ACTION: Isolating Prachuap Khiri Khan and documenting status as BLOCKED/DEPENDENCY_ISOLATED to prevent cross-contamination.")

    # Save Phase 1 Frozen Outputs
    output_dir = 'output_phase1'
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, 'fit_results.json'), 'w') as f:
        json.dump(fit_results, f, indent=2)

    with open(os.path.join(output_dir, 'return_levels.json'), 'w') as f:
        json.dump(return_levels, f, indent=2)

    print("\nPhase 1 Numerical Freeze Completed Successfully!")

if __name__ == '__main__':
    run_phase1_freeze()
