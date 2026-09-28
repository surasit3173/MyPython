"""Generate publication-ready manuscript PDF for Prachuap Khiri Khan using ReportLab."""

from __future__ import annotations

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

REPO_ROOT = Path(__file__).resolve().parents[2]
DELIVERABLES_DIR = REPO_ROOT / "CMIP6PrachuapKhiriKhan" / "deliverables"
FIG_DIR = DELIVERABLES_DIR / "figures"


def build_pdf():
    pdf_path = DELIVERABLES_DIR / "Manuscript_Prachuap_ENSO_QDM.pdf"
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        alignment=1, # Center
        spaceAfter=12,
    )

    author_style = ParagraphStyle(
        'AuthorStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        alignment=1,
        spaceAfter=4,
    )

    affil_style = ParagraphStyle(
        'AffilStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=12,
        alignment=1,
        spaceAfter=14,
    )

    h1_style = ParagraphStyle(
        'H1Style',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        'H2Style',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=10,
        leading=14,
        alignment=4, # Justified
        spaceBefore=0,
        spaceAfter=6,
    )

    caption_style = ParagraphStyle(
        'CapStyle',
        parent=styles['Normal'],
        fontName='Times-Italic',
        fontSize=8.5,
        leading=11,
        alignment=4,
        spaceBefore=4,
        spaceAfter=10,
    )

    story = []

    # Title
    story.append(Paragraph("Seasonal and Extreme Rainfall Variability in Prachuap Khiri Khan and Its Relationship with ENSO: Evaluating Signal Preservation in Quantile Delta Mapping", title_style))
    story.append(Paragraph("Surasit Punyawansiri1*", author_style))
    story.append(Paragraph("1 Office of Water Management and Hydrology, Royal Irrigation Department, Dusit, Bangkok 10300, Thailand<br/>* Corresponding Author: Surasit.irri@gmail.com", affil_style))

    # Abstract
    story.append(Paragraph("Abstract", h1_style))
    story.append(Paragraph("<b>Background and Objectives:</b> Quantile Delta Mapping (QDM) bias correction is widely used to post-process CMIP6 precipitation simulations for regional climate-impact assessment. However, bias correction performance is usually evaluated on marginal precipitation distributions, leaving unresolved whether QDM preserves or distorts large-scale atmospheric teleconnections such as El Niño–Southern Oscillation (ENSO) anomalies. This study investigates seasonal and extreme rainfall variability across Prachuap Khiri Khan, Thailand, evaluates observed ENSO teleconnection responses, and tests whether QDM improves CMIP6 representation of ENSO-conditioned precipitation anomalies.", body_style))
    story.append(Paragraph("<b>Methods:</b> Daily rainfall records (1981–2014) from 12 rain gauges were integrated with 3-month running Oceanic Niño Index (ONI) anomalies to classify management seasons into El Niño, La Niña, and Neutral phases. Eight ETCCDI precipitation indices were evaluated across Rainy (May–October) and Hot/Dry (November–April) seasons. Historical daily precipitation from five CMIP6 models (ACCESS-ESM1-5, CESM2, CanESM5, EC-Earth3, MIROC6) was corrected using blocked cross-fitted QDM (5-year climate blocks). Unpaired and paired block bootstrap (5,000 replicates) and permutation tests (4,999 resamples) with Benjamini-Hochberg false discovery rate (FDR) multiplicity control were executed.", body_style))
    story.append(Paragraph("<b>Results:</b> Observed rainfall exhibits strong seasonal contrast, with the Rainy season contributing 68.1–84.1% of annual rainfall (701.4–1128.0 mm). During Hot/Dry season El Niño phases, extreme 5-day precipitation (Rx5day) decreases by -40.1% (95% CI: [-58.9%, -12.2%]), heavy rainfall days (R10mm) drop by -37.1%, and very heavy days (R20mm) decline by -45.1%. Conversely, Hot/Dry La Niña phases significantly increase wet-day frequency (+33.2%, p = 0.0278) and consecutive wet days (CWD, +25.2%). QDM substantially eliminates marginal distributional bias across all models. However, QDM reduces anomaly error relative to observations in only 12.5% of ENSO targets (4/32), while attenuating teleconnection signals in 15.6%, amplifying signals in 40.6%, and reversing signal direction in 12.5% (e.g., Hot/Dry Rx1day and Rx5day).", body_style))
    story.append(Paragraph("<b>Application of this study:</b> Water resources planners and agricultural managers in coastal Thailand must account for severe Hot/Dry season El Niño droughts and La Niña extreme wet spells. Climate impact assessors should avoid assuming that bias-corrected CMIP6 data automatically retain physical ENSO teleconnection responses.", body_style))
    story.append(Paragraph("<b>Conclusions:</b> QDM successfully corrects marginal precipitation distributions but does not guarantee the preservation or improvement of ENSO-conditioned teleconnections. Evaluation of bias correction must be aligned with specific scientific and hydrological targets rather than relying solely on marginal distribution metrics.", body_style))
    story.append(Paragraph("<b>Keywords:</b> Precipitation extremes; CMIP6; Quantile Delta Mapping; ENSO teleconnections; Prachuap Khiri Khan; Thailand climate.", body_style))

    # Introduction
    story.append(Paragraph("1. Introduction", h1_style))
    story.append(Paragraph("Coastal regions in Southeast Asia are exceptionally vulnerable to hydroclimatic variability driven by Asian monsoon dynamics and large-scale climate modes [1]. Prachuap Khiri Khan, located on the narrow upper Peninsula of Thailand between the Tenasserim Range and the Gulf of Thailand, relies heavily on seasonal rainfall for coastal agriculture, reservoir storage, and freshwater supply [2]. Rainfall in this region exhibits pronounced seasonal contrast between the southwest monsoon Rainy season (May–October) and the northeast monsoon Hot/Dry season (November–April) [3].", body_style))
    story.append(Paragraph("Interannual rainfall variability over Thailand is strongly modulated by the El Niño–Southern Oscillation (ENSO) [4]. Warm ENSO phases (El Niño) generally suppress monsoon convection, leading to agricultural drought and reduced reservoir inflows, whereas cold phases (La Niña) enhance moisture transport and extreme precipitation risks [5]. However, the seasonal and extreme rainfall response across localized gauge networks remains insufficiently characterized, particularly regarding whether ENSO responses differ between seasonal totals and daily extreme precipitation indices.", body_style))
    story.append(Paragraph("Global Climate Models (GCMs) from the Coupled Model Intercomparison Project Phase 6 (CMIP6) serve as primary tools for climate projection [6]. Nevertheless, raw GCM precipitation simulations suffer from substantial systematic biases in rainfall frequency, intensity, and wet/dry spell lengths due to coarse spatial resolution and unresolved convective parameterization [7]. To mitigate these deficiencies, bias correction techniques—most notably Quantile Delta Mapping (QDM)—are widely applied to align model quantiles with station observations while preserving relative change signals [8].", body_style))
    story.append(Paragraph("Crucially, standard bias correction evaluation protocols assess performance almost exclusively on marginal rainfall distributions in the calibration or validation periods [9]. A critical scientific question remains: Does distributional bias correction actually improve the agreement between GCM simulations and observed ENSO-conditioned precipitation anomalies, or does it merely adjust marginal distributions without correcting underlying atmospheric teleconnections?", body_style))

    # Materials and Methods
    story.append(Paragraph("2. Materials and Methods", h1_style))
    story.append(Paragraph("2.1 Study Area", h2_style))
    story.append(Paragraph("Prachuap Khiri Khan province covers approximately 6,367 km² along the western coast of the Gulf of Thailand (11.0°N–12.6°N, 99.5°E–100.0°E). Topography transitions rapidly from coastal plains along the east to rugged mountainous terrain exceeding 1,200 m elevation along the western Myanmar border.", body_style))

    fig1_img = FIG_DIR / "Figure1_study_area_stations.png"
    if fig1_img.exists():
        story.append(Spacer(1, 6))
        story.append(Image(str(fig1_img), width=5.5*inch, height=7.5*inch))
        story.append(Paragraph("Figure 1. Study-area location map and the 12 meteorological stations across Prachuap Khiri Khan, Thailand.", caption_style))

    story.append(Paragraph("2.2 Observed Rainfall Data", h2_style))
    story.append(Paragraph("Daily precipitation records spanning 1981–2014 (34 complete calendar years) from 12 official rain gauges operated by the Thai Meteorological Department (TMD) and the Royal Irrigation Department (RID) were compiled. Quality control procedures verified completeness without inventing daily values.", body_style))

    story.append(Paragraph("2.3 CMIP6 Model Data & QDM Bias Correction", h2_style))
    story.append(Paragraph("Daily precipitation simulations from five CMIP6 models (ACCESS-ESM1-5, CESM2, CanESM5, EC-Earth3, MIROC6) were extracted over 1981–2014. Blocked cross-fitted multiplicative Quantile Delta Mapping (QDM) was executed using 5-year climate blocks at monthly resolution.", body_style))

    # Results
    story.append(Paragraph("3. Results", h1_style))
    story.append(Paragraph("3.1 Seasonal Rainfall Climatology", h2_style))
    story.append(Paragraph("Mean annual precipitation across the 12 stations ranges from 926.3 mm to 1,379.1 mm. The Rainy season contributes 68.1% to 84.1% of annual rainfall totals.", body_style))

    fig2_img = FIG_DIR / "Figure2_seasonal_climatology.png"
    if fig2_img.exists():
        story.append(Spacer(1, 6))
        story.append(Image(str(fig2_img), width=6.2*inch, height=3.3*inch))
        story.append(Paragraph("Figure 2. Seasonal rainfall climatology across the 12 meteorological stations in Prachuap Khiri Khan (1981–2014).", caption_style))

    story.append(Paragraph("3.2 Observed ENSO Response", h2_style))
    story.append(Paragraph("During Hot/Dry season El Niño phases, extreme 5-day precipitation (Rx5day) drops by -40.1% (95% CI: [-58.9%, -12.2%]), heavy rainfall days (R10mm) drop by -37.1%, and very heavy days (R20mm) decline by -45.1%. Conversely, Hot/Dry La Niña phases significantly increase wet-day frequency (+33.2%, p = 0.0278) and CWD (+25.2%).", body_style))

    fig3_img = FIG_DIR / "Figure3_observed_enso_response.png"
    if fig3_img.exists():
        story.append(Spacer(1, 6))
        story.append(Image(str(fig3_img), width=6.2*inch, height=4.9*inch))
        story.append(Paragraph("Figure 3. Observed seasonal precipitation anomalies during El Niño and La Niña phases relative to Neutral conditions.", caption_style))

    story.append(Paragraph("3.3 CMIP6 Representation of ENSO & QDM Effect", h2_style))
    story.append(Paragraph("QDM substantially eliminates marginal distributional bias across all models. However, QDM reduces anomaly error relative to observations in only 12.5% of ENSO targets (4/32), while attenuating teleconnection signals in 15.6%, amplifying signals in 40.6%, and reversing signal direction in 12.5% (e.g., Hot/Dry Rx1day and Rx5day).", body_style))

    fig4_img = FIG_DIR / "Figure4_cmip6_raw_vs_qdm_spread.png"
    if fig4_img.exists():
        story.append(Spacer(1, 6))
        story.append(Image(str(fig4_img), width=6.2*inch, height=5.0*inch))
        story.append(Paragraph("Figure 4. Comparison of raw CMIP6 model ensemble vs. QDM bias-corrected CMIP6 ensemble representation of observed ENSO anomalies.", caption_style))

    fig5_img = FIG_DIR / "Figure5_qdm_signal_preservation_synthesis.png"
    if fig5_img.exists():
        story.append(Spacer(1, 6))
        story.append(Image(str(fig5_img), width=6.2*inch, height=2.8*inch))
        story.append(Paragraph("Figure 5. Synthesis of QDM effects on ENSO teleconnection signal preservation across precipitation indices and seasons.", caption_style))

    # Discussion & Conclusions
    story.append(Paragraph("4. Discussion", h1_style))
    story.append(Paragraph("Quantile Delta Mapping operates on marginal cumulative distribution functions fitted independently of climate state or teleconnection phase. Because QDM applies quantile adjustments regardless of whether a year is El Niño, La Niña, or Neutral, it cannot correct underlying GCM deficiencies in atmospheric circulation or moisture transport. Consequently, while general rainfall bias is substantially reduced, ENSO anomaly errors may persist or amplify.", body_style))

    story.append(Paragraph("5. Conclusions", h1_style))
    story.append(Paragraph("1. Rainfall in Prachuap Khiri Khan is heavily concentrated in the Rainy season (68.1–84.1% of annual totals).<br/>2. Observed ENSO teleconnections are strongest during the Hot/Dry season, where El Niño induces severe extreme rainfall suppression (Rx5day -40.1%, R20mm -45.1%) and La Niña enhances wet-day frequency (+33.2%).<br/>3. Blocked cross-fitted QDM successfully corrects marginal precipitation distributions but improves ENSO-conditioned anomaly agreement in only 12.5% of evaluated targets.<br/>4. Evaluators and users of climate-model bias correction must distinguish between distributional bias reduction and teleconnection anomaly fidelity.", body_style))

    story.append(Paragraph("References", h1_style))
    refs = [
        "[1] Tangang FT, Juneng L, Cruz F, et al. Future changes in precipitation extremes in East Asia and Southeast Asia based on CMIP6 models. Clim Dyn. 2020;55(11):3151-3168.",
        "[2] Royal Irrigation Department (RID). Annual Hydrological Report of Thailand. Bangkok: Ministry of Agriculture and Agricultural Cooperatives; 2022.",
        "[3] Singhrattna N, Rajagopalan B, Clark M, et al. Seasonal forecasting of Thailand summer monsoon rainfall. Int J Climatol. 2005;25(5):649-664.",
        "[4] Loo YE, Liew L, Li Z. Spatial and temporal rainfall trends and variability in Southeast Asia. Atmos Res. 2015;152:145-167.",
        "[5] Räsänen TA, Kummu M. Spatiotemporal variability of ENSO impact on Mekong River discharge. Hydrol Earth Syst Sci. 2013;17(3):813-826.",
        "[6] Eyring V, Bony S, Meehl GA, et al. Overview of the Coupled Model Intercomparison Project Phase 6 (CMIP6) communication. Geosci Model Dev. 2016;9(5):1937-1958.",
        "[7] Cannon AJ, Sobie SR, Murdock TQ. Bias correction of GCM precipitation by quantile delta mapping. J Clim. 2015;28(3):1260-1279.",
        "[8] Maraun D. Bias correcting climate change simulations: a review. Curr Clim Change Rep. 2016;2(4):211-220.",
        "[9] Teutschbein C, Seibert J. Bias correction of regional climate model simulations for hydrological climate-change impact studies: Review and evaluation. J Hydrol. 2012;456:12-29.",
    ]
    for r in refs:
        story.append(Paragraph(r, body_style))

    doc.build(story)
    print("Manuscript PDF generated successfully at deliverables/Manuscript_Prachuap_ENSO_QDM.pdf")


if __name__ == "__main__":
    build_pdf()
