"""Generate publication-quality Q2-standard tables for Prachuap Khiri Khan ENSO manuscript."""

from __future__ import annotations

import os
from pathlib import Path
import pandas as pd
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "CMIP6PrachuapKhiriKhan" / "pkk_enso_output"
TABLES_DIR = REPO_ROOT / "CMIP6PrachuapKhiriKhan" / "output" / "tables"
DELIVERABLES_DIR = REPO_ROOT / "CMIP6PrachuapKhiriKhan" / "deliverables"

TABLES_DIR.mkdir(parents=True, exist_ok=True)
DELIVERABLES_DIR.mkdir(parents=True, exist_ok=True)


def set_cell_background(cell, fill_hex: str):
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def set_table_borders(table, top_sz="12", bottom_sz="12", header_bottom_sz="6"):
    tblPr = table._element.xpath('w:tblPr')
    if tblPr:
        borders = parse_xml(
            f'<w:tblBorders {nsdecls("w")}>\n'
            f'  <w:top w:val="single" w:sz="{top_sz}" w:space="0" w:color="000000"/>\n'
            f'  <w:bottom w:val="single" w:sz="{bottom_sz}" w:space="0" w:color="000000"/>\n'
            f'  <w:left w:val="none"/>\n'
            f'  <w:right w:val="none"/>\n'
            f'  <w:insideH w:val="none"/>\n'
            f'  <w:insideV w:val="none"/>\n'
            f'</w:tblBorders>'
        )
        tblPr[0].append(borders)


def format_cell_paragraph(cell, text: str, bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.LEFT, font_size=9):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = align
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.05
    run = p.add_run(str(text))
    run.font.name = "Times New Roman"
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = RGBColor(0, 0, 0)
    return run


def make_table_1():
    coords = pd.read_csv(REPO_ROOT / "CMIP6PrachuapKhiriKhan" / "data" / "station_coordinates_PrachuapKhiriKhan.csv")
    coords["station"] = coords["station"].astype(str)

    metrics = pd.read_csv(OUTPUT_DIR / "seasonal_metrics_all.csv.gz")
    obs_metrics = metrics[metrics["source_type"] == "OBSERVED"].copy()
    obs_metrics["station"] = obs_metrics["station"].astype(str)

    rainy_mean = obs_metrics[obs_metrics["season_type"] == "RAINY"].groupby("station")["PRCPTOT"].mean()
    hotdry_mean = obs_metrics[obs_metrics["season_type"] == "HOT_DRY"].groupby("station")["PRCPTOT"].mean()

    t1 = coords.copy()
    t1["rainy_mean_mm"] = t1["station"].map(rainy_mean)
    t1["hotdry_mean_mm"] = t1["station"].map(hotdry_mean)
    t1["annual_mean_mm"] = t1["rainy_mean_mm"] + t1["hotdry_mean_mm"]
    t1["rainy_ratio_pct"] = 100.0 * t1["rainy_mean_mm"] / t1["annual_mean_mm"]

    # Formatting CSV
    t1_out = pd.DataFrame({
        "Station Code": t1["station"],
        "Latitude (°N)": t1["latitude"].map("{:.2f}".format),
        "Longitude (°E)": t1["longitude"].map("{:.2f}".format),
        "Elevation (m)": t1["elevation (m.MSL.)"].replace("NS", "N/A"),
        "Rainy Season (mm)": t1["rainy_mean_mm"].map("{:.1f}".format),
        "Hot/Dry Season (mm)": t1["hotdry_mean_mm"].map("{:.1f}".format),
        "Annual Total (mm)": t1["annual_mean_mm"].map("{:.1f}".format),
        "Rainy Ratio (%)": t1["rainy_ratio_pct"].map("{:.1f}".format),
    })

    t1_out.to_csv(TABLES_DIR / "Table_01_Station_Climatology.csv", index=False)
    print("Table 1 CSV generated.")
    return t1_out


def make_table_2():
    indices_data = [
        ("PRCPTOT", "Total seasonal precipitation", "mm", "Sum of daily rainfall on wet days (P ≥ 1.0 mm)"),
        ("wet_day_frequency_pct", "Wet-day frequency", "%", "Percentage of days with P ≥ 1.0 mm in season"),
        ("Rx1day", "Maximum 1-day precipitation", "mm", "Highest single-day precipitation amount in season"),
        ("Rx5day", "Maximum 5-day consecutive precipitation", "mm", "Highest 5-day consecutive precipitation sum in season"),
        ("CDD", "Consecutive dry days", "days", "Maximum number of consecutive dry days (P < 1.0 mm)"),
        ("CWD", "Consecutive wet days", "days", "Maximum number of consecutive wet days (P ≥ 1.0 mm)"),
        ("R10mm", "Heavy precipitation days", "days", "Count of days with daily precipitation P ≥ 10.0 mm"),
        ("R20mm", "Very heavy precipitation days", "days", "Count of days with daily precipitation P ≥ 20.0 mm"),
    ]
    t2_out = pd.DataFrame(indices_data, columns=["Index Code", "Name", "Units", "Definition / Calculation Logic"])
    t2_out.to_csv(TABLES_DIR / "Table_02_Precipitation_Indices_Framework.csv", index=False)
    print("Table 2 CSV generated.")
    return t2_out


def make_table_3():
    df = pd.read_csv(OUTPUT_DIR / "primary_response_summary.csv")
    obs = df[df["source_type"] == "OBSERVED"].copy()

    rows = []
    for season in ["RAINY", "HOT_DRY"]:
        season_label = "Rainy (May–Oct)" if season == "RAINY" else "Hot/Dry (Nov–Apr)"
        sub = obs[obs["season_type"] == season]
        for metric in ["PRCPTOT", "wet_day_frequency_pct", "Rx1day", "Rx5day", "CDD", "CWD", "R10mm", "R20mm"]:
            m_sub = sub[sub["metric"] == metric]
            el = m_sub[m_sub["phase"] == "EL_NINO"].iloc[0]
            la = m_sub[m_sub["phase"] == "LA_NINA"].iloc[0]

            el_ci = f"[{el['ci_low_pct']:.1f}, {el['ci_high_pct']:.1f}]"
            la_ci = f"[{la['ci_low_pct']:.1f}, {la['ci_high_pct']:.1f}]"

            rows.append({
                "Season": season_label,
                "Precipitation Index": metric,
                "El Niño Anomaly (%)": f"{el['response_pct']:+.1f}",
                "El Niño 95% CI (%)": el_ci,
                "El Niño p-val": f"{el['permutation_p_pct']:.4f}",
                "El Niño FDR q-val": f"{el['permutation_p_bh_primary']:.4f}",
                "La Niña Anomaly (%)": f"{la['response_pct']:+.1f}",
                "La Niña 95% CI (%)": la_ci,
                "La Niña p-val": f"{la['permutation_p_pct']:.4f}",
                "La Niña FDR q-val": f"{la['permutation_p_bh_primary']:.4f}",
            })

    t3_out = pd.DataFrame(rows)
    t3_out.to_csv(TABLES_DIR / "Table_03_Observed_ENSO_Anomalies.csv", index=False)
    print("Table 3 CSV generated.")
    return t3_out


def make_table_4():
    pres = pd.read_csv(OUTPUT_DIR / "qdm_enso_signal_preservation.csv")
    rows = []
    for season in ["RAINY", "HOT_DRY"]:
        season_label = "Rainy (May–Oct)" if season == "RAINY" else "Hot/Dry (Nov–Apr)"
        sub = pres[pres["season_type"] == season]
        for metric in ["PRCPTOT", "wet_day_frequency_pct", "Rx1day", "Rx5day", "CDD", "CWD", "R10mm", "R20mm"]:
            m_sub = sub[sub["metric"] == metric]
            for phase in ["EL_NINO", "LA_NINA"]:
                row = m_sub[m_sub["phase"] == phase].iloc[0]
                rows.append({
                    "Season": season_label,
                    "Metric": metric,
                    "ENSO Phase": "El Niño" if phase == "EL_NINO" else "La Niña",
                    "Observed Anomaly (%)": f"{row['observed_response_pct']:+.1f}",
                    "Raw CMIP6 Anomaly (%)": f"{row['raw_response_pct']:+.1f}",
                    "QDM CMIP6 Anomaly (%)": f"{row['qdm_response_pct']:+.1f}",
                    "Raw Abs Error (%p)": f"{row['raw_absolute_error_vs_observed_pct_points']:.1f}",
                    "QDM Abs Error (%p)": f"{row['qdm_absolute_error_vs_observed_pct_points']:.1f}",
                    "QDM Moved Toward Obs": "Yes" if row["qdm_moved_toward_observed"] else "No",
                    "Signal Classification": row["category"],
                })

    t4_out = pd.DataFrame(rows)
    t4_out.to_csv(TABLES_DIR / "Table_04_CMIP6_QDM_Signal_Preservation.csv", index=False)
    print("Table 4 CSV generated.")
    return t4_out


def build_docx_tables():
    doc = docx.Document()

    # Document Title
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Authoritative Publication Tables: Prachuap Khiri Khan ENSO & QDM Analysis")
    r.font.name = "Times New Roman"
    r.font.size = Pt(14)
    r.font.bold = True

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = p2.add_run("Target Journal: Science Essence Journal (SEJ) / Scopus Q3 Standard\n")
    r2.font.name = "Times New Roman"
    r2.font.size = Pt(11)
    r2.font.italic = True

    # Table 1
    t1_df = make_table_1()
    p_t1 = doc.add_paragraph()
    r_t1 = p_t1.add_run("Table 1. Station characteristics and seasonal rainfall climatology across the 12 meteorological stations in Prachuap Khiri Khan (1981–2014).")
    r_t1.font.bold = True
    r_t1.font.size = Pt(10)

    table1 = doc.add_table(rows=len(t1_df) + 1, cols=len(t1_df.columns))
    table1.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(table1)

    for col_idx, col_name in enumerate(t1_df.columns):
        cell = table1.cell(0, col_idx)
        set_cell_background(cell, "F2F2F2")
        format_cell_paragraph(cell, col_name, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, font_size=8.5)

    for row_idx, row_data in enumerate(t1_df.values):
        for col_idx, val in enumerate(row_data):
            cell = table1.cell(row_idx + 1, col_idx)
            align = WD_ALIGN_PARAGRAPH.LEFT if col_idx == 0 else WD_ALIGN_PARAGRAPH.RIGHT
            format_cell_paragraph(cell, val, align=align, font_size=8.5)

    p_note1 = doc.add_paragraph()
    r_note1 = p_note1.add_run("Note: Elevation data indicated as N/A represent station records without published benchmark MSL elevation metadata. Rainy season spans May–October; Hot/Dry season spans November–April.")
    r_note1.font.size = Pt(8)
    r_note1.font.italic = True

    doc.add_paragraph() # spacing

    # Table 2
    t2_df = make_table_2()
    p_t2 = doc.add_paragraph()
    r_t2 = p_t2.add_run("Table 2. Definitions of seasonal precipitation indices, ENSO classification criteria, and statistical evaluation procedures.")
    r_t2.font.bold = True
    r_t2.font.size = Pt(10)

    table2 = doc.add_table(rows=len(t2_df) + 1, cols=len(t2_df.columns))
    table2.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(table2)

    for col_idx, col_name in enumerate(t2_df.columns):
        cell = table2.cell(0, col_idx)
        set_cell_background(cell, "F2F2F2")
        format_cell_paragraph(cell, col_name, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, font_size=8.5)

    for row_idx, row_data in enumerate(t2_df.values):
        for col_idx, val in enumerate(row_data):
            cell = table2.cell(row_idx + 1, col_idx)
            align = WD_ALIGN_PARAGRAPH.LEFT if col_idx in [0, 1, 3] else WD_ALIGN_PARAGRAPH.CENTER
            format_cell_paragraph(cell, val, align=align, font_size=8.5)

    p_note2 = doc.add_paragraph()
    r_note2 = p_note2.add_run("Note: Precipitation indices follow ETCCDI standards adapted for tropical seasonal management cycles. ENSO phases are defined using 3-month running ONI anomalies (NOAA ERSSTv5/v6) with a 5-consecutive-season threshold of ±0.5°C.")
    r_note2.font.size = Pt(8)
    r_note2.font.italic = True

    doc.add_paragraph()

    # Table 3
    t3_df = make_table_3()
    p_t3 = doc.add_paragraph()
    r_t3 = p_t3.add_run("Table 3. Observed seasonal precipitation anomalies during El Niño and La Niña phases relative to Neutral conditions across Prachuap Khiri Khan (1981–2014).")
    r_t3.font.bold = True
    r_t3.font.size = Pt(10)

    table3 = doc.add_table(rows=len(t3_df) + 1, cols=len(t3_df.columns))
    table3.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(table3)

    for col_idx, col_name in enumerate(t3_df.columns):
        cell = table3.cell(0, col_idx)
        set_cell_background(cell, "F2F2F2")
        format_cell_paragraph(cell, col_name, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, font_size=8)

    for row_idx, row_data in enumerate(t3_df.values):
        for col_idx, val in enumerate(row_data):
            cell = table3.cell(row_idx + 1, col_idx)
            align = WD_ALIGN_PARAGRAPH.LEFT if col_idx < 2 else WD_ALIGN_PARAGRAPH.RIGHT
            format_cell_paragraph(cell, val, align=align, font_size=8)

    p_note3 = doc.add_paragraph()
    r_note3 = p_note3.add_run("Note: Anomalies are expressed as percentage changes relative to Neutral conditions. 95% CIs are derived from 5,000 paired block bootstrap replicates. Permutation p-values are based on 4,999 resamples. FDR q-values apply Benjamini-Hochberg adjustment across primary tests.")
    r_note3.font.size = Pt(8)
    r_note3.font.italic = True

    doc.add_paragraph()

    # Table 4
    t4_df = make_table_4()
    p_t4 = doc.add_paragraph()
    r_t4 = p_t4.add_run("Table 4. Comparison of raw CMIP6 ensemble vs. QDM bias-corrected CMIP6 ensemble representation of ENSO-conditioned rainfall anomalies.")
    r_t4.font.bold = True
    r_t4.font.size = Pt(10)

    table4 = doc.add_table(rows=len(t4_df) + 1, cols=len(t4_df.columns))
    table4.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(table4)

    for col_idx, col_name in enumerate(t4_df.columns):
        cell = table4.cell(0, col_idx)
        set_cell_background(cell, "F2F2F2")
        format_cell_paragraph(cell, col_name, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, font_size=8)

    for row_idx, row_data in enumerate(t4_df.values):
        for col_idx, val in enumerate(row_data):
            cell = table4.cell(row_idx + 1, col_idx)
            align = WD_ALIGN_PARAGRAPH.LEFT if col_idx < 3 else WD_ALIGN_PARAGRAPH.RIGHT if col_idx < 8 else WD_ALIGN_PARAGRAPH.CENTER
            format_cell_paragraph(cell, val, align=align, font_size=8)

    p_note4 = doc.add_paragraph()
    r_note4 = p_note4.add_run("Note: CMIP6 model ensemble includes ACCESS-ESM1-5, CESM2, CanESM5, EC-Earth3, and MIROC6. QDM refers to blocked cross-fitted Quantile Delta Mapping applied at monthly resolution. Signal classification indicates whether QDM preserved, attenuated, amplified, or reversed the teleconnection signal relative to raw model anomalies.")
    r_note4.font.size = Pt(8)
    r_note4.font.italic = True

    doc.save(DELIVERABLES_DIR / "Tables_Prachuap_ENSO_QDM.docx")
    print("Tables DOCX saved to deliverables/Tables_Prachuap_ENSO_QDM.docx")


if __name__ == "__main__":
    build_docx_tables()
