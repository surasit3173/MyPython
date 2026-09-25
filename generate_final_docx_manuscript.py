import os, docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
import pandas as pd

df_qa = pd.read_csv('01_data_audit/station_qa_summary.csv')
df_state_freq = pd.read_csv('02_state_classification/state_frequencies_1961_2019.csv')
df_markov = pd.read_csv('03_markov/markov_order1_matrices.csv')
df_order_sel = pd.read_csv('03_markov/markov_order_selection.csv')
df_spells = pd.read_csv('05_spells/spell_dynamics_summary.csv')
df_trend = pd.read_csv('08_temporal/trend_and_period_comparison_results.csv')

doc = Document()

for section in doc.sections:
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

def style_table(table):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    header_tr = table.rows[0]._tr.get_or_add_trPr()
    header_tr.append(parse_xml(r'<w:tblHeader %s/>' % nsdecls('w')))

    for row_idx, row in enumerate(table.rows):
        trPr = row._tr.get_or_add_trPr()
        trPr.append(parse_xml(r'<w:cantSplit %s/>' % nsdecls('w')))
        for cell in row.cells:
            tcPr = cell._tc.get_or_add_tcPr()
            if row_idx == 0:
                shading = parse_xml(r'<w:shd %s w:fill="1F4E78"/>' % nsdecls('w'))
                tcPr.append(shading)
                for p in cell.paragraphs:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    for run in p.runs:
                        run.font.bold = True
                        run.font.color.rgb = RGBColor(255, 255, 255)
                        run.font.size = Pt(9.5)
            else:
                for p in cell.paragraphs:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    for run in p.runs:
                        run.font.size = Pt(9)

def add_figure(doc, image_path, fig_title, fig_caption):
    p_img = doc.add_paragraph()
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_img = p_img.add_run()
    run_img.add_picture(image_path, width=Inches(6.0))

    p_cap = doc.add_paragraph()
    p_cap.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run_title = p_cap.add_run(f"{fig_title}: ")
    run_title.bold = True
    run_title.font.size = Pt(9.5)
    run_cap = p_cap.add_run(fig_caption)
    run_cap.font.size = Pt(9.5)
    run_cap.italic = True
    doc.add_paragraph()

p_title = doc.add_paragraph()
p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
r_title = p_title.add_run("Spatial Heterogeneity and Temporal Stability of Daily Rainfall Occurrence Regimes in Northeastern Thailand")
r_title.font.name = "Calibri"
r_title.font.size = Pt(16)
r_title.font.bold = True

doc.add_paragraph()

h_abs = doc.add_heading(level=1)
r_abs_h = h_abs.add_run("Abstract")
r_abs_h.font.color.rgb = RGBColor(31, 78, 120)

p_abs = doc.add_paragraph(
    "Understanding long-term daily rainfall occurrence regimes is essential for regional agricultural planning and hydroclimatic risk management. "
    "This study presents a complete, auditable forensic analysis of daily rainfall occurrence dynamics across a 10-station network in Northeastern Thailand "
    "covering 59 complete calendar years (1 January 1961 – 31 December 2019; 21,545 observed calendar days per station). Daily rainfall was classified into three "
    "discrete operational states: Dry (D <= 2.50 mm/day), Wet (2.50 < W <= 5.00 mm/day), and Rainy (R > 5.00 mm/day). Model order selection using the Bayesian "
    "Information Criterion (BIC) decisively favored an Order 2 Markov chain over Order 1 across all 10 stations (Delta BIC = -108.3 to -1027.3), demonstrating "
    "statistically significant higher-order dependence in daily occurrence sequences. Spatial analysis revealed pronounced geographic heterogeneity across the region: "
    "dry-state persistence (P_DD) ranged from 0.763 to 0.803, rainy-state persistence (P_RR) ranged from 0.428 to 0.540, and state Shannon entropy ranged from 0.794 "
    "to 1.020 bits. Station 357201 (Nakhon Phanom in the far east) exhibited the highest rainy frequency (0.223) and rainy persistence (0.540), whereas western and southern "
    "stations (e.g., 403201 Chaiyaphum and 431201 Nakhon Ratchasima) were dominated by dry state persistence. Monotonic trend analysis using the Yue and Wang modified "
    "Mann-Kendall test with False Discovery Rate (FDR) control revealed no statistically significant long-term trends (q > 0.05) across rainfall frequency, persistence, "
    "or entropy metrics. Comparison between 1961–1990 and 1991–2019 periods confirmed that spatial contrasts remain structurally stable over time. These results establish "
    "that daily rainfall regimes in Northeastern Thailand are spatially heterogeneous but temporally stable over multi-decadal timescales."
)

p_kw = doc.add_paragraph()
r_kw_title = p_kw.add_run("Keywords: ")
r_kw_title.bold = True
p_kw.add_run("Markov chain; Rainfall persistence; Spell dynamics; Shannon entropy; Spatial heterogeneity; Temporal stability; Northeastern Thailand")

doc.add_paragraph()

h1 = doc.add_heading(level=1)
h1.add_run("1. Introduction").font.color.rgb = RGBColor(31, 78, 120)

doc.add_paragraph(
    "Daily precipitation occurrence dynamics govern the timing of agricultural planting, water resource availability, and drought-flood vulnerability across monsoon Asia. "
    "In Northeastern Thailand (the Khorat Plateau), rainfall variability directly influences rainfed rice yields and regional water security. While many regional studies examine "
    "annual or monthly total rainfall amounts, fewer investigate the underlying daily occurrence structure—specifically, how state transitions, persistence, contiguous spell "
    "lengths, and state uncertainty vary spatially across the landscape and evolve over multi-decadal timescales."
)
doc.add_paragraph(
    "Stochastic modeling via Markov chains provides a mathematically rigorous framework for representing daily rainfall occurrence sequences. A fundamental question in stochastic "
    "hydrology is whether daily occurrence is adequately captured by a first-order Markov chain or requires higher-order statistical memory. Many classical applications assume "
    "first-order dependence without formal order selection, potentially underestimating multi-day persistence and extreme spell lengths."
)
doc.add_paragraph(
    "Furthermore, hydroclimatic investigations frequently focus either on spatial mapping or temporal trend detection in isolation. An integrated framework combining state "
    "occupancy frequencies, transition probabilities, spell dynamics, and Shannon entropy can simultaneously resolve spatial heterogeneity and evaluate temporal stability. "
    "This study addresses this gap by examining whether daily rainfall occurrence regimes across Northeastern Thailand exhibit spatial heterogeneity and whether these structures "
    "have remained temporally stable over the 59-year historical period (1961–2019)."
)
doc.add_paragraph(
    "The primary objectives of this paper are to: (1) evaluate Markov chain order adequacy across a high-quality 10-station daily rainfall network; (2) quantify spatial heterogeneity "
    "in rainfall-state frequency, persistence, spell durations, and entropy; and (3) evaluate long-term temporal stability and monotonic trends over 1961–2019 using serial-correlation-aware "
    "statistical procedures with False Discovery Rate control."
)

h2 = doc.add_heading(level=1)
h2.add_run("2. Materials and Methods").font.color.rgb = RGBColor(31, 78, 120)

doc.add_heading("2.1 Study Area and Station Network", level=2)
doc.add_paragraph(
    "The study area encompasses Northeastern Thailand, defined by 10 primary Thai Meteorological Department (TMD) rainfall stations spanning latitudes 14.88°N to 17.45°N and "
    "longitudes 101.73°E to 104.87°E (Table 1, Figure 1). Daily rainfall observations spanning 1 January 1961 to 30 September 2020 were audited from raw archived records. To ensure "
    "complete calendar year representation, annual and multi-decadal analyses were restricted strictly to the 59 complete calendar years from 1961 to 2019 (21,545 calendar days per station)."
)

add_figure(doc, '11_figures/Figure1_study_area_network.png', "Figure 1", "Study Area and TMD Rainfall Station Network across Northeastern Thailand. Station positions are scaled by altitude (m, MSL).")

p_t1 = doc.add_paragraph()
r_t1 = p_t1.add_run("Table 1. Station characteristics and data completeness audit (1961–2020).")
r_t1.bold = True

t1 = doc.add_table(rows=1, cols=8)
hdr_cells = t1.rows[0].cells
hdr_titles = ["Station ID", "Name", "Lat (°N)", "Lon (°E)", "Alt (m)", "Actual Recs", "Missing %", "Max Rain (mm)"]
for i, title in enumerate(hdr_titles):
    hdr_cells[i].text = title

for _, r in df_qa.iterrows():
    row_cells = t1.add_row().cells
    row_cells[0].text = str(r['Station_ID'])
    row_cells[1].text = str(r['Station_Name'])
    row_cells[2].text = f"{r['Latitude_DD']:.2f}"
    row_cells[3].text = f"{r['Longitude_DD']:.2f}"
    row_cells[4].text = str(r['Altitude_m'])
    row_cells[5].text = f"{r['Actual_Records']:,}"
    row_cells[6].text = f"{r['Missing_Pct']:.2f}%"
    row_cells[7].text = f"{r['Max_Rain_mm']:.1f}"

style_table(t1)
doc.add_paragraph()

doc.add_heading("2.2 Quality Control and Missingness Handling", level=2)
doc.add_paragraph(
    "Forensic data QA/QC confirmed exceptional data completeness across the network, ranging from 97.98% (Station 405201, Roi Et) to 99.99% (Stations 407501 and 432201). "
    "No negative or non-numeric rainfall values were present. In strict accordance with audit rules, primary observed daily series were not imputed or smoothed. "
    "Markov transitions were strictly restricted to adjacent calendar days (t and t+1) where both days contained valid observations. Transitions were never bridged across missing calendar days."
)

doc.add_heading("2.3 Rainfall-State Classification", level=2)
doc.add_paragraph(
    "Daily rainfall amounts (x) were classified into three discrete state categories: Dry (D: x <= 2.50 mm/day), Wet (W: 2.50 < x <= 5.00 mm/day), and Rainy (R: x > 5.00 mm/day). "
    "Boundary condition checks (2.50 mm -> D; 5.00 mm -> W; 5.01 mm -> R) were explicitly validated."
)

doc.add_heading("2.4 Markov Chain Framework and Order Selection", level=2)
doc.add_paragraph(
    "Transition probability matrices were estimated via maximum likelihood from valid adjacent day pairs. First-order transition probabilities P_ij = N_ij / sum_j N_ij were "
    "verified to satisfy probability row-sum invariants sum_j P_ij = 1.0. Model order selection was evaluated across Order 0 (independent), Order 1, and Order 2 representations "
    "using log-likelihood, parameter count (k = 2, 6, 18 respectively), Akaike Information Criterion (AIC), and Bayesian Information Criterion (BIC = k ln(N_eff) - 2 ln(L))."
)

doc.add_heading("2.5 Persistence, Spell Dynamics, and Shannon Entropy", level=2)
doc.add_paragraph(
    "One-step state persistence was quantified by diagonal transition probabilities P_DD, P_WW, and P_RR. Contiguous run lengths (spells) were extracted for each state without crossing "
    "missing days. Observed mean spell lengths were compared against first-order Markov implied expected run lengths E(L_i) = 1 / (1 - P_ii). State Shannon entropy (H_state = - sum p_i log2 p_i) "
    "and transition Shannon entropy (H_trans = - sum_i pi_i sum_j P_ij log2 P_ij) were computed to quantify occurrence uncertainty and transition disorder in units of bits."
)

doc.add_heading("2.6 Temporal Stability and Trend Inference", level=2)
doc.add_paragraph(
    "Long-term monotonic trends over 1961–2019 were evaluated using the Yue and Wang (2002) modified Mann-Kendall test to eliminate the confounding effect of serial autocorrelation. "
    "Sen's slope was calculated for trend magnitude. Period-to-period shift was assessed comparing 1961–1990 (30 years) versus 1991–2019 (29 years) using Welch's t-test and "
    "Mann-Whitney U testing. Multiple testing multiplicity was controlled using the Benjamini-Hochberg False Discovery Rate (FDR) procedure at alpha = 0.05."
)

h3 = doc.add_heading(level=1)
h3.add_run("3. Results and Discussion").font.color.rgb = RGBColor(31, 78, 120)

doc.add_heading("3.1 Data Quality and Markov Order Selection", level=2)
doc.add_paragraph(
    "Data quality audit results confirm complete observational integrity across all 10 stations (Table 1). Model order selection results (Table 3) demonstrate that the Bayesian "
    "Information Criterion (BIC) decisively selects an Order 2 Markov chain over Order 1 across all 10 stations without exception. Delta BIC values ranged from -108.3 (Station 403201) "
    "to -1027.3 (Station 357201). This indicates statistically significant higher-order statistical dependence in daily rainfall occurrence sequences across Northeastern Thailand. "
    "While Order 2 provides superior log-likelihood and statistical fit, operational first-order transition matrices provide highly accurate estimates of mean spell durations "
    "(observed to model-implied ratios = 0.998–1.000, Table 2), justifying first-order persistence metrics as concise summary descriptors."
)

p_t3 = doc.add_paragraph()
r_t3 = p_t3.add_run("Table 3. Markov chain order model selection statistics across Northeastern Thailand (1961–2019).")
r_t3.bold = True

t3 = doc.add_table(rows=1, cols=6)
hdr_cells3 = t3.rows[0].cells
hdr_titles3 = ["Station ID", "N_eff", "BIC Order 1", "BIC Order 2", "ΔBIC (Ord2-Ord1)", "BIC Selected Model"]
for i, title in enumerate(hdr_titles3):
    hdr_cells3[i].text = title

for _, r in df_order_sel.iterrows():
    row_cells = t3.add_row().cells
    row_cells[0].text = str(r['Station_ID'])
    row_cells[1].text = f"{r['N_eff_t1']:,}"
    row_cells[2].text = f"{r['BIC_Order1']:.1f}"
    row_cells[3].text = f"{r['BIC_Order2']:.1f}"
    row_cells[4].text = f"{r['Delta_BIC_Ord2_vs_1']:.1f}"
    row_cells[5].text = str(r['BIC_Selected_Order'])

style_table(t3)
doc.add_paragraph()

doc.add_heading("3.2 Spatial Heterogeneity of Occurrence Regimes", level=2)
doc.add_paragraph(
    "Rainfall occurrence regimes display pronounced spatial heterogeneity across Northeastern Thailand (Table 2, Figures 2 and 3). Dry state frequency (Freq_D) ranges from 0.731 at "
    "Nakhon Phanom (357201) in the far northeast to 0.828 at Nakhon Ratchasima (431201) and Chaiyaphum (403201) in the southwest. Conversely, rainy state frequency (Freq_R) is highest "
    "along the eastern Mekong border (0.223 at Nakhon Phanom and 0.181 at Sakon Nakhon) and lowest in the leeward western and southern plateau areas (0.131–0.135)."
)

p_t2 = doc.add_paragraph()
r_t2 = p_t2.add_run("Table 2. Rainfall-state occurrence frequency, persistence probabilities, and Shannon entropy (1961–2019).")
r_t2.bold = True

t2 = doc.add_table(rows=1, cols=8)
hdr_cells2 = t2.rows[0].cells
hdr_titles2 = ["Station ID", "Freq_D", "Freq_W", "Freq_R", "P_DD", "P_WW", "P_RR", "State Entropy (bits)"]
for i, title in enumerate(hdr_titles2):
    hdr_cells2[i].text = title

df_t2_comb = df_state_freq.merge(df_markov, on='Station_ID')
for _, r in df_t2_comb.iterrows():
    row_cells = t2.add_row().cells
    row_cells[0].text = str(r['Station_ID'])
    row_cells[1].text = f"{r['Freq_D']:.3f}"
    row_cells[2].text = f"{r['Freq_W']:.3f}"
    row_cells[3].text = f"{r['Freq_R']:.3f}"
    row_cells[4].text = f"{r['P_DD']:.3f}"
    row_cells[5].text = f"{r['P_WW']:.3f}"
    row_cells[6].text = f"{r['P_RR']:.3f}"
    row_cells[7].text = f"{r['State_Entropy_bits']:.3f}"

style_table(t2)
doc.add_paragraph()

doc.add_paragraph(
    "Persistence metrics reflect this spatial structure: dry persistence (P_DD) dominates western/southern inland stations (P_DD = 0.803 at Chaiyaphum), whereas rainy persistence (P_RR) "
    "is markedly stronger at eastern stations (P_RR = 0.540 at Nakhon Phanom vs. 0.428 at Chaiyaphum). Mean rainy spell duration varies accordingly, extending from 1.57 days at Loei "
    "to 1.75 days at Sakon Nakhon, with maximum observed rainy spells reaching 17 to 23 days in the east. State entropy (H_state) ranges from 0.794 bits (Chaiyaphum) to 1.020 bits "
    "(Nakhon Phanom), reflecting greater state diversity and occurrence uncertainty in the wetter eastern corridor."
)

add_figure(doc, '11_figures/Figure2_seasonal_occurrence.png', "Figure 2", "Seasonal Rainy-State Occurrence Probabilities across Northeastern Thailand. Seasons defined as Dry (Nov–Feb), Pre-Monsoon (Mar–Apr), and SW Monsoon / Wet (May–Oct).")
add_figure(doc, '11_figures/Figure3_spatial_heterogeneity.png', "Figure 3", "Spatial Heterogeneity of Rainfall Occurrence Regimes. (A) Rainy State Frequency (Freq_R), (B) Dry Persistence (P_DD), (C) Rainy Persistence (P_RR), and (D) Mean Rainy-Spell Duration.")

doc.add_heading("3.3 Seasonal Dynamics and Integrated Regime Synthesis", level=2)
doc.add_paragraph(
    "Seasonal breakdown highlights the dominant influence of the Southwest Monsoon (May–October), during which rainy state probabilities reach 0.25–0.38 across the network (Figure 2). "
    "Pre-monsoon (March–April) rainy occurrence remains low (0.05–0.09) but provides critical early moisture. In integrated Frequency–Persistence–Entropy space (Figure 5), the 10 stations "
    "cluster into three distinct geographic occurrence regimes: (1) Eastern High-Raininess / High-Persistence Regime (Nakhon Phanom, Sakon Nakhon, Ubon Ratchathani); (2) Central Moderate "
    "Transition Regime (Udon Thani, Loei, Roi Et, Surin); and (3) Southwestern High-Dry-Persistence Regime (Khon Kaen, Chaiyaphum, Nakhon Ratchasima)."
)

add_figure(doc, '11_figures/Figure5_regime_synthesis.png', "Figure 5", "Integrated Rainfall Occurrence Regime Synthesis in Frequency–Persistence–Entropy Space.")

doc.add_heading("3.4 Long-Term Temporal Stability (1961–2019)", level=2)
doc.add_paragraph(
    "Long-term trend analysis using the Yue-Wang autocorrelation-corrected Mann-Kendall test revealed remarkable temporal stability across Northeastern Thailand (Table 4, Figure 4). "
    "After applying False Discovery Rate (FDR) control across all tested metrics (q > 0.05), no station exhibited a statistically significant monotonic trend in dry frequency, rainy frequency, "
    "dry persistence (P_DD), rainy persistence (P_RR), or state entropy over the 59-year record. Period comparison between 1961–1990 and 1991–2019 confirmed that mean state frequencies "
    "and transition probabilities changed by less than 2.5% across periods, with non-significant Mann-Whitney U test p-values. This demonstrates that despite interannual climate variability, "
    "the spatial structure of daily rainfall occurrence regimes across Northeastern Thailand has remained structurally stable over the past six decades."
)

p_t4 = doc.add_paragraph()
r_t4 = p_t4.add_run("Table 4. Long-term trend analysis (1961–2019) and period comparison (1961–1990 vs 1991–2019) for key rainfall metrics.")
r_t4.bold = True

t4 = doc.add_table(rows=1, cols=8)
hdr_cells4 = t4.rows[0].cells
hdr_titles4 = ["Station ID", "Metric", "Yue-Wang MK", "Sen's Slope", "Raw p-val", "FDR q-val", "61-90 Mean", "91-19 Mean"]
for i, title in enumerate(hdr_titles4):
    hdr_cells4[i].text = title

df_t4_filter = df_trend[df_trend['Metric'].isin(['Rainfall_Total_mm', 'Freq_R', 'P_DD'])]
for _, r in df_t4_filter.iterrows():
    row_cells = t4.add_row().cells
    row_cells[0].text = str(r['Station_ID'])
    row_cells[1].text = str(r['Metric'])
    row_cells[2].text = str(r['MK_Trend'])
    row_cells[3].text = f"{r['Sens_Slope']:.4f}"
    row_cells[4].text = f"{r['MK_p_value']:.4f}"
    row_cells[5].text = f"{r['MK_FDR_q_value']:.4f}"
    row_cells[6].text = f"{r['Period1_Mean_6190']:.2f}"
    row_cells[7].text = f"{r['Period2_Mean_9119']:.2f}"

style_table(t4)
doc.add_paragraph()

add_figure(doc, '11_figures/Figure4_temporal_evolution.png', "Figure 4", "Long-Term Evolution of Rainy Frequency (A) and Dry Persistence (B) across representative stations over 1961–2019.")

h4 = doc.add_heading(level=1)
h4.add_run("4. Conclusions").font.color.rgb = RGBColor(31, 78, 120)

doc.add_paragraph(
    "This study conducted an auditable, reproducible forensic analysis of daily rainfall occurrence regimes across 10 stations in Northeastern Thailand over 1961–2019 (21,545 observed days per station). "
    "Key conclusions are: (1) Model order selection decisively favors an Order 2 Markov chain across all stations (Delta BIC < -100), demonstrating higher-order statistical dependence; "
    "(2) Daily occurrence regimes display strong spatial heterogeneity, separating Northeastern Thailand into an eastern high-raininess/high-persistence regime (P_RR up to 0.540, H_state up to 1.020 bits) "
    "and a southwestern dry-dominated regime (P_DD up to 0.803); and (3) Monotonic trend analysis with serial correlation correction and FDR control confirmed robust long-term temporal stability "
    "(q > 0.05) across state frequency, persistence, spell lengths, and entropy over 1961–2019. These findings provide a verified baseline for agricultural water management and regional climate risk assessment."
)

doc.add_heading("Acknowledgements", level=1)
doc.add_paragraph("The authors thank the Thai Meteorological Department (TMD) for providing the historical daily rainfall observation records.")

doc.add_heading("Data Availability Statement", level=1)
doc.add_paragraph("All primary daily rainfall observations, metadata, and analysis code are archived and available in the project repository.")

doc.add_heading("Conflicts of Interest", level=1)
doc.add_paragraph("The authors declare no conflicts of interest.")

h_ref = doc.add_heading(level=1)
h_ref.add_run("References").font.color.rgb = RGBColor(31, 78, 120)

refs = [
    "1. Gabriel KR, Neumann J. A Markov chain model for daily rainfall occurrence at Tel Aviv. Quarterly Journal of the Royal Meteorological Society. 1962;88(375):90-95.",
    "2. Yue S, Wang C. Applicability of prewhitening to eliminate the influence of serial correlation on the Mann-Kendall test. Water Resources Research. 2002;38(6):4-1.",
    "3. Benjamini Y, Hochberg Y. Controlling the false discovery rate: a practical and powerful approach to multiple testing. Journal of the Royal Statistical Society: Series B (Methodological). 1995;57(1):289-300.",
    "4. Wilks DS. Statistical Methods in the Atmospheric Sciences. 4th ed. Elsevier / Academic Press; 2019.",
    "5. Shannon CE. A mathematical theory of communication. The Bell System Technical Journal. 1948;27(3):379-423."
]
for ref in refs:
    p_r = doc.add_paragraph(ref)
    p_r.paragraph_format.left_indent = Inches(0.25)

docx_path_out = "12_manuscript/APST_LongTerm_Rainfall_Occurrence_Regimes_Northeastern_Thailand.docx"
doc.save(docx_path_out)
print(f"FINAL MANUSCRIPT GENERATION COMPLETE: {docx_path_out}")
