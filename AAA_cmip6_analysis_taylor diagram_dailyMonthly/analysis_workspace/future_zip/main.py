#!/usr/bin/env python3
"""
main.py - End-to-end ENSO / Rainfall analysis for Prachuap Khiri Khan, Thailand.

Run:    python main.py                 # full pipeline (requires internet for ENSO)
        python main.py --allow-offline # run rainfall-only steps if NOAA unreachable
        python main.py --q1-only       # build the dedicated Q1 figure set only
        python main.py --qdm-only      # build the dedicated QDM-only Q1 figure set
        python main.py --future-q1-only # build the CMIP6 future projection Q1 set only

All tables -> output/tables/*.xlsx
All figures -> output/figures/*.{png,pdf}
Log         -> output/logs/run.log
"""
from __future__ import annotations
import argparse
import logging
import platform
import sys
import time
from datetime import datetime

import numpy as np
import pandas as pd

from src import config as C
from src import pipeline as P
from src import figures as FIG
from src import enso as ENSO
from src import iod as IOD
from src import etccdi as ETX
from src import gismap as GMAP
from src import changepoint as CP
from src import qdm_q1 as QDM
from src import future_q1 as FUTURE


def setup_logging():
    C.LOG.mkdir(parents=True, exist_ok=True)
    fmt = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    logging.basicConfig(
        level=logging.INFO, format=fmt,
        handlers=[logging.StreamHandler(sys.stdout),
                  logging.FileHandler(C.LOG / "run.log", mode="w")])
    return logging.getLogger("main")


def xl(df: pd.DataFrame, fname: str, sheet="Sheet1", tab_dir=None):
    path = (tab_dir or C.TAB) / fname
    with pd.ExcelWriter(path, engine="xlsxwriter") as w:
        df.to_excel(w, index=False, sheet_name=sheet)
    return path


def xl_sheets(sheets: dict, fname: str, tab_dir=None):
    """Write an ordered dict of {sheet_name: DataFrame} to one workbook."""
    path = (tab_dir or C.TAB) / fname
    with pd.ExcelWriter(path, engine="xlsxwriter") as w:
        for sheet, df in sheets.items():
            df.to_excel(w, index=False, sheet_name=sheet[:31])
    return path


def _info_df(extra=None):
    """Self-documenting 'Info' sheet: input data + methods + provenance."""
    base = {
        "Study area": "Prachuap Khiri Khan, Thailand",
        "Rainfall input file": C.RAIN_FILE.name,
        "Rainfall sheet": C.RAIN_SHEET,
        "Analysis period": f"{C.START_YEAR}-{C.END_YEAR}",
        "Number of years": C.END_YEAR - C.START_YEAR + 1,
        "Number of gauges": len(C.STATION_IDS),
        "Gauge IDs": ", ".join(map(str, C.STATION_IDS)),
        "Station selection": "auto (rainfall columns INTERSECT coordinate table)",
        "Areal method": C.AREAL_METHOD,
        "Wet season": "May-Oct", "Dry season": "Nov-Apr (cross-year)",
        "Significance level alpha": C.ALPHA,
        "Trend method (primary)": "TFPW-MK (Yue et al. 2002) + Sen slope (Gilbert 1987 CI)",
        "Trend cross-checks": "original MK; Hamed-Rao Modified-MK (1998)",
        "ENSO sources": "NOAA CPC ONI (oni.ascii.txt) + ERSSTv5 Nino-3.4 (1991-2020 clim)",
        "ONI event rule": (f"El Nino>={C.ONI_ELNINO}, La Nina<={C.ONI_LANINA}; "
                           f">= {C.ONI_MIN_CONSECUTIVE} consecutive seasons"),
        "IOD source": "NOAA PSL HadISST DMI (when INCLUDE_IOD)",
        "Coordinate table": C.GIS_COORD_FILE.name,
        "Boundary (GIS)": C.BOUNDARY_SHP.name + " (UTM 47N)",
        "Data integrity": "real observations only; no fabricated/imputed values",
        "Generated (UTC)": datetime.utcnow().isoformat(timespec="seconds"),
    }
    if extra:
        base.update(extra)
    return pd.DataFrame({"Field": list(base.keys()),
                         "Value": [str(v) for v in base.values()]})


def write_results(fname, df, sig_mask=None, info_extra=None, tab_dir=None,
                  main_sheet="Results", extra_sheets=None):
    """Write a results workbook with: Info sheet + full results + (optional)
    a separate 'Significant' sheet, so it is publication-ready and self-documented.
    """
    sheets = {"Info": _info_df(info_extra), main_sheet: df}
    if extra_sheets:
        sheets.update(extra_sheets)
    if sig_mask is not None:
        sig = df[sig_mask].reset_index(drop=True)
        sheets["Significant"] = sig if len(sig) else pd.DataFrame(
            {"note": ["no rows significant at alpha"]})
    return xl_sheets(sheets, fname, tab_dir=tab_dir)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--allow-offline", action="store_true",
                    help="Continue with rainfall-only steps if NOAA is unreachable.")
    ap.add_argument("--max-lag", type=int, default=12)
    ap.add_argument("--q1-only", action="store_true",
                    help="Generate only the dedicated Q1 figure set in output/q1_standard.")
    ap.add_argument("--qdm-only", action="store_true",
                    help="Generate only the dedicated QDM figure/table set in output/qdm_q1.")
    ap.add_argument("--qdm-source", type=str, default=str(C.QDM_SOURCE_DIR),
                    help="Folder containing the QDM evaluation workbook and companion files.")
    ap.add_argument("--future-q1-only", action="store_true",
                    help="Generate only the dedicated CMIP6 future projection Q1 set in output/future_q1.")
    ap.add_argument("--future-source", type=str, default=str(C.FUTURE_SOURCE_DIR),
                    help="Folder containing observed and bias-corrected CMIP6 daily rainfall CSV files.")
    ap.add_argument("--future-gis-dir", type=str, default=str(C.FUTURE_GIS_DIR),
                    help="Folder containing boundary.shp and station_coordinates.csv.")
    ap.add_argument("--future-framework-output", type=str, default=str(C.FUTURE_FRAMEWORK_OUTPUT_DIR),
                    help="Optional framework outputs folder used to validate overlapping trend results.")
    ap.add_argument("--future-area", type=str, default=getattr(C, "STUDY_AREA_NAME", "Study area"),
                    help="Display name of the study area, shown on future-Q1 figures/tables.")
    args = ap.parse_args()

    log = setup_logging()
    t0 = time.time()
    runtime = dict(started=datetime.now().isoformat(timespec="seconds"),
                   python=platform.python_version(), platform=platform.platform())
    log.info("=== ENSO-Rainfall Pipeline (Prachuap Khiri Khan) ===")

    if args.qdm_only:
        manifest = QDM.build_qdm_q1_outputs(args.qdm_source)
        runtime["finished"] = datetime.now().isoformat(timespec="seconds")
        runtime["seconds"] = round(time.time() - t0, 1)
        log.info("QDM-only figure set written to %s", manifest["figure_dir"])
        log.info("QDM-only tables written to %s", manifest["table_dir"])
        log.info("QDM-only run complete in %.1fs.", runtime["seconds"])
        return

    if args.future_q1_only:
        manifest = FUTURE.build_future_q1_outputs(
            args.future_source, args.future_gis_dir, args.future_framework_output,
            area_name=args.future_area,
        )
        runtime["finished"] = datetime.now().isoformat(timespec="seconds")
        runtime["seconds"] = round(time.time() - t0, 1)
        log.info("Future-Q1 figure set written to %s", manifest["figure_dir"])
        log.info("Future-Q1 tables written to %s", manifest["table_dir"])
        log.info("Future-Q1 run complete in %.1fs.", runtime["seconds"])
        return

    # ---------------- STEP 0/1 LOAD + QC -----------------------------------
    daily = P.load_rainfall()
    qc = P.quality_control(daily)
    with pd.ExcelWriter(C.TAB / "DATA_QC_REPORT.xlsx", engine="xlsxwriter") as w:
        qc["summary"].to_excel(w, index=False, sheet_name="summary")
        qc["per_station"].to_excel(w, index=False, sheet_name="per_station")
        qc["missing_dates"].to_excel(w, index=False, sheet_name="missing_dates")
    log.info("QC passed=%s", qc["passed"])
    if not qc["passed"]:
        log.error("QC failed - inspect DATA_QC_REPORT.xlsx. Aborting per spec.")
        sys.exit(2)

    # ---------------- STEP 2 AGGREGATION -----------------------------------
    agg = P.aggregate(daily, "AREAL")
    issues = P.validate_aggregates(agg)
    if issues:
        log.error("Aggregation validation issues:\n  - %s", "\n  - ".join(issues))
        sys.exit(3)
    log.info("Aggregation validated: complete monthly/annual/wet/dry totals.")

    monthly = agg["monthly"]; annual = agg["annual"]["annual_mm"]
    wet = agg["wet"]["wet_mm"]
    # Keep only COMPLETE dry seasons (181/182 days). Incomplete 1981 & 2015
    # are excluded, never imputed.
    dd = agg["dry"]
    def _dry_exp(y):
        leap = (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0))
        return 182 if leap else 181
    complete_dry_years = [y for y in dd.index if dd.loc[y, "n_days"] == _dry_exp(y)]
    dry = dd.loc[complete_dry_years, "dry_mm"]

    xl(monthly.reset_index().rename(columns={"index": "date"}),
       "MONTHLY_RAINFALL.xlsx", "monthly")
    xl(agg["annual"].reset_index(), "ANNUAL_RAINFALL.xlsx", "annual")
    xl(agg["wet"].reset_index(), "WET_SEASON_RAINFALL.xlsx", "wet")
    xl(agg["dry"].loc[dry.index].reset_index(), "DRY_SEASON_RAINFALL.xlsx", "dry")

    series_by_var = {"Annual": annual, "Wet": wet, "Dry": dry}

    # ---------------- DEDICATED Q1 FIGURES ---------------------------------
    try:
        q1 = P.build_q1_standard_figures(daily, station_case=500003,
                                         timescale_case="Wet")
        xl(q1["climatology_shift"],
           "Q1_TABLE_01_CLIMATOLOGY_SHIFT.xlsx", "climatology_shift",
           tab_dir=C.Q1)
        xl(q1["spatial_coherence"],
           "Q1_TABLE_02_SPATIAL_COHERENCE.xlsx", "spatial_coherence",
           tab_dir=C.Q1)
        q1_obs = q1["methodological_contrast"]["observed"]
        q1_tfpw = q1["methodological_contrast"]["tfpw"]
        q1_diag = q1["methodological_contrast"]["diagnostics"]
        q1_meta = pd.DataFrame([{
            "station": q1["methodological_contrast"]["station"],
            "timescale": q1["methodological_contrast"]["timescale"],
            "lag1_autocorr": round(q1_diag.lag1_autocorr, 4),
            "lag1_critical": round(q1_diag.lag1_critical, 4),
            "prewhitening_applied": bool(q1_diag.prewhitening_applied),
            "original_mk_p": round(q1_diag.original_result.p_value, 4),
            "tfpw_mk_p": round(q1_diag.tfpw_result.p_value, 4),
            "original_sen_slope": round(q1_diag.original_result.sens_slope, 4),
            "tfpw_sen_slope": round(q1_diag.tfpw_result.sens_slope, 4),
        }])
        xl_sheets({"metadata": q1_meta, "observed": q1_obs, "tfpw": q1_tfpw},
                  "Q1_TABLE_03_METHOD_CONTRAST.xlsx", tab_dir=C.Q1)
        log.info("Q1 figure set written to %s", C.Q1)
        if args.q1_only:
            runtime["finished"] = datetime.now().isoformat(timespec="seconds")
            runtime["seconds"] = round(time.time() - t0, 1)
            runtime["enso_downloaded"] = False
            runtime["iod_included"] = False
            log.info("Q1-only run complete in %.1fs.", runtime["seconds"])
            return
    except Exception as e:                                    # noqa: BLE001
        log.warning("Q1 figure set skipped (%s).", e)
        if args.q1_only:
            raise

    # ---------------- STEP 4 DESCRIPTIVE -----------------------------------
    desc = P.descriptive(series_by_var)
    xl(desc, "TABLE_01_DESCRIPTIVE_STATISTICS.xlsx", "descriptive")
    log.info("Descriptive statistics written.")

    # ---------------- STEP 9/10 TREND (no ENSO needed) ---------------------
    tfpw, sens, cross = P.trend_table(series_by_var)
    xl(tfpw, "TABLE_07_TFPW_MK_RESULTS.xlsx", "tfpw_mk")
    xl(sens, "TABLE_08_SENS_SLOPE.xlsx", "sens_slope")
    xl(cross, "TABLE_07b_TREND_METHOD_CROSSCHECK.xlsx", "crosscheck")
    log.info("Trend analysis (TFPW-MK + cross-checks) written.")

    # ---------------- STEP 11 figures (rainfall-only ones) -----------------
    FIG.init()
    FIG.fig01_climatology(monthly)
    FIG.fig02_annual_series(annual)
    for var, name, title in [
        ("Annual", "FIGURE_08_annual_trend", "Annual Rainfall Trend (Sen + TFPW-MK)"),
        ("Wet", "FIGURE_09_wet_trend", "Wet-Season Rainfall Trend"),
        ("Dry", "FIGURE_10_dry_trend", "Dry-Season Rainfall Trend")]:
        srow = sens[sens["variable"] == var].iloc[0]
        FIG.fig_trend(series_by_var[var], srow["sens_slope_mm_per_year"],
                      srow["intercept"], srow["ci95_low"], srow["ci95_high"],
                      title, name)

    # ---------------- PER-STATION ANALYSIS (12 gauges x 3 timescales) -------
    ps = P.per_station_series(daily)
    ps_desc = P.per_station_descriptive(ps)
    xl(ps_desc, "TABLE_13_PER_STATION_DESCRIPTIVE.xlsx", "per_station")

    # Per-station trend with ALL THREE methods, each in its own sheet, plus a
    # side-by-side comparison sheet (TFPW-MK primary, MK + Hamed-Rao as checks).
    ps_detail, ps_comp = P.per_station_trend_all_methods(ps)
    _tfpw = ps_detail["TFPW_MK"]
    write_results(
        "TABLE_14_PER_STATION_TREND.xlsx", _tfpw,
        sig_mask=_tfpw["significant"], main_sheet="TFPW_MK",
        info_extra={"Table": "Per-station rainfall trend, 12 gauges x 3 timescales",
                    "Primary method": "TFPW-MK; 'Significant' sheet = TFPW p<alpha",
                    "Other sheets": "Original_MK, Modified_MK_HamedRao, Comparison"},
        extra_sheets={"Original_MK": ps_detail["Original_MK"],
                      "Modified_MK_HamedRao": ps_detail["Modified_MK_HamedRao"],
                      "Comparison": ps_comp})

    # Taylor statistics vs areal-mean reference (spatial coherence)
    tay = P.taylor_stats(ps, series_by_var)
    xl(tay, "TABLE_16_TAYLOR_STATISTICS.xlsx", "taylor")
    FIG.fig_taylor(tay)
    FIG.fig_per_station_trend(ps_detail["TFPW_MK"])
    FIG.fig_significant_trends(ps, ps_detail["TFPW_MK"], ps_comp)
    n_sig = int(ps_detail["TFPW_MK"]["significant"].sum())
    n_disagree = int((~ps_comp["methods_agree"]).sum())
    log.info("Per-station analysis: %d gauges x 3 timescales; %d/%d TFPW-MK "
             "trends significant; methods disagree on %d of %d cells.",
             len(C.STATION_IDS), n_sig, len(ps_comp), n_disagree, len(ps_comp))

    # ---------------- GIS: significance maps (separate output/gis/) ---------
    area = None
    try:
        area = GMAP.StudyArea()
        tf = ps_detail["TFPW_MK"]
        for var, fn in [("Annual", "MAP_01_trend_annual"),
                        ("Wet", "MAP_02_trend_wet"),
                        ("Dry", "MAP_03_trend_dry")]:
            sub = tf[tf["timescale"] == var][
                ["station", "sens_slope_mm_yr", "significant"]].copy()
            GMAP.significance_map(
                area, sub, "sens_slope_mm_yr", "significant",
                f"{var} Rainfall Trend (TFPW-MK Sen's slope)", fn,
                "Sen's slope (mm yr$^{-1}$)")
        # --- same Sen's-slope surface, significance markers by alternative
        #     methods, so reviewers see WHERE methods disagree (markers differ,
        #     surface identical). MAP_10-15.
        method_maps = [("Original_MK", "MK", "MK"),
                       ("Modified_MK_HamedRao", "HamedRao", "Hamed-Rao MMK")]
        mno = 10
        for key, tag, lbl in method_maps:
            det = ps_detail[key]
            for var in ("Annual", "Wet", "Dry"):
                sub = det[det["timescale"] == var][
                    ["station", "sens_slope_mm_yr", "significant"]].copy()
                GMAP.significance_map(
                    area, sub, "sens_slope_mm_yr", "significant",
                    f"{var} Rainfall Trend ({lbl} Sen's slope)",
                    f"MAP_{mno}_trend_{var.lower()}_{tag}",
                    "Sen's slope (mm yr$^{-1}$)")
                mno += 1
        log.info("GIS trend maps written to %s", C.GIS_OUT)
    except Exception as e:                                    # noqa: BLE001
        log.warning("GIS maps skipped (%s).", e)

    # ---------------- ETCCDI extreme indices (separate output/extremes/) ----
    etx = ETX.compute_all_stations(daily, C.STATION_IDS, C.ETCCDI_BASE_PERIOD)
    xl(etx, "ETCCDI_01_INDICES_BY_STATION_YEAR.xlsx", "indices", tab_dir=C.EXTREMES)
    etx_tr = P.etccdi_trends(etx, ETX.INDEX_NAMES)
    write_results("ETCCDI_02_TREND_PER_STATION.xlsx", etx_tr,
                  sig_mask=etx_tr["tfpw_sig"], main_sheet="trend",
                  tab_dir=C.EXTREMES,
                  info_extra={"Table": "Per-station ETCCDI index trends (8 indices)",
                              "Method": "TFPW-MK + Hamed-Rao; 'Significant' = TFPW p<alpha",
                              "Indices": ", ".join(ETX.INDEX_NAMES),
                              "Wet-day threshold": "1 mm",
                              "R95p/R99p base period": f"{C.ETCCDI_BASE_PERIOD}"})
    # regional (areal-mean of station indices) trend summary, per index
    reg = etx.groupby("year")[ETX.INDEX_NAMES].mean()
    reg_rows = []
    for idx in ETX.INDEX_NAMES:
        from src.mktrend import tfpw_mk, modified_mk_hamed_rao
        x = reg[idx].dropna().astype(float).values
        rt = tfpw_mk(x, C.ALPHA); rh = modified_mk_hamed_rao(x, C.ALPHA)
        reg_rows.append(dict(index=idx, unit=ETX.INDEX_UNITS[idx], n=rt.n,
                             sens_slope=round(rt.sens_slope, 4),
                             ci95_low=round(rt.sens_slope_lcl, 4),
                             ci95_high=round(rt.sens_slope_ucl, 4),
                             tfpw_p=round(rt.p_value, 4),
                             tfpw_sig=bool(rt.significant),
                             hamedrao_p=round(rh.p_value, 4),
                             hamedrao_sig=bool(rh.significant),
                             trend=rt.trend))
    xl(pd.DataFrame(reg_rows), "ETCCDI_03_REGIONAL_TREND_SUMMARY.xlsx",
       "regional", tab_dir=C.EXTREMES)

    # ETCCDI time-series figure (regional mean per index, 8 panels)
    FIG.fig_etccdi_series(reg, ETX.INDEX_NAMES, ETX.INDEX_UNITS)
    # ETCCDI GIS grid: per-index Sen slope + significance at gauges
    if area is not None:
        panels = []
        for idx in ETX.INDEX_NAMES:
            sub = etx_tr[etx_tr["index"] == idx][
                ["station", "sens_slope", "tfpw_sig"]].copy()
            panels.append(dict(values=sub, value_col="sens_slope",
                               sig_col="tfpw_sig", title=idx,
                               cbar_label=f"slope ({ETX.INDEX_UNITS[idx]}/yr)"))
        GMAP.significance_map_grid(
            area, panels, "MAP_04_etccdi_trends",
            "ETCCDI Extreme-Precipitation Trends (Sen's slope, * filled = p<0.05)")
    n_etx_sig = int(etx_tr["tfpw_sig"].sum())
    log.info("ETCCDI: 8 indices x %d gauges; %d/%d station-index trends "
             "significant (TFPW-MK).", len(C.STATION_IDS), n_etx_sig, len(etx_tr))

    # ---------------- CHANGE-POINT / REGIME SHIFT (separate output/changepoint/)
    cp_tab = CP.per_station_changepoints(ps)
    write_results("CHANGEPOINT_01_PER_STATION.xlsx", cp_tab,
                  sig_mask=cp_tab["pettitt_sig"], main_sheet="changepoint",
                  tab_dir=C.CHANGEPOINT,
                  info_extra={"Table": "Per-station regime-shift detection",
                              "Methods": "Pettitt + Bayesian (Normal-Gamma) + "
                                         "sequential MK; AIC/BIC step-vs-trend",
                              "'Significant' sheet": "Pettitt p<alpha",
                              "step_size units": "mm (post-mean minus pre-mean)"})
    cp_field = CP.field_significance_by_timescale(ps, n_mc=2000)
    write_results("CHANGEPOINT_02_FIELD_SIGNIFICANCE.xlsx", cp_field,
                  main_sheet="field_sig", tab_dir=C.CHANGEPOINT,
                  info_extra={"Table": "Field significance of the change-point cluster",
                              "Method": "AR(1)-surrogate Monte-Carlo (2000 trials)",
                              "Interpretation": "field_p_value<alpha => cluster "
                                                "exceeds chance under autocorrelation"})
    FIG.fig_changepoint_series(ps, cp_tab)
    picks = [(r.station, r.timescale) for r in
             cp_tab[cp_tab.pettitt_sig].itertuples()][:6]
    if picks:
        FIG.fig_sequential_mk(ps, cp_tab, picks)
    if area is not None:
        for var in ["Wet", "Dry"]:
            sub = cp_tab[cp_tab.timescale == var][
                ["station", "pettitt_year", "pettitt_sig", "step_size"]].copy()
            GMAP.year_map(area, sub, "pettitt_year", "pettitt_sig",
                          f"{var}-Season Change-Point Year (Pettitt)",
                          f"MAP_08_changepoint_year_{var.lower()}",
                          "Change-point year", out_dir=C.CHANGEPOINT,
                          dir_col="step_size")
    n_cp_sig = int(cp_tab["pettitt_sig"].sum())
    fw = cp_field.set_index("timescale")["field_p_value"].to_dict()
    log.info("Change-point: %d/%d station-series with significant shift; "
             "field-significance p (Wet=%.3f, Dry=%.3f).",
             n_cp_sig, len(cp_tab), fw.get("Wet", float('nan')),
             fw.get("Dry", float('nan')))

    # ---------------- STEP 3 ENSO (network) --------------------------------
    enso_ok = False
    try:
        enso_m, enso_y = ENSO.build_enso()
        xl(enso_m, "ENSO_MONTHLY.xlsx", "enso_monthly")
        xl(enso_y, "ENSO_YEARLY.xlsx", "enso_yearly")
        enso_ok = True
        log.info("ENSO indices downloaded: %d monthly rows.", len(enso_m))
    except ENSO.ENSODownloadError as e:
        if not args.allow_offline:
            log.error("ENSO download failed and --allow-offline not set. "
                      "Aborting per spec.\n%s", e)
            sys.exit(4)
        log.warning("ENSO download failed; continuing rainfall-only "
                    "(--allow-offline). ENSO-dependent steps SKIPPED.\n%s", e)

    if enso_ok:
        nino_y = enso_y.set_index("year")["Nino34"]
        # Official persistence-based event label drives composites/comparisons;
        # the descriptive per-season label is retained in the exported tables.
        phase_y = enso_y.set_index("year")["ENSO_Event"]
        nino_src = enso_m.attrs.get("nino34_source", "unknown")
        log.info("Nino-3.4 provenance: %s", nino_src)
        nino_m = enso_m[["year", "month", "Nino34"]].copy()
        nino_m_idx = pd.Series(
            nino_m["Nino34"].values,
            index=pd.to_datetime(dict(year=nino_m.year, month=nino_m.month, day=1)))

        # STEP 5 correlation
        pairs = {"Annual vs Nino3.4": (annual, nino_y),
                 "Wet vs Nino3.4": (wet, nino_y),
                 "Dry vs Nino3.4": (dry, nino_y)}
        xl(P.correlation_table(pairs, "pearson"), "TABLE_02_PEARSON.xlsx")
        xl(P.correlation_table(pairs, "spearman"), "TABLE_03_SPEARMAN.xlsx")

        # STEP 6 lag
        mser = pd.Series(monthly["rain_mm"].values, index=monthly.index)
        lag_tab, best = P.lag_correlation(mser, nino_m_idx, args.max_lag)
        xl(lag_tab, "TABLE_04_LAG_CORRELATION.xlsx")
        FIG.fig06_lag(lag_tab)
        log.info("Best lag = %d months (r=%.3f)", best["lag_months"], best["r"])

        # STEP 7 composite + STEP 8 group comparison
        xl(P.composite(series_by_var, phase_y), "TABLE_05_ENSO_COMPOSITE.xlsx")
        xl(P.group_comparison(series_by_var, phase_y),
           "TABLE_06_GROUP_COMPARISON.xlsx")

        # figures 3,4,5,7
        FIG.fig03_nino(enso_m)
        FIG.fig_scatter(nino_y, annual, "Nino-3.4 (degC)", "Annual rainfall (mm)",
                        "Annual Rainfall vs Nino-3.4", "FIGURE_04_annual_vs_nino")
        FIG.fig_scatter(nino_y, wet, "Nino-3.4 (degC)", "Wet-season rainfall (mm)",
                        "Wet-Season Rainfall vs Nino-3.4", "FIGURE_05_wet_vs_nino")
        FIG.fig07_boxplot(series_by_var, phase_y)

        # Per-station correlation with Nino-3.4 (significance heatmap)
        ps_corr = P.per_station_enso_corr(ps, nino_y, "pearson")
        write_results("TABLE_15_PER_STATION_ENSO_CORRELATION.xlsx", ps_corr,
                      sig_mask=ps_corr["significant"], main_sheet="station_corr",
                      info_extra={"Table": "Per-station rainfall-Nino3.4 correlation",
                                  "Method": "Pearson r + Fisher-z 95% CI",
                                  "'Significant' sheet": "p<alpha"})
        FIG.fig_per_station_enso_corr(ps_corr)
        if area is not None:
            for var, fn in [("Annual", "MAP_05_enso_corr_annual"),
                            ("Wet", "MAP_06_enso_corr_wet"),
                            ("Dry", "MAP_07_enso_corr_dry")]:
                sub = ps_corr[ps_corr["timescale"] == var][
                    ["station", "r", "significant"]].copy()
                GMAP.significance_map(
                    area, sub, "r", "significant",
                    f"{var} Rainfall–Niño-3.4 Correlation", fn,
                    "Pearson r")
        n_corr_sig = int(ps_corr["significant"].sum())
        log.info("Per-station ENSO correlation: %d/%d significant at a=0.05.",
                 n_corr_sig, len(ps_corr))

    # ---------------- OPTIONAL: IOD / DMI second predictor -----------------
    iod_ok = False
    if C.INCLUDE_IOD:
        try:
            dmi_m, dmi_y = IOD.fetch_dmi()
            xl(dmi_m, "DMI_MONTHLY.xlsx", "dmi_monthly")
            xl(dmi_y, "DMI_YEARLY.xlsx", "dmi_yearly")
            iod_ok = True
            log.info("DMI/IOD downloaded: %d monthly rows.", len(dmi_m))
        except Exception as e:                                # noqa: BLE001
            log.warning("DMI/IOD unavailable; IOD analysis SKIPPED (not "
                        "fabricated).\n%s", e)

    if C.INCLUDE_IOD and iod_ok:
        dmi_yser = dmi_y.set_index("year")["DMI"]
        # Rainfall ~ DMI correlation (continuous), mirroring the Nino-3.4 tables
        dmi_pairs = {"Annual vs DMI": (annual, dmi_yser),
                     "Wet vs DMI": (wet, dmi_yser),
                     "Dry vs DMI": (dry, dmi_yser)}
        xl(P.correlation_table(dmi_pairs, "pearson"), "TABLE_09_DMI_PEARSON.xlsx")
        xl(P.correlation_table(dmi_pairs, "spearman"),
           "TABLE_10_DMI_SPEARMAN.xlsx")
        FIG.fig_scatter(dmi_yser, annual, "DMI (degC)", "Annual rainfall (mm)",
                        "Annual Rainfall vs DMI (IOD)", "FIGURE_11_annual_vs_dmi")

        # Multivariate comparison: Rainfall ~ Nino3.4 vs ~ DMI vs ~ Nino3.4+DMI
        if enso_ok:
            mt_all, ct_all = [], []
            for var, s in series_by_var.items():
                mt, ct = P.predictor_comparison(
                    s, {"Nino34": nino_y, "DMI": dmi_yser}, var)
                mt_all.append(mt); ct_all.append(ct)
            model_tab = pd.concat(mt_all, ignore_index=True)
            coef_tab = pd.concat(ct_all, ignore_index=True)
            xl(model_tab, "TABLE_11_PREDICTOR_MODEL_COMPARISON.xlsx", "models")
            xl(coef_tab, "TABLE_12_MULTIVARIATE_COEFFICIENTS.xlsx", "coefficients")
            FIG.fig_r2_comparison(model_tab)
            log.info("IOD multivariate comparison written "
                     "(Nino3.4 vs DMI vs both).")

    # ---------------- STEP 12/13 VALIDATION + RELEASE ----------------------
    runtime["finished"] = datetime.now().isoformat(timespec="seconds")
    runtime["seconds"] = round(time.time() - t0, 1)
    runtime["enso_downloaded"] = enso_ok
    runtime["iod_included"] = bool(C.INCLUDE_IOD and iod_ok)
    _release_report(qc, desc, tfpw, sens, cross, runtime, enso_ok)
    log.info("DONE in %.1fs. ENSO steps %s. IOD %s.",
             runtime["seconds"], "INCLUDED" if enso_ok else "SKIPPED (offline)",
             "INCLUDED" if (C.INCLUDE_IOD and iod_ok) else "SKIPPED")


def _release_report(qc, desc, tfpw, sens, cross, runtime, enso_ok):
    import glob, os
    tables = sorted(os.path.basename(p) for p in glob.glob(str(C.TAB / "*.xlsx")))
    figs = sorted(os.path.basename(p) for p in glob.glob(str(C.FIG / "*.png")))
    with pd.ExcelWriter(C.TAB / "FINAL_RELEASE_REPORT.xlsx",
                        engine="xlsxwriter") as w:
        qc["summary"].to_excel(w, index=False, sheet_name="QC_summary")
        desc.to_excel(w, index=False, sheet_name="Descriptive")
        tfpw.to_excel(w, index=False, sheet_name="TFPW_MK")
        sens.to_excel(w, index=False, sheet_name="Sens_slope")
        cross.to_excel(w, index=False, sheet_name="Trend_crosscheck")
        pd.DataFrame([runtime]).T.reset_index().rename(
            columns={"index": "key", 0: "value"}).to_excel(
            w, index=False, sheet_name="Runtime")
        pd.DataFrame({"generated_tables": tables}).to_excel(
            w, index=False, sheet_name="Tables")
        pd.DataFrame({"generated_figures": figs}).to_excel(
            w, index=False, sheet_name="Figures")
        pd.DataFrame({"validation": [
            f"Years 1981-2014 complete: {qc['summary']['n_missing_calendar_days'].iloc[0]==0}",
            f"No missing values: {qc['summary']['total_missing_values'].iloc[0]==0}",
            f"ENSO steps executed: {enso_ok}"]}).to_excel(
            w, index=False, sheet_name="Validation")


if __name__ == "__main__":
    main()
