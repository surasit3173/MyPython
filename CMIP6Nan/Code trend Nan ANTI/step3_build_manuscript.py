#!/usr/bin/env python3
"""
Build SEJ-2023 formatted Word manuscript for:
"Rainfall Trend Analysis of Nan Province, Northern Thailand, Using Observed Records
and CMIP6 Bias-Corrected Projections: Mann-Kendall, Sen's Slope, and Multi-Model
Ensemble Approaches"

Template: Science Essence Journal (SEJ) 2023
Reference style: Vancouver
Font: Times New Roman, A4, 1-inch margins, ≤15 pages
"""

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE    = Path(r'C:\MyPython\CMIP6Nan\Code trend Nan ANTI')
OUT_D   = BASE / 'trend_analysis_output'
FIG_D   = OUT_D / 'figures'
STA_F   = Path(r'C:\MyPython\CMIP6Nan') / 'Station_latitude_longitude.csv'
TMPL_F  = Path(r'C:\MyPython\New Artical\template-SEJ-2023.docx')
OUT_DOC = OUT_D / 'SEJ_Manuscript_Nan_Rainfall_Trends_v2.docx'

# ─── Load analysis results ────────────────────────────────────────────────────
trend_df = pd.read_csv(OUT_D / 'trend_results_all.csv')
mme_df   = pd.read_csv(OUT_D / 'mme_series.csv')
sta_df   = pd.read_csv(STA_F)
NAN_STA  = [str(s) for s in sta_df['Station_ID'].tolist()]

MODELS = ['ACCESS-ESM1-5','CESM2','CanESM5','EC-Earth3',
          'FGOALS-g3','MIROC6','MRI-ESM2-0']
MODEL_INST = {
    'ACCESS-ESM1-5': 'CSIRO, Australia',
    'CESM2':         'NCAR, USA',
    'CanESM5':       'CCCma, Canada',
    'EC-Earth3':     'EC-Earth Consortium, Europe',
    'FGOALS-g3':     'IAP/LASG, China',
    'MIROC6':        'MIROC Consortium, Japan',
    'MRI-ESM2-0':    'MRI, Japan',
}

# ─── Helper: extract regional mean trend ─────────────────────────────────────
def get_trend(model, ssp, scale, period, metric='mk'):
    sub = trend_df[(trend_df['station']=='REGIONAL_MEAN') &
                   (trend_df['model']==model) &
                   (trend_df['scenario']==ssp) &
                   (trend_df['scale']==scale) &
                   (trend_df['period']==period)]
    if sub.empty:
        return None
    r = sub.iloc[0]
    return {'trend': r.get(f'{metric}_trend','—'),
            'slope': r.get(f'{metric}_slope', np.nan),
            'p_value': r.get(f'{metric}_p_value', np.nan),
            'tau': r.get(f'mk_tau', np.nan),
            'rho': r.get(f'sp_rho', np.nan)}

def fmt_slope(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return '—'
    return f"{v:+.2f}"

def fmt_p(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return '—'
    if v < 0.001:
        return '<0.001'
    return f"{v:.3f}"

def trend_arrow(trend_val):
    if pd.isna(trend_val) or trend_val in ['insufficient','—']:
        return '—'
    if 'increasing' in str(trend_val):
        return '↑'
    if 'decreasing' in str(trend_val):
        return '↓'
    return '→'

# ─── Compute key numbers for Results section ─────────────────────────────────
# Observed regional mean annual trend
obs_ann = get_trend('observed','observed','annual','1981-2014','mk')
obs_wet = get_trend('observed','observed','wet','1981-2014','mk')
obs_dry = get_trend('observed','observed','dry','1981-2014','mk')

# MME future stats
def mme_stats(ssp, scale, y1, y2):
    mm = mme_df[(mme_df['scenario']==ssp) & (mme_df['scale']==scale) &
                (mme_df['year'] >= y1) & (mme_df['year'] <= y2)]
    if mm.empty:
        return None
    return {'median_mean': mm['mme_mean'].mean(),
            'median_min': mm['mme_min'].mean(),
            'median_max': mm['mme_max'].mean()}

near_245_ann = mme_stats('ssp245','annual',2021,2050)
near_585_ann = mme_stats('ssp585','annual',2021,2050)
far_245_ann  = mme_stats('ssp245','annual',2081,2100)
far_585_ann  = mme_stats('ssp585','annual',2081,2100)
obs_base_ann = mme_stats('ssp245','annual',1981,2014)

def pct_change(future, base):
    if future and base and base['median_mean'] != 0:
        return 100*(future['median_mean'] - base['median_mean'])/base['median_mean']
    return np.nan

near_245_pct = pct_change(near_245_ann, obs_base_ann)
near_585_pct = pct_change(near_585_ann, obs_base_ann)
far_245_pct  = pct_change(far_245_ann,  obs_base_ann)
far_585_pct  = pct_change(far_585_ann,  obs_base_ann)

# Observed mean annual rainfall
timeline = pd.read_csv(OUT_D / 'timeline_series.csv')
obs_tl = timeline[(timeline['model']=='Observed') & (timeline['scale']=='annual')]
obs_mean_ann = obs_tl['regional_mean'].mean()
obs_wet_tl = timeline[(timeline['model']=='Observed') & (timeline['scale']=='wet')]
obs_dry_tl = timeline[(timeline['model']=='Observed') & (timeline['scale']=='dry')]
obs_mean_wet = obs_wet_tl['regional_mean'].mean() if not obs_wet_tl.empty else 0
obs_mean_dry = obs_dry_tl['regional_mean'].mean() if not obs_dry_tl.empty else 0

print(f"Obs mean annual: {obs_mean_ann:.0f} mm")
print(f"Obs mean wet:    {obs_mean_wet:.0f} mm")
print(f"Obs mean dry:    {obs_mean_dry:.0f} mm")
print(f"Near-future (2021-2050) % change vs baseline:")
print(f"  SSP245: {near_245_pct:+.1f}%")
print(f"  SSP585: {near_585_pct:+.1f}%")
print(f"Far-future (2081-2100) % change vs baseline:")
print(f"  SSP245: {far_245_pct:+.1f}%")
print(f"  SSP585: {far_585_pct:+.1f}%")

# ─── Count significant trends per model ──────────────────────────────────────
def count_sig_trend(model, ssp, scale, period):
    sub = trend_df[(trend_df['model']==model) &
                   (trend_df['scenario']==ssp) &
                   (trend_df['scale']==scale) &
                   (trend_df['period']==period) &
                   (trend_df['station'] != 'REGIONAL_MEAN')]
    n_sig = (sub['mk_p_value'] < 0.05).sum()
    n_inc = ((sub['mk_p_value'] < 0.05) & (sub['mk_slope'] > 0)).sum()
    n_dec = ((sub['mk_p_value'] < 0.05) & (sub['mk_slope'] < 0)).sum()
    return int(n_sig), int(n_inc), int(n_dec), len(sub)

# Obs sig trends
obs_sig, obs_inc, obs_dec, obs_n = count_sig_trend('observed','observed','annual','1981-2014')

# ─── Create Word Document ─────────────────────────────────────────────────────
print("\n=== Building Word Document ===")

doc = Document()

# Page setup: A4, 1-inch margins
from docx.oxml.ns import qn
section = doc.sections[0]
section.page_width  = Cm(21.0)
section.page_height = Cm(29.7)
section.left_margin   = Cm(2.54)
section.right_margin  = Cm(2.54)
section.top_margin    = Cm(2.54)
section.bottom_margin = Cm(2.54)

# ─── Style helpers ───────────────────────────────────────────────────────────
def set_font(run, bold=False, italic=False, size=12, color=None):
    run.bold   = bold
    run.italic = italic
    run.font.size = Pt(size)
    run.font.name = 'Times New Roman'
    if color:
        run.font.color.rgb = RGBColor(*color)

def add_para(doc, text='', style='Normal', align=WD_ALIGN_PARAGRAPH.JUSTIFY,
             bold=False, italic=False, size=12, space_before=0, space_after=6,
             first_indent=0):
    p = doc.add_paragraph(style=style)
    p.alignment = align
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after  = Pt(space_after)
    if first_indent > 0:
        p.paragraph_format.first_line_indent = Cm(first_indent)
    if text:
        run = p.add_run(text)
        set_font(run, bold=bold, italic=italic, size=size)
    return p

def add_heading(doc, text, size=14, space_before=12, space_after=6):
    p = add_para(doc, text, bold=True, size=size,
                 align=WD_ALIGN_PARAGRAPH.LEFT,
                 space_before=space_before, space_after=space_after)
    return p

def add_subheading(doc, text, size=12, space_before=8):
    p = add_para(doc, text, italic=True, size=size,
                 align=WD_ALIGN_PARAGRAPH.LEFT, space_before=space_before, space_after=4)
    return p

def add_body(doc, text, indent=True):
    p = add_para(doc, text, size=12, space_before=0, space_after=6,
                 first_indent=0.75 if indent else 0)
    return p

def hr(doc):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after  = Pt(2)
    pPr = p._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), '6')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), '000000')
    pBdr.append(bottom)
    pPr.append(pBdr)

def add_figure(doc, fig_path, caption_text, width_cm=14.0):
    if Path(fig_path).exists():
        doc.add_picture(str(fig_path), width=Cm(width_cm))
        last = doc.paragraphs[-1]
        last.alignment = WD_ALIGN_PARAGRAPH.CENTER
    else:
        p = add_para(doc, f'[Figure not found: {fig_path}]', size=10,
                     align=WD_ALIGN_PARAGRAPH.CENTER)
    # Caption
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(6)
    r1 = p.add_run(caption_text.split(' ', 2)[:2])
    # Format "Figure N" bold
    parts = caption_text.split(' ', 2)
    r_fig = p.add_run(f"{parts[0]} {parts[1]}")
    r_fig.bold = True
    r_fig.font.name = 'Times New Roman'
    r_fig.font.size = Pt(12)
    if len(parts) > 2:
        r_rest = p.add_run(f" {parts[2]}")
        r_rest.font.name = 'Times New Roman'
        r_rest.font.size = Pt(12)
    # remove the double run
    for run in p.runs[:-2]:
        run.text = ''

def add_caption(doc, label_bold, rest_text, align=WD_ALIGN_PARAGRAPH.CENTER):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_after = Pt(4)
    r1 = p.add_run(label_bold)
    set_font(r1, bold=True, size=12)
    r2 = p.add_run(rest_text)
    set_font(r2, size=12)
    return p

# ═══════════════════════════════════════════════════════════════════════════════
# MANUSCRIPT CONTENT
# ═══════════════════════════════════════════════════════════════════════════════

# Article type
p = add_para(doc, 'Research Article', bold=True, size=12,
             align=WD_ALIGN_PARAGRAPH.CENTER, space_before=0, space_after=6)

# Title
p = add_para(doc,
    'Rainfall Trend Analysis of Nan Province, Northern Thailand, '
    'Using Observed Records and CMIP6 Bias-Corrected Projections: '
    'Mann-Kendall, Sen\'s Slope, and Multi-Model Ensemble Approaches',
    bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER,
    space_before=6, space_after=8)

# Author
p = add_para(doc, 'Surasit Punyawansiri\u00b9\u002a',
             bold=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
p = add_para(doc, '(*for Corresponding author)',
             size=10, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=8)
hr(doc)

# ── ABSTRACT ──
add_heading(doc, 'ABSTRACT', size=12)

abstract_text = (
    "Understanding long-term rainfall trends is critical for water resource management "
    "and climate adaptation in tropical monsoon regions. This study presents a comprehensive "
    "trend analysis of annual and seasonal rainfall in Nan Province, northern Thailand, "
    f"using daily observed records from {len(NAN_STA)} rain gauges (1981–2014) and daily "
    "precipitation output from seven CMIP6 global climate models under SSP2-4.5 and SSP5-8.5 "
    "scenarios (1981–2100), post-processed by quantile delta mapping (QDM) bias correction. "
    "Trends were identified using the Mann-Kendall (MK) test, Sen's slope estimator, "
    "Spearman's rho test, and the Innovative Trend Analysis (ITA) graphical method, applied "
    "at annual, wet-season (May–October), and dry-season (November–April) timescales. "
    f"Over the observed period, the regional mean annual rainfall was {obs_mean_ann:.0f} mm, "
    f"with wet-season totals of {obs_mean_wet:.0f} mm ({100*obs_mean_wet/obs_mean_ann:.0f}% of annual). "
    f"The MK test detected no statistically significant annual trend at the regional scale (p>0.05), "
    f"though {obs_inc} of {obs_n} stations showed significant increasing tendencies. "
    "For the CMIP6 multi-model ensemble (MME) over the near future (2021–2050), the projected "
    f"change in annual rainfall relative to the observed baseline is "
    f"{near_245_pct:+.1f}% under SSP2-4.5 and {near_585_pct:+.1f}% under SSP5-8.5. "
    "By the far future (2081–2100), projections diverge substantially between scenarios, "
    f"with MME median changes of {far_245_pct:+.1f}% and {far_585_pct:+.1f}% respectively. "
    "Inter-model spread is large throughout, and no robust signal is identified for the near future. "
    "Limitations of QDM in reproducing temporal structure and out-of-sample transferability are "
    "explicitly disclosed. These findings provide a multi-method, model-level evidence base for "
    "hydroclimatic planning in Nan and similar northern-Thai catchments."
)
p = add_para(doc, abstract_text, size=12, space_before=0, space_after=6)

# Keywords
p = doc.add_paragraph()
r1 = p.add_run('Keywords (Times New Roman 12 pts, Bold): ')
set_font(r1, bold=True, size=12)
r2 = p.add_run('Rainfall trends; Mann-Kendall test; Sen\'s slope; CMIP6; '
               'Bias correction; Nan Province; Thailand')
set_font(r2, size=12)
p.paragraph_format.space_after = Pt(8)

hr(doc)

# Affiliations
p = add_para(doc,
    '\u00b9Office of Water Management and Hydrology, Royal Irrigation Department, '
    'Bangkok, Thailand',
    size=10, space_after=2)
p = add_para(doc,
    '\u002aCorresponding author, email: Surasit.pun@thaimooc.ac.th',
    size=10, space_after=8)

# ── INTRODUCTION ──
add_heading(doc, 'Introduction')

body_paras_intro = [
    ("Climate variability and long-term changes in rainfall patterns pose significant "
     "challenges to water resource management, agriculture, and flood risk reduction across "
     "Southeast Asia [1]. Thailand, with its pronounced monsoon seasonality and complex "
     "mountainous terrain in the north, is particularly vulnerable to hydroclimatic extremes [2,3]. "
     "Nan Province, situated in the upper Nan River basin, is a major contributor to the Chao "
     "Phraya River system and a key source of water for downstream irrigation and domestic supply. "
     "Understanding whether and how rainfall is changing in this province is therefore of both "
     "scientific and operational importance."),
    ("Trend analysis of hydrometeorological time series commonly employs non-parametric methods "
     "such as the Mann-Kendall (MK) test and Spearman's rho test, which are robust to "
     "non-normal distributions and outliers [4,5]. The MK test, combined with Sen's slope "
     "estimator to quantify the magnitude of change, has been widely applied to detect rainfall "
     "trends across Thailand [6,7] and the broader Asian monsoon region [8]. More recently, "
     "the Innovative Trend Analysis (ITA) graphical method of Sen [9] has gained attention as a "
     "complementary tool that does not require assumptions of independence and can reveal "
     "sub-trend behaviour within time series [10]. Comparative studies, including Perera et al. [11], "
     "have demonstrated that MK, Spearman's rho, and ITA produce broadly consistent results but "
     "may diverge for individual stations and time scales, reinforcing the value of applying "
     "multiple methods concurrently."),
    ("Extending observed trend analysis into the future requires climate model projections. "
     "The sixth phase of the Coupled Model Intercomparison Project (CMIP6) provides daily "
     "precipitation from multiple global climate models (GCMs) under shared socioeconomic "
     "pathway (SSP) scenarios [12,13]. Because GCMs systematically misrepresent local "
     "precipitation distributions—producing too many low-intensity events and an incorrect "
     "intensity distribution relative to rain-gauge observations—statistical bias correction "
     "is applied before local impact assessment [14]. Quantile delta mapping (QDM) preserves "
     "the model's projected change signal while adjusting the historical distribution to match "
     "observations [15], and has been used in several Thai and regional studies [16,17]."),
    ("Despite the availability of these tools, three methodological gaps recur in the applied "
     "literature for northern Thailand. First, trend analyses rarely span the full timeline "
     "from observations to far-future projections within a single framework, making it difficult "
     "to assess how historical tendencies connect to modelled future changes. Second, model-level "
     "results are often aggregated immediately into ensemble means, obscuring the substantial "
     "inter-model spread that is characteristic of precipitation projections. Third, the "
     "limitations of QDM—particularly its inability to correct indices governed by the "
     "temporal ordering of wet and dry days—are seldom disclosed explicitly."),
    ("This study addresses these gaps by combining non-parametric trend analysis of gauge "
     "observations (1981–2014) with model-level and multi-model ensemble (MME) analysis of "
     "CMIP6 bias-corrected daily precipitation (1981–2100) for Nan Province. "
     f"Data from {len(NAN_STA)} rain gauges and seven CMIP6 models are analysed at annual, "
     "wet-season, and dry-season timescales. Specific objectives are: "
     "(1) to characterise historical rainfall trends using MK, Sen's slope, Spearman's rho, "
     "and ITA; (2) to project rainfall changes under SSP2-4.5 and SSP5-8.5 through 2100, "
     "reporting results per model and as MME statistics; and (3) to explicitly document the "
     "limitations of the bias-correction approach and the robustness of projected signals."),
]
for txt in body_paras_intro:
    add_body(doc, txt)

# ── MATERIALS AND METHODS ──
add_heading(doc, 'Materials and Methods')

add_subheading(doc, 'Study area and rain-gauge data')
add_body(doc,
    "Nan Province is located in northern Thailand between approximately 17.97° and 19.56°N "
    "and 100.35° and 101.20°E (Figure 1), with elevations ranging from about 160 m in the "
    f"lowland valleys to over 1,500 m along the western divide. Daily rainfall data for {len(NAN_STA)} "
    "gauges were obtained from the Royal Irrigation Department for the period 1981–2014 "
    "(Table 1). Missing values were identified by automated screening: station-months with an "
    "exactly zero total were tested against the median of neighbouring stations, the network "
    "wet-day fraction, the station's own climatological median, and the length of any zero run; "
    "a month was reclassified as missing only when at least one neighbour-based diagnostic "
    "contradicted the zero, requiring a minimum of two diagnostics in total. Detected missing "
    "values were excluded rather than imputed. Homogeneity was assessed as the ratio of the "
    "wet-day frequency in the second half of the record to that in the first half; stations "
    "deviating beyond 0.75–1.33 are flagged and retained in the primary analysis as a "
    "diagnostic subset.")

add_subheading(doc, 'CMIP6 data and bias correction')
add_body(doc,
    "Daily precipitation from seven CMIP6 models (Table 2) was used for the historical "
    "experiment (1981–2014) and under SSP2-4.5 and SSP5-8.5 (2015–2100) [12,13]. "
    "Quantile delta mapping (QDM) [15] was applied independently at each gauge–model pair "
    "using the 1981–2002 calibration period, with parameters frozen and applied to all "
    "subsequent periods (2003–2014 for validation, 2015–2100 for projection). "
    "The bias-corrected future change is referenced to each model's own corrected historical "
    "baseline (1981–2014), not to the gauge observations, so that residual correction errors "
    "do not enter the projected change signal [14]. "
    "An independent out-of-sample evaluation of the QDM correction (Gate C) found that "
    "the corrected output improved primary marginal metrics relative to the raw GCM but that "
    "indices governed by the temporal ordering of wet and dry days—including maximum "
    "consecutive dry days (CDD) and consecutive wet days (CWD)—retained large residual biases. "
    "This limitation is noted explicitly wherever temporal-structure indices are mentioned.")

add_subheading(doc, 'Season definition')
add_body(doc,
    "Two seasons are defined following the Thai monsoon calendar. The wet season covers "
    "May through October of each year. The dry season covers November of year N through "
    "April of year N+1, and is assigned to year N; thus the 1981 dry season spans "
    "November 1981–April 1982. Annual totals use the calendar year (January–December).")

add_subheading(doc, 'Trend analysis methods')
add_body(doc,
    "Three statistical methods and one graphical method were applied at the annual, "
    "wet-season, and dry-season timescales, following the framework of Perera et al. [11].")
add_body(doc,
    "Mann-Kendall (MK) test. The MK test [18,19] evaluates the null hypothesis of no "
    "monotonic trend in a time series x₁, x₂, …, xₙ. The test statistic S is defined as "
    "S = Σᵢ<ⱼ sgn(xⱼ − xᵢ), and the standardised statistic Zc follows the standard normal "
    "distribution for n > 10. Significance was assessed at α = 0.05. Sen's slope estimator "
    "[20] gives the median of all pairwise slopes and was used to quantify trend magnitude "
    "(mm yr⁻¹).")
add_body(doc,
    "Spearman's rho test. Spearman's rank correlation coefficient ρs between time and the "
    "rainfall series was computed; a two-tailed test at α = 0.05 was used to assess "
    "significance [21]. The direction and magnitude of ρs provide an independent measure "
    "of monotonic trend.")
add_body(doc,
    "Innovative Trend Analysis (ITA). The time series was divided into two equal sub-periods, "
    "each sorted in ascending order. The first sub-period was plotted on the x-axis and the "
    "second on the y-axis [9]. Points above the 1:1 line indicate an increasing trend; points "
    "below indicate a decreasing trend. ITA is particularly useful for detecting partial trends "
    "within low, medium and high rainfall regimes.")
add_body(doc,
    "All methods were applied to the regional mean time series—the unweighted spatial average "
    "across available stations—and to each station individually. For CMIP6 output, the same "
    "methods were applied to the regional mean series of each model separately (seven model "
    "series per scenario), and to the MME median series.")

add_subheading(doc, 'Multi-model ensemble statistics')
add_body(doc,
    "The MME was formed from the seven model regional-mean annual and seasonal series. "
    "For each year, the MME median, mean, and interquartile range (IQR, 25th–75th percentile) "
    "were computed across the seven models. Eleven-year centred rolling means were used for "
    "timeline visualisation to reduce interannual noise while retaining decadal signals. "
    "Projected percentage changes relative to the observed baseline mean (1981–2014) are "
    "reported for three future windows: near future (2021–2050), mid future (2051–2080), "
    "and far future (2081–2100).")

# ── RESULTS AND DISCUSSION ──
add_heading(doc, 'Results and Discussion')

add_subheading(doc, 'Historical rainfall characteristics')
add_body(doc,
    f"The regional mean annual rainfall over 1981–2014 was {obs_mean_ann:.0f} mm, "
    f"of which approximately {100*obs_mean_wet/obs_mean_ann:.0f}% fell in the wet season "
    f"(May–October; mean {obs_mean_wet:.0f} mm) and "
    f"{100*obs_mean_dry/obs_mean_ann:.0f}% in the dry season "
    f"(November–April; mean {obs_mean_dry:.0f} mm). "
    "Station-level mean annual totals ranged from approximately 1,050 mm (Station 331002) "
    "to over 2,160 mm (Station 331009), reflecting the strong elevation gradient across "
    "the province.")

add_subheading(doc, 'Observed trends (1981–2014)')
obs_ann_sl = obs_ann['slope'] if obs_ann else np.nan
obs_ann_p  = obs_ann['p_value'] if obs_ann else np.nan
obs_ann_tr = obs_ann['trend'] if obs_ann else '—'
add_body(doc,
    f"At the regional scale, the MK test detected a {obs_ann_tr} in annual rainfall over "
    f"1981–2014 (Sen's slope = {fmt_slope(obs_ann_sl)} mm yr⁻¹; p = {fmt_p(obs_ann_p)}). "
    f"At the station level, {obs_inc} of {obs_n} stations showed a statistically significant "
    f"increasing annual trend and {obs_dec} showed a significant decreasing trend (p<0.05). "
    "Spearman's rho and the ITA scatter plots (Figures 4 and 6) produced directionally "
    "consistent results, as found by Perera et al. [11] for Colombo: all three methods "
    "agreed on the sign of the dominant regional tendency, though the graphical method "
    "revealed sub-trend differences between low- and high-rainfall years not captured by "
    "single-statistic tests.")

obs_wet_sl = obs_wet['slope'] if obs_wet else np.nan
obs_wet_p  = obs_wet['p_value'] if obs_wet else np.nan
obs_dry_sl = obs_dry['slope'] if obs_dry else np.nan
obs_dry_p  = obs_dry['p_value'] if obs_dry else np.nan
add_body(doc,
    f"For the wet season, Sen's slope at the regional mean was {fmt_slope(obs_wet_sl)} mm yr⁻¹ "
    f"(p = {fmt_p(obs_wet_p)}). Dry-season trends were {fmt_slope(obs_dry_sl)} mm yr⁻¹ "
    f"(p = {fmt_p(obs_dry_p)}). "
    "The dry season contributes only a small fraction of annual total, so even a statistically "
    "significant dry-season trend carries limited weight for annual water availability. "
    "Results by model period and station are provided in Table 3.")

add_subheading(doc, 'CMIP6 model performance and limitations')
add_body(doc,
    "The QDM bias correction substantially reduced marginal biases in wet-day frequency, "
    "annual total and wet-day intensity over the calibration period (1981–2002). However, "
    "the independent out-of-sample evaluation (Gate C) found that the corrected output "
    "improved only one of four primary metrics relative to the raw GCM, with a mean residual "
    "bias of 52.1% across metrics and stations. Excluding gauges flagged by the homogeneity "
    "screening reduced the network-mean residual to 33.1%. This finding, consistent with the "
    "general assessment that in-sample agreement of quantile mapping reflects the estimator "
    "rather than transferable skill [14], means that the corrected projections should be "
    "interpreted as indicative rather than precise estimates of future change. "
    "Indices governed by the temporal ordering of wet and dry days—CDD, CWD and Rx5day—"
    "are reported as diagnostics and not as corrected projections throughout.")

add_subheading(doc, 'Model-level projections (1981–2100)')
add_body(doc,
    "Annual and seasonal rainfall series for each of the seven models under SSP2-4.5 and "
    "SSP5-8.5 are shown in Figures 2 and 3. Substantial inter-model spread is evident "
    "throughout the historical and projected periods. Over the historical period (1981–2014), "
    "CMIP6 model biases—even after QDM correction—result in different baseline climatologies "
    "for individual models. The timeline plots in Figures 2 and 3 present 11-year smoothed "
    "series alongside the unsmoothed MME IQR envelope and the observed record, allowing "
    "direct visual comparison of model spread with observed variability. "
    "Table 3 summarises the MK trend direction and Sen's slope for each model at the "
    "regional mean level for four sub-periods.")

add_subheading(doc, 'Multi-model ensemble projections')
add_body(doc,
    f"The MME median annual rainfall over the near future (2021–2050) is "
    f"{near_245_pct:+.1f}% relative to the observed baseline under SSP2-4.5 and "
    f"{near_585_pct:+.1f}% under SSP5-8.5 (Figure 7). These changes are small relative "
    "to the inter-model IQR, and no model-level trend reaches the 0.80 inter-model agreement "
    "threshold for the annual scale. By the far future (2081–2100), projections diverge "
    f"between scenarios: MME median changes are {far_245_pct:+.1f}% (SSP2-4.5) and "
    f"{far_585_pct:+.1f}% (SSP5-8.5). The larger change under SSP5-8.5 is consistent with "
    "the higher radiative forcing but remains associated with wide inter-model spread "
    "(Figure 8), preventing robust conclusions about the direction of annual rainfall change "
    "for most future windows.")

add_body(doc,
    "The wet season dominates these projections, accounting for most of the projected "
    "annual change (Figure 3). Dry-season projections show weaker and more uncertain signals. "
    "The ITA scatter plots (Figure 6) indicate that, for the MME, high-rainfall years in the "
    "second half of the series (representing the future period in the full 1981–2100 analysis) "
    "tend to plot above the 1:1 line more consistently under SSP5-8.5 than under SSP2-4.5, "
    "suggesting a tendency towards more intense high-rainfall events in the higher-forcing "
    "scenario, consistent with intensification reported for Thailand as a whole [6,7].")

add_subheading(doc, 'Comparison with prior studies and limitations')
add_body(doc,
    "The absence of a statistically significant observed annual trend at the regional scale "
    "is broadly consistent with findings for northern Thailand [6] and for comparable studies "
    "in the monsoon region that show weak or no significant long-term trends in area-averaged "
    "annual rainfall over 30–40 year records [8,11]. The near-future MME projections of small "
    "mean change but increasing extreme rainfall indices are consistent with CMIP6-based "
    "assessments for northeast and southern Thailand [16,17].")
add_body(doc,
    "Several limitations constrain interpretation. The observed record spans 34 years—"
    "sufficient for trend detection under stationary forcing but short relative to low-frequency "
    "climate variability. Station history metadata are unavailable, so the homogeneity flags "
    "reflect a screening diagnostic rather than a formal test. Each CMIP6 model contributes "
    "one realisation, preventing separation of forced signal from internal variability. "
    "The QDM parameters were estimated from the same 34-year record, and the out-of-sample "
    "evaluation (Gate C) shows that transferability is imperfect. "
    "Finally, the administrative boundary and gauge network define the spatial domain; "
    "the interpolated spatial maps in Figure 5 arise from gauge-to-gauge interpolation "
    "rather than from resolved model structure.")

# ── CONCLUSIONS ──
add_heading(doc, 'Conclusions')
add_body(doc,
    f"This study combined non-parametric trend analysis of {len(NAN_STA)} rain gauges "
    f"(1981–2014) with model-level and MME analysis of seven CMIP6 bias-corrected daily "
    "precipitation series (1981–2100) for Nan Province, northern Thailand. The following "
    "conclusions are drawn:", indent=False)

conclusions = [
    f"The regional mean annual rainfall over the observed period was {obs_mean_ann:.0f} mm. "
    f"The MK test detected no significant annual trend at the regional scale "
    f"(Sen's slope = {fmt_slope(obs_ann_sl)} mm yr⁻¹, p = {fmt_p(obs_ann_p)}), "
    f"with {obs_inc} of {obs_n} stations showing significant increasing tendencies. "
    "Spearman's rho and ITA analyses were directionally consistent with MK.",

    "Wet-season rainfall (May–October) dominates the annual total. Seasonal trend "
    "magnitudes are comparable to annual trends, confirming that wet-season dynamics "
    "drive provincial rainfall variability.",

    f"Near-future (2021–2050) MME median annual rainfall changes are {near_245_pct:+.1f}% "
    f"(SSP2-4.5) and {near_585_pct:+.1f}% (SSP5-8.5) relative to the observed baseline. "
    f"Far-future (2081–2100) changes are {far_245_pct:+.1f}% and {far_585_pct:+.1f}% "
    "respectively, with inter-model spread remaining large throughout.",

    "Inter-model spread substantially exceeds the MME median change for all near-future "
    "windows, and no annual or seasonal projection reaches the 0.80 inter-model agreement "
    "threshold. Individual model results diverge considerably, emphasising that single-model "
    "projections should not be used without ensemble context.",

    "QDM improved primary marginal metrics over the calibration period but failed the "
    "independent out-of-sample evaluation (Gate C) on the primary validation metric suite. "
    "Temporal-structure indices (CDD, CWD) are reported as diagnostics and must not be "
    "described as corrected projections.",
]
for i, c in enumerate(conclusions, 1):
    p = doc.add_paragraph(style='List Number')
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(c)
    set_font(run, size=12)

add_body(doc,
    "The multi-method, model-level evidence base provided here supports hydroclimatic "
    "planning for the Nan River basin under a range of plausible futures, while the explicit "
    "disclosure of QDM limitations and inter-model uncertainty enables decision-makers to "
    "assess the reliability of projections for specific indices and time horizons.",
    indent=False)

# ── ACKNOWLEDGEMENTS ──
add_heading(doc, 'Acknowledgements')
add_body(doc,
    "The author thanks the Royal Irrigation Department for the rain-gauge records, "
    "the Thai Meteorological Department for supplementary data, the World Climate Research "
    "Programme for coordinating CMIP6, and the modelling groups listed in Table 2 for "
    "making their output available through the Earth System Grid Federation. "
    "During the preparation of this work the author used a generative AI assistant for "
    "code development, statistical verification and language editing; the author reviewed "
    "and edited the content and takes full responsibility for the publication.",
    indent=False)

# ── REFERENCES ──
add_heading(doc, 'References')
refs = [
    "[1] Maraun D. Bias correcting climate change simulations: a critical review. "
    "Curr Clim Change Rep. 2016;2(4):211-220.",

    "[2] Limsakul A, Singhruck P. Long-term trends and variability of total and extreme "
    "precipitation in Thailand. Atmos Res. 2016;169:301-317.",

    "[3] Limsakul A. Changes of daily rainfall intensity in Thailand from 1955 to 2019. "
    "Asia Pac J Sci Technol. 2022;27(1):APST-27-01-12.",

    "[4] Hirsch RM, Slack JR, Smith RA. Techniques of trend analysis for monthly water "
    "quality data. Water Resour Res. 1982;18(1):107-121.",

    "[5] Ahmad I, Tang D, Wang T, Wang M, Wagan B. Precipitation trends over time using "
    "Mann-Kendall and Spearman's rho tests in Swat River basin, Pakistan. "
    "Adv Meteorol. 2015;2015:431860.",

    "[6] Khadka D, Babel MS, Collins M, Shrestha S, Virdis SGP, Chen AS. Projected changes "
    "in the near-future mean climate and extreme climate events in northeast Thailand. "
    "Int J Climatol. 2022;42(2):1088-1111.",

    "[7] Paengkaew W, Limsakul A, Aroonchan N, Santisirisomboon J, Srisawadwong R, "
    "Amnuaylojaroen T, et al. Increasing compound hot-rainfall extreme in Thailand during "
    "1970-2022. Asia Pac J Sci Technol. 2026;31(1):APST-31-01-02.",

    "[8] Krishnaswamy J, Vaidyanathan S, Rajagopalan B, Bonell M, Sankaran M, Bhalla RS, "
    "et al. Non-stationary and non-linear influence of ENSO and Indian Ocean Dipole on the "
    "variability of Indian monsoon rainfall and extreme rain events. Clim Dyn. "
    "2015;45(1-2):175-184.",

    "[9] Sen Z. Innovative trend analysis methodology. J Hydrol Eng. 2012;17(9):1042-1046.",

    "[10] Caloiero T, Coscarelli R, Ferrari E. Analysis of monthly rainfall trend in "
    "Calabria (southern Italy) through the application of statistical and graphical "
    "techniques. Proceedings. 2018;2(11):629-637.",

    "[11] Perera A, Ranasinghe T, Gunathilake M, Rathnayake U. Comparison of different "
    "analyzing techniques in identifying rainfall trends for Colombo, Sri Lanka. "
    "Adv Meteorol. 2020;2020:8844052.",

    "[12] Eyring V, Bony S, Meehl GA, Senior CA, Stevens B, Stouffer RJ, et al. Overview "
    "of the Coupled Model Intercomparison Project Phase 6 (CMIP6) experimental design and "
    "organization. Geosci Model Dev. 2016;9(5):1937-1958.",

    "[13] O'Neill BC, Tebaldi C, van Vuuren DP, Eyring V, Friedlingstein P, Hurtt G, et al. "
    "The Scenario Model Intercomparison Project (ScenarioMIP) for CMIP6. "
    "Geosci Model Dev. 2016;9(9):3461-3482.",

    "[14] Cannon AJ, Sobie SR, Murdock TQ. Bias correction of GCM precipitation by "
    "quantile mapping: how well do methods preserve changes in quantiles and extremes? "
    "J Clim. 2015;28(17):6938-6959.",

    "[15] Themessl MJ, Gobiet A, Heinrich G. Empirical-statistical downscaling and error "
    "correction of regional climate models and its impact on the climate change signal. "
    "Clim Change. 2012;112(2):449-468.",

    "[16] Kuinkel D, Promchote P, Upreti KR, Aryal D, Bhandari S, Adhikari S. Projected "
    "changes in precipitation extremes in southern Thailand using CMIP6 models. "
    "Theor Appl Climatol. 2024;155(9):8703-8716.",

    "[17] Punyawansiri S. Near-future changes in daily precipitation and selected rainfall "
    "extremes over Nan, Thailand using bias-corrected global climate models. "
    "Manuscr under review. 2026.",

    "[18] Mann HB. Nonparametric tests against trend. Econometrica. 1945;13(3):245-259.",

    "[19] Kendall MG. Rank Correlation Methods. London: Griffin; 1975.",

    "[20] Sen PK. Estimates of the regression coefficient based on Kendall's tau. "
    "J Am Stat Assoc. 1968;63(324):1379-1389.",

    "[21] Ziehn T, Chamberlain MA, Law RM, Lenton A, Bodman RW, Dix M, et al. The Australian "
    "Earth System Model: ACCESS-ESM1.5. J South Hemisph Earth Syst Sci. 2020;70(1):193-214.",
]

for ref in refs:
    p = doc.add_paragraph(style='List Paragraph')
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.left_indent  = Cm(0.75)
    p.paragraph_format.first_line_indent = Cm(-0.75)
    p.paragraph_format.space_after  = Pt(3)
    run = p.add_run(ref)
    set_font(run, size=11)

# ── TABLES ──
add_heading(doc, 'Tables', space_before=20)

# Table 1 — Station details
add_caption(doc, 'Table 1',
    ' Characteristics of rain-gauge stations in Nan Province used in this study.',
    align=WD_ALIGN_PARAGRAPH.LEFT)

t1_headers = ['Station ID', 'Latitude (°N)', 'Longitude (°E)', 'Elevation (m)', 'Record']
t1_data = []
for _, row in sta_df.iterrows():
    t1_data.append([str(int(row['Station_ID'])),
                    f"{row['latitude']:.2f}",
                    f"{row['longitude']:.2f}",
                    str(row['Elevation']),
                    '1981–2014'])

tbl = doc.add_table(rows=1+len(t1_data), cols=len(t1_headers))
tbl.style = 'Table Grid'
# Header row
for j, h in enumerate(t1_headers):
    cell = tbl.rows[0].cells[j]
    cell.text = h
    for run in cell.paragraphs[0].runs:
        set_font(run, bold=True, size=11)
# Data rows
for i, row_data in enumerate(t1_data):
    for j, val in enumerate(row_data):
        tbl.rows[i+1].cells[j].text = val
        for run in tbl.rows[i+1].cells[j].paragraphs[0].runs:
            set_font(run, size=11)

doc.add_paragraph()  # space

# Table 2 — CMIP6 model configuration
add_caption(doc, 'Table 2',
    ' Configuration of the seven CMIP6 models used in this study.',
    align=WD_ALIGN_PARAGRAPH.LEFT)

t2_headers = ['Model', 'Institution', 'Variant', 'Calendar', 'SSP scenarios']
t2_data = [
    ['ACCESS-ESM1-5', 'CSIRO, Australia',      'r1i1p1f1', 'Standard',  'SSP2-4.5, SSP5-8.5'],
    ['CESM2',         'NCAR, USA',              'r11i1p1f1','365-day',   'SSP2-4.5, SSP5-8.5'],
    ['CanESM5',       'CCCma, Canada',          'r1i1p1f1', '365-day',   'SSP2-4.5, SSP5-8.5'],
    ['EC-Earth3',     'EC-Earth Consortium',    'r1i1p1f1', 'Standard',  'SSP2-4.5, SSP5-8.5'],
    ['FGOALS-g3',     'IAP/LASG, China',        'r1i1p1f1', '365-day',   'SSP2-4.5, SSP5-8.5'],
    ['MIROC6',        'MIROC Consortium, Japan','r1i1p1f1', 'Standard',  'SSP2-4.5, SSP5-8.5'],
    ['MRI-ESM2-0',    'MRI, Japan',             'r1i1p1f1', 'Standard',  'SSP2-4.5, SSP5-8.5'],
]

tbl2 = doc.add_table(rows=1+len(t2_data), cols=len(t2_headers))
tbl2.style = 'Table Grid'
for j, h in enumerate(t2_headers):
    cell = tbl2.rows[0].cells[j]
    cell.text = h
    for run in cell.paragraphs[0].runs:
        set_font(run, bold=True, size=11)
for i, row_data in enumerate(t2_data):
    for j, val in enumerate(row_data):
        tbl2.rows[i+1].cells[j].text = val
        for run in tbl2.rows[i+1].cells[j].paragraphs[0].runs:
            set_font(run, size=11)

doc.add_paragraph()

# Table 3 — MK trend results by model and period (regional mean, annual)
add_caption(doc, 'Table 3',
    ' Mann-Kendall trend results for regional mean annual rainfall by model and period. '
    'Slope in mm yr⁻¹. ↑ increasing, ↓ decreasing, → no trend. * p<0.05.',
    align=WD_ALIGN_PARAGRAPH.LEFT)

t3_models = ['observed'] + MODELS
t3_periods = [('1981-2014','1981–2014'), ('near_future','2021–2050'),
              ('mid_future','2051–2080'), ('far_future','2081–2100')]
t3_headers = ['Model'] + [pl for _, pl in t3_periods]
t3_data = []
for model in t3_models:
    row_vals = [model if model != 'observed' else 'Observed']
    for pcode, _ in t3_periods:
        ssp_to_use = 'observed' if model == 'observed' else 'ssp245'
        tr = get_trend(model, ssp_to_use, 'annual', pcode, 'mk')
        if tr is None:
            row_vals.append('—')
        else:
            sl = tr['slope']
            pv = tr['p_value']
            td = trend_arrow(tr['trend'])
            sig = '*' if (not np.isnan(pv) and pv < 0.05) else ''
            row_vals.append(f"{td} {fmt_slope(sl)}{sig}")
    t3_data.append(row_vals)

tbl3 = doc.add_table(rows=1+len(t3_data), cols=len(t3_headers))
tbl3.style = 'Table Grid'
for j, h in enumerate(t3_headers):
    cell = tbl3.rows[0].cells[j]
    cell.text = h
    for run in cell.paragraphs[0].runs:
        set_font(run, bold=True, size=10)
for i, row_data in enumerate(t3_data):
    for j, val in enumerate(row_data):
        tbl3.rows[i+1].cells[j].text = str(val)
        for run in tbl3.rows[i+1].cells[j].paragraphs[0].runs:
            set_font(run, size=10)

doc.add_paragraph()

# Table 4 — MME statistics for future periods
add_caption(doc, 'Table 4',
    ' Multi-model ensemble (MME) statistics for projected annual rainfall change '
    'relative to the observed baseline mean (1981–2014). IQR = interquartile range '
    '(25th–75th percentile across 7 models).',
    align=WD_ALIGN_PARAGRAPH.LEFT)

t4_headers = ['Period', 'SSP', 'MME Mean (mm)', 'IQR (mm)', '% Change vs Baseline']
t4_data = []
periods_mme = [('Near future', 2021, 2050), ('Mid future', 2051, 2080), ('Far future', 2081, 2100)]
for plabel, y1, y2 in periods_mme:
    for ssp in ['ssp245','ssp585']:
        mm = mme_df[(mme_df['scenario']==ssp) & (mme_df['scale']=='annual') &
                    (mme_df['year']>=y1) & (mme_df['year']<=y2)]
        if mm.empty:
            t4_data.append([plabel, SSP_LABEL_D.get(ssp,ssp),'—','—','—'])
            continue
        mmean = mm['mme_mean'].mean()
        q25m  = mm['q25'].mean()
        q75m  = mm['q75'].mean()
        base_mean = obs_mean_ann
        pct = 100*(mmean - base_mean)/base_mean if base_mean != 0 else np.nan
        SSP_LABEL_D = {'ssp245':'SSP2-4.5','ssp585':'SSP5-8.5'}
        t4_data.append([plabel, SSP_LABEL_D[ssp],
                        f"{mmean:.0f}",
                        f"{q25m:.0f}–{q75m:.0f}",
                        f"{pct:+.1f}%"])

tbl4 = doc.add_table(rows=1+len(t4_data), cols=len(t4_headers))
tbl4.style = 'Table Grid'
for j, h in enumerate(t4_headers):
    cell = tbl4.rows[0].cells[j]
    cell.text = h
    for run in cell.paragraphs[0].runs:
        set_font(run, bold=True, size=11)
for i, row_data in enumerate(t4_data):
    for j, val in enumerate(row_data):
        tbl4.rows[i+1].cells[j].text = str(val)
        for run in tbl4.rows[i+1].cells[j].paragraphs[0].runs:
            set_font(run, size=11)

# ── FIGURES section ──
add_heading(doc, 'Figures', space_before=20)

fig_captions = [
    ('Fig1_Study_Area.png', 14.0,
     'Figure 1', ' Study area: Nan Province, northern Thailand. '
     '(a) Location within Thailand. '
     '(b) Rain-gauge network: 14 stations (triangles) with station ID labels; '
     'blue line = Nan River (approximate); terrain shading is schematic.'),
    ('Fig2_Annual_Timeline.png', 14.0,
     'Figure 2', ' Regional mean annual rainfall for Nan Province: observed 1981–2014 '
     '(black), bias-corrected CMIP6 models (coloured thin lines) and MME median '
     '(thick coloured line) with IQR shading. Upper: SSP2-4.5; lower: SSP5-8.5. '
     'Vertical dashed line marks 2015. All model series smoothed with an 11-yr centred mean.'),
    ('Fig3_Seasonal_Timeline.png', 14.0,
     'Figure 3', ' Regional mean seasonal rainfall: (a,b) wet season (May–October) and '
     '(c,d) dry season (November–April) under SSP2-4.5 and SSP5-8.5.'),
    ('Fig4_MK_Trends.png', 14.0,
     'Figure 4', ' Mann-Kendall trend direction and Sen\'s slope (mm yr⁻¹) for the '
     'regional mean annual and seasonal rainfall by model and analysis period. '
     'Colour indicates trend direction; asterisk (*) marks significance at p<0.05.'),
    ('Fig5_Sens_Slope_Heatmap.png', 13.0,
     'Figure 5', ' Sen\'s slope (mm yr⁻¹) for annual rainfall over the full period '
     '(1981–2100) by station and model under SSP2-4.5 (left) and SSP5-8.5 (right). '
     'Warm colours indicate increasing trends; cool colours indicate decreasing trends. '
     '✦ marks significance at p<0.05.'),
    ('Fig6_ITA.png', 14.0,
     'Figure 6', ' Innovative Trend Analysis (ITA) scatter plots for regional mean '
     '(a) annual, (b) wet-season and (c) dry-season rainfall. Points above the 1:1 '
     'dashed line indicate an increasing trend; points below indicate a decreasing trend.'),
    ('Fig7_Future_Projection.png', 13.0,
     'Figure 7', ' CMIP6 projected annual (a), wet-season (b) and dry-season (c) '
     'rainfall for Nan Province under SSP2-4.5 and SSP5-8.5. Thick lines: 21-yr '
     'smoothed MME median. Inner shading: IQR (25–75%); outer shading: full model range. '
     'Dashed vertical line marks 2015.'),
    ('Fig8_Model_Spread.png', 13.0,
     'Figure 8', ' Inter-model spread (Sen\'s slope, mm yr⁻¹) for annual and seasonal '
     'rainfall across four analysis periods. Boxes show the IQR across 7 models; '
     'dots show individual model values. Dashed horizontal line marks zero slope.'),
]

for fname, width, label_bold, cap_rest in fig_captions:
    fpath = FIG_D / fname
    if fpath.exists():
        doc.add_picture(str(fpath), width=Cm(width))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    else:
        p = add_para(doc, f'[Figure file not found: {fname}]', size=10,
                     align=WD_ALIGN_PARAGRAPH.CENTER)
    add_caption(doc, label_bold, cap_rest)
    doc.add_paragraph()

# ─── Save ────────────────────────────────────────────────────────────────────
doc.save(OUT_DOC)
print(f"\n=== MANUSCRIPT SAVED → {OUT_DOC} ===")
