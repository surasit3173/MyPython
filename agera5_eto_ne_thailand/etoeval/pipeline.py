"""End-to-end pipelines.

Stage 1 (station data only - runs now): QC, completeness, homogeneity
screening, iterative wind-break masking, station PM-ETo reference ensemble
and its structural sensitivity.

Stage 2 (requires the AgERA5 extract): nominal accuracy of inputs, ETo and
rainfall (three extraction methods); error structure in space (station x
month) and time (stationarity of error series); Shapley vs first-order Taylor
attribution; Monte Carlo vs Taylor propagation of random input errors;
propagation to the reference-crop net irrigation requirement; cross-validated
bias adjustment.

Design follows Soulis et al. (2025) for the application chain and extraction
comparison, and Tran et al. (2026) for input accuracy and error propagation.
"""
from __future__ import annotations

import hashlib
import json
import logging
import platform
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

from . import agera5, fao56, plots, propagation
from .data import Config, assemble_station_table, completeness_table, quality_control
from .evaluation import (PM_INPUTS, add_anomalies, block_bootstrap_ci, cross_validate_adjustment, metrics,
                         net_irrigation_requirement, shapley_eto, shapley_nir)
from .homogeneity import screen_station_network
from .reference import annual_totals, build_reference_ensemble, iterative_wind_break_masking

logger = logging.getLogger(__name__)
__version__ = "1.0.0"

SCREEN_VARS: dict[str, bool] = {"wind_raw": True, "sun": True, "rh": False, "tmax": False, "tmin": False,
                                "pan": True, "rain": True}


def _manifest(cfg: Config, stage: str, outputs: list[Path], extra: dict[str, object]) -> Path:
    cfg_text = (cfg.raw_dir.parent.parent / "config.yaml").read_text(encoding="utf-8")
    pkgs = {p: version(p) for p in ("numpy", "pandas", "scipy", "xarray", "matplotlib")}
    man = {
        "project": "AgERA5 v2.0 ETo evaluation, Northeast Thailand", "pipeline_version": __version__,
        "stage": stage, "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": platform.python_version(), "packages": pkgs,
        "config_sha256": hashlib.sha256(cfg_text.encode()).hexdigest(),
        "outputs": [str(p.relative_to(cfg.out_dir)) for p in outputs], **extra,
    }
    path = cfg.out_dir / stage / "MANIFEST.json"
    path.write_text(json.dumps(man, indent=2, default=str), encoding="utf-8")
    return path


def _annual_complete(df: pd.DataFrame, obs: str, est: str) -> pd.DataFrame:
    """Annual sums of paired monthly values for station-years with 12 valid pairs.

    Returns
    -------
    pandas.DataFrame
        Index (stncode, year), columns ``obs`` and ``est`` (no infilling).
    """
    v = df.dropna(subset=[obs, est])
    g = v.groupby(["stncode", "year"])
    yr = g[[obs, est]].sum()
    return yr[g.size() == 12]


def _season(month: pd.Series, seasons: dict[str, list[int]]) -> pd.Series:
    lut = {m: s for s, ms in seasons.items() for m in ms}
    return month.map(lut)


# --------------------------------------------------------------------------- Stage 1
def run_stage1(cfg: Config, n_sim: int = 5000) -> dict[str, pd.DataFrame]:
    """Station-only analysis. Writes tables and figures under ``out_dir/stage1``.

    Returns
    -------
    dict
        Key tables (also written as CSV).
    """
    out = cfg.out_dir / "stage1"
    tdir, fdir = out / "tables", out / "figures"
    tdir.mkdir(parents=True, exist_ok=True)
    fdir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    raw = assemble_station_table(cfg)
    clean, qc_log = quality_control(raw, cfg.robust_z_limit)
    screen = screen_station_network(clean, SCREEN_VARS, n_sim=n_sim, seed=cfg.seed)
    import yaml
    rcfg = yaml.safe_load((cfg.raw_dir.parent.parent / "config.yaml").read_text(encoding="utf-8"))["reference"]
    masked, actions, wind_final = iterative_wind_break_masking(
        clean, float(rcfg["wind_break_q"]), float(rcfg["wind_break_min_shift_pct"]), n_sim, cfg.seed)
    comp_before = completeness_table(clean, cfg)
    comp_after = completeness_table(masked, cfg)

    ref = build_reference_ensemble(masked, cfg)
    ref_unmasked = build_reference_ensemble(clean, cfg)
    ann = annual_totals(ref)
    ann_summary = ann.groupby(["stncode", "member"])["eto_mm_year"].agg(["mean", "std", "count"]).reset_index()

    # Structural sensitivity by month (median and range across stations of climatological effect).
    clim = ref.groupby(["stncode", "member", "month"])["eto_mm_day"].mean().unstack("member")
    eff = pd.DataFrame({
        "Wind unit: knot vs m s\u207b\u00b9": 100 * (clim["knot|FAO56"] / clim["ms-1|FAO56"] - 1),
        "\u00c5ngstr\u00f6m: Glover\u2013McCulloch vs FAO-56": 100 * (clim["ms-1|GloverMcCulloch"] / clim["ms-1|FAO56"] - 1),
    }).reset_index().melt(id_vars=["stncode", "month"], var_name="factor", value_name="pct")
    sens = eff.groupby(["factor", "month"], sort=False)["pct"].agg(median="median", lo="min", hi="max").reset_index()

    # Elevation and soil-heat-flux sensitivity (annual mean ETo, member m s-1|FAO56).
    base = ref[ref["member"] == "ms-1|FAO56"].copy()
    rows = []
    for z in (0.0, 300.0):
        e = fao56.eto_penman_monteith(base["tmax"], base["tmin"], base["ea"], base["u2"], base["rs"], base["ra"], z, 0.0)
        rows.append({"test": f"elevation {z:.0f} m vs {cfg.assumed_elevation_m:.0f} m",
                     "pct_change_mean_eto": 100 * (np.nanmean(e) / np.nanmean(base["eto_mm_day"]) - 1)})
    rows.append({"test": "monthly G (FAO-56 Eq. 43/44) vs G = 0",
                 "pct_change_mean_eto": 100 * (np.nanmean(base["eto_g_mm_day"]) / np.nanmean(base["eto_mm_day"]) - 1)})
    ab = ref_unmasked.groupby("member")["eto_mm_day"].mean() / ref.groupby("member")["eto_mm_day"].mean()
    for mem, v in ab.items():
        rows.append({"test": f"unmasked vs masked wind ({mem})", "pct_change_mean_eto": 100 * (v - 1)})
    other_sens = pd.DataFrame(rows)

    tables = {"qc_rejections": qc_log, "completeness_after_qc": comp_before, "completeness_after_wind_masking": comp_after,
              "homogeneity_screening": screen, "wind_masking_actions": actions, "wind_screening_final": wind_final,
              "reference_annual_summary": ann_summary, "reference_monthly_sensitivity": sens,
              "reference_other_sensitivity": other_sens}
    for name, t in tables.items():
        p = tdir / f"{name}.csv"
        t.to_csv(p, index=False)
        written.append(p)
    for name, t in (("station_reference_ensemble_masked", ref), ("station_reference_ensemble_unmasked", ref_unmasked),
                    ("station_monthly_clean_masked", masked)):
        p = out / f"{name}.csv"
        t.to_csv(p, index=False)
        written.append(p)

    written += plots.plot_wind_homogeneity(clean, masked, actions, cfg.stations, fdir / "fig_wind_homogeneity")
    written += plots.plot_reference_envelope(ref, cfg.stations, fdir / "fig_reference_envelope")
    written += plots.plot_reference_sensitivity(sens, fdir / "fig_reference_sensitivity")
    written.append(_manifest(cfg, "stage1", written, {"qc_rejected_values": int(len(qc_log)),
                                                       "wind_masking_actions": int(len(actions))}))
    return tables


# --------------------------------------------------------------------------- Stage 2
def _pair_inputs(ref: pd.DataFrame, agm: pd.DataFrame) -> pd.DataFrame:
    keys = ["stncode", "year", "month"]
    a = agm.rename(columns={"tmax_c": "ag_tmax", "tmin_c": "ag_tmin", "vp_kpa": "ag_ea", "u2": "ag_u2",
                            "rs_mj": "ag_rs", "eto_native_mm_day": "ag_eto", "eto_pm_mm_day": "ag_eto_pm",
                            "pr_mm_month": "ag_pr"})
    cols = keys + ["method", "ag_tmax", "ag_tmin", "ag_ea", "ag_u2", "ag_rs", "ag_eto", "ag_eto_pm", "ag_pr", "days"]
    return ref.merge(a[cols], on=keys, how="inner", suffixes=("", "_ag"))


def run_stage2(cfg: Config, daily: pd.DataFrame, n_mc: int = 500) -> dict[str, pd.DataFrame]:
    """AgERA5 evaluation. Writes tables and figures under ``out_dir/stage2``.

    Parameters
    ----------
    cfg : Config
        Configuration.
    daily : pandas.DataFrame
        AgERA5 station extract (output of :func:`etoeval.agera5.extract_station_daily`).
    n_mc : int, default 500
        Monte Carlo sample size per station-month.

    Returns
    -------
    dict
        Key result tables.
    """
    s1 = cfg.out_dir / "stage1"
    out = cfg.out_dir / "stage2"
    tdir, fdir = out / "tables", out / "figures"
    tdir.mkdir(parents=True, exist_ok=True)
    fdir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    names = {s.code: s.name for s in cfg.stations}

    ref = pd.read_csv(s1 / "station_reference_ensemble_masked.csv")
    ref_un = pd.read_csv(s1 / "station_reference_ensemble_unmasked.csv")
    st_month = pd.read_csv(s1 / "station_monthly_clean_masked.csv")
    agm = agera5.agera5_pm_monthly(agera5.monthly_from_daily(daily), cfg.stations, cfg.assumed_elevation_m)
    agm = agm[(agm["year"] >= cfg.start_year) & (agm["year"] <= cfg.end_year)]
    pair = _pair_inputs(ref, agm)
    pair["season"] = _season(pair["month"], cfg.seasons)
    members = sorted(pair["member"].unique())
    methods = [m for m in agera5.METHODS if m in set(pair["method"])]

    # Central reference (mean of members) for figures; tables report every member.
    central = pair.groupby(["stncode", "year", "month", "method"]).agg(
        obs=("eto_mm_day", "mean"), est=("ag_eto", "first"), est_pm=("ag_eto_pm", "first"), days=("days", "first"),
        season=("season", "first")).reset_index()

    # 1. Nominal accuracy of inputs (Tran et al., 2026).
    rows = []
    for meth in methods:
        p = pair[pair["method"] == meth]
        for code, g in p.groupby("stncode"):
            g0 = g[g["member"] == members[0]]
            for v, o, e in (("tmax", "tmax", "ag_tmax"), ("tmin", "tmin", "ag_tmin"), ("ea", "ea", "ag_ea")):
                rows.append({"variable": v, "variant": "-", "method": meth, "stncode": code, **metrics(g0[o], g0[e])})
            for unit in sorted(g["wind_unit"].unique()):
                gu = g[(g["wind_unit"] == unit) & (g["angstrom"] == "FAO56")]
                rows.append({"variable": "u2", "variant": unit, "method": meth, "stncode": code, **metrics(gu["u2"], gu["ag_u2"])})
            for ang in sorted(g["angstrom"].unique()):
                ga = g[(g["angstrom"] == ang) & (g["wind_unit"] == g["wind_unit"].iloc[0])]
                rows.append({"variable": "rs", "variant": ang, "method": meth, "stncode": code, **metrics(ga["rs"], ga["ag_rs"])})
    input_metrics = pd.DataFrame(rows)

    # 2. ETo accuracy per member, method and level (+ block-bootstrap CI, pooled).
    rows, boot = [], []
    for (mem, meth), g in pair.groupby(["member", "method"]):
        g = g.sort_values(["stncode", "year", "month"])
        an = add_anomalies(g.rename(columns={"eto_mm_day": "obs", "ag_eto": "est"}), ["obs", "est"])
        for code, gg in an.groupby("stncode"):
            rows.append({"member": mem, "method": meth, "stncode": code, "level": "monthly", **metrics(gg["obs"], gg["est"])})
            rows.append({"member": mem, "method": meth, "stncode": code, "level": "anomaly",
                         **metrics(gg["obs_anom"], gg["est_anom"], anomalies=True)})
            cl = gg.dropna(subset=["obs", "est"]).groupby("month")[["obs", "est"]].mean()
            rows.append({"member": mem, "method": meth, "stncode": code, "level": "climatology", **metrics(cl["obs"], cl["est"])})
        rows.append({"member": mem, "method": meth, "stncode": "all", "level": "monthly", **metrics(an["obs"], an["est"])})
        rows.append({"member": mem, "method": meth, "stncode": "all", "level": "anomaly",
                     **metrics(an["obs_anom"], an["est_anom"], anomalies=True)})
        d = an.dropna(subset=["obs", "est"])
        for stat, fn in (("mbe", lambda x: float((x["est"] - x["obs"]).mean())),
                         ("rmse", lambda x: float(np.sqrt(((x["est"] - x["obs"]) ** 2).mean())))):
            lo, hi = block_bootstrap_ci(d, fn, cfg.bootstrap_block, cfg.bootstrap_n, cfg.seed)
            boot.append({"member": mem, "method": meth, "stat": stat, "estimate": fn(d), "ci95_lo": lo, "ci95_hi": hi})
        g["eto_month"] = g["eto_mm_day"] * g["days"]
        g["ag_month"] = g["ag_eto"] * g["days"]
        yr = _annual_complete(g, "eto_month", "ag_month")
        rows.append({"member": mem, "method": meth, "stncode": "all", "level": "annual", **metrics(yr["eto_month"], yr["ag_month"])})
    eto_metrics = pd.DataFrame(rows)
    eto_boot = pd.DataFrame(boot)

    # Sensitivity: unmasked wind reference.
    pair_un = _pair_inputs(ref_un, agm)
    sens_rows = [{"member": mem, "method": meth, "reference": "unmasked wind",
                  **metrics(g["eto_mm_day"], g["ag_eto"])} for (mem, meth), g in pair_un.groupby(["member", "method"])]
    sens_rows += [{"member": mem, "method": meth, "reference": "masked wind (main)",
                   **metrics(g["eto_mm_day"], g["ag_eto"])} for (mem, meth), g in pair.groupby(["member", "method"])]
    eto_mask_sens = pd.DataFrame(sens_rows)

    # 3. Replication of native ETo from AgERA5 monthly inputs (validates input-based attribution).
    rep = [{"stncode": code, "method": meth, **metrics(g["est"], g["est_pm"])}
           for (code, meth), g in central.groupby(["stncode", "method"])]
    replication = pd.DataFrame(rep)

    # 4. Rainfall accuracy (station monthly totals vs AgERA5 monthly sums).
    pr = st_month[["stncode", "year", "month", "rain"]].merge(
        agm[["stncode", "year", "month", "method", "pr_mm_month"]], on=["stncode", "year", "month"])
    rows = []
    ann_rows = []
    for meth, g in pr.groupby("method"):
        for code, gg in g.groupby("stncode"):
            rows.append({"method": meth, "stncode": code, "level": "monthly", **metrics(gg["rain"], gg["pr_mm_month"])})
        yr = _annual_complete(g, "rain", "pr_mm_month")
        rows.append({"method": meth, "stncode": "all", "level": "annual", **metrics(yr["rain"], yr["pr_mm_month"])})
        ann_rows.append(yr.reset_index().assign(variable="pr", method=meth).rename(columns={"rain": "obs", "pr_mm_month": "est"}))
    pr_metrics = pd.DataFrame(rows)
    for meth, g in central.groupby("method"):
        g = g.assign(o=g["obs"] * g["days"], e=g["est"] * g["days"])
        yr = _annual_complete(g, "o", "e")
        ann_rows.append(yr.reset_index().assign(variable="eto", method=meth).rename(columns={"o": "obs", "e": "est"}))
    annual_pairs = pd.concat(ann_rows, ignore_index=True)

    # 5. Error structure: station x month bias (nearest) and stationarity of error series.
    near = pair[pair["method"] == "nearest"]
    n0 = near[near["member"] == members[0]]
    bias_rows = []
    for v, o, e in (("tmax", "tmax", "ag_tmax"), ("tmin", "tmin", "ag_tmin"), ("ea", "ea", "ag_ea")):
        b = (n0[e] - n0[o]).groupby([n0["stncode"], n0["month"]]).mean()
        bias_rows.append(b.rename("mbe").reset_index().assign(variable=v))
    nu = near[(near["wind_unit"] == "m s-1") & (near["angstrom"] == "FAO56")]
    for v, o, e in (("u2", "u2", "ag_u2"), ("rs", "rs", "ag_rs")):
        b = (nu[e] - nu[o]).groupby([nu["stncode"], nu["month"]]).mean()
        bias_rows.append(b.rename("mbe").reset_index().assign(variable=v))
    cn = central[central["method"] == "nearest"]
    b = (cn["est"] - cn["obs"]).groupby([cn["stncode"], cn["month"]]).mean()
    bias_rows.append(b.rename("mbe").reset_index().assign(variable="eto"))
    bias_sm = pd.concat(bias_rows, ignore_index=True)

    stat_rows = []
    for v, o, e, mult in (("tmax", "tmax", "ag_tmax", False), ("tmin", "tmin", "ag_tmin", False),
                          ("ea", "ea", "ag_ea", True)):
        stat_rows.append(propagation.error_stationarity(n0.rename(columns={o: "obs", e: "est"}), v, mult, seed=cfg.seed))
    for v, o, e in (("u2", "u2", "ag_u2"), ("rs", "rs", "ag_rs")):
        stat_rows.append(propagation.error_stationarity(nu.rename(columns={o: "obs", e: "est"}), v, True, seed=cfg.seed))
    stat_rows.append(propagation.error_stationarity(cn, "eto", True, seed=cfg.seed))
    prn = pr[pr["method"] == "nearest"]
    pry = _annual_complete(prn, "rain", "pr_mm_month").reset_index()
    stat_rows.append(propagation.error_stationarity(pry.assign(month=1).rename(columns={"rain": "obs", "pr_mm_month": "est"}),
                                                    "pr_annual", True, min_months=1, seed=cfg.seed))
    stationarity = pd.concat(stat_rows, ignore_index=True)

    # 6. Attribution: exact Shapley vs first-order Taylor, per member (nearest).
    att_rows = []
    for mem, g in near.groupby("member"):
        g = g.dropna(subset=list(PM_INPUTS) + ["ag_tmax", "ag_tmin", "ag_ea", "ag_u2", "ag_rs"])
        st_in = g[list(PM_INPUTS)]
        ag_in = g[["ag_tmax", "ag_tmin", "ag_ea", "ag_u2", "ag_rs"]].set_axis(list(PM_INPUTS), axis=1)
        sh = shapley_eto(st_in, ag_in, g["ra"].to_numpy(), g["z"].to_numpy())
        ty = propagation.taylor_decomposition(st_in, ag_in, g["ra"].to_numpy(), g["z"].to_numpy())
        att_rows.append(pd.concat([g[["stncode", "year", "month", "season"]], sh, ty.drop(columns="delta")], axis=1).assign(member=mem))
    attribution = pd.concat(att_rows, ignore_index=True)
    summ = []
    for meth, pre in (("Shapley", "phi_"), ("Taylor", "lin_")):
        for v in PM_INPUTS:
            st_means = attribution.groupby(["season", "stncode"])[f"{pre}{v}"].mean()
            for sea, s in st_means.groupby(level="season"):
                summ.append({"season": sea, "method": meth, "variable": v, "mean": float(s.mean()),
                             "lo": float(s.min()), "hi": float(s.max())})
    att_summary = pd.DataFrame(summ)
    att_summary["season"] = pd.Categorical(att_summary["season"], list(cfg.seasons))
    att_summary = att_summary.sort_values(["season", "method", "variable"])
    lin_err = attribution.assign(resid=attribution["delta"] - attribution["lin_total"]).groupby("member")["resid"].agg(
        mean_resid="mean", mae_resid=lambda x: float(np.abs(x).mean())).reset_index()

    # 7. Monte Carlo vs Taylor propagation of random input errors.
    mc_rows = []
    for mem, g in near.groupby("member"):
        g = g.dropna(subset=list(PM_INPUTS) + ["ag_tmax", "ag_tmin", "ag_ea", "ag_u2", "ag_rs"]).reset_index(drop=True)
        err = pd.DataFrame({"month": g["month"]})
        for v, a in zip(PM_INPUTS, ("ag_tmax", "ag_tmin", "ag_ea", "ag_u2", "ag_rs")):
            err[f"e_{v}"] = g[a] - g[v]
        model = propagation.fit_error_model(err)
        mc = propagation.monte_carlo_propagation(g[list(PM_INPUTS)], g["ra"].to_numpy(), g["z"].to_numpy(),
                                                 g["month"].to_numpy(), model, n_samples=n_mc, seed=cfg.seed)
        mc_rows.append(pd.concat([g[["stncode", "year", "month"]], mc], axis=1).assign(member=mem))
        corr = err.drop(columns="month").corr()
        corr.to_csv(tdir / f"input_error_correlation_{mem.replace('|', '_')}.csv")
    mc_all = pd.concat(mc_rows, ignore_index=True)
    snorm_cols = ["snorm_mc_corr", "snorm_mc_indep", "snorm_taylor_corr", "snorm_taylor_indep"]
    mc_month = mc_all.groupby("month")[snorm_cols].median().reset_index()

    # 8. Net irrigation requirement of the reference crop (central reference, nearest).
    nir = cn.merge(st_month[["stncode", "year", "month", "rain"]], on=["stncode", "year", "month"]).merge(
        prn[["stncode", "year", "month", "pr_mm_month"]], on=["stncode", "year", "month"])
    nir = nir.dropna(subset=["obs", "est", "rain", "pr_mm_month"]).copy()
    nir["eto_obs_m"] = nir["obs"] * nir["days"]
    nir["eto_est_m"] = nir["est"] * nir["days"]
    nir["nir_obs"] = net_irrigation_requirement(nir["eto_obs_m"], nir["rain"])
    nir["nir_est"] = net_irrigation_requirement(nir["eto_est_m"], nir["pr_mm_month"])
    split = shapley_nir(nir["eto_obs_m"].to_numpy(), nir["rain"].to_numpy(), nir["eto_est_m"].to_numpy(), nir["pr_mm_month"].to_numpy())
    nir = pd.concat([nir.reset_index(drop=True), split], axis=1)
    cnt = nir.groupby(["stncode", "year"]).size()
    full = cnt[cnt == 12].index
    nir_y = nir.set_index(["stncode", "year"]).loc[full].groupby(["stncode", "year"])[
        ["nir_obs", "nir_est", "phi_eto", "phi_p", "delta"]].sum()
    nir_station = nir_y.groupby("stncode").mean().reset_index()
    nir_station["station"] = nir_station["stncode"].map(names)
    nir_metrics = pd.DataFrame([{"stncode": "all", **metrics(nir_y["nir_obs"], nir_y["nir_est"])}] +
                               [{"stncode": c, **metrics(g["nir_obs"], g["nir_est"])} for c, g in nir_y.groupby("stncode")])

    # 9. Cross-validated bias adjustment (central ETo reference; rainfall scaling only).
    cv_rows, cv_station = [], []
    pe = cn[["stncode", "year", "month", "obs", "est"]]
    for meth in ("scaling", "linear"):
        for scheme in ("loyo_block", "loso"):
            pr_cv = cross_validate_adjustment(pe, meth, scheme)
            cv_rows.append({"variable": "eto", "method": meth, "scheme": scheme,
                            **{f"raw_{k}": v for k, v in metrics(pr_cv["obs"], pr_cv["est"]).items()},
                            **{f"adj_{k}": v for k, v in metrics(pr_cv["obs"], pr_cv["est_adj"]).items()}})
            if scheme == "loso":
                for code, g in pr_cv.groupby("stncode"):
                    cv_station.append({"station": names[int(code)], "method": meth,
                                       "rmse_raw": metrics(g["obs"], g["est"])["rmse"],
                                       "rmse_adj": metrics(g["obs"], g["est_adj"])["rmse"]})
    pp = prn.rename(columns={"rain": "obs", "pr_mm_month": "est"})[["stncode", "year", "month", "obs", "est"]]
    for scheme in ("loyo_block", "loso"):
        pr_cv = cross_validate_adjustment(pp, "scaling", scheme)
        cv_rows.append({"variable": "pr", "method": "scaling", "scheme": scheme,
                        **{f"raw_{k}": v for k, v in metrics(pr_cv["obs"], pr_cv["est"]).items()},
                        **{f"adj_{k}": v for k, v in metrics(pr_cv["obs"], pr_cv["est_adj"]).items()}})
    cv_table = pd.DataFrame(cv_rows)
    cv_station_df = pd.DataFrame(cv_station)

    tables = {"input_metrics": input_metrics, "eto_metrics": eto_metrics, "eto_bootstrap_ci": eto_boot,
              "eto_wind_masking_sensitivity": eto_mask_sens, "agera5_eto_replication": replication,
              "precip_metrics": pr_metrics, "annual_pairs": annual_pairs, "bias_station_month": bias_sm,
              "error_stationarity": stationarity, "attribution_rows": attribution, "attribution_seasonal": att_summary,
              "taylor_linearisation_error": lin_err, "propagation_rows": mc_all, "propagation_by_month": mc_month,
              "nir_station_mean_annual": nir_station, "nir_metrics": nir_metrics, "bias_adjustment_cv": cv_table,
              "bias_adjustment_loso_station": cv_station_df}
    for name, t in tables.items():
        p = tdir / f"{name}.csv"
        t.to_csv(p, index=False)
        written.append(p)

    im = input_metrics[((input_metrics["variable"] == "u2") & (input_metrics["variant"] == "m s-1")) |
                       ((input_metrics["variable"] == "rs") & (input_metrics["variant"] == "FAO56")) |
                       (~input_metrics["variable"].isin(["u2", "rs"]))]
    written += plots.plot_input_metrics(im, fdir / "fig_input_accuracy")
    written += plots.plot_bias_heatmaps(bias_sm, cfg.stations, fdir / "fig_bias_station_month")
    written += plots.plot_annual_scatter(annual_pairs, fdir / "fig_annual_scatter")
    rc = pair[pair["method"] == "nearest"].groupby(["stncode", "member", "month"])["eto_mm_day"].mean().unstack("member")
    ref_clim = pd.DataFrame({"lo": rc.min(axis=1), "hi": rc.max(axis=1)}).reset_index()
    ag_clim = cn.groupby(["stncode", "month"]).agg(native=("est", "mean"), pm=("est_pm", "mean")).reset_index()
    written += plots.plot_seasonal_cycle(ref_clim, ag_clim, cfg.stations, fdir / "fig_seasonal_cycle")
    written += plots.plot_attribution(att_summary.assign(season=att_summary["season"].astype(str)), fdir / "fig_attribution")
    written += plots.plot_propagation(mc_month, fdir / "fig_error_propagation")
    written += plots.plot_nir_and_adjustment(nir_station, cv_station_df, fdir / "fig_nir_adjustment")
    written.append(_manifest(cfg, "stage2", written, {"n_monthly_pairs_nearest_central": int(cn.dropna(subset=["obs", "est"]).shape[0]),
                                                       "monte_carlo_n": n_mc}))
    return tables
