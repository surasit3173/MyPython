# -*- coding: utf-8 -*-
"""
src/io_export.py — Audit workbook export (Info / Comprehensive / Significant),
per the project's Figure & Table Quality Standard section 5.
"""

import pandas as pd
import config


def write_results_workbook(df_all, out_path, source_files, coord_file, boundary_file, timestamp):
    info_rows = [
        ("Framework version", "Q1 Hydroclimatology Trend + GIS Framework v2.8"),
        ("Study area", config.STUDY_AREA_NAME),
        ("Generated (UTC)", timestamp),
        ("Rainfall source file(s)", "; ".join(source_files)),
        ("Station coordinate file", coord_file),
        ("Study-area boundary file", boundary_file),
        ("Number of stations analyzed", int(df_all["Station"].nunique())),
        ("Analysis period completeness threshold", f"{config.COMPLETENESS_THRESHOLD:.0%}"),
        ("Minimum record length (years)", config.MIN_YEARS),
        ("Significance level (alpha)", config.ALPHA),
        ("Wet-season months", str(config.WET_MONTHS)),
        ("Dry-season months", str(config.DRY_MONTHS)),
        ("Primary trend-test decision rule", "TFPW-MK if lag-1 autocorrelation significant at alpha; else Original MK"),
        ("Mandatory cross-checks reported for every test", "Original MK; TFPW-MK; MMK (Hamed & Rao, 1998)"),
        ("Change-point test", "Pettitt (1979), via pyhomogeneity, computed on RAW (non-prewhitened) series, using the deterministic closed-form asymptotic p-value (sim=0), clipped to [0,1]. See CHANGELOG_v2.6_to_v2.7.md (the library's default Monte Carlo p-value is non-reproducible run-to-run)."),
        ("Seasonal completeness validation", "Structural (calendar-boundary) completeness check applied to every season (Annual/Wet/Dry): a candidate year is only considered AT ALL if its full required calendar-month span lies entirely within the dataset's actual date range, computed from config.py month definitions + the data's own min/max date (not hard-coded). Prevents edge hydrological-years at the start/end of the record (e.g. a Dry season requiring Nov-Dec of the year before the record begins) from being silently counted as complete. See N_StructurallyPossible column and CHANGELOG_v2.3_to_v2.4.md."),
        ("Diagnostic figure CI band", "Anchored at (median(x), median(y)) per station-season, matching scipy.stats.theilslopes' own intercept convention. A v2.4 plotting bug (fixed in v2.5) previously reused the point-estimate intercept with the CI-bound slopes, producing a physically impossible band (e.g. +-20,000 mm on ~1,000 mm data). See CHANGELOG_v2.4_to_v2.5.md."),
        ("Diagnostic figure layout", "Stats box and legend are both fixed-position and length-capped so neither can overlap the other regardless of station (batch-verified across all 36 station-season figures via real rendered bounding boxes, not spot-checked). See CHANGELOG_v2.5_to_v2.6.md and CHANGELOG_v2.7_to_v2.8.md."),
        ("Multiple-testing correction", "Benjamini-Hochberg (1995) FDR, applied within each season family"),
        ("Field significance", "Bootstrap Monte Carlo, independence-across-tests null, per season family"),
        ("GIS interpolation method", f"Inverse-distance weighting, power={config.IDW_POWER}, clipped to study-area boundary"),
        ("Data integrity statement", "Real observations only. No imputation, interpolation, or synthetic filling of missing days/months/years. Incomplete periods are dropped, not filled (drop-not-fill, min_count=1)."),
        ("Known limitation - TFPW", "Plain TFPW (Yue & Wang, 2002) used, not variance-corrected VCTFPW; TFPW-MK is a conservative cross-check, not the sole basis for a trend claim."),
        ("Known limitation - field significance", "Does not model inter-gauge spatial cross-correlation; treats tests as independent under the null within a season family."),
        ("Known limitation - GIS surface", "The IDW surface is indicative only, especially between widely-spaced or non-significant gauges; per-gauge marker values are the actual result."),
        ("Known statistical pitfall - MMK-HR", "The Hamed & Rao (1998) variance correction can produce a mathematically invalid negative corrected variance for some short/negatively-autocorrelated series (observed in this run — see MMK_HR_Valid=False rows). This is a documented edge case of the method itself, not a data or code error. p_MMK_HR is left blank and MMK_HR_Valid=False for those rows; do not treat a blank value as 'not significant'."),
    ]
    info_df = pd.DataFrame(info_rows, columns=["Field", "Value"])

    sig_df = df_all[df_all["Significant(FDR)"] == "Yes"].copy()

    comparison_cols = ["Station", "Scale", "p_MK", "p_TFPW_MK", "p_MMK_HR", "MMK_HR_Valid",
                       "PrimaryMethod", "p_Primary", "MethodAgreement", "Significant(FDR)"]
    comparison_df = df_all[comparison_cols].copy()

    with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
        info_df.to_excel(writer, sheet_name="Info", index=False)
        df_all.to_excel(writer, sheet_name="Comprehensive", index=False)
        comparison_df.to_excel(writer, sheet_name="MethodComparison", index=False)
        if len(sig_df) > 0:
            sig_df.to_excel(writer, sheet_name="Significant", index=False)
        else:
            pd.DataFrame([{"Note": "No station-season-method combination was significant after FDR correction."}]).to_excel(
                writer, sheet_name="Significant", index=False
            )
        for sheet in writer.sheets.values():
            sheet.set_column(0, 30, 16)
