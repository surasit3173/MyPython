import numpy as np
import pandas as pd

def compute_spells(binary_series):
    """
    Extract lengths of consecutive dry spells (0) and wet spells (1).
    Discontinues spells across missing days (NaN).
    Returns dict of lists: {'dry_spells': [...], 'wet_spells': [...]}
    """
    dry_spells = []
    wet_spells = []

    curr_state = None
    curr_len = 0

    for val in binary_series.values:
        if pd.isna(val):
            if curr_state == 0 and curr_len > 0:
                dry_spells.append(curr_len)
            elif curr_state == 1 and curr_len > 0:
                wet_spells.append(curr_len)
            curr_state = None
            curr_len = 0
        else:
            val = int(val)
            if curr_state is None:
                curr_state = val
                curr_len = 1
            elif val == curr_state:
                curr_len += 1
            else:
                if curr_state == 0:
                    dry_spells.append(curr_len)
                else:
                    wet_spells.append(curr_len)
                curr_state = val
                curr_len = 1

    if curr_state == 0 and curr_len > 0:
        dry_spells.append(curr_len)
    elif curr_state == 1 and curr_len > 0:
        wet_spells.append(curr_len)

    return {
        'dry_spells': dry_spells,
        'wet_spells': wet_spells
    }


def compute_spell_statistics(spells_list):
    """
    Compute mean, std, median, max, count, and theoretical expected length based on geometric distribution.
    For Markov chain, expected dry spell length E[D] = 1 / p01.
    Expected wet spell length E[W] = 1 / p10 = 1 / (1 - p11).
    """
    if not spells_list:
        return {
            'count': 0, 'mean': np.nan, 'std': np.nan, 'median': np.nan, 'max': np.nan
        }
    arr = np.array(spells_list)
    return {
        'count': len(arr),
        'mean': float(np.mean(arr)),
        'std': float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0,
        'median': float(np.median(arr)),
        'max': int(np.max(arr))
    }
