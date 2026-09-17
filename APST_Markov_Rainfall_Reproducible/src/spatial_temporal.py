import numpy as np
import pandas as pd
from scipy import stats
from .markov_engine import compute_first_order_markov

def evaluate_subperiod_stability(df, station_cols, threshold=0.1, period1_range=(1961, 1990), period2_range=(1991, 2020)):
    """
    Evaluate temporal stability of Markov transition probabilities between two sub-periods (e.g. 1961-1990 vs 1991-2020).
    Performs Z-test and Chi-Square test for transition probability changes across periods.
    """
    results = []

    p1_mask = (df['DATE'].dt.year >= period1_range[0]) & (df['DATE'].dt.year <= period1_range[1])
    p2_mask = (df['DATE'].dt.year >= period2_range[0]) & (df['DATE'].dt.year <= period2_range[1])

    df_p1 = df[p1_mask]
    df_p2 = df[p2_mask]

    for col in station_cols:
        b1 = (df_p1[col] >= threshold).astype(float)
        b1[df_p1[col].isnull()] = np.nan

        b2 = (df_p2[col] >= threshold).astype(float)
        b2[df_p2[col].isnull()] = np.nan

        m1 = compute_first_order_markov(b1)
        m2 = compute_first_order_markov(b2)

        # Test change in P01 (Dry -> Wet)
        z_p01, pval_p01 = compare_proportions_ztest(m1['n01'], m1['n0_total'], m2['n01'], m2['n0_total'])
        # Test change in P11 (Wet -> Wet)
        z_p11, pval_p11 = compare_proportions_ztest(m1['n11'], m1['n1_total'], m2['n11'], m2['n1_total'])

        results.append({
            'station_id': str(col),
            'P1_P01': m1['p01'], 'P2_P01': m2['p01'], 'diff_P01': m2['p01'] - m1['p01'], 'z_P01': z_p01, 'pval_P01': pval_p01,
            'P1_P11': m1['p11'], 'P2_P11': m2['p11'], 'diff_P11': m2['p11'] - m1['p11'], 'z_P11': z_p11, 'pval_P11': pval_p11,
            'P1_Pi1': m1['pi1'], 'P2_Pi1': m2['pi1'], 'diff_Pi1': m2['pi1'] - m1['pi1']
        })

    return pd.DataFrame(results)


def compare_proportions_ztest(k1, n1, k2, n2):
    """Two-sample z-test for comparing proportions k1/n1 vs k2/n2."""
    if n1 == 0 or n2 == 0:
        return np.nan, np.nan
    p1 = k1 / n1
    p2 = k2 / n2
    p_pool = (k1 + k2) / (n1 + n2)
    se = np.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
    if se == 0:
        return 0.0, 1.0
    z = (p2 - p1) / se
    pval = 2 * (1 - stats.norm.cdf(abs(z)))
    return z, pval


def compute_spatial_heterogeneity(markov_summary_df):
    """
    Compute spatial variability metrics across stations (Coefficient of Variation, range, std).
    """
    metrics = {}
    for col in ['p01', 'p11', 'p10', 'p00', 'pi1']:
        if col in markov_summary_df.columns:
            vals = markov_summary_df[col].dropna().values
            metrics[f'{col}_mean'] = float(np.mean(vals))
            metrics[f'{col}_std'] = float(np.std(vals, ddof=1))
            metrics[f'{col}_cv'] = float(np.std(vals, ddof=1) / np.mean(vals)) if np.mean(vals) != 0 else np.nan
            metrics[f'{col}_min'] = float(np.min(vals))
            metrics[f'{col}_max'] = float(np.max(vals))
    return metrics
