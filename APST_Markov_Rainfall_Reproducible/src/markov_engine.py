import numpy as np
import pandas as pd
from scipy import stats

def compute_first_order_markov(binary_series):
    """
    Compute 1st-order Markov transition probabilities and counts for a binary series (0=Dry, 1=Wet).
    Ignores transitions involving NaN (i.e. missing days).
    Returns dict with counts (n00, n01, n10, n11) and probabilities (p00, p01, p10, p11).
    Note: p00 = n00/(n00+n01), p01 = n01/(n00+n01), p10 = n10/(n10+n11), p11 = n11/(n10+n11).
    """
    valid_series = binary_series.dropna()
    s_curr = valid_series.iloc[:-1].values
    s_next = valid_series.iloc[1:].values

    # Ensure transition is between consecutive days
    idx_curr = valid_series.index[:-1]
    idx_next = valid_series.index[1:]
    is_consecutive = (idx_next - idx_curr == 1)

    s_curr = s_curr[is_consecutive]
    s_next = s_next[is_consecutive]

    n00 = int(np.sum((s_curr == 0) & (s_next == 0)))
    n01 = int(np.sum((s_curr == 0) & (s_next == 1)))
    n10 = int(np.sum((s_curr == 1) & (s_next == 0)))
    n11 = int(np.sum((s_curr == 1) & (s_next == 1)))

    n0_total = n00 + n01
    n1_total = n10 + n11

    p00 = n00 / n0_total if n0_total > 0 else np.nan
    p01 = n01 / n0_total if n0_total > 0 else np.nan
    p10 = n10 / n1_total if n1_total > 0 else np.nan
    p11 = n11 / n1_total if n1_total > 0 else np.nan

    # Stationary distribution (pi0, pi1) for 1st-order Markov chain
    # pi1 = p01 / (p01 + p10)
    # pi0 = p10 / (p01 + p10)
    denom = p01 + p10 if (p01 + p10) > 0 else np.nan
    pi1 = p01 / denom if denom > 0 else np.nan
    pi0 = p10 / denom if denom > 0 else np.nan

    return {
        'n00': n00, 'n01': n01, 'n10': n10, 'n11': n11,
        'n0_total': n0_total, 'n1_total': n1_total,
        'p00': p00, 'p01': p01, 'p10': p10, 'p11': p11,
        'pi0': pi0, 'pi1': pi1
    }


def compute_second_order_markov(binary_series):
    """
    Compute 2nd-order Markov transition probabilities (p000, p001, p010, p011, p100, p101, p110, p111).
    Ignores non-consecutive transitions across missing days.
    """
    valid_series = binary_series.dropna()
    idx = valid_series.index

    s_t0 = valid_series.iloc[:-2].values
    s_t1 = valid_series.iloc[1:-1].values
    s_t2 = valid_series.iloc[2:].values

    c1 = (idx[1:-1] - idx[:-2] == 1)
    c2 = (idx[2:] - idx[1:-1] == 1)
    consec = c1 & c2

    s_t0 = s_t0[consec]
    s_t1 = s_t1[consec]
    s_t2 = s_t2[consec]

    counts = {}
    probs = {}

    for prev2 in [0, 1]:
        for prev1 in [0, 1]:
            mask_prev = (s_t0 == prev2) & (s_t1 == prev1)
            n_prev = np.sum(mask_prev)
            for curr in [0, 1]:
                key_n = f"n_{prev2}{prev1}{curr}"
                key_p = f"p_{prev2}{prev1}{curr}"
                cnt = int(np.sum(mask_prev & (s_t2 == curr)))
                counts[key_n] = cnt
                probs[key_p] = cnt / n_prev if n_prev > 0 else np.nan

    return {**counts, **probs}


def model_order_selection_aic_bic(binary_series):
    """
    Perform AIC and BIC log-likelihood test to determine optimal Markov chain order (Order 0 vs Order 1 vs Order 2).
    Order 0: Independent Bernoulli scheme.
    Order 1: 1st order Markov chain.
    Order 2: 2nd order Markov chain.
    """
    m1 = compute_first_order_markov(binary_series)
    m2 = compute_second_order_markov(binary_series)

    # Total transitions in 1st order
    N = m1['n0_total'] + m1['n1_total']
    if N == 0:
        return {'best_order_aic': np.nan, 'best_order_bic': np.nan}

    p_wet = (m1['n01'] + m1['n11']) / N
    p_dry = 1 - p_wet

    # Log-likelihood Order 0
    ll0 = (m1['n00'] + m1['n10']) * np.log(p_dry) + (m1['n01'] + m1['n11']) * np.log(p_wet)
    aic0 = -2 * ll0 + 2 * 1
    bic0 = -2 * ll0 + np.log(N) * 1

    # Log-likelihood Order 1
    ll1 = (m1['n00'] * np.log(m1['p00']) if m1['p00'] > 0 else 0) + \
          (m1['n01'] * np.log(m1['p01']) if m1['p01'] > 0 else 0) + \
          (m1['n10'] * np.log(m1['p10']) if m1['p10'] > 0 else 0) + \
          (m1['n11'] * np.log(m1['p11']) if m1['p11'] > 0 else 0)
    aic1 = -2 * ll1 + 2 * 2
    bic1 = -2 * ll1 + np.log(N) * 2

    # Log-likelihood Order 2
    ll2 = 0
    for p2 in [0, 1]:
        for p1 in [0, 1]:
            for curr in [0, 1]:
                cnt = m2[f'n_{p2}{p1}{curr}']
                prob = m2[f'p_{p2}{p1}{curr}']
                if cnt > 0 and prob > 0:
                    ll2 += cnt * np.log(prob)
    aic2 = -2 * ll2 + 2 * 4
    bic2 = -2 * ll2 + np.log(N) * 4

    aics = {0: aic0, 1: aic1, 2: aic2}
    bics = {0: bic0, 1: bic1, 2: bic2}

    best_aic = min(aics, key=aics.get)
    best_bic = min(bics, key=bics.get)

    return {
        'll0': ll0, 'aic0': aic0, 'bic0': bic0,
        'll1': ll1, 'aic1': aic1, 'bic1': bic1,
        'll2': ll2, 'aic2': aic2, 'bic2': bic2,
        'best_order_aic': best_aic,
        'best_order_bic': best_bic
    }
