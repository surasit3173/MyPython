# =============================================================================
# rainfall_trend_analysis_obs_mmk2.py
# =============================================================================
# Version : 5.1 — Publication Ready (Scientifically Corrected)
#
# Senior Climate Scientist + Hydrologist Edition
#
# Scientific References
# ---------------------
# Mann (1945)
# Kendall (1975)
# Sen (1968)
# Gilbert (1987)
# Hamed & Rao (1998)
# Pettitt (1979)
#
# =============================================================================

from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, Optional, List

import numpy as np
import pandas as pd

import scipy.stats as stats

from scipy.stats import norm
from scipy.stats import t

import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from openpyxl.styles import Alignment

# =============================================================================
# VERSION
# =============================================================================

VERSION: str = "5.1 — Publication Ready (Scientifically Corrected)"

# =============================================================================
# CONSTANTS
# =============================================================================

ALPHA: float = 0.05

MIN_YEARS: int = 10

WET_DAY_THRESHOLD: float = 0.1

FIG_DPI: int = 600

# =============================================================================
# COLORS
# =============================================================================

PREMIUM_GREEN: str = "#0B5D3B"

PREMIUM_RED: str = "#7A1E1E"

PREMIUM_GOLD: str = "#B8860B"

SOFT_BAR: str = "#E8E8E8"

OBSERVED_COLOR: str = "#6C7A89"

CI_COLOR: str = "#BDBDBD"

BACKGROUND_COLOR: str = "#FAFAFA"

# =============================================================================
# MATPLOTLIB STYLE
# =============================================================================

mpl.rcParams["font.family"] = "Times New Roman"

mpl.rcParams["axes.labelsize"] = 13

mpl.rcParams["axes.titlesize"] = 15

mpl.rcParams["xtick.labelsize"] = 11

mpl.rcParams["ytick.labelsize"] = 11

mpl.rcParams["legend.fontsize"] = 10

# =============================================================================
# OUTPUT FOLDER
# =============================================================================

def create_output_folder(base_dir: Path) -> Path:

    """
    Create timestamped output directory.
    """

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    outdir = base_dir / f"Rainfall_Trend_Output_{timestamp}"

    outdir.mkdir(
        parents=True,
        exist_ok=True
    )

    return outdir

# =============================================================================
# LOAD DATA
# =============================================================================

def load_data(filepath: str) -> pd.DataFrame:

    """
    Load rainfall dataset.

    Supported formats
    -----------------
    - CSV
    - XLSX

    Supported date structures
    -------------------------
    - YEAR MONTH DAY
    - Single DATE column
    """

    ext = Path(filepath).suffix.lower()

    if ext == ".csv":

        df = pd.read_csv(filepath)

    elif ext in [".xlsx", ".xls"]:

        df = pd.read_excel(filepath)

    else:

        raise ValueError(
            f"Unsupported file format: {ext}"
        )

    df.columns = [

        str(c).strip().upper()

        for c in df.columns
    ]

    cols = df.columns.tolist()

    # =========================================================================
    # YEAR MONTH DAY
    # =========================================================================

    if all(

        c in cols

        for c in ["YEAR", "MONTH", "DAY"]
    ):

        dates = pd.to_datetime(

            {
                "year": df["YEAR"].astype(int),

                "month": df["MONTH"].astype(int),

                "day": df["DAY"].astype(int)
            },

            errors="coerce"
        )

        df.index = dates

        df = df.drop(

            columns=[
                "YEAR",
                "MONTH",
                "DAY"
            ]
        )

    # =========================================================================
    # SINGLE DATE COLUMN
    # =========================================================================

    else:

        first_col = df.columns[0]

        dates = pd.to_datetime(

            df[first_col],

            errors="coerce"
        )

        df.index = dates

        df = df.drop(columns=[first_col])

    # =========================================================================
    # CLEAN
    # =========================================================================

    df = df.loc[df.index.notna()]

    for c in df.columns:

        df[c] = pd.to_numeric(

            df[c],

            errors="coerce"
        )

    df = df.sort_index()

    return df

# =============================================================================
# QUALITY CONTROL
# =============================================================================

def quality_control(
    df: pd.DataFrame
) -> Tuple[pd.DataFrame, pd.DataFrame]:

    """
    Rainfall quality control.

    Includes
    --------
    - Missing diagnostics
    - Gap analysis
    - Short-gap interpolation
    - Outlier diagnostics
    - Physical consistency
    """

    clean = df.copy()

    qc = {}

    for station in clean.columns:

        s = clean[station].copy()

        # ---------------------------------------------------------------------
        # Missing
        # ---------------------------------------------------------------------

        n_missing = int(s.isna().sum())

        pct_missing = (

            n_missing / len(s)

        ) * 100

        # ---------------------------------------------------------------------
        # Interpolation
        # ---------------------------------------------------------------------

        filled = s.interpolate(

            method="time",

            limit=3,

            limit_direction="both"
        )

        # ---------------------------------------------------------------------
        # Physical consistency
        # ---------------------------------------------------------------------

        filled = filled.clip(lower=0.0)

        # ---------------------------------------------------------------------
        # Gap analysis
        # ---------------------------------------------------------------------

        gaps = []

        is_na = s.isna().values

        start = None

        for i, v in enumerate(is_na):

            if v and start is None:

                start = i

            elif not v and start is not None:

                gaps.append(i - start)

                start = None

        if start is not None:

            gaps.append(len(s) - start)

        max_gap = max(gaps) if len(gaps) > 0 else 0

        # ---------------------------------------------------------------------
        # Outlier diagnostics
        # ---------------------------------------------------------------------

        wet = s[s >= WET_DAY_THRESHOLD]

        if len(wet) > 0:

            q1 = wet.quantile(0.25)

            q3 = wet.quantile(0.75)

            iqr = q3 - q1

            upper = q3 + 3 * iqr

            n_outliers = int(

                (s > upper).sum()
            )

        else:

            upper = np.nan

            n_outliers = 0

        clean[station] = filled

        qc[station] = {

            "Missing_Count": n_missing,

            "Missing_%": round(
                pct_missing,
                2
            ),

            "Interpolated_Count": int(

                filled.notna().sum()

                - s.notna().sum()
            ),

            "Max_Gap_Length": max_gap,

            "Outlier_Count": n_outliers,

            "Upper_Outlier_Fence": round(
                upper,
                2
            ) if not pd.isna(upper)
            else np.nan
        }

    qc_df = pd.DataFrame(qc).T

    return clean, qc_df

# =============================================================================
# TEMPORAL AGGREGATION
# =============================================================================

def aggregate_scales(
    df: pd.DataFrame
) -> Dict[str, pd.DataFrame]:

    """
    Aggregate rainfall series.

    Annual:
    Jan–Dec  →  resample YE

    Wet season:
    May–Oct  →  resample YE on filtered months

    Dry season (Hydrological Year):
    Nov(Y) – Apr(Y+1)  →  DRY_YEAR = Y+1
    Edge seasons that are structurally incomplete are DROPPED:
      * DRY_YEAR == data_start_year        (Jan–Apr only, no Nov–Dec)
      * DRY_YEAR == data_end_year + 1      (Nov–Dec only, no Jan–Apr)
    Expected N for 1981–2014:
      DRY_YEAR 1982 … 2014  →  N = 33 complete seasons
    """

    # =========================================================================
    # ANNUAL
    # =========================================================================

    annual = (
        df
        .resample("YE")
        .sum(min_count=330)
    )

    # =========================================================================
    # WET
    # =========================================================================

    wet = (
        df[
            df.index.month.isin([5, 6, 7, 8, 9, 10])
        ]
        .resample("YE")
        .sum(min_count=150)
    )

    # =========================================================================
    # DRY  (Hydrological Year with edge trimming)
    # =========================================================================

    # Step 1: assign every Nov/Dec row to the NEXT calendar year
    # so that Nov-1981 + Dec-1981 + Jan-1982 + … + Apr-1982
    # all share DRY_YEAR = 1982 (one complete dry season).
    dry_df = df.copy()

    dry_year = np.where(
        dry_df.index.month >= 11,
        dry_df.index.year + 1,
        dry_df.index.year
    )

    dry_df["DRY_YEAR"] = dry_year

    dry_only = dry_df[
        dry_df.index.month.isin([11, 12, 1, 2, 3, 4])
    ]

    dry = (
        dry_only
        .groupby("DRY_YEAR")
        .sum(numeric_only=True)
    )

    # Step 2: determine which edge DRY_YEARs are structurally incomplete.
    #   * DRY_YEAR = data_start_year  →  only Jan–Apr exist (no Nov–Dec
    #     from the preceding year which is outside the study period).
    #   * DRY_YEAR = data_end_year+1  →  only Nov–Dec exist (no Jan–Apr
    #     from the following year which is outside the study period).
    _data_start_year: int = int(df.index.year.min())   # e.g. 1981
    _data_end_year:   int = int(df.index.year.max())   # e.g. 2014

    _first_full_dry_year: int = _data_start_year + 1   # 1982 — first complete
    _last_full_dry_year:  int = _data_end_year          # 2014 — last complete

    # dry.index is still integer (DRY_YEAR) at this point — filter before
    # converting to DatetimeIndex.
    dry = dry[
        (dry.index >= _first_full_dry_year) &
        (dry.index <= _last_full_dry_year)
    ]

    # Step 3: convert integer DRY_YEAR index to DatetimeIndex (Dec-31).
    dry.index = pd.to_datetime(
        dry.index.astype(str) + "-12-31"
    )

    return {
        "annual": annual,
        "wet":    wet,
        "dry":    dry
    }

# =============================================================================
# DESCRIPTIVE STATISTICS
# =============================================================================

def descriptive_statistics(
    scales: Dict[str, pd.DataFrame],
    daily_df: pd.DataFrame
) -> pd.DataFrame:

    """
    Descriptive rainfall statistics.
    """

    rows = []

    for scale_name, df in scales.items():

        for station in df.columns:

            s = df[station].dropna()

            if len(s) == 0:
                continue

            d = daily_df[station].dropna()

            wet_indicator = (

                d >= WET_DAY_THRESHOLD

            ).astype(int)

            annual_wet = wet_indicator.groupby(

                wet_indicator.index.year

            ).sum()

            wet_days = annual_wet.mean()

            mean = s.mean()

            std = s.std()

            cv = (std / mean) * 100

            rows.append({

                "Scale": scale_name,

                "Station": station,

                "Mean": round(mean, 2),

                "Std": round(std, 2),

                "CV%": round(cv, 2),

                "Min": round(s.min(), 2),

                "Max": round(s.max(), 2),

                "Wet-days/yr": round(
                    wet_days,
                    1
                )
            })

    return pd.DataFrame(rows)

# =============================================================================
# AUTOCORRELATION SIGNIFICANCE
# =============================================================================

def autocorrelation_significance(
    r: float,
    n: int
) -> Tuple[float, float, bool]:

    """
    Lag-1 autocorrelation significance test.
    """

    if np.isnan(r):

        return np.nan, np.nan, False

    t_stat = r * np.sqrt(

        (n - 2)

        / (1 - r**2)
    )

    p = 2 * (

        1 - t.cdf(
            abs(t_stat),
            df=n-2
        )
    )

    return t_stat, p, p < ALPHA

# =============================================================================
# MMK LAG RULE
# =============================================================================

def mmk_max_lag_from_n(n: int) -> int:

    """
    Maximum lag used by MMK effective sample-size correction.
    Hamed & Rao (1998): lags 1..floor(n/3), bounded by n-1.
    """

    if n < 2:
        return 0

    return min(int(n / 3), n - 1)

# =============================================================================
# MK VARIANCE
# =============================================================================

def mk_variance(
    x: np.ndarray
) -> float:

    """
    Mann-Kendall variance.
    """

    n = len(x)

    _, counts = np.unique(

        x,

        return_counts=True
    )

    ties = counts[counts > 1]

    tie_sum = np.sum(

        ties *

        (ties - 1) *

        (2 * ties + 5)
    )

    return (

        n *

        (n - 1) *

        (2*n + 5)

        - tie_sum

    ) / 18

# =============================================================================
# STANDARD MK
# =============================================================================

def mk_test(
    x: np.ndarray
) -> Optional[Dict]:

    """
    Standard Mann-Kendall test.
    """

    x = np.asarray(x, dtype=float)

    x = x[~np.isnan(x)]

    n = len(x)

    if n < MIN_YEARS:
        return None

    S = 0

    for i in range(n - 1):

        S += np.sum(

            np.sign(
                x[i+1:] - x[i]
            )
        )

    var_s = mk_variance(x)

    if S > 0:

        z = (

            S - 1

        ) / np.sqrt(var_s)

    elif S < 0:

        z = (

            S + 1

        ) / np.sqrt(var_s)

    else:

        z = 0.0

    p = 2 * (

        1 - norm.cdf(abs(z))
    )

    tau = S / (

        0.5 * n * (n - 1)
    )

    return {

        "S": S,

        "Var(S)": var_s,

        "Z": z,

        "p-value": p,

        "Tau": tau
    }

# =============================================================================
# EFFECTIVE SAMPLE SIZE
# =============================================================================

def effective_sample_size(
    x: np.ndarray
) -> tuple[float, list[tuple[int, float]]]:

    """
    Effective sample size n* per Hamed & Rao (1998), Eq. 3.

    Correction factor
    -----------------
    n / n*  =  1 + (2/n) * Σ_{i=1}^{⌊n/3⌋}  (1 − i/n) * ρ_s(i)

    where ρ_s(i) is the Spearman rank autocorrelation at lag i.

    IMPORTANT: The summation runs over ALL lags 1 … ⌊n/3⌋ (not only
    significant lags). Restricting the sum to significant lags only is
    a common but technically non-H&R98 shortcut that can under-correct
    when several moderate, non-individually-significant lags accumulate.

    Significant lags are recorded separately (returned as sig_lags) for
    reporting and for the decision of whether to apply the correction:
    if no lag is individually significant, the series is treated as
    iid and n* = n (no correction applied — cf. H&R98 §3).

    Parameters
    ----------
    x : array-like
        Annual / seasonal rainfall values (NaN-cleaned internally).

    Returns
    -------
    n_eff : float
        Effective sample size.  Always in [1, n].
    sig_lags : list of (lag, rho) tuples
        Lags whose rank autocorrelation is individually significant
        at the ALPHA level.
    """

    x = np.asarray(x, dtype=float)

    x = x[~np.isnan(x)]

    n = len(x)

    if n < 4:
        return float(n), []

    ranks = stats.rankdata(x)

    # H&R98 recommend truncating the lag sum at ⌊n/3⌋ to balance
    # resolution against estimator variance.
    max_lag = mmk_max_lag_from_n(n)

    sig_lags:  list[tuple[int, float]] = []
    summation: float = 0.0            # accumulates ALL lags

    for lag in range(1, max_lag + 1):

        r = np.corrcoef(
            ranks[:-lag],
            ranks[lag:]
        )[0, 1]

        _, _, sig = autocorrelation_significance(r, n)

        if sig:
            sig_lags.append((lag, r))

        # H&R98 Eq. 3: accumulate ALL lags, significant or not.
        summation += (1.0 - lag / n) * r

    # If no lag is individually significant, treat series as iid → n* = n.
    if len(sig_lags) == 0:
        return float(n), []

    # Correction factor  n/n*  (must be ≥ 1 to avoid inflating n*).
    correction = 1.0 + (2.0 / n) * summation
    correction = max(correction, 1.0)   # negative AC would give corr < 1

    n_eff = n / correction

    # Physical bounds: n* ∈ [1, n].
    n_eff = max(1.0, min(float(n), n_eff))

    return n_eff, sig_lags

# =============================================================================
# MODIFIED MK
# =============================================================================

def modified_mk_test(
    x: np.ndarray
) -> Optional[Dict]:

    """
    Modified Mann-Kendall test.

    Hamed & Rao (1998)
    """

    mk = mk_test(x)

    if mk is None:

        return None

    x = np.asarray(x, dtype=float)

    x = x[~np.isnan(x)]

    n = len(x)

    n_eff, sig_lags = effective_sample_size(x)
    max_lag_used = mmk_max_lag_from_n(n)

    correction_factor = n / n_eff

    var_adj = mk["Var(S)"] * correction_factor

    if mk["S"] > 0:

        z = (

            mk["S"] - 1

        ) / np.sqrt(var_adj)

    elif mk["S"] < 0:

        z = (

            mk["S"] + 1

        ) / np.sqrt(var_adj)

    else:

        z = 0.0

    p = 2 * (

        1 - norm.cdf(abs(z))
    )

    return {

        "S": mk["S"],

        "Var(S)": mk["Var(S)"],

        "Var_adj": var_adj,

        "Z": z,

        "p-value": p,

        "Tau": mk["Tau"],

        "n_eff": n_eff,

        "Correction_Factor": correction_factor,

        "Max_Lag_Used": max_lag_used,

        "Lag_Range_Used": (
            f"1-{max_lag_used}"
            if max_lag_used >= 1
            else "None"
        ),

        "Significant_Lags": str(sig_lags),

        "Significant": p < ALPHA
    }

# =============================================================================
# SEN'S SLOPE
# =============================================================================

def sens_slope(
    series: pd.Series,
    alpha: float = 0.05,
    var_s_override: Optional[float] = None
) -> Tuple[float, float, float]:

    """
    Sen's slope estimator with Gilbert (1987) 95 % CI.

    Parameters
    ----------
    series : pd.Series
        Annual or seasonal rainfall series (DatetimeIndex).
    alpha : float
        Significance level for CI (default 0.05 → 95 % CI).
    var_s_override : float, optional
        If supplied, this value replaces the standard Var(S) when
        computing the rank index C_α = Z_{1−α/2} · √Var(S).
        Pass ``mmk["Var_adj"]`` to obtain the MMK-corrected CI
        (wider than the standard MK CI when positive autocorrelation
        is present), following Gilbert (1987) §14.3 as adapted by
        Hamed & Rao (1998).

    Returns
    -------
    slope : float
        Sen's slope (mm yr⁻¹).
    ci_low : float
        Lower bound of the 95 % CI.
    ci_high : float
        Upper bound of the 95 % CI.

    Notes
    -----
    The rank index C_α indexes into the sorted pairwise-slope array:
        M1 = ⌈(N − C_α) / 2⌉
        M2 = ⌊(N + C_α) / 2⌋
    where N = number of pairwise slopes.
    Using Var*(S) (MMK) instead of Var(S) (standard MK) yields a
    wider CI, correctly reflecting reduced effective information when
    autocorrelation is present.
    """

    s = series.dropna()

    if len(s) < MIN_YEARS:
        return np.nan, np.nan, np.nan

    years  = s.index.year.values.astype(float)
    values = s.values.astype(float)

    # ------------------------------------------------------------------
    # Pairwise slopes
    # ------------------------------------------------------------------
    slopes = []

    for i in range(len(values) - 1):

        for j in range(i + 1, len(values)):

            delta_year = years[j] - years[i]

            if delta_year == 0:
                continue

            slopes.append(
                (values[j] - values[i]) / delta_year
            )

    slopes = np.sort(np.asarray(slopes))

    N = len(slopes)

    slope = np.median(slopes)

    # ------------------------------------------------------------------
    # Rank index C_α  (Gilbert 1987, eq. 14.3)
    # ------------------------------------------------------------------
    # Use caller-supplied Var_adj (MMK) when available; fall back to
    # the standard Var(S) from mk_variance (standard MK).
    var_s = (
        var_s_override
        if (var_s_override is not None and np.isfinite(var_s_override))
        else mk_variance(values)
    )

    C_alpha = norm.ppf(1 - alpha / 2) * np.sqrt(var_s)

    M1 = int(np.ceil( (N - C_alpha) / 2))
    M2 = int(np.floor((N + C_alpha) / 2))

    M1 = max(0, min(M1, N - 1))
    M2 = max(0, min(M2, N - 1))

    ci_low  = slopes[M1]
    ci_high = slopes[M2]

    ci_low, ci_high = sorted([ci_low, ci_high])

    return slope, ci_low, ci_high

# =============================================================================
# PETTITT TEST
# =============================================================================

def pettitt_test(
    x: np.ndarray
) -> Tuple[float, float, float]:

    """
    Pettitt change-point test.
    """

    x = np.asarray(x, dtype=float)

    x = x[~np.isnan(x)]

    n = len(x)

    if n < MIN_YEARS:

        return np.nan, np.nan, np.nan

    K = np.zeros(n)

    for t in range(1, n):

        left = x[:t]

        right = x[t:]

        diff = np.subtract.outer(

            right,

            left
        )

        K[t] = np.sum(np.sign(diff))

    Kmax = np.max(np.abs(K))

    if Kmax == 0:

        return np.nan, 1.0, 0.0

    cp = int(np.argmax(np.abs(K)))

    p = 2 * np.exp(

        (-6 * Kmax**2)

        / (n**3 + n**2)
    )

    return cp, p, Kmax

# =============================================================================
# TREND ANALYSIS
# =============================================================================

def run_trend_analysis(
    scales: Dict[str, pd.DataFrame]
):

    """
    Run standard MK, Modified MK (H&R98), Sen's slope, and Pettitt tests
    for every (scale, station) combination.

    Sen's slope CI is computed TWICE per series:
      * CI_Low_MK  / CI_High_MK  — uses standard Var(S)   (Gilbert 1987)
      * CI_Low_MMK / CI_High_MMK — uses Var*(S) = Var_adj  (H&R98 adapted)

    The MMK CI is wider whenever positive autocorrelation is present,
    correctly reflecting the reduced effective information in the series.
    CI_Low and CI_High (backwards-compatible keys) map to the MMK CI so
    that existing figure code automatically shows the corrected interval.
    """

    mk_rows      = []
    mmk_rows     = []
    sens_rows    = []
    pettitt_rows = []

    for scale_name, df in scales.items():

        for station in df.columns:

            s = df[station].dropna()

            if len(s) < MIN_YEARS:
                continue

            arr = s.values

            # ------------------------------------------------------------------
            # Standard MK
            # ------------------------------------------------------------------
            mk = mk_test(arr)

            # ------------------------------------------------------------------
            # Modified MK (Hamed & Rao 1998)
            # ------------------------------------------------------------------
            mmk = modified_mk_test(arr)

            # ------------------------------------------------------------------
            # Sen's slope — standard CI  (uses Var(S))
            # ------------------------------------------------------------------
            slope, lo_mk, hi_mk = sens_slope(s)

            # ------------------------------------------------------------------
            # Sen's slope — MMK CI  (uses Var*(S) = Var_adj)
            # Wider CI when positive autocorrelation is present.
            # Falls back to standard CI if mmk is None.
            # ------------------------------------------------------------------
            if mmk is not None:

                _, lo_mmk, hi_mmk = sens_slope(
                    s,
                    var_s_override=mmk["Var_adj"]
                )

            else:

                lo_mmk, hi_mmk = lo_mk, hi_mk

            # ------------------------------------------------------------------
            # Pettitt change-point
            # ------------------------------------------------------------------
            cp, p_pet, Kmax = pettitt_test(arr)

            cp_year = (
                s.index.year[cp]
                if not np.isnan(cp)
                else np.nan
            )

            # ------------------------------------------------------------------
            # Collect rows
            # ------------------------------------------------------------------
            mk_rows.append({
                "Scale":   scale_name,
                "Station": station,
                **mk
            })

            mmk_rows.append({
                "Scale":   scale_name,
                "Station": station,
                **mmk
            })

            sens_rows.append({
                "Scale":              scale_name,
                "Station":            station,
                "Slope_mm_per_year":  slope,

                # Standard MK CI  (Var(S))
                "CI_Low_MK":          lo_mk,
                "CI_High_MK":         hi_mk,

                # Modified MK CI  (Var*(S)) — wider when AC > 0
                "CI_Low_MMK":         lo_mmk,
                "CI_High_MMK":        hi_mmk,

                # Backwards-compatible keys used by figure functions →
                # default to the scientifically correct MMK CI.
                "CI_Low":             lo_mmk,
                "CI_High":            hi_mmk
            })

            pettitt_rows.append({
                "Scale":            scale_name,
                "Station":          station,
                "Change_Point_Year": cp_year,
                "Pettitt_p":        p_pet,
                "Homogeneity": (
                    "Homogeneous"
                    if p_pet >= ALPHA
                    else "Non-Homogeneous"
                )
            })

    return (
        pd.DataFrame(mk_rows),
        pd.DataFrame(mmk_rows),
        pd.DataFrame(sens_rows),
        pd.DataFrame(pettitt_rows)
    )

# =============================================================================
# FIGURE SYSTEM (UNIFIED PUBLICATION STANDARD)
# =============================================================================

FIG_TITLE_SIZE = 18
PANEL_TITLE_SIZE = 15
AXIS_LABEL_SIZE = 13
TICK_SIZE = 11
LEGEND_SIZE = 10
TEXTBOX_SIZE = 10

OBSERVED_BAR_COLOR = "#DDDDDD"
NON_SIGNIF_COLOR = "#CFCFCF"
PETTITT_COLOR = "#1E3D59"

SCALE_ORDER = ["annual", "wet", "dry"]
SCALE_LABEL = {
    "annual": "Annual",
    "wet": "Wet Season",
    "dry": "Dry Season"
}
SCALE_TAG = {
    "annual": "Annual",
    "wet": "WetSeason",
    "dry": "DrySeason"
}
SCALE_RAIN_TITLE = {
    "annual": "Annual Rainfall",
    "wet": "Wet Season Rainfall",
    "dry": "Dry Season Rainfall"
}
PANEL_SUBTITLE = {
    "annual": "(a) Annual Rainfall",
    "wet": "(b) Wet Season (May–Oct)",
    "dry": "(c) Dry Season (Nov–Apr)"
}
VARIABILITY_TITLE = {
    "annual": "Annual Total",
    "wet": "Wet Season",
    "dry": "Dry Season"
}

def _station_label(station: str) -> str:
    return f"Station {station}"

def _figure_dirs(outdir: Path) -> Dict[str, Path]:

    base_adv = outdir / "Advanced_Publication_Figures"
    folders = {
        "classic_multi": outdir / "Publication_Classic" / "MultiStation",
        "classic_single": outdir / "Publication_Classic" / "SingleStation",
        "luxury_multi": outdir / "Luxury_Pettitt_Q1" / "MultiStation",
        "luxury_single": outdir / "Luxury_Pettitt_Q1" / "SingleStation",
        "acf_combined": base_adv / "Autocorrelation" / "Combined",
        "acf_single": base_adv / "Autocorrelation" / "SingleStation",
        "ts_combined": base_adv / "TimeSeries" / "Combined",
        "ts_single": base_adv / "TimeSeries" / "SingleStation",
        "z_combined": base_adv / "ZComparison" / "Combined",
        "z_single": base_adv / "ZComparison" / "SingleStation",
        "sen_combined": base_adv / "SenSlope" / "Combined",
        "sen_single": base_adv / "SenSlope" / "SingleStation",
        "var_combined": base_adv / "Variability" / "Combined",
        "var_single": base_adv / "Variability" / "SingleStation"
    }
    for p in folders.values():
        p.mkdir(parents=True, exist_ok=True)
    return folders

def _apply_axes_style(
    ax: plt.Axes,
    xlabel: str = "",
    ylabel: str = "",
    show_grid: bool = True
) -> None:

    ax.set_facecolor(BACKGROUND_COLOR)
    ax.tick_params(labelsize=TICK_SIZE, pad=4)
    if xlabel:
        ax.set_xlabel(
            xlabel,
            fontsize=AXIS_LABEL_SIZE,
            fontweight="bold",
            labelpad=8
        )
    if ylabel:
        ax.set_ylabel(
            ylabel,
            fontsize=AXIS_LABEL_SIZE,
            fontweight="bold",
            labelpad=8
        )
    if show_grid:
        ax.grid(linestyle=":", alpha=0.20)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

def _style_legend(legend_obj) -> None:

    if legend_obj is None:
        return
    legend_obj.set_frame_on(True)
    frame = legend_obj.get_frame()
    frame.set_facecolor("white")
    frame.set_edgecolor("#BDBDBD")
    frame.set_alpha(0.95)

def _qa_figure(fig: plt.Figure, fig_name: str) -> None:

    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    fb = fig.bbox
    issues = []

    for txt in fig.findobj(match=lambda o: isinstance(o, mpl.text.Text)):
        bb = txt.get_window_extent(renderer=renderer)
        if bb.width > 0 and bb.height > 0:
            if bb.x0 < fb.x0 or bb.y0 < fb.y0 or bb.x1 > fb.x1 or bb.y1 > fb.y1:
                issues.append("clipped_text")
                break

    for ax in fig.axes:
        if not ax.get_visible():
            continue
        abb = ax.get_tightbbox(renderer)
        if abb is not None:
            if abb.x0 < fb.x0 or abb.y0 < fb.y0 or abb.x1 > fb.x1 or abb.y1 > fb.y1:
                issues.append("clipped_axes")
                break
        if (len(ax.lines) == 0 and len(ax.patches) == 0 and
                len(ax.collections) == 0 and len(ax.images) == 0):
            issues.append("empty_subplot")
            break
        if ax.get_visible() and ax.get_xaxis().get_visible() and ax.get_yaxis().get_visible():
            if ax.get_xlabel() == "" and ax.get_ylabel() == "":
                issues.append("missing_axis_labels")

    legend = fig.legends[0] if len(fig.legends) > 0 else None
    if legend is not None:
        lbb = legend.get_window_extent(renderer=renderer)
        if lbb.x0 < fb.x0 or lbb.y0 < fb.y0 or lbb.x1 > fb.x1 or lbb.y1 > fb.y1:
            issues.append("legend_overlap_or_clipped")

    if len(issues) > 0:
        print(f"[QA] {fig_name}: " + ", ".join(sorted(set(issues))))

def _save_figure(fig: plt.Figure, outbase: Path) -> None:

    try:
        fig.tight_layout()
    except Exception:
        pass
    _qa_figure(fig, outbase.name)
    fig.savefig(
        outbase.with_suffix(".png"),
        dpi=FIG_DPI,
        transparent=False,
        bbox_inches="tight"
    )
    fig.savefig(
        outbase.with_suffix(".pdf"),
        dpi=FIG_DPI,
        transparent=False,
        bbox_inches="tight"
    )
    plt.close(fig)

def _trend_geometry(
    s: pd.Series,
    slope: float,
    ci_low: float,
    ci_high: float
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:

    yrs = s.index.year.values.astype(float)
    vals = s.values.astype(float)
    x0 = np.nanmedian(yrs)
    y0 = np.nanmedian(vals)
    fit = slope * (yrs - x0) + y0
    fit_lo = ci_low * (yrs - x0) + y0
    fit_hi = ci_high * (yrs - x0) + y0
    return yrs, vals, fit, fit_lo, fit_hi

def _draw_trend_panel(
    ax: plt.Axes,
    station: str,
    scale: str,
    scales: Dict[str, pd.DataFrame],
    mmk_df: pd.DataFrame,
    sens_df: pd.DataFrame,
    pettitt_df: Optional[pd.DataFrame] = None,
    with_pettitt: bool = False,
    show_ylabel: bool = True,
    show_xlabel: bool = True
) -> None:

    s = scales[scale][station].dropna()
    mmk = mmk_df[
        (mmk_df["Scale"] == scale) &
        (mmk_df["Station"] == station)
    ].iloc[0]
    sen = sens_df[
        (sens_df["Scale"] == scale) &
        (sens_df["Station"] == station)
    ].iloc[0]

    slope = float(sen["Slope_mm_per_year"])
    lo = float(sen["CI_Low"])
    hi = float(sen["CI_High"])
    yrs, vals, fit, fit_lo, fit_hi = _trend_geometry(s, slope, lo, hi)
    trend_color = PREMIUM_GREEN if slope >= 0 else PREMIUM_RED
    ci_alpha = 0.18 if bool(mmk["Significant"]) else 0.08

    ax.bar(
        yrs, vals,
        width=0.72,
        color=OBSERVED_BAR_COLOR,
        edgecolor="none",
        alpha=0.90,
        zorder=1
    )
    ax.plot(
        yrs, vals,
        color=OBSERVED_COLOR,
        lw=1.2,
        marker="o",
        markersize=3.8,
        markerfacecolor="white",
        markeredgewidth=0.8,
        zorder=3
    )
    ax.fill_between(
        yrs, fit_lo, fit_hi,
        color=CI_COLOR,
        alpha=ci_alpha,
        zorder=2
    )
    ax.plot(
        yrs, fit,
        color=trend_color,
        lw=3.0,
        zorder=4
    )

    if with_pettitt and pettitt_df is not None:
        pet = pettitt_df[
            (pettitt_df["Scale"] == scale) &
            (pettitt_df["Station"] == station)
        ].iloc[0]
        cp_year = pet["Change_Point_Year"]
        if pd.notna(cp_year):
            ax.axvline(
                cp_year,
                color=PETTITT_COLOR,
                linestyle="--",
                lw=2.0,
                zorder=5
            )
            yr_min, yr_max = np.nanmin(yrs), np.nanmax(yrs)
            shift = 0.4 if cp_year < ((yr_min + yr_max) / 2) else -2.2
            y_top = ax.get_ylim()[1]
            ax.text(
                cp_year + shift,
                y_top * 0.90,
                f"CP: {int(cp_year)}",
                color=PETTITT_COLOR,
                fontsize=TEXTBOX_SIZE,
                fontweight="bold"
            )

    txt = (
        f"Z = {mmk['Z']:.2f}\n"
        f"p = {mmk['p-value']:.4f}\n"
        f"Slope = {slope:.2f} mm/yr"
    )
    text_x = 0.67
    cp_year_local = None
    if with_pettitt and pettitt_df is not None:
        pet_local = pettitt_df[
            (pettitt_df["Scale"] == scale) &
            (pettitt_df["Station"] == station)
        ].iloc[0]
        cp_year_local = pet_local["Change_Point_Year"]
    if pd.notna(cp_year_local):
        mid_year = float(np.nanmedian(yrs))
        text_x = 0.02 if float(cp_year_local) >= mid_year else 0.67

    ax.text(
        text_x,
        0.95,
        txt,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=TEXTBOX_SIZE,
        bbox=dict(
            facecolor="white",
            edgecolor="#BDBDBD",
            alpha=0.95,
            boxstyle="round,pad=0.40"
        ),
        zorder=10
    )

    _apply_axes_style(
        ax,
        xlabel="Year" if show_xlabel else "",
        ylabel="Precipitation (mm)" if show_ylabel else ""
    )

def _trend_legend_handles(with_pettitt: bool) -> List:

    items = [
        Patch(facecolor=OBSERVED_BAR_COLOR, edgecolor="none", label="Observed Rainfall"),
        Patch(facecolor=CI_COLOR, edgecolor="none", alpha=0.25, label="95% Confidence Interval"),
        Line2D([0], [0], color=PREMIUM_GREEN, lw=3.0, label="Increasing Trend (Sen's Slope > 0)"),
        Line2D([0], [0], color=PREMIUM_RED, lw=3.0, label="Decreasing Trend (Sen's Slope < 0)")
    ]
    if with_pettitt:
        items.append(
            Line2D([0], [0], color=PETTITT_COLOR, lw=2.0, linestyle="--", label="Pettitt Change Point")
        )
    return items

# =============================================================================
# PUBLICATION CLASSIC / LUXURY
# =============================================================================

def elite_triple_panel(
    station: str,
    scales: Dict[str, pd.DataFrame],
    mmk_df: pd.DataFrame,
    sens_df: pd.DataFrame,
    pettitt_df: pd.DataFrame,
    outdir: Path
) -> None:

    dirs = _figure_dirs(outdir)

    fig, axes = plt.subplots(
        3, 1,
        figsize=(12, 14),
        constrained_layout=True
    )
    fig.patch.set_facecolor(BACKGROUND_COLOR)

    for i, scale in enumerate(SCALE_ORDER):
        ax = axes[i]
        _draw_trend_panel(
            ax, station, scale, scales, mmk_df, sens_df,
            with_pettitt=False,
            show_ylabel=True,
            show_xlabel=True
        )
        ax.set_title(PANEL_SUBTITLE[scale], fontsize=PANEL_TITLE_SIZE, fontweight="bold", loc="left")

    fig.suptitle(
        f"Trend Analysis: {_station_label(station)}",
        fontsize=FIG_TITLE_SIZE,
        fontweight="bold"
    )
    lg = fig.legend(
        handles=_trend_legend_handles(with_pettitt=False),
        loc="lower center",
        bbox_to_anchor=(0.5, -0.02),
        ncol=4,
        frameon=True,
        fontsize=LEGEND_SIZE + 1
    )
    _style_legend(lg)

    _save_figure(fig, dirs["classic_single"] / f"PublicationClassic_{station}")

def luxury_pettitt_panel(
    station: str,
    scales: Dict[str, pd.DataFrame],
    mmk_df: pd.DataFrame,
    sens_df: pd.DataFrame,
    pettitt_df: pd.DataFrame,
    outdir: Path
) -> None:

    dirs = _figure_dirs(outdir)

    fig, axes = plt.subplots(
        3, 1,
        figsize=(12, 14),
        constrained_layout=True
    )
    fig.patch.set_facecolor(BACKGROUND_COLOR)

    for i, scale in enumerate(SCALE_ORDER):
        ax = axes[i]
        _draw_trend_panel(
            ax, station, scale, scales, mmk_df, sens_df,
            pettitt_df=pettitt_df,
            with_pettitt=True,
            show_ylabel=True,
            show_xlabel=True
        )
        ax.set_title(PANEL_SUBTITLE[scale], fontsize=PANEL_TITLE_SIZE, fontweight="bold", loc="left")

    fig.suptitle(
        f"Trend Analysis: {_station_label(station)}",
        fontsize=FIG_TITLE_SIZE,
        fontweight="bold"
    )
    lg = fig.legend(
        handles=_trend_legend_handles(with_pettitt=True),
        loc="lower center",
        bbox_to_anchor=(0.5, -0.02),
        ncol=5,
        frameon=True,
        fontsize=LEGEND_SIZE + 1
    )
    _style_legend(lg)

    _save_figure(fig, dirs["luxury_single"] / f"LuxuryPettittQ1_{station}")

def plot_publication_classic_multistation(
    scales: Dict[str, pd.DataFrame],
    mmk_df: pd.DataFrame,
    sens_df: pd.DataFrame,
    outdir: Path
) -> None:

    dirs = _figure_dirs(outdir)
    stations = list(scales["annual"].columns)
    if len(stations) == 0:
        return

    for scale in SCALE_ORDER:
        ncols = min(3, max(1, len(stations)))
        nrows = int(np.ceil(len(stations) / ncols))
        fig, axes = plt.subplots(
            nrows, ncols,
            figsize=(6.2 * ncols, 4.2 * nrows),
            squeeze=False,
            constrained_layout=True
        )
        fig.patch.set_facecolor(BACKGROUND_COLOR)
        for i, station in enumerate(stations):
            ax = axes[i // ncols, i % ncols]
            _draw_trend_panel(
                ax, station, scale, scales, mmk_df, sens_df,
                with_pettitt=False,
                show_ylabel=(i % ncols == 0),
                show_xlabel=(i // ncols == nrows - 1)
            )
            ax.set_title(_station_label(station), fontsize=PANEL_TITLE_SIZE, fontweight="bold")
        for j in range(len(stations), nrows * ncols):
            axes[j // ncols, j % ncols].set_visible(False)
        fig.suptitle(
            f"Publication Classic: {SCALE_RAIN_TITLE[scale]}",
            fontsize=FIG_TITLE_SIZE,
            fontweight="bold"
        )
        lg = fig.legend(
            handles=_trend_legend_handles(with_pettitt=False),
            loc="lower center",
            bbox_to_anchor=(0.5, -0.02),
            ncol=4,
            frameon=True,
            fontsize=LEGEND_SIZE + 1
        )
        _style_legend(lg)
        _save_figure(fig, dirs["classic_multi"] / f"PublicationClassic_{SCALE_TAG[scale]}")

def plot_luxury_pettitt_multistation(
    scales: Dict[str, pd.DataFrame],
    mmk_df: pd.DataFrame,
    sens_df: pd.DataFrame,
    pettitt_df: pd.DataFrame,
    outdir: Path
) -> None:

    dirs = _figure_dirs(outdir)
    stations = list(scales["annual"].columns)
    if len(stations) == 0:
        return

    for scale in SCALE_ORDER:
        ncols = min(3, max(1, len(stations)))
        nrows = int(np.ceil(len(stations) / ncols))
        fig, axes = plt.subplots(
            nrows, ncols,
            figsize=(6.2 * ncols, 4.2 * nrows),
            squeeze=False,
            constrained_layout=True
        )
        fig.patch.set_facecolor(BACKGROUND_COLOR)
        for i, station in enumerate(stations):
            ax = axes[i // ncols, i % ncols]
            _draw_trend_panel(
                ax, station, scale, scales, mmk_df, sens_df,
                pettitt_df=pettitt_df,
                with_pettitt=True,
                show_ylabel=(i % ncols == 0),
                show_xlabel=(i // ncols == nrows - 1)
            )
            ax.set_title(_station_label(station), fontsize=PANEL_TITLE_SIZE, fontweight="bold")
        for j in range(len(stations), nrows * ncols):
            axes[j // ncols, j % ncols].set_visible(False)
        fig.suptitle(
            f"Luxury Pettitt Q1: {SCALE_RAIN_TITLE[scale]}",
            fontsize=FIG_TITLE_SIZE,
            fontweight="bold"
        )
        lg = fig.legend(
            handles=_trend_legend_handles(with_pettitt=True),
            loc="lower center",
            bbox_to_anchor=(0.5, -0.02),
            ncol=5,
            frameon=True,
            fontsize=LEGEND_SIZE + 1
        )
        _style_legend(lg)
        _save_figure(fig, dirs["luxury_multi"] / f"LuxuryPettittQ1_{SCALE_TAG[scale]}")

# =============================================================================
# ADVANCED PUBLICATION FIGURES
# =============================================================================

def plot_autocorrelation_correlogram(
    scales: Dict[str, pd.DataFrame],
    mmk_df: pd.DataFrame,
    outdir: Path
) -> None:

    dirs = _figure_dirs(outdir)

    for scale in SCALE_ORDER:
        df = scales[scale]
        selected = []

        for station in df.columns:
            s = df[station].dropna()
            n = len(s)
            if n < MIN_YEARS:
                continue
            mmk_row = mmk_df[
                (mmk_df["Scale"] == scale) &
                (mmk_df["Station"] == station)
            ]
            if mmk_row.empty:
                continue

            if "Max_Lag_Used" in mmk_row.columns:
                max_lag = int(mmk_row.iloc[0]["Max_Lag_Used"])
            else:
                max_lag = mmk_max_lag_from_n(n)

            if max_lag < 1:
                continue
            vals = s.values.astype(float)
            lags = np.arange(1, max_lag + 1)
            rvals = np.array([
                np.corrcoef(vals[lag:], vals[:-lag])[0, 1]
                for lag in lags
            ], dtype=float)
            sig_thr = 1.96 / np.sqrt(n)
            sig_mask = np.abs(rvals) > sig_thr
            mmk_sig = (not mmk_row.empty) and bool(mmk_row.iloc[0]["Significant"])
            if mmk_sig or bool(np.any(sig_mask)):
                selected.append((station, lags, rvals, sig_mask, sig_thr, max_lag))

        if len(selected) == 0:
            continue

        ncols = 3
        nrows = int(np.ceil(len(selected) / ncols))
        fig, axes = plt.subplots(
            nrows, ncols,
            figsize=(5.2 * ncols, 3.8 * nrows),
            squeeze=False,
            constrained_layout=True
        )
        fig.patch.set_facecolor(BACKGROUND_COLOR)

        for i, (station, lags, rvals, sig_mask, sig_thr, max_lag) in enumerate(selected):
            ax = axes[i // ncols, i % ncols]
            colors = np.where(sig_mask, PREMIUM_GOLD, NON_SIGNIF_COLOR)
            ax.bar(lags, rvals, color=colors, edgecolor="#8F8F8F", linewidth=0.6, zorder=3)
            ax.axhline(sig_thr, color=PREMIUM_RED, linestyle="--", linewidth=1.0, zorder=2)
            ax.axhline(-sig_thr, color=PREMIUM_RED, linestyle="--", linewidth=1.0, zorder=2)
            ax.axhline(0, color="#777777", linewidth=0.8, zorder=1)
            ax.set_ylim(-1, 1)
            ax.set_xticks(lags)
            ax.set_title(
                f"{_station_label(station)}\n({SCALE_LABEL[scale]})",
                fontsize=PANEL_TITLE_SIZE,
                fontweight="bold"
            )
            if i // ncols == nrows - 1:
                ax.set_xlabel("Lag", fontsize=AXIS_LABEL_SIZE, fontweight="bold")
            if i % ncols == 0:
                ax.set_ylabel("Autocorrelation", fontsize=AXIS_LABEL_SIZE, fontweight="bold")
            _apply_axes_style(ax, show_grid=True)

            f1, ax1 = plt.subplots(
                1, 1,
                figsize=(5.2, 4.0),
                constrained_layout=True
            )
            f1.patch.set_facecolor(BACKGROUND_COLOR)
            ax1.bar(lags, rvals, color=colors, edgecolor="#8F8F8F", linewidth=0.6, zorder=3)
            ax1.axhline(sig_thr, color=PREMIUM_RED, linestyle="--", linewidth=1.0, zorder=2)
            ax1.axhline(-sig_thr, color=PREMIUM_RED, linestyle="--", linewidth=1.0, zorder=2)
            ax1.axhline(0, color="#777777", linewidth=0.8, zorder=1)
            ax1.set_ylim(-1, 1)
            ax1.set_xticks(lags)
            ax1.set_title(
                f"{_station_label(station)}\n({SCALE_LABEL[scale]})",
                fontsize=PANEL_TITLE_SIZE,
                fontweight="bold"
            )
            _apply_axes_style(ax1, xlabel="Lag", ylabel="Autocorrelation")
            _save_figure(f1, dirs["acf_single"] / f"ACF_{SCALE_TAG[scale]}_{station}")

        for j in range(len(selected), nrows * ncols):
            axes[j // ncols, j % ncols].set_visible(False)

        fig.suptitle(
            f"Autocorrelation Structure:\n{SCALE_RAIN_TITLE[scale]}",
            fontsize=FIG_TITLE_SIZE,
            fontweight="bold"
        )
        lg = fig.legend(
            handles=[
                Patch(facecolor=PREMIUM_GOLD, edgecolor="#8F8F8F", label="Significant autocorrelation"),
                Patch(facecolor=NON_SIGNIF_COLOR, edgecolor="#8F8F8F", label="Non-significant"),
                Line2D([0], [0], color=PREMIUM_RED, linestyle="--", lw=1.0, label="95% significance limit")
            ],
            loc="lower center",
            bbox_to_anchor=(0.5, -0.02),
            ncol=3,
            frameon=True,
            fontsize=LEGEND_SIZE + 1
        )
        _style_legend(lg)
        fig.text(
            0.5,
            -0.04,
            "Golden bars indicate |r| > 1.96/sqrt(N); lag range follows MMK (1..floor(N/3))",
            ha="center",
            va="top",
            fontsize=TEXTBOX_SIZE
        )
        _save_figure(fig, dirs["acf_combined"] / f"ACF_{SCALE_TAG[scale]}")

def plot_significant_timeseries(
    scales: Dict[str, pd.DataFrame],
    mmk_df: pd.DataFrame,
    sens_df: pd.DataFrame,
    outdir: Path
) -> None:

    dirs = _figure_dirs(outdir)

    for scale in SCALE_ORDER:
        sig_rows = mmk_df[
            (mmk_df["Scale"] == scale) &
            (mmk_df["Significant"] == True)
        ]
        stations = sig_rows["Station"].tolist()
        if len(stations) == 0:
            continue

        ncols = min(3, len(stations))
        nrows = int(np.ceil(len(stations) / ncols))
        fig, axes = plt.subplots(
            nrows, ncols,
            figsize=(6.3 * ncols, 4.2 * nrows),
            squeeze=False,
            constrained_layout=True
        )
        fig.patch.set_facecolor(BACKGROUND_COLOR)

        for i, station in enumerate(stations):
            ax = axes[i // ncols, i % ncols]
            _draw_trend_panel(
                ax, station, scale, scales, mmk_df, sens_df,
                with_pettitt=False,
                show_ylabel=(i % ncols == 0),
                show_xlabel=(i // ncols == nrows - 1)
            )
            ax.set_title(_station_label(station), fontsize=PANEL_TITLE_SIZE, fontweight="bold")

            f1, ax1 = plt.subplots(
                1, 1,
                figsize=(7.4, 5.6),
                constrained_layout=True
            )
            f1.patch.set_facecolor(BACKGROUND_COLOR)
            _draw_trend_panel(
                ax1, station, scale, scales, mmk_df, sens_df,
                with_pettitt=False,
                show_ylabel=True,
                show_xlabel=True
            )
            ax1.set_title(_station_label(station), fontsize=PANEL_TITLE_SIZE, fontweight="bold")
            lg1 = f1.legend(
                handles=_trend_legend_handles(with_pettitt=False),
                loc="lower center",
                bbox_to_anchor=(0.5, -0.12),
                ncol=4,
                frameon=True,
                fontsize=LEGEND_SIZE + 1
            )
            _style_legend(lg1)
            _save_figure(f1, dirs["ts_single"] / f"SignificantTS_{SCALE_TAG[scale]}_{station}")

        for j in range(len(stations), nrows * ncols):
            axes[j // ncols, j % ncols].set_visible(False)

        fig.suptitle(
            f"MMK Significant Trends:\n{SCALE_RAIN_TITLE[scale]}",
            fontsize=FIG_TITLE_SIZE,
            fontweight="bold"
        )
        lg = fig.legend(
            handles=_trend_legend_handles(with_pettitt=False),
            loc="lower center",
            bbox_to_anchor=(0.5, -0.02),
            ncol=4,
            frameon=True,
            fontsize=LEGEND_SIZE + 1
        )
        _style_legend(lg)
        _save_figure(fig, dirs["ts_combined"] / f"SignificantTS_{SCALE_TAG[scale]}")

def plot_z_comparison(
    mk_df: pd.DataFrame,
    mmk_df: pd.DataFrame,
    outdir: Path
) -> None:

    dirs = _figure_dirs(outdir)

    for scale in SCALE_ORDER:
        merged = pd.merge(
            mk_df[mk_df["Scale"] == scale][["Station", "Z"]],
            mmk_df[mmk_df["Scale"] == scale][["Station", "Z"]],
            on="Station",
            suffixes=("_MK", "_MMK")
        ).sort_values("Station")

        if merged.empty:
            continue

        x = np.arange(len(merged))
        width = 0.36
        fig_w = max(12, len(merged) * 0.90)
        fig, ax = plt.subplots(
            1, 1,
            figsize=(fig_w, 6.4),
            constrained_layout=True
        )
        fig.patch.set_facecolor(BACKGROUND_COLOR)
        mmk_colors = [PREMIUM_GREEN if z >= 0 else PREMIUM_RED for z in merged["Z_MMK"].values]

        ax.bar(x - width / 2, merged["Z_MK"], width=width, color=PREMIUM_GOLD, edgecolor="#6E5E2A", label="MK Z")
        ax.bar(x + width / 2, merged["Z_MMK"], width=width, color=mmk_colors, edgecolor="#3A3A3A", label="MMK Z")
        ax.axhline(1.96, color=PREMIUM_RED, linestyle="--", linewidth=1.1)
        ax.axhline(-1.96, color=PREMIUM_RED, linestyle="--", linewidth=1.1)
        ax.axhline(0, color="#777777", linewidth=0.8)

        for i, (_, row) in enumerate(merged.iterrows()):
            delta = row["Z_MK"] - row["Z_MMK"]
            y = max(row["Z_MK"], row["Z_MMK"])
            ax.text(i, y + 0.12, f"\u0394Z={delta:.2f}", ha="center", va="bottom", fontsize=TEXTBOX_SIZE)

            f1, ax1 = plt.subplots(
                1, 1,
                figsize=(5.3, 4.0),
                constrained_layout=True
            )
            f1.patch.set_facecolor(BACKGROUND_COLOR)
            xx = np.array([0, 1], dtype=float)
            ax1.bar(xx[0], row["Z_MK"], color=PREMIUM_GOLD, width=0.58, edgecolor="#6E5E2A")
            ax1.bar(xx[1], row["Z_MMK"], color=PREMIUM_GREEN if row["Z_MMK"] >= 0 else PREMIUM_RED, width=0.58, edgecolor="#3A3A3A")
            ax1.axhline(1.96, color=PREMIUM_RED, linestyle="--", linewidth=1.0)
            ax1.axhline(-1.96, color=PREMIUM_RED, linestyle="--", linewidth=1.0)
            ax1.axhline(0, color="#777777", linewidth=0.8)
            ax1.set_xticks(xx)
            ax1.set_xticklabels(["MK", "MMK"])
            ax1.set_title(f"MK vs MMK:\nStation {row['Station']}", fontsize=PANEL_TITLE_SIZE, fontweight="bold")
            ax1.text(
                0.97,
                0.04,
                f"\u0394Z = {delta:.2f}",
                transform=ax1.transAxes,
                ha="right",
                va="bottom",
                fontsize=TEXTBOX_SIZE,
                bbox=dict(facecolor="white", edgecolor="#BDBDBD", alpha=0.95, boxstyle="round,pad=0.35")
            )
            _apply_axes_style(ax1, ylabel="Z statistic")
            _save_figure(f1, dirs["z_single"] / f"ZComparison_{SCALE_TAG[scale]}_{row['Station']}")

        ax.set_xticks(x)
        ax.set_xticklabels(
            [f"Station\n{s}" for s in merged["Station"].tolist()],
            rotation=45,
            ha="right"
        )
        ax.set_title(f"MK vs MMK:\n{SCALE_RAIN_TITLE[scale]}", fontsize=FIG_TITLE_SIZE, fontweight="bold")
        _apply_axes_style(ax, ylabel="Z statistic")
        lg = ax.legend(
            frameon=True,
            fontsize=LEGEND_SIZE + 1,
            loc="upper right",
            bbox_to_anchor=(0.995, 0.995),
            ncol=2
        )
        _style_legend(lg)
        fig.text(
            0.985,
            0.015,
            "\u0394Z = MK \u2212 MMK\npositive \u0394Z indicates inflation by autocorrelation.",
            ha="right",
            va="bottom",
            fontsize=TEXTBOX_SIZE,
            bbox=dict(facecolor="white", edgecolor="#BDBDBD", alpha=0.95, boxstyle="round,pad=0.45")
        )
        _save_figure(fig, dirs["z_combined"] / f"ZComparison_{SCALE_TAG[scale]}")

def plot_sens_slope_summary(
    sens_df: pd.DataFrame,
    mmk_df: pd.DataFrame,
    outdir: Path
) -> None:

    dirs = _figure_dirs(outdir)

    slope_tbl = (
        sens_df
        .pivot(index="Station", columns="Scale", values="Slope_mm_per_year")
        .reindex(columns=SCALE_ORDER)
        .sort_index()
    )

    if not slope_tbl.empty:
        vals = slope_tbl.values.astype(float)
        finite = vals[np.isfinite(vals)]
        vmax = max(np.max(np.abs(finite)) if finite.size > 0 else 1.0, 1.0e-8)
        cmap = mpl.colors.LinearSegmentedColormap.from_list(
            "sen_divergence",
            [PREMIUM_RED, "#F7F7F7", PREMIUM_GREEN]
        )
        fig, ax = plt.subplots(
            1, 1,
            figsize=(10.5, max(5.0, slope_tbl.shape[0] * 0.50)),
            constrained_layout=True
        )
        fig.patch.set_facecolor(BACKGROUND_COLOR)
        im = ax.imshow(vals, cmap=cmap, vmin=-vmax, vmax=vmax, aspect="auto")
        ax.set_xticks(np.arange(len(SCALE_ORDER)))
        ax.set_xticklabels([SCALE_LABEL[s] for s in SCALE_ORDER], fontsize=TICK_SIZE)
        ax.set_yticks(np.arange(slope_tbl.shape[0]))
        ax.set_yticklabels([_station_label(s) for s in slope_tbl.index.tolist()], fontsize=TICK_SIZE)
        for r in range(slope_tbl.shape[0]):
            for c in range(len(SCALE_ORDER)):
                v = vals[r, c]
                txt = "NA" if np.isnan(v) else f"{v:.2f}"
                color = "white" if (not np.isnan(v) and abs(v) > 0.55 * vmax) else "black"
                ax.text(c, r, txt, ha="center", va="center", fontsize=TEXTBOX_SIZE, color=color, fontweight="bold")
        cbar = fig.colorbar(im, ax=ax, pad=0.02)
        cbar.set_label("Sen's slope\n(mm yr\u207b\u00b9)", fontsize=AXIS_LABEL_SIZE, fontweight="bold")
        ax.set_title("Sen Slope Summary Heatmap", fontsize=FIG_TITLE_SIZE, fontweight="bold")
        _apply_axes_style(ax, show_grid=False)
        _save_figure(fig, dirs["sen_combined"] / "SenSlope_Heatmap")

    for scale in SCALE_ORDER:
        merged = pd.merge(
            sens_df[sens_df["Scale"] == scale],
            mmk_df[
                (mmk_df["Scale"] == scale) &
                (mmk_df["Significant"] == True)
            ][["Station", "Significant"]],
            on="Station",
            how="inner"
        )

        if merged.empty:
            continue

        merged["AbsSlope"] = merged["Slope_mm_per_year"].abs()
        merged = merged.sort_values("AbsSlope", ascending=True)
        err = merged["CI_High"].values - merged["CI_Low"].values
        colors = [PREMIUM_GREEN if v >= 0 else PREMIUM_RED for v in merged["Slope_mm_per_year"]]

        fig, ax = plt.subplots(
            1, 1,
            figsize=(10.2, max(4.8, len(merged) * 0.5)),
            constrained_layout=True
        )
        fig.patch.set_facecolor(BACKGROUND_COLOR)
        ax.barh(
            [_station_label(s) for s in merged["Station"].values],
            merged["Slope_mm_per_year"].values,
            color=colors,
            xerr=err,
            ecolor="#4C4C4C",
            capsize=3
        )
        ax.axvline(0, color="#777777", linewidth=0.8)
        ax.set_title(f"Significant Sen Slopes:\n{SCALE_RAIN_TITLE[scale]}", fontsize=FIG_TITLE_SIZE, fontweight="bold")
        _apply_axes_style(ax, xlabel="Slope (mm/year)", ylabel="Station")
        _save_figure(fig, dirs["sen_combined"] / f"SenSlope_Bar_{SCALE_TAG[scale]}")

    for station in sens_df["Station"].unique():
        st = sens_df[sens_df["Station"] == station].set_index("Scale").reindex(SCALE_ORDER)
        if st.empty:
            continue
        slopes = st["Slope_mm_per_year"].values.astype(float)
        err_low = np.abs(slopes - st["CI_Low"].values.astype(float))
        err_high = np.abs(st["CI_High"].values.astype(float) - slopes)
        yerr = np.vstack([err_low, err_high])
        colors = [PREMIUM_GREEN if v >= 0 else PREMIUM_RED for v in slopes]
        fig, ax = plt.subplots(
            1, 1,
            figsize=(6.2, 4.5),
            constrained_layout=True
        )
        fig.patch.set_facecolor(BACKGROUND_COLOR)
        ax.bar(np.arange(len(SCALE_ORDER)), slopes, color=colors, yerr=yerr, capsize=4, ecolor="#4C4C4C")
        ax.axhline(0, color="#777777", linewidth=0.8)
        ax.set_xticks(np.arange(len(SCALE_ORDER)))
        ax.set_xticklabels([SCALE_LABEL[s] for s in SCALE_ORDER], rotation=20, ha="right")
        ax.set_title(f"Sen Slope by Season:\nStation {station}", fontsize=PANEL_TITLE_SIZE, fontweight="bold")
        _apply_axes_style(ax, ylabel="Slope (mm/year)")
        _save_figure(fig, dirs["sen_single"] / f"SenSlope_{station}")

def plot_station_variability(
    scales: Dict[str, pd.DataFrame],
    outdir: Path
) -> None:

    dirs = _figure_dirs(outdir)
    rng = np.random.default_rng(42)

    for scale in SCALE_ORDER:
        df = scales[scale]
        med = df.median(skipna=True).sort_values()
        ordered = med.index.tolist()
        if len(ordered) == 0:
            continue
        data = [df[st].dropna().values.astype(float) for st in ordered]

        fig, ax = plt.subplots(
            1, 1,
            figsize=(max(11.5, len(ordered) * 0.75), 6.6),
            constrained_layout=True
        )
        fig.patch.set_facecolor(BACKGROUND_COLOR)
        bp = ax.boxplot(data, patch_artist=True, widths=0.60, showfliers=True)
        for box in bp["boxes"]:
            box.set(facecolor=OBSERVED_BAR_COLOR, edgecolor="#666666", linewidth=1.0)
        for median in bp["medians"]:
            median.set(color=PREMIUM_GOLD, linewidth=2.0)
        for whisker in bp["whiskers"]:
            whisker.set(color="#666666", linewidth=1.0)
        for cap in bp["caps"]:
            cap.set(color="#666666", linewidth=1.0)
        for flier in bp["fliers"]:
            flier.set(marker="o", markerfacecolor="#999999", markeredgecolor="#999999", markersize=3, alpha=0.45)

        means = []
        for i, arr in enumerate(data, start=1):
            jitter = rng.normal(0.0, 0.06, size=len(arr))
            ax.scatter(i + jitter, arr, s=12, color=OBSERVED_COLOR, alpha=0.50, linewidths=0, zorder=2)
            means.append(np.nanmean(arr) if len(arr) > 0 else np.nan)

            f1, ax1 = plt.subplots(
                1, 1,
                figsize=(5.4, 4.2),
                constrained_layout=True
            )
            f1.patch.set_facecolor(BACKGROUND_COLOR)
            arr_clean = np.asarray(arr, dtype=float)
            ax1.hist(arr_clean, bins=max(8, min(18, len(arr_clean) // 2 + 2)), color=OBSERVED_BAR_COLOR, edgecolor="#666666", alpha=0.95)
            ax1.axvline(np.nanmedian(arr_clean), color=PREMIUM_GOLD, linewidth=2.0, label="Median")
            ax1.axvline(np.nanmean(arr_clean), color=PREMIUM_GREEN, linewidth=1.8, linestyle="--", label="Mean")
            ax1.set_title(
                f"Rainfall Distribution:\n{_station_label(ordered[i-1])} ({SCALE_LABEL[scale]})",
                fontsize=PANEL_TITLE_SIZE,
                fontweight="bold"
            )
            _apply_axes_style(ax1, xlabel="Rainfall (mm)", ylabel="Frequency")
            lg1 = ax1.legend(frameon=True, fontsize=LEGEND_SIZE + 1, loc="upper right")
            _style_legend(lg1)
            _save_figure(f1, dirs["var_single"] / f"Variability_{SCALE_TAG[scale]}_{ordered[i-1]}")

        ax.scatter(np.arange(1, len(ordered) + 1), means, marker="D", s=45, color=PREMIUM_GREEN, edgecolors="white", linewidths=0.8, zorder=3)
        ax.set_xticks(np.arange(1, len(ordered) + 1))
        ax.set_xticklabels([f"Station\n{s}" for s in ordered], rotation=45, ha="right")
        ax.set_title(f"Rainfall Variability:\n{VARIABILITY_TITLE[scale]}", fontsize=FIG_TITLE_SIZE, fontweight="bold")
        _apply_axes_style(ax, xlabel="Station", ylabel="Rainfall (mm)")
        _save_figure(fig, dirs["var_combined"] / f"Boxplot_{SCALE_TAG[scale]}")
# =============================================================================
# EXPORT EXCEL
# =============================================================================

def export_excel(
    outpath: Path,
    desc_df: pd.DataFrame,
    mk_df: pd.DataFrame,
    mmk_df: pd.DataFrame,
    sens_df: pd.DataFrame,
    pettitt_df: pd.DataFrame,
    qc_df: pd.DataFrame
) -> None:

    """
    Export Excel workbook.
    """

    comparison = pd.merge(

        mk_df[
            ["Scale","Station","p-value"]
        ],

        mmk_df[
            ["Scale","Station","p-value"]
        ],

        on=["Scale","Station"],

        suffixes=("_MK","_MMK")
    )

    summary = mmk_df.groupby(

        "Scale"

    )["Significant"].value_counts()

    with pd.ExcelWriter(

        outpath,

        engine="openpyxl"
    ) as writer:

        desc_df.to_excel(
            writer,
            sheet_name="1_Descriptive",
            index=False
        )

        mk_df.to_excel(
            writer,
            sheet_name="2_Standard_MK",
            index=False
        )

        mmk_df.to_excel(
            writer,
            sheet_name="3_Modified_MK",
            index=False
        )

        pettitt_df.to_excel(
            writer,
            sheet_name="4_Pettitt_CP",
            index=False
        )

        sens_df.to_excel(
            writer,
            sheet_name="5_Sens_Slope",
            index=False
        )

        comparison.to_excel(
            writer,
            sheet_name="6_Comparison",
            index=False
        )

        summary.to_frame(
            "Count"
        ).to_excel(
            writer,
            sheet_name="7_Research_Summary"
        )

        qc_df.to_excel(
            writer,
            sheet_name="QC_Report"
        )

        wb = writer.book

        for ws in wb.worksheets:

            for row in ws.iter_rows():

                for cell in row:

                    cell.alignment = Alignment(

                        vertical="center",

                        wrap_text=True
                    )

# =============================================================================
# MARKDOWN SUMMARY
# =============================================================================

def write_markdown_summary(
    outpath: Path,
    mmk_df: pd.DataFrame,
    pettitt_df: pd.DataFrame
) -> None:

    """
    Research summary markdown.
    """

    lines = []

    lines.append("# Research Summary\n")

    lines.append("## Trend Overview\n")

    for scale in mmk_df["Scale"].unique():

        sub = mmk_df[

            mmk_df["Scale"] == scale
        ]

        sig = int(

            sub["Significant"].sum()
        )

        total = len(sub)

        lines.append(

            f"- {scale}: "
            f"{sig}/{total} significant trends"
        )

    lines.append("\n## Methodological Notes\n")

    lines.append(
        "- Modified MK follows Hamed & Rao (1998)."
    )

    lines.append(
        "- Sen's slope CI follows Gilbert (1987)."
    )

    lines.append(
        "- FDR correction recommended for multiple testing."
    )

    lines.append("\n## Limitations\n")

    lines.append(
        "- Pettitt identifies one dominant change point only."
    )

    with open(
        outpath,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "\n".join(lines)
        )

# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    """
    Main workflow.
    """

    if len(sys.argv) < 2:

        print(
            "\nUsage:\n"
            "python rainfall_trend_analysis_obs_mmk2.py [datafile]\n"
        )

        return

    filepath = sys.argv[1]

    print("="*80)

    print(VERSION)

    print("="*80)

    # =========================================================================
    # OUTPUT
    # =========================================================================

    project_root = Path.cwd()

    results_root = project_root / "RESULTS"

    results_root.mkdir(
        exist_ok=True
    )

    outdir = create_output_folder(
        results_root
    )

    # =========================================================================
    # LOAD
    # =========================================================================

    print("[1] Loading data")

    raw = load_data(filepath)

    # =========================================================================
    # QC
    # =========================================================================

    print("[2] Quality control")

    daily, qc_df = quality_control(raw)

    # =========================================================================
    # AGGREGATION
    # =========================================================================

    print("[3] Temporal aggregation")

    scales = aggregate_scales(daily)

    # =========================================================================
    # DESCRIPTIVE
    # =========================================================================

    print("[4] Descriptive statistics")

    desc_df = descriptive_statistics(

        scales,

        daily
    )

    # =========================================================================
    # TREND ANALYSIS
    # =========================================================================

    print("[5] Trend analysis")

    (
        mk_df,
        mmk_df,
        sens_df,
        pettitt_df

    ) = run_trend_analysis(scales)

    # =========================================================================
    # FIGURES
    # =========================================================================

    print("[6] Publication-quality figures")

    for station in daily.columns:

        elite_triple_panel(
            station,
            scales,
            mmk_df,
            sens_df,
            pettitt_df,
            outdir
        )

        luxury_pettitt_panel(
            station,
            scales,
            mmk_df,
            sens_df,
            pettitt_df,
            outdir
        )

    plot_publication_classic_multistation(
        scales,
        mmk_df,
        sens_df,
        outdir
    )

    plot_luxury_pettitt_multistation(
        scales,
        mmk_df,
        sens_df,
        pettitt_df,
        outdir
    )

    print("[6B] Advanced publication figures")

    plot_autocorrelation_correlogram(
        scales,
        mmk_df,
        outdir
    )

    plot_significant_timeseries(
        scales,
        mmk_df,
        sens_df,
        outdir
    )

    plot_z_comparison(
        mk_df,
        mmk_df,
        outdir
    )

    plot_sens_slope_summary(
        sens_df,
        mmk_df,
        outdir
    )

    plot_station_variability(
        scales,
        outdir
    )

    # =========================================================================
    # EXCEL
    # =========================================================================

    print("[7] Excel export")

    export_excel(

        outdir / "Rainfall_Trend_Results.xlsx",

        desc_df,

        mk_df,

        mmk_df,

        sens_df,

        pettitt_df,

        qc_df
    )

    # =========================================================================
    # MARKDOWN
    # =========================================================================

    print("[8] Markdown summary")

    write_markdown_summary(

        outdir / "Research_Summary.md",

        mmk_df,

        pettitt_df
    )

    print("\nDONE")

    print(f"\nResults:\n{outdir}")

# =============================================================================

if __name__ == "__main__":

    main()

# =============================================================================
