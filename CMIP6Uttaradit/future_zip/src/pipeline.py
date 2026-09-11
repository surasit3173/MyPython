"""
pipeline.py
===========
Data loading, quality control, aggregation, and ENSO-independent / ENSO-dependent
statistical analysis for the Prachuap Khiri Khan ENSO-rainfall study.

Design rules (per project requirements):
  * Never fabricate or impute missing data. Gaps are reported, not filled.
  * Every aggregate is validated for completeness before use.
  * All numeric outputs are written to .xlsx; nothing is hard-coded.
"""
from __future__ import annotations
import logging
import numpy as np
import pandas as pd
from scipy import stats

from . import config as C
from .mktrend import mann_kendall, tfpw_mk, modified_mk_hamed_rao, tfpw_diagnostics

log = logging.getLogger("pipeline")


# --------------------------------------------------------------------------- #
# STEP 0 - LOAD
# --------------------------------------------------------------------------- #
def load_rainfall() -> pd.DataFrame:
    """Load daily multi-station rainfall and build a daily areal series.

    Returns a DataFrame indexed by date with columns:
        <station ids...>, AREAL
    The provided file stores 12 gauges (cols 500xxx) on YEAR/MONTH/DAY rows.
    """
    df = pd.read_excel(C.RAIN_FILE, sheet_name=C.RAIN_SHEET)
    missing_cols = [s for s in C.STATION_IDS if s not in df.columns]
    if missing_cols:
        raise ValueError(f"Expected station columns missing: {missing_cols}")

    # Build calendar; invalid dates -> NaT, then reported (never silently dropped)
    df["date"] = pd.to_datetime(
        dict(year=df["YEAR"], month=df["MONTH"], day=df["DAY"]),
        errors="coerce")
    n_bad = int(df["date"].isna().sum())
    if n_bad:
        raise ValueError(f"{n_bad} invalid calendar dates encountered in input.")
    df = df.set_index("date").sort_index()

    stations = df[C.STATION_IDS].astype(float)
    areal = _build_areal(stations)
    out = stations.copy()
    out["AREAL"] = areal
    log.info("Loaded %d daily records, %d stations, %s -> %s",
             len(out), len(C.STATION_IDS), out.index.min().date(),
             out.index.max().date())
    return out


def _thiessen_weights() -> pd.Series:
    """Voronoi-area (Thiessen) weights from station coordinates, clipped to the
    convex hull of the gauge network. Returned normalised to sum 1."""
    from scipy.spatial import Voronoi, ConvexHull
    from shapely.geometry import Polygon, MultiPoint  # optional dependency
    coords = pd.read_excel(C.COORD_FILE)
    coords.columns = [str(c).strip() for c in coords.columns]
    coords = coords[coords["station"].isin(C.STATION_IDS)]
    pts = coords[["longitude", "latitude"]].to_numpy()
    hull = MultiPoint(pts).convex_hull.buffer(0.05)
    vor = Voronoi(pts)
    weights = {}
    for i, sid in enumerate(coords["station"].to_numpy()):
        region = vor.regions[vor.point_region[i]]
        if not region or -1 in region:
            poly = hull
        else:
            poly = Polygon([vor.vertices[v] for v in region]).intersection(hull)
        weights[sid] = poly.area if not poly.is_empty else 0.0
    w = pd.Series(weights, dtype=float)
    return w / w.sum()


def _build_areal(stations: pd.DataFrame) -> pd.Series:
    if C.AREAL_METHOD == "thiessen":
        try:
            w = _thiessen_weights().reindex(C.STATION_IDS)
            log.info("Thiessen weights: %s", w.round(3).to_dict())
            return stations.mul(w.values, axis=1).sum(axis=1)
        except Exception as e:  # pragma: no cover - optional deps
            log.warning("Thiessen weighting unavailable (%s); using areal mean.", e)
    return stations.mean(axis=1)


# --------------------------------------------------------------------------- #
# STEP 1 - QUALITY CONTROL
# --------------------------------------------------------------------------- #
def quality_control(daily: pd.DataFrame) -> dict:
    """Per-station QC. Returns dict of report DataFrames and a hard pass/fail."""
    rows = []
    stations = C.STATION_IDS
    full_range = pd.date_range(f"{C.START_YEAR}-01-01", f"{C.END_YEAR}-12-31",
                               freq="D")
    missing_dates = full_range.difference(daily.index)
    dup_dates = daily.index[daily.index.duplicated()]

    for s in stations:
        col = daily[s]
        rows.append(dict(
            station=s,
            n=int(col.shape[0]),
            n_missing=int(col.isna().sum()),
            n_negative=int((col < 0).sum()),
            n_zero=int((col == 0).sum()),
            pct_zero=round((col == 0).mean() * 100, 2),
            min=float(col.min()), max=float(col.max()),
            mean=round(float(col.mean()), 3),
        ))
    qc = pd.DataFrame(rows)
    summary = pd.DataFrame([dict(
        first_date=daily.index.min(), last_date=daily.index.max(),
        n_days=len(daily), n_expected_days=len(full_range),
        n_missing_calendar_days=len(missing_dates),
        n_duplicate_dates=len(dup_dates),
        n_stations=len(stations),
        total_missing_values=int(daily[stations].isna().sum().sum()),
        total_negative_values=int((daily[stations] < 0).sum().sum()),
    )])
    hard_fail = (summary["n_missing_calendar_days"].iloc[0] > 0
                 or summary["n_duplicate_dates"].iloc[0] > 0
                 or summary["total_missing_values"].iloc[0] > 0
                 or summary["total_negative_values"].iloc[0] > 0)
    return dict(per_station=qc, summary=summary, passed=not hard_fail,
                missing_dates=pd.Series(missing_dates, name="missing_date"))


# --------------------------------------------------------------------------- #
# STEP 2 - AGGREGATION
# --------------------------------------------------------------------------- #
def aggregate(daily: pd.DataFrame, col: str = "AREAL"):
    """Return monthly, annual, wet-season, dry-season totals for `col`.

    Dry season Y = Nov(Y-1)+Dec(Y-1)+Jan(Y)+Feb(Y)+Mar(Y)+Apr(Y).
    A season/year is emitted only if ALL constituent days are present (no
    imputation). Completeness is enforced downstream by validate_aggregates().
    """
    s = daily[col]
    monthly = s.resample("MS").sum().rename("rain_mm").to_frame()
    monthly["year"] = monthly.index.year
    monthly["month"] = monthly.index.month
    # day counts to verify completeness
    daycount = s.resample("MS").count()
    monthly["n_days"] = daycount.values

    annual = (s.groupby(s.index.year).sum().rename_axis("year")
              .rename("annual_mm").to_frame())
    annual["n_days"] = s.groupby(s.index.year).count().values

    # WET season (May-Oct) keyed by calendar year
    wmask = s.index.month.isin(C.WET_MONTHS)
    wet = (s[wmask].groupby(s[wmask].index.year).sum()
           .rename_axis("year").rename("wet_mm").to_frame())
    wet["n_days"] = s[wmask].groupby(s[wmask].index.year).count().values

    # DRY season (Nov(Y-1)-Apr(Y)) keyed by ending year Y
    idx = s.index
    dry_year = np.where(idx.month.isin([11, 12]), idx.year + 1, idx.year)
    dmask = idx.month.isin(C.DRY_MONTHS)
    dser = pd.Series(s.values[dmask], index=dry_year[dmask])
    dry = (dser.groupby(level=0).sum().rename_axis("year")
           .rename("dry_mm").to_frame())
    dry["n_days"] = dser.groupby(level=0).count().values

    return dict(monthly=monthly, annual=annual, wet=wet, dry=dry)


def validate_aggregates(agg: dict) -> list[str]:
    """Hard validation: report (do not silently fix) any incompleteness."""
    issues = []
    yrs = set(range(C.START_YEAR, C.END_YEAR + 1))

    a = agg["annual"]
    if set(a.index) != yrs:
        issues.append(f"Annual years {set(a.index)} != expected {yrs}")
    bad = a.index[(a["n_days"] < 365)]
    # leap years legitimately have 366; non-leap 365
    for y in a.index:
        exp = 366 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 365
        if a.loc[y, "n_days"] != exp:
            issues.append(f"Annual {y}: {a.loc[y,'n_days']} days (expected {exp})")

    w = agg["wet"]
    for y in w.index:
        exp = 31*4 + 30*2  # May,Jul,Aug,Oct=31 ; Jun,Sep=30  -> 184 days
        if w.loc[y, "n_days"] != exp:
            issues.append(f"Wet {y}: {w.loc[y,'n_days']} days (expected {exp})")

    d = agg["dry"]
    # A dry season is complete only with all Nov(Y-1)..Apr(Y) days present:
    # 181 days, or 182 in a leap year (Feb of year Y). Incomplete seasons
    # (1981: no Nov/Dec 1980; 2015: no Jan-Apr 2015) MUST be excluded, never filled.
    def _dry_expected(y):
        leap = (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0))
        return 182 if leap else 181
    complete = [y for y in d.index if d.loc[y, "n_days"] == _dry_expected(y)]
    expected_complete = list(range(C.START_YEAR + 1, C.END_YEAR + 1))
    if complete != expected_complete:
        issues.append(f"Complete dry years {complete} != expected "
                      f"{expected_complete}")
    incomplete = [int(y) for y in d.index if y not in complete]
    if incomplete:
        log.info("Dry seasons excluded as incomplete (not imputed): %s", incomplete)

    mon = agg["monthly"]
    for ts, r in mon.iterrows():
        exp = ts.days_in_month
        if r["n_days"] != exp:
            issues.append(f"Month {ts.date()}: {int(r['n_days'])} days (exp {exp})")
    return issues


# --------------------------------------------------------------------------- #
# STEP 4 - DESCRIPTIVE STATISTICS
# --------------------------------------------------------------------------- #
def descriptive(series_map: dict[str, pd.Series]) -> pd.DataFrame:
    rows = []
    for name, x in series_map.items():
        x = x.dropna().astype(float)
        rows.append(dict(
            variable=name, n=int(x.size),
            mean=x.mean(), median=x.median(), min=x.min(), max=x.max(),
            std=x.std(ddof=1),
            cv_pct=(x.std(ddof=1) / x.mean() * 100) if x.mean() else np.nan,
            skew=stats.skew(x), kurtosis=stats.kurtosis(x),
        ))
    return pd.DataFrame(rows).round(3)


# --------------------------------------------------------------------------- #
# STEP 5 - CORRELATION (Pearson / Spearman with bootstrap-free CI)
# --------------------------------------------------------------------------- #
def _corr_ci(r, n, alpha=C.ALPHA):
    """Fisher z 95% CI for a correlation coefficient."""
    if n < 4 or abs(r) >= 1:
        return (np.nan, np.nan)
    z = np.arctanh(r)
    se = 1.0 / np.sqrt(n - 3)
    zc = stats.norm.ppf(1 - alpha / 2)
    return (np.tanh(z - zc * se), np.tanh(z + zc * se))


def correlation_table(pairs: dict[str, tuple[pd.Series, pd.Series]], method: str):
    rows = []
    for label, (a, b) in pairs.items():
        d = pd.concat([a, b], axis=1, join="inner").dropna()
        x, y = d.iloc[:, 0].values, d.iloc[:, 1].values
        if method == "pearson":
            r, p = stats.pearsonr(x, y)
        else:
            r, p = stats.spearmanr(x, y)
        lo, hi = _corr_ci(r, len(x))
        rows.append(dict(pair=label, method=method, n=len(x),
                         r=round(r, 4), p_value=round(p, 4),
                         ci95_low=round(lo, 4), ci95_high=round(hi, 4),
                         significant=bool(p < C.ALPHA)))
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# STEP 6 - LAG CORRELATION
# --------------------------------------------------------------------------- #
def lag_correlation(monthly_rain: pd.Series, nino34_monthly: pd.Series,
                    max_lag: int = 12):
    """Pearson r between monthly rainfall and Nino3.4 at lags 0..max_lag
    (Nino3.4 leading rainfall)."""
    d = pd.concat([monthly_rain.rename("rain"),
                   nino34_monthly.rename("nino")], axis=1, join="inner").dropna()
    rows = []
    for k in range(0, max_lag + 1):
        x = d["nino"].shift(k)
        dd = pd.concat([x, d["rain"]], axis=1).dropna()
        if len(dd) < 4:
            continue
        r, p = stats.pearsonr(dd.iloc[:, 0], dd.iloc[:, 1])
        rows.append(dict(lag_months=k, r=round(r, 4), p_value=round(p, 4),
                         n=len(dd), significant=bool(p < C.ALPHA)))
    tab = pd.DataFrame(rows)
    best = tab.iloc[tab["r"].abs().idxmax()]
    return tab, best


# --------------------------------------------------------------------------- #
# STEP 7/8 - ENSO COMPOSITE + GROUP COMPARISON
# --------------------------------------------------------------------------- #
def composite(series_by_var: dict[str, pd.Series], phase_by_year: pd.Series):
    rows = []
    for var, s in series_by_var.items():
        d = pd.concat([s.rename("v"), phase_by_year.rename("phase")],
                      axis=1, join="inner").dropna()
        for ph, g in d.groupby("phase"):
            rows.append(dict(variable=var, phase=ph, n=len(g),
                             mean=round(g["v"].mean(), 2),
                             median=round(g["v"].median(), 2),
                             std=round(g["v"].std(ddof=1), 2)))
    return pd.DataFrame(rows)


def group_comparison(series_by_var: dict[str, pd.Series], phase_by_year: pd.Series):
    rows = []
    for var, s in series_by_var.items():
        d = pd.concat([s.rename("v"), phase_by_year.rename("phase")],
                      axis=1, join="inner").dropna()
        groups = [g["v"].values for _, g in d.groupby("phase") if len(g) >= 3]
        labels = [ph for ph, g in d.groupby("phase") if len(g) >= 3]
        if len(groups) < 2:
            rows.append(dict(variable=var, test="insufficient groups",
                             statistic=np.nan, p_value=np.nan,
                             effect_size=np.nan, normal_all=np.nan))
            continue
        normal = all(stats.shapiro(g).pvalue > C.ALPHA
                     for g in groups if 3 <= len(g) <= 5000)
        if normal:
            stat, p = stats.f_oneway(*groups)
            test = "One-way ANOVA"
            # eta^2 effect size
            grand = np.concatenate(groups)
            ss_b = sum(len(g) * (g.mean() - grand.mean())**2 for g in groups)
            ss_t = ((grand - grand.mean())**2).sum()
            es = ss_b / ss_t if ss_t else np.nan
            es_name = "eta_squared"
        else:
            stat, p = stats.kruskal(*groups)
            test = "Kruskal-Wallis"
            N = sum(len(g) for g in groups)
            es = (stat - len(groups) + 1) / (N - len(groups)) if N > len(groups) else np.nan
            es_name = "epsilon_squared"
        rows.append(dict(variable=var, test=test, groups="|".join(map(str, labels)),
                         statistic=round(float(stat), 4), p_value=round(float(p), 4),
                         effect_size=round(float(es), 4), effect_metric=es_name,
                         normal_all=bool(normal), significant=bool(p < C.ALPHA)))
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# STEP 9/10 - TREND (TFPW-MK required + Hamed-Rao + Sen slope)
# --------------------------------------------------------------------------- #
def trend_table(series_by_var: dict[str, pd.Series]):
    """Return (tfpw_df, sens_df, cross_df) with TFPW-MK as primary, plus
    original MK and Hamed-Rao Modified MK as robustness cross-checks."""
    tfpw_rows, sens_rows, cross_rows = [], [], []
    for var, s in series_by_var.items():
        x = s.dropna().astype(float).values
        rt = tfpw_mk(x, C.ALPHA)
        rm = mann_kendall(x, C.ALPHA)
        rh = modified_mk_hamed_rao(x, C.ALPHA)
        tfpw_rows.append(dict(variable=var, n=rt.n, tau=round(rt.tau, 4),
                              z=round(rt.z, 4), p_value=round(rt.p_value, 4),
                              trend=rt.trend, significant=rt.significant,
                              lag1_autocorr=round(rt.autocorr_lag1, 4)
                              if rt.autocorr_lag1 is not None else None,
                              note=rt.note))
        sens_rows.append(dict(variable=var,
                              sens_slope_mm_per_year=round(rt.sens_slope, 4),
                              ci95_low=round(rt.sens_slope_lcl, 4),
                              ci95_high=round(rt.sens_slope_ucl, 4),
                              intercept=round(rt.intercept, 3)))
        for r in (rm, rh, rt):
            cross_rows.append(dict(variable=var, method=r.method, z=round(r.z, 4),
                                   p_value=round(r.p_value, 4), trend=r.trend,
                                   significant=r.significant,
                                   sens_slope=round(r.sens_slope, 4)))
    return (pd.DataFrame(tfpw_rows), pd.DataFrame(sens_rows),
            pd.DataFrame(cross_rows))


# --------------------------------------------------------------------------- #
# Multivariate predictor comparison (ENSO vs IOD vs both)
# --------------------------------------------------------------------------- #
def _ols(y: np.ndarray, X: np.ndarray):
    """Plain OLS with intercept. Returns dict with betas, se, t, p, R2, adjR2, AIC.

    X is the design matrix WITHOUT the intercept column (added here).
    Implemented in numpy/scipy for transparency and zero heavy dependencies.
    """
    n = len(y)
    Xd = np.column_stack([np.ones(n), X])
    k = Xd.shape[1]                      # params incl. intercept
    beta, *_ = np.linalg.lstsq(Xd, y, rcond=None)
    resid = y - Xd @ beta
    sse = float(resid @ resid)
    sst = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - sse / sst if sst > 0 else np.nan
    adj_r2 = 1.0 - (1.0 - r2) * (n - 1) / (n - k) if n > k else np.nan
    dof = n - k
    sigma2 = sse / dof if dof > 0 else np.nan
    XtX_inv = np.linalg.pinv(Xd.T @ Xd)
    se = np.sqrt(np.diag(sigma2 * XtX_inv))
    with np.errstate(divide="ignore", invalid="ignore"):
        tvals = beta / se
    pvals = 2.0 * stats.t.sf(np.abs(tvals), dof)
    # AIC for Gaussian OLS: n*ln(SSE/n) + 2*(k+1)  (k params + variance)
    aic = n * np.log(sse / n) + 2 * (k + 1) if sse > 0 else -np.inf
    return dict(beta=beta, se=se, t=tvals, p=pvals, r2=r2, adj_r2=adj_r2,
                aic=aic, n=n, k=k)


def _vif(X: np.ndarray) -> list[float]:
    """Variance inflation factor for each column of X (no intercept col)."""
    p = X.shape[1]
    vifs = []
    for j in range(p):
        yj = X[:, j]
        Xj = np.delete(X, j, axis=1)
        if Xj.shape[1] == 0:
            vifs.append(1.0)
            continue
        fit = _ols(yj, Xj)
        vifs.append(float(1.0 / (1.0 - fit["r2"])) if fit["r2"] < 1 else np.inf)
    return vifs


def predictor_comparison(rainfall: pd.Series,
                         predictors: dict[str, pd.Series],
                         label: str):
    """Compare Rainfall ~ each single predictor vs the full multivariate model.

    predictors: ordered {name: yearly_series}. All series are aligned on the
    common set of years (listwise deletion; nothing imputed). Returns
    (model_table, coef_table). model_table lists R2/adjR2/AIC/n for every model
    incl. each single-predictor model and the combined model; coef_table gives
    standardised-free coefficients, SE, t, p and VIF for the combined model.
    """
    names = list(predictors.keys())
    df = pd.concat([rainfall.rename("Y")] +
                   [predictors[n].rename(n) for n in names], axis=1).dropna()
    if len(df) < len(names) + 2:
        raise ValueError(f"{label}: too few overlapping years for regression")
    y = df["Y"].to_numpy(float)

    model_rows = []
    # single-predictor models
    for n in names:
        f = _ols(y, df[[n]].to_numpy(float))
        model_rows.append(dict(target=label, model=n, n=f["n"],
                               R2=round(f["r2"], 4), adj_R2=round(f["adj_r2"], 4),
                               AIC=round(f["aic"], 2),
                               slope_p=round(float(f["p"][1]), 4)))
    # combined model
    Xc = df[names].to_numpy(float)
    fc = _ols(y, Xc)
    model_rows.append(dict(target=label, model=" + ".join(names), n=fc["n"],
                           R2=round(fc["r2"], 4), adj_R2=round(fc["adj_r2"], 4),
                           AIC=round(fc["aic"], 2), slope_p=np.nan))
    # rank by AIC (lower is better) for an explicit "which explains best"
    mt = pd.DataFrame(model_rows)
    mt["AIC_rank"] = mt["AIC"].rank(method="min").astype(int)
    mt["best_by_AIC"] = mt["AIC_rank"] == 1

    # coefficient + VIF table for the combined model
    vifs = _vif(Xc)
    coef_rows = [dict(target=label, term="Intercept",
                      coef=round(float(fc["beta"][0]), 4),
                      se=round(float(fc["se"][0]), 4),
                      t=round(float(fc["t"][0]), 3),
                      p_value=round(float(fc["p"][0]), 4), VIF=np.nan)]
    for i, n in enumerate(names, start=1):
        coef_rows.append(dict(target=label, term=n,
                              coef=round(float(fc["beta"][i]), 4),
                              se=round(float(fc["se"][i]), 4),
                              t=round(float(fc["t"][i]), 3),
                              p_value=round(float(fc["p"][i]), 4),
                              VIF=round(vifs[i - 1], 3)))
    return mt, pd.DataFrame(coef_rows)


# --------------------------------------------------------------------------- #
# Per-station analysis (12 gauges x 3 timescales) + Taylor-diagram statistics
# --------------------------------------------------------------------------- #
def dry_expected(y: int) -> int:
    """Expected day count of dry season ending in year y (Nov(y-1)-Apr(y))."""
    leap = (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0))
    return 182 if leap else 181


def per_station_series(daily: pd.DataFrame) -> dict[int, dict[str, pd.Series]]:
    """{station_id: {'Annual':s, 'Wet':s, 'Dry':s}} using the SAME completeness
    rule as the areal analysis (incomplete dry seasons excluded, never filled)."""
    out: dict[int, dict[str, pd.Series]] = {}
    for sid in C.STATION_IDS:
        a = aggregate(daily, sid)
        annual = a["annual"]["annual_mm"]
        wet = a["wet"]["wet_mm"]
        dd = a["dry"]
        keep = [y for y in dd.index if dd.loc[y, "n_days"] == dry_expected(y)]
        dry = dd.loc[keep, "dry_mm"]
        out[sid] = {"Annual": annual, "Wet": wet, "Dry": dry}
    return out


def monthly_climatology_shift(
    daily: pd.DataFrame,
    windows: tuple[tuple[int, int], tuple[int, int]] = ((1981, 1990), (2005, 2014)),
) -> pd.DataFrame:
    """Mean monthly climatology and cumulative percentage for two time windows."""
    rows = []
    months = np.arange(1, 13)
    for sid in C.STATION_IDS:
        monthly = aggregate(daily, sid)["monthly"].reset_index()
        for start, end in windows:
            sub = monthly[(monthly["year"] >= start) & (monthly["year"] <= end)]
            clim = sub.groupby("month")["rain_mm"].mean().reindex(months)
            total = float(clim.sum())
            if total > 0 and np.isfinite(total):
                cumulative = clim.cumsum() / total * 100.0
            else:
                cumulative = pd.Series(np.nan, index=months)
            peak_month = int(clim.idxmax()) if clim.notna().any() else None
            for month in months:
                rows.append(dict(
                    station=sid,
                    period=f"{start}-{end}",
                    period_start=start,
                    period_end=end,
                    month=int(month),
                    mean_rain_mm=float(clim.loc[month]) if pd.notna(clim.loc[month]) else np.nan,
                    cumulative_pct=float(cumulative.loc[month]) if pd.notna(cumulative.loc[month]) else np.nan,
                    peak_month=peak_month,
                ))
    return pd.DataFrame(rows)


def q1_method_contrast_payload(
    ps: dict[int, dict[str, pd.Series]],
    station: int = 500003,
    timescale: str = "Wet",
) -> dict:
    """Station-level payload for the Q1 TFPW methodological contrast figure."""
    series = ps[station][timescale].dropna().astype(float)
    years = series.index.to_numpy(dtype=int)
    diag = tfpw_diagnostics(series.values, C.ALPHA)
    tfpw_years = years[1:] if diag.prewhitening_applied else years
    observed_aligned = series.values[1:] if diag.prewhitening_applied else series.values
    center_offset = float(np.median(observed_aligned) -
                          np.median(diag.trend_restored_series))
    trend_restored_centered = diag.trend_restored_series + center_offset
    tfpw_df = pd.DataFrame({
        "year": tfpw_years,
        "trend_restored_mm": trend_restored_centered,
        "trend_restored_raw_mm": diag.trend_restored_series,
        "residual_mm": diag.restored_residuals,
    })
    return {
        "station": station,
        "timescale": timescale,
        "observed": pd.DataFrame({"year": years, "rain_mm": series.values}),
        "tfpw": tfpw_df,
        "diagnostics": diag,
        "center_offset_mm": center_offset,
    }


def q1_spatial_coherence_inputs(ps: dict[int, dict[str, pd.Series]]) -> pd.DataFrame:
    """TFPW station trend table tailored to the tri-panel Q1 spatial map."""
    detail, _ = per_station_trend_all_methods(ps)
    tfpw = detail["TFPW_MK"].copy()
    tfpw["abs_sens_slope_mm_yr"] = tfpw["sens_slope_mm_yr"].abs()
    tfpw["abs_z"] = tfpw["z"].abs()
    return tfpw


def per_station_descriptive(ps: dict[int, dict[str, pd.Series]]) -> pd.DataFrame:
    rows = []
    for sid, by_var in ps.items():
        for var, s in by_var.items():
            x = s.dropna().astype(float)
            rows.append(dict(station=sid, timescale=var, n=int(x.size),
                             mean_mm=round(x.mean(), 1),
                             std_mm=round(x.std(ddof=1), 1),
                             cv_pct=round(x.std(ddof=1) / x.mean() * 100, 1)
                             if x.mean() else np.nan))
    return pd.DataFrame(rows)


def per_station_trend(ps: dict[int, dict[str, pd.Series]]) -> pd.DataFrame:
    """TFPW-MK + Sen slope per station per timescale (primary method)."""
    rows = []
    for sid, by_var in ps.items():
        for var, s in by_var.items():
            x = s.dropna().astype(float).values
            r = tfpw_mk(x, C.ALPHA)
            rows.append(dict(
                station=sid, timescale=var, n=r.n,
                sens_slope_mm_yr=round(r.sens_slope, 3),
                ci95_low=round(r.sens_slope_lcl, 3),
                ci95_high=round(r.sens_slope_ucl, 3),
                tau=round(r.tau, 3), p_value=round(r.p_value, 4),
                trend=r.trend, significant=bool(r.significant)))
    return pd.DataFrame(rows)


_TREND_METHODS = {
    "TFPW_MK": tfpw_mk,                       # primary (per spec)
    "Original_MK": mann_kendall,
    "Modified_MK_HamedRao": modified_mk_hamed_rao,
}


def per_station_trend_all_methods(ps: dict[int, dict[str, pd.Series]]):
    """Run all three trend tests per station x timescale.

    Returns (detail, comparison):
      detail      : {method_name: DataFrame} full statistics for each method
      comparison  : one row per station x timescale with each method's p-value,
                    significance, a methods-agree flag and the lag-1
                    autocorrelation, so divergence between methods is explicit.
    """
    detail = {name: [] for name in _TREND_METHODS}
    comp_rows = []
    for sid, by_var in ps.items():
        for var, s in by_var.items():
            x = s.dropna().astype(float).values
            res = {}
            for name, fn in _TREND_METHODS.items():
                r = fn(x, C.ALPHA)
                res[name] = r
                detail[name].append(dict(
                    station=sid, timescale=var, method=r.method, n=r.n,
                    S=round(r.S, 1), tau=round(r.tau, 4),
                    var_S=round(r.var_S, 2), z=round(r.z, 4),
                    p_value=round(r.p_value, 4), trend=r.trend,
                    significant=bool(r.significant),
                    sens_slope_mm_yr=round(r.sens_slope, 4),
                    ci95_low=round(r.sens_slope_lcl, 4),
                    ci95_high=round(r.sens_slope_ucl, 4),
                    intercept=round(r.intercept, 3),
                    lag1_autocorr=(round(r.autocorr_lag1, 4)
                                   if r.autocorr_lag1 is not None else None),
                    note=r.note))
            tf = res["TFPW_MK"]
            row = dict(station=sid, timescale=var, n=tf.n,
                       lag1_autocorr=(round(tf.autocorr_lag1, 4)
                                      if tf.autocorr_lag1 is not None else None),
                       sens_slope_mm_yr=round(tf.sens_slope, 4),
                       ci95_low=round(tf.sens_slope_lcl, 4),
                       ci95_high=round(tf.sens_slope_ucl, 4),
                       intercept=round(tf.intercept, 3))
            for name in _TREND_METHODS:
                row[f"{name}_z"] = round(res[name].z, 4)
                row[f"{name}_p"] = round(res[name].p_value, 4)
                row[f"{name}_sig"] = bool(res[name].significant)
            sigs = [res[n].significant for n in _TREND_METHODS]
            row["n_methods_significant"] = int(sum(sigs))
            row["methods_agree"] = bool(len(set(sigs)) == 1)
            comp_rows.append(row)
    detail_dfs = {n: pd.DataFrame(r) for n, r in detail.items()}
    return detail_dfs, pd.DataFrame(comp_rows)


def etccdi_trends(allidx: pd.DataFrame, index_names: list[str]) -> pd.DataFrame:
    """Per-station trend of each annual ETCCDI index: TFPW-MK primary +
    Hamed-Rao Modified-MK cross-check, Sen's slope with 95% CI."""
    rows = []
    for sid in allidx["station"].unique():
        sub = allidx[allidx["station"] == sid].sort_values("year")
        for idx in index_names:
            x = sub[idx].dropna().astype(float).values
            if len(x) < 4:
                continue
            rt = tfpw_mk(x, C.ALPHA)
            rh = modified_mk_hamed_rao(x, C.ALPHA)
            rows.append(dict(
                station=sid, index=idx, n=rt.n,
                sens_slope=round(rt.sens_slope, 4),
                ci95_low=round(rt.sens_slope_lcl, 4),
                ci95_high=round(rt.sens_slope_ucl, 4),
                tau=round(rt.tau, 4),
                tfpw_z=round(rt.z, 4), tfpw_p=round(rt.p_value, 4),
                tfpw_sig=bool(rt.significant),
                hamedrao_p=round(rh.p_value, 4), hamedrao_sig=bool(rh.significant),
                lag1_autocorr=(round(rt.autocorr_lag1, 4)
                               if rt.autocorr_lag1 is not None else None),
                methods_agree=bool(rt.significant == rh.significant),
                trend=rt.trend))
    return pd.DataFrame(rows)


def per_station_enso_corr(ps: dict[int, dict[str, pd.Series]],
                          nino_y: pd.Series, method: str = "pearson") -> pd.DataFrame:
    """Correlation of each station's seasonal rainfall with annual Nino-3.4."""
    rows = []
    for sid, by_var in ps.items():
        for var, s in by_var.items():
            d = pd.concat([s.rename("r"), nino_y.rename("n")],
                          axis=1, join="inner").dropna()
            if len(d) < 4:
                continue
            if method == "pearson":
                r, p = stats.pearsonr(d["r"], d["n"])
            else:
                r, p = stats.spearmanr(d["r"], d["n"])
            lo, hi = _corr_ci(r, len(d))
            rows.append(dict(station=sid, timescale=var, method=method,
                             n=len(d), r=round(r, 4), p_value=round(p, 4),
                             ci95_low=round(lo, 4), ci95_high=round(hi, 4),
                             significant=bool(p < C.ALPHA)))
    return pd.DataFrame(rows)


def taylor_stats(ps: dict[int, dict[str, pd.Series]],
                 areal_by_var: dict[str, pd.Series]) -> pd.DataFrame:
    """Taylor statistics of each station vs the areal-mean reference.

    For every timescale: Pearson correlation, std-dev ratio (sigma_station /
    sigma_areal) and the normalised centred RMS difference
    E' = sqrt(1 + ratio^2 - 2*ratio*corr). The reference (areal mean) sits at
    ratio = 1, corr = 1, E' = 0.
    """
    rows = []
    for var, ref in areal_by_var.items():
        ref = ref.dropna().astype(float)
        sref = ref.std(ddof=1)
        for sid, by_var in ps.items():
            s = by_var[var]
            d = pd.concat([s.rename("t"), ref.rename("r")],
                          axis=1, join="inner").dropna()
            if len(d) < 4 or sref == 0:
                continue
            corr = float(np.corrcoef(d["t"], d["r"])[0, 1])
            sstd = d["t"].std(ddof=1)
            ratio = sstd / sref
            crmsd = float(np.sqrt(max(1 + ratio ** 2 - 2 * ratio * corr, 0.0)))
            rows.append(dict(station=sid, timescale=var, n=len(d),
                             std_station=round(sstd, 2), std_ref=round(sref, 2),
                             std_ratio=round(ratio, 4), corr=round(corr, 4),
                             norm_crmsd=round(crmsd, 4)))
    return pd.DataFrame(rows)


def build_q1_standard_figures(
    daily: pd.DataFrame,
    station_case: int = 500003,
    timescale_case: str = "Wet",
):
    """Generate the dedicated Q1-ready figure trio in output/q1_standard."""
    from . import figures, gismap

    figures.init()
    ps = per_station_series(daily)
    clim = monthly_climatology_shift(daily)
    contrast = q1_method_contrast_payload(ps, station=station_case,
                                          timescale=timescale_case)
    spatial = q1_spatial_coherence_inputs(ps)

    figures.fig_q1_dual_axis_climatology_shift(clim)
    figures.fig_q1_methodological_contrast(contrast)
    area = gismap.StudyArea()
    gismap.q1_spatial_coherence_map(area, spatial)

    return {
        "climatology_shift": clim,
        "methodological_contrast": contrast,
        "spatial_coherence": spatial,
        "output_dir": C.Q1,
    }
