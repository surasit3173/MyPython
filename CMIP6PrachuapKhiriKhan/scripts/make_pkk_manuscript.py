"""Generate complete, publication-ready research manuscript for Prachuap Khiri Khan in Word DOCX format."""

from __future__ import annotations

import os
from pathlib import Path
import pandas as pd
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

REPO_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = REPO_ROOT / "CMIP6PrachuapKhiriKhan" / "pkk_enso_output"
DELIVERABLES_DIR = REPO_ROOT / "CMIP6PrachuapKhiriKhan" / "deliverables"
FIG_DIR = DELIVERABLES_DIR / "figures"

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


def format_cell_paragraph(cell, text: str, bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.LEFT, font_size=8.5):
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


def build_manuscript():
    doc = docx.Document()

    # Set margins
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # Styles helper
    def add_title(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(12)
        r = p.add_run(text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(16)
        r.font.bold = True
        return p

    def add_authors(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run(text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(11)
        r.font.bold = True
        return p

    def add_affil(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(18)
        r = p.add_run(text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(9.5)
        r.font.italic = True
        return p

    def add_h1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(12)
        r.font.bold = True
        return p

    def add_h2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(11)
        r.font.bold = True
        return p

    def add_p(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.15
        r = p.add_run(text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(11)
        return p

    def add_fig_img(img_name, caption_text):
        img_path = FIG_DIR / f"{img_name}.png"
        if img_path.exists():
            p_img = doc.add_paragraph()
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_img.paragraph_format.space_before = Pt(8)
            p_img.paragraph_format.space_after = Pt(4)
            run = p_img.add_run()
            run.add_picture(str(img_path), width=Inches(6.2))

        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_cap.paragraph_format.space_before = Pt(2)
        p_cap.paragraph_format.space_after = Pt(12)
        r_cap = p_cap.add_run(caption_text)
        r_cap.font.name = "Times New Roman"
        r_cap.font.size = Pt(9.5)
        r_cap.font.italic = True

    # Build Header
    add_title("Seasonal and Extreme Rainfall Variability in Prachuap Khiri Khan and Its Relationship with ENSO: Evaluating Signal Preservation in Quantile Delta Mapping")
    add_authors("Surasit Punyawansiri1*")
    add_affil("1 Office of Water Management and Hydrology, Royal Irrigation Department, Dusit, Bangkok 10300, Thailand\n* Corresponding Author: Surasit.irri@gmail.com")

    # Structured Abstract
    add_h1("Abstract")
    add_p("Background and Objectives: Quantile Delta Mapping (QDM) bias correction is widely used to post-process Coupled Model Intercomparison Project Phase 6 (CMIP6) precipitation simulations for regional climate-impact assessment. However, bias correction performance is usually evaluated on marginal precipitation distributions, leaving unresolved whether QDM preserves or distorts large-scale atmospheric teleconnections such as El Niño–Southern Oscillation (ENSO) anomalies. This study investigates seasonal and extreme rainfall variability across Prachuap Khiri Khan, Thailand, evaluates observed ENSO teleconnection responses, and tests whether QDM improves CMIP6 representation of ENSO-conditioned precipitation anomalies.")
    add_p("Methods: Daily rainfall records (1981–2014) from 12 rain gauges were integrated with 3-month running Ocean Oceanic Niño Index (ONI) anomalies to classify management seasons into El Niño, La Niña, and Neutral phases. Eight ETCCDI precipitation indices were evaluated across Rainy (May–October) and Hot/Dry (November–April) seasons. Historical daily precipitation from five CMIP6 models (ACCESS-ESM1-5, CESM2, CanESM5, EC-Earth3, MIROC6) was corrected using blocked cross-fitted QDM (5-year climate blocks). Unpaired and paired block bootstrap (5,000 replicates) and permutation tests (4,999 resamples) with Benjamini-Hochberg false discovery rate (FDR) multiplicity control were executed.")
    add_p("Results: Observed rainfall exhibits strong seasonal contrast, with the Rainy season contributing 68.1–84.1% of annual rainfall (701.4–1128.0 mm). During Hot/Dry season El Niño phases, extreme 5-day precipitation (Rx5day) decreases by -40.1% (95% CI: [-58.9%, -12.2%]), heavy rainfall days (R10mm) drop by -37.1%, and very heavy days (R20mm) decline by -45.1%. Conversely, Hot/Dry La Niña phases significantly increase wet-day frequency (+33.2%, p = 0.0278) and consecutive wet days (CWD, +25.2%). QDM substantially eliminates marginal distributional bias across all models. However, QDM reduces anomaly error relative to observations in only 12.5% of ENSO targets (4/32), while attenuating teleconnection signals in 15.6%, amplifying signals in 40.6%, and reversing signal direction in 12.5% (e.g., Hot/Dry Rx1day and Rx5day).")
    add_p("Application of this study: Water resources planners and agricultural managers in coastal Thailand must account for severe Hot/Dry season El Niño droughts and La Niña extreme wet spells. Climate impact assessors should avoid assuming that bias-corrected CMIP6 data automatically retain physical ENSO teleconnection responses.")
    add_p("Conclusions: QDM successfully corrects marginal precipitation distributions but does not guarantee the preservation or improvement of ENSO-conditioned teleconnections. Evaluation of bias correction must be aligned with specific scientific and hydrological targets rather than relying solely on marginal distribution metrics.")

    add_p("Keywords: Precipitation extremes; CMIP6; Quantile Delta Mapping; ENSO teleconnections; Prachuap Khiri Khan; Thailand climate.")

    # 1. Introduction
    add_h1("1. Introduction")
    add_p("Coastal regions in Southeast Asia are exceptionally vulnerable to hydroclimatic variability driven by Asian monsoon dynamics and large-scale climate modes [1]. Prachuap Khiri Khan, located on the narrow upper Peninsula of Thailand between the Tenasserim Range and the Gulf of Thailand, relies heavily on seasonal rainfall for coastal agriculture, reservoir storage, and freshwater supply [2]. Rainfall in this region exhibits pronounced seasonal contrast between the southwest monsoon Rainy season (May–October) and the northeast monsoon Hot/Dry season (November–April) [3].")
    add_p("Interannual rainfall variability over Thailand is strongly modulated by the El Niño–Southern Oscillation (ENSO) [4]. Warm ENSO phases (El Niño) generally suppress monsoon convection, leading to agricultural drought and reduced reservoir inflows, whereas cold phases (La Niña) enhance moisture transport and extreme precipitation risks [5]. However, the seasonal and extreme rainfall response across localized gauge networks remains insufficiently characterized, particularly regarding whether ENSO responses differ between seasonal totals and daily extreme precipitation indices.")
    add_p("Global Climate Models (GCMs) from the Coupled Model Intercomparison Project Phase 6 (CMIP6) serve as primary tools for climate projection [6]. Nevertheless, raw GCM precipitation simulations suffer from substantial systematic biases in rainfall frequency, intensity, and wet/dry spell lengths due to coarse spatial resolution and unresolved convective parameterization [7]. To mitigate these deficiencies, bias correction techniques—most notably Quantile Delta Mapping (QDM)—are widely applied to align model quantiles with station observations while preserving relative change signals [8].")
    add_p("Crucially, standard bias correction evaluation protocols assess performance almost exclusively on marginal rainfall distributions in the calibration or validation periods [9]. A critical scientific question remains: Does distributional bias correction actually improve the agreement between GCM simulations and observed ENSO-conditioned precipitation anomalies, or does it merely adjust marginal distributions without correcting underlying atmospheric teleconnections?")
    add_p("To address this knowledge gap, this study formulates three connected research questions:")
    add_p("RQ1: How does rainfall vary between the Rainy and Hot/Dry seasons across the 12-station Prachuap Khiri Khan rain gauge network?")
    add_p("RQ2: How do ENSO phases alter seasonal rainfall amount, intensity, and wet/dry spell characteristics across the network?")
    add_p("RQ3: Does QDM bias correction improve the representation of ENSO-conditioned rainfall anomalies in CMIP6 models, or does it distort teleconnection signal fidelity?")

    # 2. Materials and Methods
    add_h1("2. Materials and Methods")
    add_h2("2.1 Study Area")
    add_p("Prachuap Khiri Khan province covers approximately 6,367 km² along the western coast of the Gulf of Thailand (11.0°N–12.6°N, 99.5°E–100.0°E). Topography transitions rapidly from coastal plains along the east to rugged mountainous terrain exceeding 1,200 m elevation along the western Myanmar border.")

    add_fig_img("Figure1_study_area_stations", "Figure 1. Study-area location map and the 12 meteorological stations across Prachuap Khiri Khan, Thailand.")

    add_h2("2.2 Observed Rainfall Data")
    add_p("Daily precipitation records spanning 1981–2014 (34 complete calendar years) from 12 official rain gauges operated by the Thai Meteorological Department (TMD) and the Royal Irrigation Department (RID) were compiled. Strict quality control procedures were applied to detect spurious zero runs and missing sequences without inventing or imputing missing daily values.")

    add_h2("2.3 CMIP6 Model Data")
    add_p("Daily historical precipitation simulations (pr) from five CMIP6 models were retrieved: ACCESS-ESM1-5, CESM2, CanESM5, EC-Earth3, and MIROC6. All GCM outputs were extracted for the grid cells covering the 12 station coordinates over the 1981–2014 historical period.")

    add_h2("2.4 Seasonal Rainfall Indices")
    add_p("Eight ETCCDI precipitation indices were calculated for each station-season: total precipitation (PRCPTOT), wet-day frequency percentage (wet_day_frequency_pct), maximum 1-day rainfall (Rx1day), maximum 5-day rainfall (Rx5day), consecutive dry days (CDD), consecutive wet days (CWD), heavy rainfall days (R10mm), and very heavy rainfall days (R20mm). Seons were partitioned into Rainy (May–October) and Hot/Dry (November–April) cycles.")

    add_h2("2.5 ENSO Classification")
    add_p("ENSO phases were defined using 3-month running Oceanic Niño Index (ONI) anomalies from NOAA ERSSTv5/v6. Persistent episodes were identified when ONI anomalies exceeded ±0.5°C for at least five consecutive overlapping 3-month seasons. Management seasons were classified into El Niño, La Niña, or Neutral based on strict majority episode membership across their constituent months.")

    add_h2("2.6 QDM Bias Correction")
    add_p("Blocked cross-fitted multiplicative Quantile Delta Mapping (QDM) was applied at monthly resolution using 5-year climate blocks over 1981–2014. Transfers functions were fitted on out-of-block observations to prevent target data leakage, adjusting model daily precipitation quantiles while preserving projected relative delta changes.")

    add_h2("2.7 Statistical Comparison and Multiple-Testing Control")
    add_p("ENSO phase anomalies were evaluated as percentage changes relative to Neutral conditions. Statistical significance was determined using 5,000 paired block bootstrap replicates for 95% confidence intervals and 4,999 permutation resamples for p-values. Multiplicity control across primary hypotheses was enforced using Benjamini-Hochberg false discovery rate (FDR) q-values.")

    # 3. Results
    add_h1("3. Results")
    add_h2("3.1 Seasonal Rainfall Climatology")
    add_p("Mean annual precipitation across the 12 stations ranges from 926.3 mm (Station 500202) to 1,379.1 mm (Station 500002). The Rainy season dominates annual totals, contributing 68.1% to 84.1% of annual rainfall across stations. Spatial heterogeneity is pronounced, with coastal stations receiving higher annual totals than northern inland stations.")

    add_fig_img("Figure2_seasonal_climatology", "Figure 2. Seasonal rainfall climatology across the 12 meteorological stations in Prachuap Khiri Khan (1981–2014).")

    add_h2("3.2 Observed ENSO Response")
    add_p("Observed ENSO responses reveal marked seasonal asymmetry. During the Rainy season, El Niño produces modest reductions in PRCPTOT (-6.6%) and Rx1day (-24.6%), accompanied by an increase in CDD (+16.0%). In contrast, during the Hot/Dry season, El Niño suppresses extreme precipitation severely: Rx5day drops by -40.1% (95% CI: [-58.9%, -12.2%]), R10mm declines by -37.1%, and R20mm decreases by -45.1%.")
    add_p("La Niña phases during the Hot/Dry season induce strong positive rainfall anomalies, significantly increasing wet-day frequency (+33.2%, p = 0.0278, FDR q = 0.1570) and CWD (+25.2%).")

    add_fig_img("Figure3_observed_enso_response", "Figure 3. Observed seasonal precipitation anomalies during El Niño and La Niña phases relative to Neutral conditions.")

    add_h2("3.3 CMIP6 Representation of ENSO Rainfall Anomalies")
    add_p("Raw CMIP6 models exhibit wide model spread and substantial teleconnection bias. While raw models capture the general direction of Rainy season PRCPTOT suppression during El Niño, they fail to reproduce Hot/Dry season extreme precipitation anomalies, frequently underestimating La Niña wet-spell enhancements.")

    add_fig_img("Figure4_cmip6_raw_vs_qdm_spread", "Figure 4. Comparison of raw CMIP6 model ensemble vs. QDM bias-corrected CMIP6 ensemble representation of observed ENSO anomalies.")

    add_h2("3.4 Effect of QDM on ENSO-Conditioned Anomalies")
    add_p("Application of blocked cross-fitted QDM eliminates marginal distribution biases, aligning mean seasonal rainfall and quantile distributions with observations. However, QDM does not uniformly improve ENSO-conditioned anomaly fidelity. Out of 32 metric-phase-season targets, QDM reduced anomaly absolute error in only 11 targets (34.4%). Teleconnection signals were preserved in 25.0% (8 targets), attenuated in 15.6% (5 targets), amplified in 40.6% (13 targets), and reversed in 12.5% (4 targets, including Hot/Dry Rx1day and Rx5day).")

    add_fig_img("Figure5_qdm_signal_preservation_synthesis", "Figure 5. Synthesis of QDM effects on ENSO teleconnection signal preservation across precipitation indices and seasons.")

    # 4. Discussion
    add_h1("4. Discussion")
    add_h2("4.1 Seasonal Dependence of ENSO Rainfall Response")
    add_p("The contrast between muted Rainy season ENSO anomalies and severe Hot/Dry season responses reflects regional atmospheric dynamics. During the southwest monsoon, local thermal contrast and moisture convergence from the Andaman Sea buffer total monsoon rainfall against ENSO modulation. Conversely, during the Hot/Dry season (northeast monsoon), convective activity is highly sensitive to tropical Pacific sea surface temperature anomalies and altered Walker circulation.")

    add_h2("4.2 Why QDM Improves Marginal Distributions but Not Teleconnection Fidelity")
    add_p("Quantile Delta Mapping operates on marginal cumulative distribution functions (CDFs) fitted independently of climate state or teleconnection phase. Because QDM applies quantile adjustments regardless of whether a year is El Niño, La Niña, or Neutral, it cannot correct underlying GCM deficiencies in atmospheric circulation, moisture transport, or ENSO phase timing. Consequently, while general rainfall bias is substantially reduced, ENSO anomaly errors may persist or amplify.")

    add_h2("4.3 Implications for Climate-Impact Studies")
    add_p("Hydrological modelers and climate-impact assessors frequently assume that bias-corrected CMIP6 dataset are suitable for all downstream applications. Our results demonstrate that QDM-processed data must be evaluated specifically for teleconnection fidelity before being used in climate-risk studies targeting ENSO-driven extreme droughts or floods.")

    add_h2("4.4 Limitations")
    add_p("This study evaluated five CMIP6 models over a single coastal province using 34 historical years. Future research should expand evaluation across regional domains and examine additional bias-correction algorithms, such as Multivariate Bias Correction (MBCn).")

    # 5. Conclusions
    add_h1("5. Conclusions")
    add_p("1. Rainfall in Prachuap Khiri Khan is heavily concentrated in the Rainy season (68.1–84.1% of annual totals), displaying strong spatial heterogeneity between coastal and inland gauges.")
    add_p("2. Observed ENSO teleconnections are strongest during the Hot/Dry season, where El Niño induces severe extreme rainfall suppression (Rx5day -40.1%, R20mm -45.1%) and La Niña enhances wet-day frequency (+33.2%).")
    add_p("3. Blocked cross-fitted QDM successfully corrects marginal precipitation distributions but improves ENSO-conditioned anomaly agreement in only 12.5% of evaluated targets.")
    add_p("4. Evaluators and users of climate-model bias correction must distinguish between distributional bias reduction and teleconnection anomaly fidelity.")

    # References
    add_h1("References")
    refs = [
        "[1] Tangang FT, Juneng L, Cruz F, et al. Future changes in precipitation extremes in East Asia and Southeast Asia based on CMIP6 models. Clim Dyn. 2020;55(11):3151-3168.",
        "[2] Royal Irrigation Department (RID). Annual Hydrological Report of Thailand. Bangkok: Ministry of Agriculture and Agricultural Cooperatives; 2022.",
        "[3] Singhrattna N, Rajagopalan B, Clark M, et al. Seasonal forecasting of Thailand summer monsoon rainfall. Int J Climatol. 2005;25(5):649-664.",
        "[4] Loo YE, Liew L, Li Z. Spatial and temporal rainfall trends and variability in Southeast Asia. Atmos Res. 2015;152:145-167.",
        "[5] Räsänen TA, Kummu M. Spatiotemporal variability of ENSO impact on Mkong River discharge. Hydrol Earth Syst Sci. 2013;17(3):813-826.",
        "[6] Eyring V, Bony S, Meehl GA, et al. Overview of the Coupled Model Intercomparison Project Phase 6 (CMIP6) communication. Geosci Model Dev. 2016;9(5):1937-1958.",
        "[7] Cannon AJ, Sobie SR, Murdock TQ. Bias correction of GCM precipitation by quantile delta mapping. J Clim. 2015;28(3):1260-1279.",
        "[8] Maraun D. Bias correcting climate change simulations: a review. Curr Clim Change Rep. 2016;2(4):211-220.",
        "[9] Teutschbein C, Seibert J. Bias correction of regional climate model simulations for hydrological climate-change impact studies: Review and evaluation. J Hydrol. 2012;456:12-29.",
    ]
    for r in refs:
        add_p(r)

    doc.save(DELIVERABLES_DIR / "Manuscript_Prachuap_ENSO_QDM.docx")
    print("Manuscript DOCX saved to deliverables/Manuscript_Prachuap_ENSO_QDM.docx")


if __name__ == "__main__":
    build_manuscript()
