"""Author the APST manuscript from the supplied template and validated tables."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


HERE = Path(__file__).resolve().parent
TEMPLATE = Path(r"D:\วารสาร APST\Updated-APST-format-September-16-2025.docx")
DERIVED = HERE / "derived"
FIGURES = HERE / "figures"
OUT = HERE / "APST_Phetchaburi_Precipitation_Extremes_Manuscript.docx"
PROJECT = HERE.parent / "utt_etccdi_easr_20260905"
PRIMARY_RESULTS = PROJECT / "outputs" / "phetchaburi_final2" / "results"


def set_run(run, size=10, bold=False, italic=False, font="Times New Roman", color=None):
    run.font.name = font
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), font)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    if color:
        run.font.color.rgb = RGBColor(*color)


def set_para(p, size=10, bold=False, italic=False, align=None, spacing=24, before=0, after=0, keep=False):
    pf = p.paragraph_format
    pf.line_spacing = Pt(spacing)
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.keep_with_next = keep
    pf.widow_control = True
    if align is not None:
        p.alignment = align
    for r in p.runs:
        set_run(r, size=size, bold=bold, italic=italic)
    return p


def add_text(doc, text: str, *, size=10, bold=False, italic=False, align=None, spacing=24, before=0, after=0, keep=False, style=None):
    p = doc.add_paragraph(style=style) if style else doc.add_paragraph()
    if text:
        r = p.add_run(text)
        set_run(r, size=size, bold=bold, italic=italic)
    set_para(p, size=size, bold=bold, italic=italic, align=align, spacing=spacing, before=before, after=after, keep=keep)
    return p


def add_equation(doc, text: str, number: int):
    """Add an editable Word math paragraph using Unicode math notation."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.line_spacing = Pt(18)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    omath_para = OxmlElement("m:oMathPara")
    omath = OxmlElement("m:oMath")
    mr = OxmlElement("m:r")
    mt = OxmlElement("m:t")
    mt.text = text
    mr.append(mt)
    omath.append(mr)
    omath_para.append(omath)
    p._p.append(omath_para)
    r = p.add_run(f"   ({number})")
    set_run(r, size=9, font="Times New Roman")
    return p


def add_heading(doc, text: str, *, level=1):
    p = doc.add_paragraph()
    r = p.add_run(text)
    set_run(r, size=10, bold=(level == 1), italic=(level == 2))
    set_para(p, size=10, bold=(level == 1), italic=(level == 2), spacing=24, before=0, after=0, keep=True)
    return p


def add_caption(doc, label: str, text: str, above=True):
    p = doc.add_paragraph()
    r = p.add_run(label + " ")
    set_run(r, size=9, bold=True)
    r = p.add_run(text)
    set_run(r, size=9)
    set_para(p, size=9, spacing=12, before=0 if above else 0, after=0 if above else 6, keep=above)
    return p


def set_cell_text(cell, text, *, bold=False, size=8.0, color=None, align=WD_ALIGN_PARAGRAPH.CENTER):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = align
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = Pt(9)
    r = p.add_run(str(text))
    set_run(r, size=size, bold=bold, color=color)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def table_borders(table):
    tbl = table._tbl
    tblPr = tbl.tblPr
    old = tblPr.find(qn("w:tblBorders"))
    if old is not None:
        tblPr.remove(old)
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "bottom", "insideH"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "5")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "7F7F7F")
        borders.append(el)
    for edge in ("left", "right", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "nil")
        borders.append(el)
    tblPr.append(borders)


def shade_cell(cell, fill="E7E6E6"):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = tcPr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tcPr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_table_widths(table, widths):
    for row in table.rows:
        for cell, width in zip(row.cells, widths):
            cell.width = Inches(width)
            tcPr = cell._tc.get_or_add_tcPr()
            tcW = tcPr.find(qn("w:tcW"))
            if tcW is None:
                tcW = OxmlElement("w:tcW")
                tcPr.append(tcW)
            tcW.set(qn("w:w"), str(int(width * 1440)))
            tcW.set(qn("w:type"), "dxa")


def repeat_table_header(row):
    trPr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    trPr.append(tbl_header)


def add_table_stations(doc):
    """Add the exact 13 station records used by the primary analysis run."""
    coords = pd.read_csv(PRIMARY_RESULTS / "station_coordinates_used.csv", dtype={"station": str})
    coords = coords.sort_values("station")
    add_caption(doc, "Table 1.", "Rain-gauge stations used in the Phetchaburi analysis. Station IDs, coordinates and elevations are the values in the primary analysis input.")
    cols = ["Station ID", "Latitude (°N)", "Longitude (°E)", "Elevation (m MSL)"]
    table = doc.add_table(rows=1, cols=4)
    table.autofit = False
    table.style = "Table Grid"
    repeat_table_header(table.rows[0])
    for j, c in enumerate(cols):
        set_cell_text(table.rows[0].cells[j], c, bold=True, size=7.4)
        shade_cell(table.rows[0].cells[j])
    for _, row in coords.iterrows():
        cells = table.add_row().cells
        vals = [str(row["station"]), f"{float(row['latitude']):.4f}", f"{float(row['longitude']):.4f}", f"{float(row['elevation (m.MSL.)']):.2f}"]
        for j, value in enumerate(vals):
            set_cell_text(cells[j], value, size=7.4, align=WD_ALIGN_PARAGRAPH.CENTER)
    table_borders(table)
    set_table_widths(table, [1.05, 1.25, 1.35, 1.45])
    add_text(doc, "Notes: No station names are assigned because the analysis input identifies gauges by station ID only.", size=8, spacing=10, after=6)


def add_table_models(doc):
    models = [
        ("ACCESS-ESM1-5", "CSIRO / ARCCSS", "Australia"),
        ("CanESM5", "Environment and Climate Change Canada / CCCma", "Canada"),
        ("CESM2", "NCAR", "United States"),
        ("EC-Earth3", "EC-Earth Consortium", "Europe"),
        ("FGOALS-g3", "Chinese Academy of Sciences / LASG", "China"),
        ("MIROC6", "MIROC Consortium", "Japan"),
        ("MRI-ESM2-0", "Meteorological Research Institute", "Japan"),
    ]
    add_caption(doc, "Table 2.", "List of the CMIP6 GCMs used in the study.")
    cols = ["Model", "Institution / consortium", "Country", "Series used"]
    table = doc.add_table(rows=1, cols=4)
    table.autofit = False
    table.style = "Table Grid"
    repeat_table_header(table.rows[0])
    for j, c in enumerate(cols):
        set_cell_text(table.rows[0].cells[j], c, bold=True, size=7.2)
        shade_cell(table.rows[0].cells[j])
    for model, institution, country in models:
        cells = table.add_row().cells
        vals = [model, institution, country, "Historical 1995–2014; SSP2-4.5; SSP5-8.5"]
        for j, value in enumerate(vals):
            set_cell_text(cells[j], value, size=7.0, align=WD_ALIGN_PARAGRAPH.LEFT if j in (0, 1, 3) else WD_ALIGN_PARAGRAPH.CENTER)
    table_borders(table)
    set_table_widths(table, [1.05, 2.10, 0.92, 2.10])
    add_text(doc, "Notes: All seven models were used for the historical baseline and both future scenarios. The supplied daily series were already bias-corrected; the correction procedure was not re-estimated in this study.", size=8, spacing=10, after=6)


def add_table_indices(doc):
    rows = [
        ("PRCPTOT", "Annual total wet-day precipitation", "ΣRR for RR ≥ 1 mm", "mm"),
        ("SDII", "Mean precipitation intensity on wet days", "PRCPTOT divided by the number of wet days (RR ≥ 1 mm)", "mm day−1"),
        ("Rx1day", "Maximum 1-day precipitation", "Annual maximum daily precipitation", "mm"),
        ("Rx5day", "Maximum 5-day precipitation", "Annual maximum consecutive 5-day precipitation total", "mm"),
        ("CDD", "Consecutive dry days", "Annual maximum number of consecutive days with RR < 1 mm", "days"),
        ("CWD", "Consecutive wet days", "Annual maximum number of consecutive days with RR ≥ 1 mm", "days"),
        ("R10mm", "Heavy precipitation days", "Annual number of days with RR ≥ 10 mm", "days"),
        ("R20mm", "Very heavy precipitation days", "Annual number of days with RR ≥ 20 mm", "days"),
        ("R50mm", "Very heavy precipitation days", "Annual number of days with RR ≥ 50 mm", "days"),
        ("R95p", "Very wet-day precipitation", "Annual precipitation total on wet days exceeding the station-specific 95th-percentile wet-day threshold", "mm"),
        ("R99p", "Extremely wet-day precipitation", "Annual precipitation total on wet days exceeding the station-specific 99th-percentile wet-day threshold", "mm"),
    ]
    add_caption(doc, "Table 3.", "Definitions of extreme precipitation indices used in the study.")
    cols = ["Index", "Name", "Operational definition", "Unit"]
    table = doc.add_table(rows=1, cols=4)
    table.autofit = False
    table.style = "Table Grid"
    repeat_table_header(table.rows[0])
    for j, c in enumerate(cols):
        set_cell_text(table.rows[0].cells[j], c, bold=True, size=7.2)
        shade_cell(table.rows[0].cells[j])
    for row in rows:
        cells = table.add_row().cells
        for j, value in enumerate(row):
            set_cell_text(cells[j], value, size=6.9, align=WD_ALIGN_PARAGRAPH.LEFT if j in (1, 2) else WD_ALIGN_PARAGRAPH.CENTER)
    table_borders(table)
    set_table_widths(table, [0.72, 1.55, 3.65, 0.62])
    add_text(doc, "Notes: A wet day is RR ≥ 1 mm. R95p and R99p use station-specific fixed wet-day thresholds estimated from 1981–2014 and retained for all annual and future-window calculations.", size=8, spacing=10, after=6)


def add_table_observed(doc, table_df):
    add_caption(doc, "Table 4.", "Observed trend counts and station-median Sen slopes for the 1981–2014 annual precipitation-index series. MK denotes the primary unadjusted standard Mann–Kendall decision; BH-FDR denotes the Benjamini–Hochberg decision across all 143 station–index tests.")
    cols = ["Index", "Unit", "MK inc.", "MK dec.", "MK NS", "BH inc.", "BH dec.", "Median Sen slope\nper decade"]
    table = doc.add_table(rows=1, cols=len(cols))
    table.autofit = False
    table.style = "Table Grid"
    for j, c in enumerate(cols):
        set_cell_text(table.rows[0].cells[j], c, bold=True, size=7.5)
        shade_cell(table.rows[0].cells[j])
    for _, row in table_df.iterrows():
        cells = table.add_row().cells
        vals = [row.Index, row.Unit, int(row.Increasing_MK), int(row.Decreasing_MK), int(row.Not_significant_MK), int(row.Increasing_BH_FDR), int(row.Decreasing_BH_FDR), f"{row.Median_Sen_slope_per_decade:.2f}"]
        for j, v in enumerate(vals):
            set_cell_text(cells[j], v, size=7.5, align=WD_ALIGN_PARAGRAPH.LEFT if j < 2 else WD_ALIGN_PARAGRAPH.CENTER)
    table_borders(table)
    set_table_widths(table, [0.72, 0.82, 0.55, 0.55, 0.55, 0.62, 0.62, 1.05])
    add_text(doc, "Notes: Units are those of the index; slope is expressed per decade. “NS” means not significant at α = 0.05. R95p and R99p use station-specific fixed wet-day thresholds estimated from 1981–2014.", size=8, spacing=10, after=6)


def add_table_future(doc, table_df):
    add_caption(doc, "Table 5.", "Model-first relative change in annual precipitation indices for 2021–2050 relative to the model-consistent 1995–2014 baseline. The median and IQR are calculated across seven models after taking each model’s station median; +/–/0 counts give the number of models with positive, negative or zero station-median change.")
    cols = ["Scenario", "Index", "Median (%)", "IQR (%)", "Range (%)", "+ / – / 0"]
    table = doc.add_table(rows=1, cols=len(cols))
    table.autofit = False
    table.style = "Table Grid"
    for j, c in enumerate(cols):
        set_cell_text(table.rows[0].cells[j], c, bold=True, size=7.4)
        shade_cell(table.rows[0].cells[j])
    for _, row in table_df.iterrows():
        cells = table.add_row().cells
        scenario = "SSP2-4.5" if row.Scenario == "SSP2-4.5" else "SSP5-8.5"
        vals = [scenario, row.Index, f"{row.Median_relative_change_pct:.1f}", f"{row.IQR_low_pct:.1f} to {row.IQR_high_pct:.1f}", f"{row.Min_pct:.1f} to {row.Max_pct:.1f}", f"{int(row.Positive_models)}/{int(row.Negative_models)}/{int(row.Zero_models)}"]
        for j, v in enumerate(vals):
            set_cell_text(cells[j], v, size=7.3, align=WD_ALIGN_PARAGRAPH.LEFT if j < 2 else WD_ALIGN_PARAGRAPH.CENTER)
    table_borders(table)
    set_table_widths(table, [0.85, 0.72, 0.78, 1.10, 1.10, 0.78])
    add_text(doc, "Notes: A positive value denotes an increase relative to the baseline. This aggregation describes model spread; it is not a formal probability distribution and does not imply model independence.", size=8, spacing=10, after=6)


def add_figure(doc, path: Path, label: str, text: str, width=6.25):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.keep_with_next = True
    run = p.add_run()
    run.add_picture(str(path), width=Inches(width))
    cap = add_caption(doc, label, text, above=False)
    cap.alignment = WD_ALIGN_PARAGRAPH.LEFT
    return p


def add_line_numbering(doc):
    sectPr = doc.sections[0]._sectPr
    old = sectPr.find(qn("w:lnNumType"))
    if old is not None:
        sectPr.remove(old)
    ln = OxmlElement("w:lnNumType")
    ln.set(qn("w:count"), "1")
    ln.set(qn("w:restart"), "newPage")
    ln.set(qn("w:distance"), "360")
    sectPr.append(ln)


def clear_body(doc):
    body = doc._element.body
    sectPr = body.sectPr
    for child in list(body):
        if child is not sectPr:
            body.remove(child)


def main():
    table_obs = pd.read_csv(DERIVED / "table_observed_trends.csv")
    table_future = pd.read_csv(DERIVED / "table_future_change_model_first.csv")
    meta = json.loads((DERIVED / "derived_results.json").read_text(encoding="utf-8"))
    doc = Document(str(TEMPLATE))
    clear_body(doc)
    add_line_numbering(doc)
    sec = doc.sections[0]
    sec.top_margin = Inches(1); sec.bottom_margin = Inches(1); sec.left_margin = Inches(1); sec.right_margin = Inches(1)
    sec.header_distance = Inches(0.4924); sec.footer_distance = Inches(1)

    title = add_text(doc, "Observed and Near-Term Projected Precipitation Extremes in Phetchaburi Province under SSP2-4.5 and SSP5-8.5", size=12, bold=True, spacing=24, after=0)
    add_text(doc, "Surasit Punyawansiri1,*", size=10, spacing=24)
    add_text(doc, "1Office of Water Management and Hydrology, Royal Irrigation Department, Dusit, Bangkok 10300, Thailand", size=10, spacing=24)
    add_text(doc, "*Corresponding author: Surasit.pu@ku.th", size=10, spacing=24, after=6)

    add_text(doc, "Abstract", size=10, bold=True, spacing=24, keep=True)
    abstract = ("Phetchaburi Province is exposed to competing precipitation signals: declining wet-day accumulation can coexist with short-duration heavy rainfall. "
                "This study quantifies observed and near-term changes in 11 annual precipitation-extreme indices from 13 rain gauges for 1981–2014 and from seven bias-corrected CMIP6 daily model series for 2021–2050 under SSP2-4.5 and SSP5-8.5. "
                "Annual indices were screened at 90% completeness; standard Mann–Kendall testing with Sen’s slope was the primary inference, and Benjamini–Hochberg false-discovery-rate control was applied to the 143 observed station–index tests. "
                "The observations show widespread decreases in PRCPTOT and CWD, increases in CDD, SDII, Rx1day, R95p and R99p, and weaker spatial coherence for Rx5day and R50mm. "
                "Model-first station-median changes are mixed: under SSP2-4.5, the median changes are −2.5% for PRCPTOT, +7.6% for Rx5day and +59.0% for R99p; under SSP5-8.5 they are −9.0%, −0.7% and +20.1%, respectively, with broad inter-model ranges. "
                "A station-referenced inverse-distance-weighting (IDW) depiction is used only to show spatial contrast: SSP2-4.5 is near-neutral or weakly positive in the northern and central province and more negative in the southern and southeastern station cluster, whereas SSP5-8.5 is more broadly negative. The IDW fields are descriptive and are not interpreted as dynamically downscaled or independently validated gridded projections.")
    add_text(doc, abstract, size=10, spacing=24, after=0)
    add_text(doc, "Keywords: Climate change, Inverse distance weighting, Mann–Kendall test, Multi-model ensemble, Sen’s slope, Yue–Wang variance correction", size=10, spacing=24, after=6)

    add_heading(doc, "1. Introduction", level=1)
    add_text(doc, "Changes in precipitation extremes affect water-supply reliability, drought persistence, flood risk, agricultural productivity and community safety. The physical basis is not a simple shift in annual totals: warming increases atmospheric moisture capacity, while circulation, monsoon timing and land–sea contrasts determine whether that moisture appears as more intense events, longer dry spells or both [1,2]. For this reason, precipitation-extreme assessments commonly use a family of complementary duration, intensity, frequency and percentile indices rather than a single rainfall metric [2].")
    add_text(doc, "The Coupled Model Intercomparison Project Phase 6 (CMIP6) provides a coordinated basis for comparing model responses [3]. Its ScenarioMIP experiments pair climate-model physics with shared socioeconomic pathways, including SSP2-4.5 and SSP5-8.5 [4,5]. CMIP6 multi-model ensembles are valuable for regional assessment, but their local application remains constrained by structural model uncertainty and the sensitivity of extremes to bias-correction choices. A Southeast-Asia assessment found strong spatial and seasonal contrasts in downscaled extremes, while a Cyprus study showed that model spread can reverse the sign of individual indices even when the ensemble narrative appears consistent [6,7]. These findings motivate an index-by-index presentation with an explicit baseline, aggregation order and uncertainty treatment.")
    add_text(doc, "Within Thailand, recent studies have documented non-stationary rainfall variability, observed trends and projected changes in extreme precipitation across southern, northern and central basins [16,17,18,19,20]. However, a station-level assessment that combines multiple ETCCDI-family indices, observed trends and near-term scenario changes remains limited for Phetchaburi Province. The province is an important water-resource and agricultural area in the Phetchaburi–Prachuap Khiri Khan region, where future flood-risk and rainfall changes have direct planning relevance [16,20].")
    add_text(doc, "The present study addresses this gap through three methodological features. First, it uses 11 ETCCDI-family indices spanning duration, intensity, frequency and percentile-based metrics. Second, it combines standard Mann–Kendall/Sen inference with Benjamini–Hochberg false-discovery-rate control and a Yue–Wang effective-sample-size diagnostic. Third, it uses model-first aggregation—calculating each model’s station median before summarizing across the seven-model ensemble—to prevent models with greater spatial heterogeneity from receiving disproportionate weight. The study also presents station-referenced IDW fields as descriptive visualizations, explicitly distinguishing spatial depiction from dynamically downscaled projection [21,22,23,24,25,26,27].")
    add_text(doc, "Phetchaburi is a useful test case because its 13-gauge network spans coastal, lowland and interior areas that are represented unevenly by station locations. The present analysis addresses three questions: (i) which precipitation-extreme indices changed during 1981–2014; (ii) how do seven CMIP6 models differ in their 2021–2050 changes relative to a model-consistent 1995–2014 baseline; and (iii) what broad spatial contrast is suggested by station-referenced IDW fields for the two scenarios? The findings are intended to provide region-specific evidence for drainage design, reservoir operation and agricultural water allocation, while retaining the limitations of station-referenced interpolation [28,29,30].")

    add_heading(doc, "2. Materials and Methods", level=1)
    add_heading(doc, "2.1 Study area, observations and model series", level=2)
    add_text(doc, "The study area is Phetchaburi Province, Thailand. Daily gauge observations cover 1981–2014 at 13 stations (Figure 1; Table 1). The supplied model package contains daily historical and scenario series from the seven CMIP6 GCMs listed in Table 2. Historical model values were summarized for 1995–2014 and future values for 2021–2050. The supplied CMIP6 series were already bias-corrected daily data. The metadata available with this run did not specify the correction algorithm, reference dataset, calibration interval, regridding or ensemble realization; these steps were not re-estimated here. Results therefore condition on the supplied bias-corrected input and do not constitute independent validation of that correction. Reference [8] describes the general importance of checking bias-correction behavior but is not asserted to be the method used here [21,30].")
    add_table_stations(doc)
    add_table_models(doc)
    add_heading(doc, "2.2 Annual precipitation indices and quality control", level=2)
    add_text(doc, "We calculated an ETCCDI-family set of 11 annual indices (Table 3): PRCPTOT (wet-day precipitation total), SDII (wet-day mean intensity), Rx1day and Rx5day (annual one- and five-day maxima), CDD and CWD (maximum consecutive dry and wet days), R10mm, R20mm and R50mm (counts of days at or above 10, 20 and 50 mm), and R95p and R99p (annual precipitation above station-specific 95th and 99th wet-day thresholds). A wet day was RR ≥ 1 mm. The percentile thresholds were fixed once from each station’s complete 1981–2014 wet-day distribution; they were not re-estimated separately in each year or future window. Thus R95p and R99p are fixed-reference percentile indices and should not be read as a claim of exact equivalence to every ETCCDI software implementation [2,30].")
    add_table_indices(doc)
    add_text(doc, "The analysis used the Gregorian calendar for observations. CanESM5, CESM2 and FGOALS-g3 use a 365-day no-leap calendar; February 29 is therefore absent from these model series and was not imputed. Annual completeness was evaluated using the applicable model calendar. Annual summaries required at least 90% valid daily records. A missing day was not silently converted to zero; it interrupted spells and moving windows. The minimum annual completeness across model records was 99.726776%.")
    add_heading(doc, "2.3 Trend inference and multiple testing", level=2)
    add_text(doc, "The primary observed and within-window future diagnostic used the standard two-sided Mann–Kendall statistic [9] and the median pairwise Sen slope [10]. For an annual series x₁, …, xₙ, the Mann–Kendall score, tie-corrected variance and continuity-corrected Z statistic were defined as:")
    add_equation(doc, "S = Σᵢ₌₁ⁿ⁻¹ Σⱼ₌ᵢ₊₁ⁿ sgn(xⱼ − xᵢ)", 1)
    add_equation(doc, "Var(S) = [n(n − 1)(2n + 5) − Σₜ tₜ(tₜ − 1)(2tₜ + 5)] / 18", 2)
    add_equation(doc, "Zₘₖ = (S − 1)/√Var(S) if S > 0; 0 if S = 0; (S + 1)/√Var(S) if S < 0", 3)
    add_text(doc, "The Sen slope was the median of all pairwise slopes, and a trend was labelled significant at α = 0.05:")
    add_equation(doc, "β̂ = median[(xⱼ − xᵢ)/(j − i)], 1 ≤ i < j ≤ n", 4)
    add_text(doc, "The 143 observed station–index p-values were also adjusted using the Benjamini–Hochberg false-discovery-rate procedure [11]. After sorting p-values p₍₁₎ ≤ … ≤ p₍ₘ₎, the largest retained rank k satisfies:")
    add_equation(doc, "p₍ₖ₎ ≤ kq / m", 5)
    add_text(doc, "This controls the expected proportion of false discoveries among the flagged tests but is not a field-significance test. Yue–Wang effective-sample-size correction was retained as a sensitivity diagnostic for serial dependence [12], with the Hamed–Rao warning about autocorrelation motivating the comparison [13]. The 2010 SDII value at station 465002 was undefined because no wet day (RR ≥ 1 mm) occurred in that station-year; consequently, the annual series contained 33 valid observations for standard MK/Sen analysis and was excluded from Yue–Wang MMK because of the irregular-year structure.")
    add_text(doc, "For the Yue–Wang diagnostic, the annual series was first detrended with the Sen slope. Autocorrelations of the detrended residuals at all available lags were then combined to obtain the effective sample size and the adjusted Mann–Kendall variance:")
    add_equation(doc, "n/n_eff = 1 + 2 Σₖ₌₁ⁿ⁻¹ (1 − k/n)ρₖ;     Var_YW(S) = Var(S)(n/n_eff);     n_eff = n/(n/n_eff)", 6)
    add_heading(doc, "2.4 Future-change aggregation", level=2)
    add_text(doc, "For model m, scenario s and index i, the change was calculated from the model’s own baseline and future means as:")
    add_equation(doc, "Δₘ,ₛ,ᵢ = 100 × (X̄future,ₘ,ₛ,ᵢ − X̄base,ₘ,ᵢ) / X̄base,ₘ,ᵢ", 7)
    add_text(doc, "The model-first summary first took the median across the 13 stations within each model, then reported the median, interquartile range and range across the seven models. This order prevents a model with more spatially variable station changes from receiving extra weight. Standard MK results for each model–station–index in 2021–2050 were retained as an unadjusted within-window diagnostic only; they were not interpreted as evidence of a forced trend or as a substitute for the baseline-to-future comparison.")
    add_heading(doc, "2.5 Station-referenced IDW mapping", level=2)
    add_text(doc, "Inverse-distance weighting (IDW), a deterministic interpolator for irregularly spaced observations [14], was used to communicate spatial contrast. For a map location x, the displayed field was:")
    add_equation(doc, "ẑ(x) = Σⱼ wⱼ zⱼ / Σⱼ wⱼ,     wⱼ = d(x, xⱼ)⁻²", 8)
    add_text(doc, "The station-referenced model-median changes were weighted with a power parameter of 2. The resulting fields were masked to the Phetchaburi provincial boundary. These maps are descriptive spatial depictions of station-referenced changes and are not interpreted as dynamically downscaled or independently validated gridded projections. Areas outside the station convex hull are treated as spatial extrapolation.")

    add_heading(doc, "3. Results", level=1)
    add_heading(doc, "3.1 Data completeness and observed trends", level=2)
    add_text(doc, "The final run produced 4,862 station-year index records, 143 observed trend rows, 60,060 future index records, 2,002 future trend rows and 2,002 future-change rows. The observed 95th-percentile thresholds ranged from 14.5 to 42.8 mm and the 99th-percentile thresholds from 26.6 to 76.448 mm, confirming that a common provincial threshold would have removed substantial local intensity contrast.")
    add_text(doc, "The dominant observed signal was a decline in accumulation and wet-spell duration paired with increases in dry-spell duration and rainfall intensity (Table 4; Figure 2). Standard MK identified 93 of 143 tests as significant; after BH-FDR control, 88 remained significant. PRCPTOT decreased at nine stations after the primary test, with a median Sen slope of −164.88 mm per decade. CWD decreased at 11 stations (median −27.04 days per decade), whereas CDD increased at 10 stations (median +9.23 days per decade). SDII increased at nine stations (median +0.54 mm day−1 per decade), and Rx1day, R95p and R99p increased at seven, eight and nine stations, respectively, in the primary test. Rx5day was spatially less coherent, with only two significant decreases, and R50mm had five increases, one decrease and six non-significant station results.")
    add_table_observed(doc, table_obs)
    add_figure(doc, FIGURES / "Figure1_Phetchaburi.png", "Figure 1.", "Phetchaburi Province, elevation background and locations of the 13 rain gauges. Station IDs, the Thailand inset, north arrow and scale bar provide geographic context.")
    add_figure(doc, FIGURES / "Figure2_observed_trends.png", "Figure 2.", "Observed annual precipitation-index trends for 1981–2014. (a) Sen slopes standardized within each index only for visual comparison; raw slopes are reported in Table 4. (b) Direction of the standard MK result among tests retained after BH-FDR adjustment across all 143 station–index tests; white cells are not significant.")

    add_heading(doc, "3.2 Near-term model changes", level=2)
    add_text(doc, "The model-first results show a mixed near-term response rather than a single provincial shift (Table 5; Figure 3). Under SSP2-4.5, the median PRCPTOT change was −2.5% (IQR −6.5 to +8.0%), while Rx1day, Rx5day, R95p and R99p had medians of +4.8%, +7.6%, +9.6% and +59.0%, respectively. The large R99p range (−13.0 to +194.1%) reflects both model spread and the small denominators of an extreme-tail index. CDD and CWD had medians of −8.3% and −9.0%, but their model ranges crossed zero for CDD and remained broad for CWD.")
    add_text(doc, "Under SSP5-8.5, the median PRCPTOT change was −9.0% (IQR −15.0 to +1.2%). R10mm decreased by −9.6% and CWD by −7.2%, whereas R20mm increased by +2.7% and R99p by +20.1%; the corresponding IQRs crossed zero for most indices. The seven-model sign counts show this uncertainty directly: for PRCPTOT, SSP2-4.5 produced three positive and four negative model medians, while SSP5-8.5 produced two positive and five negative medians. The contrast is therefore stronger for the total-rainfall signal under SSP5-8.5 than for the tail indices. R50mm is a count index with low event frequency; its large relative percentages (for example, an SSP2-4.5 median of +33.3% with a model range of −33.3 to +300.0%) are unstable when baseline counts are small and should not be used as a headline climate signal.")
    add_table_future(doc, table_future)
    add_figure(doc, FIGURES / "Figure3_future_model_changes.png", "Figure 3.", "Model-first station-median relative changes for 2021–2050 relative to 1995–2014. Each open circle is one CMIP6 model after its station median is calculated; the black point is the seven-model median and the thick segment is the interquartile range. The spread, particularly for R50mm, R95p and R99p, is a central result rather than an error bar around a single deterministic projection.")

    add_heading(doc, "3.3 Within-window trend diagnostics", level=2)
    add_text(doc, "The 30-year future-window standard MK diagnostic flagged 56 of 1,001 SSP2-4.5 model–station–index series (45 increasing and 11 decreasing) and 76 of 1,001 SSP5-8.5 series (5 increasing and 71 decreasing). These unadjusted counts do not establish field significance and are not interchangeable with the model-first mean changes. They are retained as a temporal diagnostic: a model can show a negative 2021–2050 slope even when its future mean is above the 1995–2014 baseline, and vice versa. This separation is important for avoiding the common conflation of projected level change with a monotonic trend within a short window.")

    add_heading(doc, "3.4 Spatial depiction of PRCPTOT change", level=2)
    add_text(doc, "The IDW fields provide a spatial depiction of the station-referenced model-median PRCPTOT changes (Figure 4). Under SSP2-4.5, the northern and central parts of the province are close to neutral or weakly positive, whereas the southern and southeastern station cluster shows more negative changes. Under SSP5-8.5, negative changes are more spatially extensive across the province. These patterns represent spatial interpolation of station-referenced projected changes and should not be interpreted as continuous-resolution climate projections between gauges.")
    add_figure(doc, FIGURES / "Figure4_prcptot_idw_fields.png", "Figure 4.", "Spatial distribution of projected changes in annual precipitation total (PRCPTOT) over Phetchaburi Province for 2021–2050 relative to 1995–2014 under SSP2-4.5 and SSP5-8.5. (a) SSP2-4.5; (b) SSP5-8.5. IDW was used to depict station-referenced model-median changes. The same percentage scale is used in both panels. White areas outside the Phetchaburi provincial boundary represent polygon masking; station markers show the 13 gauges without connecting lines. Areas outside the station convex hull represent spatial extrapolation rather than independently validated gridded projections.")

    add_heading(doc, "4. Discussion", level=1)
    add_heading(doc, "4.1 A drying background with stronger short-duration intensity", level=2)
    add_text(doc, "The observed Phetchaburi pattern combines a lower annual wet-day total and shorter wet spells with longer dry spells and stronger wet-day intensity. The observed combination is consistent with a redistribution of rainfall between wet-day frequency and intensity, although the station-based analysis does not identify the underlying atmospheric mechanism. The result should be interpreted as a change in the distribution of rainfall, not as evidence that every heavy-rainfall threshold increases everywhere. The station-level matrix in Figure 2 shows that Rx5day and R50mm are less coherent than Rx1day, R95p and R99p, which is consistent with the stronger sampling variability of multi-day and high-threshold counts.")
    add_text(doc, "The direction of the historical signal is broadly consistent with Thai studies that report non-stationary rainfall variability, spatially heterogeneous trends and changes in extreme-event frequency [17,18,19,20,28]. It is not appropriate, however, to transfer regional averages directly to Phetchaburi. The present study’s gauges, shorter observation period and fixed local percentile thresholds define a different estimand. Likewise, the Cyprus study’s finding that model rankings and index signs vary by period and scenario is a useful methodological comparison, not evidence for a Phetchaburi mechanism [7].")
    add_heading(doc, "4.2 Scenario and model uncertainty", level=2)
    add_text(doc, "The near-term projections do not support a single deterministic narrative. SSP5-8.5 has a more negative PRCPTOT median than SSP2-4.5, but the IQR still crosses zero. The tail indices show the opposite tension: R99p increases in both median summaries, yet model ranges are very wide. Tail changes can be sensitive to the baseline mean, a small number of events and the supplied bias-correction method. Bias correction can improve distributional agreement while also altering temporal dependence and event sequencing; it should therefore be validated for the intended extreme metric rather than treated as neutral preprocessing [8,15,21,22,27].")
    add_text(doc, "The broad model spread is scientifically informative. CMIP6 ensemble members are not independent random draws, and the seven-model median is a robust descriptive centre rather than a calibrated probability. Recent assessments of CMIP6 model selection, statistical downscaling and artificial-intelligence downscaling likewise emphasize that model skill and method choice can change the local signal [21,22,23,24,25,26,30]. The model-first aggregation reduces the influence of station count but does not eliminate structural model uncertainty, internal variability or scenario ambiguity. The ensemble summaries indicate a tendency toward lower wet-day precipitation totals under SSP5-8.5, while several upper-tail indices show positive median changes but substantial inter-model uncertainty.")
    add_heading(doc, "4.3 Statistical and spatial limitations", level=2)
    add_text(doc, "Three limitations bound the interpretation. First, the 1981–2014 record is 34 years, so extreme-tail indices and 30-year future trends have limited effective sample sizes. Standard MK/Sen is reported as the primary reproducible analysis, while Yue–Wang is a sensitivity diagnostic; the two can differ when autocorrelation changes the variance estimate. Second, BH-FDR is applied to the observed family of tests but not to the unadjusted future-window diagnostic, which is explicitly descriptive. Third, IDW is a visualization of station-referenced values. It cannot recover topographic or coastal gradients absent from the network and can extrapolate outside the convex hull. The IDW surface is especially sensitive to station density and boundary geometry, as is common for station-based spatial depictions [22,27]; it should therefore be used to compare broad spatial contrast, not to infer unsupported fine-scale gradients.")

    add_heading(doc, "5. Conclusion", level=1)
    add_text(doc, "Phetchaburi observations show declining wet-day totals and wet spells alongside longer dry spells and stronger conditional and upper-tail intensity at many stations. Seven CMIP6 models project a more negative PRCPTOT median under SSP5-8.5, but model spread remains wide and tail indices are especially uncertain. Standard MK/Sen with BH-FDR provides the primary inference; Yue–Wang is a sensitivity check. The two-panel IDW fields provide a descriptive view of broad station-referenced spatial contrast and should not be interpreted as independently validated continuous-resolution projections.")

    add_heading(doc, "Ethical Approval", level=1)
    add_text(doc, "Not applicable. This study used existing meteorological and climate-model datasets and involved no human participants or animals.")
    add_heading(doc, "Author Contributions", level=1)
    add_text(doc, "S.P.: Conceptualization, Methodology, Software, Validation, Formal analysis, Investigation, Data curation, Visualization, Writing – original draft, Writing – review & editing.")
    add_heading(doc, "Conflicts of Interest", level=1)
    add_text(doc, "The author declares that he has no conflict of interest.")
    add_heading(doc, "Declaration of Generative AI and AI-Assisted Technologies in the Writing Process", level=1)
    add_text(doc, "During the preparation of this work the author used OpenAI Codex to assist with language editing, document formatting, code review and figure preparation. After using this tool, the author reviewed and edited the content as needed and takes full responsibility for the content of the publication.")

    add_heading(doc, "Data Availability", level=1)
    add_text(doc, "The observed gauge series and supplied bias-corrected CMIP6 daily series used in this study were obtained from the sources described in Section 2.1. Derived annual-index, trend and model-change tables are available from the corresponding author upon reasonable request, subject to source-data permissions.")
    add_heading(doc, "Code Availability", level=1)
    add_text(doc, "The reproducible analysis workflow, configuration manifest and quality-control scripts are available from the corresponding author upon reasonable request.")

    add_heading(doc, "References", level=1)
    refs = [
        "1. Intergovernmental Panel on Climate Change. Climate change 2021: the physical science basis. Contribution of Working Group I to the Sixth Assessment Report. Cambridge: Cambridge University Press; 2021.",
        "2. Zhang X, Alexander L, Hegerl GC, Jones P, Tank AK, Peterson TC, et al. Indices for monitoring changes in extremes based on daily temperature and precipitation data. Wiley Interdiscip Rev Clim Change. 2011;2(6):851–870.",
        "3. Eyring V, Bony S, Meehl GA, Senior CA, Stevens B, Stouffer RJ, et al. Overview of the Coupled Model Intercomparison Project Phase 6 (CMIP6) experimental design and organization. Geosci Model Dev. 2016;9:1937–1958.",
        "4. O’Neill BC, Tebaldi C, van Vuuren DP, Eyring V, Friedlingstein P, Hurtt G, et al. The Scenario Model Intercomparison Project (ScenarioMIP) for CMIP6. Geosci Model Dev. 2016;9:3461–3482.",
        "5. Riahi K, van Vuuren DP, Kriegler E, Edmonds J, O’Neill BC, Fujimori S, et al. The Shared Socioeconomic Pathways and their energy, land use, and greenhouse gas emissions implications: an overview. Glob Environ Change. 2017;42:153–168.",
        "6. Try S, Qin X. Evaluation of future changes in climate extremes over Southeast Asia using downscaled CMIP6 GCM projections. Water. 2024;16:2207. doi:10.3390/w16152207.",
        "7. Gödek Hayal NP, Zaifoglu H, Yanmaz AM. Projecting precipitation extremes over Cyprus using CMIP6 climate scenarios. Nat Hazards. 2026;122:368. doi:10.1007/s11069-026-08119-4.",
        "8. Cannon AJ, Sobie SR, Murdock TQ. Bias correction of GCM precipitation by quantile delta mapping: how well do methods preserve changes in quantiles and extremes? J Clim. 2015;28:6938–6959.",
        "9. Mann HB. Nonparametric tests against trend. Econometrica. 1945;13(3):245–259.",
        "10. Sen PK. Estimates of the regression coefficient based on Kendall’s tau. J Am Stat Assoc. 1968;63(324):1379–1389.",
        "11. Benjamini Y, Hochberg Y. Controlling the false discovery rate: a practical and powerful approach to multiple testing. J R Stat Soc Series B. 1995;57(1):289–300.",
        "12. Yue S, Wang CY. The Mann–Kendall test modified by effective sample size to detect trend in serially correlated hydrological series. Water Resour Manag. 2004;18:201–218.",
        "13. Hamed KH, Rao AR. A modified Mann–Kendall trend test for autocorrelated data. J Hydrol. 1998;204(1–4):182–196.",
        "14. Shepard D. A two-dimensional interpolation function for irregularly-spaced data. In: Proceedings of the 23rd ACM National Conference. New York: ACM; 1968. p. 517–524.",
        "15. Maraun D. Bias correcting climate change simulations—a critical review. Curr Clim Change Rep. 2016;2:211–220.",
        "16. Kuinkel D, Promchote P, Upreti KR, Wang S-Y. Projected changes in precipitation extremes in Southern Thailand using CMIP6 models. Theor Appl Climatol. 2024;155(9):8703–8716. doi:10.1007/s00704-024-05150-y.",
        "17. Madolli MJ, Gade SA, Tangdamrongsub N, Debnath S, Gupta V, Datta A, Himanshu SK. Non-stationarity and temporal dependence of seasonal and extreme rainfall in Thailand and their linkages with ENSO and IOD. Theor Appl Climatol. 2026;157(6). doi:10.1007/s00704-026-06315-7.",
        "18. Chaiwino W, Chaisee K, Oonariya C, Wongsaijai B. Analysis of long-term rainfall trend and extreme in upper northern Thailand. Sci Rep. 2025;15:33380. doi:10.1038/s41598-025-18217-1.",
        "19. de Oliveira-Júnior JF, Mendes D, Porto HD, Cardoso KRA, Ferreira Neto JA, da Silva EBC, Pereira MA, Mendes MCD, Baracho BBD, Jamjareegulgarn P. Analysis of drought and extreme precipitation events in Thailand: trends, climate modeling, and implications for climate change adaptation. Sci Rep. 2025;15:4501. doi:10.1038/s41598-025-86826-x.",
        "20. Nontikansak P, Shrestha S, Shanmugam MS, Loc HH, Virdis SGP. Rainfall extremes under climate change in the Pasak River Basin, Thailand. J Water Clim Change. 2022;13(10):3729–3746. doi:10.2166/wcc.2022.232.",
        "21. Humphries UW, Waqas M, Hlaing PT, Dechpichai P, Wangwongchai A. Assessment of CMIP6 GCMs for selecting a suitable climate model for precipitation projections in Southern Thailand. Results Eng. 2024;23:102417. doi:10.1016/j.rineng.2024.102417.",
        "22. Waqas M, Humphries UW. Artificial intelligence-driven precipitation downscaling and projections over Thailand using CMIP6 climate models. Big Earth Data. 2025;9(3):583–614. doi:10.1080/20964471.2025.2547500.",
        "23. Prathom C, Champrasert P. General Circulation Model Downscaling Using Interpolation–Machine Learning Model Combination–Case Study: Thailand. Sustainability. 2023;15(12):9668. doi:10.3390/su15129668.",
        "24. Muthuvel D, Qin X. Spatial concurrence risk of extreme precipitations in Southeast Asia under climate change using temporally dynamic complex networks. J Hydrol. 2026;664(Part B):134526. doi:10.1016/j.jhydrol.2025.134526.",
        "25. Jiang Y, Ge F, Chen Q, Lin Z, Fraedrich K, Chen Z. How compound wind and precipitation extremes change over Southeast Asia: a comprehensive assessment from CMIP6 models. Atmos Sci Lett. 2025;26(2). doi:10.1002/asl.1293.",
        "26. Singh AK, Roshni T, Singh V. Projected intensification of precipitation extremes in the Kosi Basin using CMIP6 models. Sci Rep. 2026;16:12565. doi:10.1038/s41598-026-43723-1.",
        "27. Addisuu AA, Mengistu Tsidu G, Basupi LV. Improving daily CMIP6 precipitation in Southern Africa through bias correction—Part 2: representation of extreme precipitation. Climate. 2025;13(5):93. doi:10.3390/cli13050093.",
        "28. Madolli MJ, Gade SA, Gupta V, Chakraborty A, et al. A systematic review on rainfall patterns of Thailand: insights into variability and its relationship with ENSO and IOD. Earth-Sci Rev. 2025;264:105102. doi:10.1016/j.earscirev.2025.105102.",
        "29. Jeefoo P, Preedapirom Jeefoo W, Rojanavasu P, Mekruksavanich S, Lerk-U-Suke S, Kantawong K, Chaiwongsai J, Rachata N. Future flood risk zones using CMIP6 climate modeling and geoinformatics in Phetchaburi Province, Thailand. In: 2024 8th International Conference on Information Technology (InCIT). 2024. p. 66. doi:10.1109/InCIT63192.2024.10810530.",
        "30. Zhang B, Song S, Wang H, Guo T, Ding Y. Evaluation of the performance of CMIP6 models in simulating extreme precipitation and its projected changes in global climate regions. Nat Hazards. 2024;121(2):1737–1763. doi:10.1007/s11069-024-06850-4.",
    ]
    for ref in refs:
        p = add_text(doc, ref, size=9, spacing=18, after=0)
        p.paragraph_format.left_indent = Inches(0.22)
        p.paragraph_format.first_line_indent = Inches(-0.22)

    # Ensure all normal visible body runs obey the template's font contract.
    for p in doc.paragraphs:
        for r in p.runs:
            if r.font.name is None:
                set_run(r, size=10)
    doc.core_properties.title = "Observed and Near-Term Projected Precipitation Extremes in Phetchaburi Province under SSP2-4.5 and SSP5-8.5"
    doc.core_properties.author = "Surasit Punyawansiri"
    doc.core_properties.subject = "Precipitation extremes, Phetchaburi, CMIP6, Mann–Kendall, IDW"
    doc.save(str(OUT))
    print(OUT)


if __name__ == "__main__":
    main()
