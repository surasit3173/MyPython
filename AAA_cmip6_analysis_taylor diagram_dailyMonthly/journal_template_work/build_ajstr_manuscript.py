from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path("C:/MyPython/AAA_cmip6_analysis_taylor diagram_dailyMonthly")
REFERENCE = ROOT / "journal_template_work" / "AJSTR_template_reference.docx"
FINAL = ROOT / "journal_template_work" / "AJSTR_CMIP6_QDM_ready_for_submission.docx"
RESULTS = ROOT / "qdm_p_np_publication_out"
OLD_MS = ROOT / "cmip6bc_q1_editable" / "ID1558_Manuscript_BSJ.docx"
FIG_OLD = ROOT / "cmip6bc_q1_notiers_work" / "cmip6bc" / "out" / "figures"
FIG_NEW = RESULTS / "figures"


def clear_body(doc: Document) -> None:
    body = doc._body._element
    for child in list(body):
        if child.tag.endswith("sectPr"):
            continue
        body.remove(child)


def set_run(run, font="Angsana New", size=12, bold=False, italic=False):
    run.font.name = font
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic


def add_para(doc, text="", font="Angsana New", size=12, bold=False, italic=False, align=None,
             before=0, after=0, first_line=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.0
    if first_line:
        p.paragraph_format.first_line_indent = Inches(0.25)
    if align is not None:
        p.alignment = align
    r = p.add_run(text)
    set_run(r, font=font, size=size, bold=bold, italic=italic)
    return p


def add_mixed_para(doc, label, text, before=0, after=0):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.0
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run(label)
    set_run(r, size=12, bold=True)
    r = p.add_run(text)
    set_run(r, size=12)
    return p


def add_heading(doc, number, title):
    return add_para(doc, f"{number}. {title}", size=12, bold=True,
                    align=WD_ALIGN_PARAGRAPH.LEFT, before=8, after=2)


def add_subheading(doc, number, title):
    return add_para(doc, f"{number} {title}", size=12, bold=True,
                    align=WD_ALIGN_PARAGRAPH.LEFT, before=6, after=1)


def add_caption(doc, kind, number, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.0
    r = p.add_run(f"{kind} {number}.")
    set_run(r, size=12, bold=True)
    r = p.add_run(" " + text)
    set_run(r, size=12)
    return p
    return p


def shade_cell(cell, fill="D9EAF7"):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def set_cell_text(cell, text, bold=False, size=10):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.0
    r = p.add_run(str(text))
    set_run(r, size=size, bold=bold)


def add_table(doc, headers, rows, widths=None, font_size=9):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.autofit = False
    for i, h in enumerate(headers):
        shade_cell(table.rows[0].cells[i])
        set_cell_text(table.rows[0].cells[i], h, bold=True, size=font_size)
    for row in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row):
            set_cell_text(cells[i], value, size=font_size)
    if widths:
        for row in table.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Inches(w)
    return table


def copy_source_tables():
    doc = Document(OLD_MS)
    tables = []
    for table in doc.tables[:2]:
        rows = []
        for row in table.rows:
            rows.append([cell.text.replace("\n", " ").strip() for cell in row.cells])
        tables.append(rows)
    return tables


def fmt(x, nd=2, signed=False):
    if pd.isna(x):
        return "n/a"
    val = float(x)
    s = f"{val:+.{nd}f}" if signed else f"{val:.{nd}f}"
    return s


def method_summary_rows():
    summary = pd.read_csv(RESULTS / "summary.csv")
    metrics = [
        ("Mean absolute PBIAS (%)", "PBIAS", 2, "lower"),
        ("Kolmogorov-Smirnov D", "KS_D", 3, "lower"),
        ("Mean absolute q99 bias (%)", "q99_relbias_pct", 2, "lower"),
        ("Monthly RMSE (mm)", "mRMSE", 2, "lower"),
        ("Monthly KGE", "mKGE", 3, "higher"),
        ("Monthly correlation r", "mr", 3, "higher"),
        ("Monthly climatology r", "clim_r", 3, "higher"),
    ]
    labels = {
        "QDM_NP_annual": "NP annual",
        "QDM_NP_monthly": "NP monthly",
        "QDM_P_annual": "P annual",
        "QDM_P_monthly": "P monthly",
    }
    rows = []
    val = summary[summary.period == "validation"]
    for label, metric, nd, direction in metrics:
        d = val[val.metric == metric].set_index("method")
        values = {m: float(d.loc[m, "corrected_mean"]) for m in labels}
        raw = float(d.iloc[0]["raw_mean"])
        best_method = min(values, key=lambda k: abs(values[k]) if metric in {"PBIAS", "q99_relbias_pct"} or direction == "lower" else -values[k])
        rows.append([
            label,
            fmt(raw, nd),
            fmt(values["QDM_NP_annual"], nd),
            fmt(values["QDM_NP_monthly"], nd),
            fmt(values["QDM_P_annual"], nd),
            fmt(values["QDM_P_monthly"], nd),
            labels[best_method],
        ])
    return rows


def parametric_rows():
    diag = pd.read_csv(RESULTS / "fit_diagnostics.csv")
    pdiag = diag[(diag.family == "parametric") & (diag.period == "validation")]
    pdiag = pdiag.drop_duplicates(["method", "model", "station", "group"])
    rows = []
    for method, label in [("QDM_P_annual", "P annual"), ("QDM_P_monthly", "P monthly")]:
        d = pdiag[pdiag.method == method]
        obs_top = d["obs_dist"].value_counts().head(3)
        mod_top = d["mod_dist"].value_counts().head(3)
        cap = int(diag[(diag.method == method) & (diag.period == "validation")]["n_output_capped"].sum())
        clipped = int(diag[(diag.method == method) & (diag.period == "validation")]["n_delta_clipped_low"].sum() +
                      diag[(diag.method == method) & (diag.period == "validation")]["n_delta_clipped_high"].sum())
        rows.append([
            label,
            "; ".join(f"{k} ({v})" for k, v in obs_top.items()),
            "; ".join(f"{k} ({v})" for k, v in mod_top.items()),
            str(cap),
            str(clipped),
        ])
    return rows


def add_figure(doc, path, number, caption):
    add_caption(doc, "Figure", number, caption)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run()
    r.add_picture(str(path), width=Inches(6.25))


def build():
    shutil.copyfile(REFERENCE, FINAL)
    doc = Document(FINAL)
    clear_body(doc)

    sec = doc.sections[0]
    sec.page_width = Inches(8.27)
    sec.page_height = Inches(11.69)
    sec.left_margin = Inches(0.79)
    sec.right_margin = Inches(0.79)
    sec.top_margin = Inches(0.98)
    sec.bottom_margin = Inches(0.89)
    sec.different_first_page_header_footer = True

    styles = doc.styles
    styles["Normal"].font.name = "Angsana New"
    styles["Normal"]._element.rPr.rFonts.set(qn("w:eastAsia"), "Angsana New")
    styles["Normal"].font.size = Pt(12)

    add_para(doc, "Article", size=12, italic=True, before=8, after=4)
    add_para(
        doc,
        "Parametric and Non-Parametric Quantile Delta Mapping for CMIP6 Daily Rainfall Bias Correction under Independent Temporal Validation in Prachuap Khiri Khan, Thailand",
        font="Palatino Linotype",
        size=18,
        bold=True,
        before=0,
        after=6,
    )
    add_para(doc, "Surasit Punyawansiri1*", size=12, bold=True, after=2)
    add_para(doc, "1 Office of Water Management and Hydrology, Royal Irrigation Department, Dusit, Bangkok 10300, Thailand", size=12, after=2)
    add_para(doc, "* Correspondence: Surasit.irri@gmail.com", size=12, after=8)

    abstract = (
        "Bias correction is widely applied to global climate model precipitation before hydrological and climate-impact use, yet method performance is often judged within the same period used for calibration. This study compared parametric and non-parametric Quantile Delta Mapping (QDM) for daily CMIP6 rainfall in Prachuap Khiri Khan Province, Thailand, using a strict split-sample design. Daily observations from 12 rain-gauge stations and historical simulations from five CMIP6 models during 1981-2014 were divided into calibration (1981-2000) and independent validation (2001-2014) periods. Four QDM variants were evaluated: empirical non-parametric annual fitting, empirical non-parametric monthly fitting, parametric annual fitting, and parametric monthly fitting with Akaike Information Criterion selection among gamma, generalized extreme value, Weibull, lognormal, and Pearson type III distributions. The non-parametric monthly method performed best overall in validation, reducing monthly RMSE from 116.20 to 109.38 mm, increasing monthly Kling-Gupta efficiency from 0.229 to 0.332, and improving monthly correlation in 80.0% of station-model combinations. Non-parametric annual QDM gave the lowest upper-tail bias, reducing mean absolute q99 bias from 52.98% to 24.79%. All QDM variants substantially improved distributional agreement, with Kolmogorov-Smirnov D reduced from 0.201 to 0.102-0.123. The results show that monthly empirical QDM is the most robust option for this monsoon-influenced coastal province, while parametric QDM requires explicit tail safeguards."
    )
    add_mixed_para(doc, "Abstract: ", abstract, before=6, after=4)
    add_mixed_para(
        doc,
        "Keywords: ",
        "bias correction; quantile delta mapping; CMIP6; rainfall; independent validation; Thailand; parametric distribution; empirical CDF",
        after=8,
    )

    add_heading(doc, "1", "Introduction")
    for text in [
        "Daily rainfall is a controlling variable for water resources planning, flood and drought risk assessment, agricultural scheduling, and climate-change adaptation in Southeast Asia. Global climate models from the Coupled Model Intercomparison Project Phase 6 (CMIP6) provide physically based simulations for these applications, but their precipitation output contains systematic biases arising from spatial resolution, parameterized convection, and regional circulation errors [1,2]. These biases are particularly important in Thailand, where monsoon seasonality, orographic gradients, and coastal rainfall mechanisms combine to produce strongly skewed and intermittent daily rainfall distributions.",
        "Quantile mapping and its extensions are among the most widely used statistical bias-correction methods for climate-impact studies [3,4]. Quantile Delta Mapping (QDM) is attractive because it adjusts distributional biases while preserving model-projected relative changes at a given quantile [5]. For precipitation, however, QDM must handle zero inflation, dry-day frequency, extreme upper tails, and sampling instability. These issues are not merely computational: they affect whether corrected data are scientifically defensible for hydrological design and climate-risk interpretation.",
        "A key weakness in many bias-correction applications is the absence of an independent temporal validation period. When the same historical observations are used both to estimate and to evaluate the transfer function, reported performance can be overly optimistic. This study therefore evaluates QDM under a strict fit-freeze-apply protocol: all thresholds, empirical quantiles, and parametric distributions are estimated from 1981-2000 only and then applied to 2001-2014 without re-estimating any observation-dependent quantity.",
        "The objective is to compare parametric and non-parametric QDM, each implemented with annual pooled and month-wise calibration, for CMIP6 daily rainfall in Prachuap Khiri Khan Province. The analysis asks which method gives the most transferable correction during independent validation and which performance dimensions improve or deteriorate after correction.",
    ]:
        add_para(doc, text, first_line=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    add_heading(doc, "2", "Materials and Methods")
    add_subheading(doc, "2.1", "Study area and data")
    for text in [
        "Prachuap Khiri Khan Province is a narrow coastal province on the western Gulf of Thailand. Its rainfall regime is shaped by maritime moisture, monsoon variability, and topographic contrast between the coastal plain and the Tenasserim Range. The study used daily rainfall observations from 12 stations for 1981-2014 and historical daily precipitation from five CMIP6 models: ACCESS-ESM1-5, CanESM5, CESM2, EC-Earth3, and MIROC6.",
        "Input files were screened for declared missing values before any negative-value handling. Small negative residuals within the configured tolerance were clipped to zero, whereas deeper negative values were treated as missing. Model precipitation units were checked and converted to millimetres per day where needed. Calendars were paired by actual dates rather than forcing every model to share the same number of rows.",
    ]:
        add_para(doc, text, first_line=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    station_table, model_table = copy_source_tables()
    add_caption(doc, "Table", 1, "Rain-gauge station characteristics used for the analysis.")
    add_table(doc, station_table[0], station_table[1:], widths=[0.60, 0.55, 0.60, 0.55, 0.65, 0.83, 0.65, 0.83, 0.55], font_size=8)
    add_para(doc, "Note: n/a indicates metadata not available in the station file; the rainfall record itself was retained when quality-control criteria were satisfied.", size=10, italic=True, after=4)

    add_caption(doc, "Table", 2, "CMIP6 historical simulations included in the study.")
    add_table(doc, model_table[0], model_table[1:], widths=[0.95, 1.18, 0.75, 0.60, 0.50, 0.80, 0.82], font_size=8)
    add_para(doc, "Note: Distinct daily values summarize effective spatial information across the 12 stations after station extraction.", size=10, italic=True, after=4)

    add_subheading(doc, "2.2", "Split-sample QDM design")
    for text in [
        "The analysis followed a calibration-validation split. The transfer function was estimated from 1981-2000 and then frozen before application to the independent validation period 2001-2014. Observations from 2001-2014 were used only for evaluation.",
        "Wet-day frequency adaptation was applied before QDM. The observed wet-day threshold was 1.0 mm day-1. For each model, station, and calibration group, a model-side wet threshold was selected so that the calibration wet-day frequency matched the observed calibration wet-day frequency. That threshold was then frozen and reused in validation.",
        "For precipitation, QDM was implemented in multiplicative form. For a target model value x, the non-exceedance probability tau was obtained from the target-period model distribution. The corrected value was calculated as Fobs,h-1(tau) multiplied by x/Fmod,h-1(tau), with delta ratios bounded using the configured limits. This preserves the split-sample protocol because target-period quantiles are model-only quantities.",
    ]:
        add_para(doc, text, first_line=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    add_subheading(doc, "2.3", "Parametric and non-parametric variants")
    for text in [
        "Four variants were evaluated. QDM_NP_annual used empirical cumulative distribution functions from all calendar months pooled together. QDM_NP_monthly used empirical cumulative distribution functions fitted separately for each calendar month. QDM_P_annual and QDM_P_monthly used parametric distributions selected by minimum AIC from gamma, generalized extreme value, Weibull, lognormal, and Pearson type III candidates. Kolmogorov-Smirnov statistics were recorded as fit diagnostics.",
        "Parametric upper tails were numerically constrained to prevent implausible extrapolated rainfall from dominating downstream metrics. The cap was recorded for every station, model, method, and period in the diagnostic table. This safeguard is reported explicitly because unconstrained parametric tails can generate physically unrealistic daily rainfall in finite samples.",
    ]:
        add_para(doc, text, first_line=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    add_subheading(doc, "2.4", "Evaluation metrics")
    add_para(doc, "Performance was assessed over calibration and independent validation periods using systematic bias, distributional fidelity, upper-tail relative bias, monthly RMSE and MAE, Nash-Sutcliffe efficiency, Kling-Gupta efficiency, monthly correlation, monthly climatology correlation, and annual correlation. The primary comparison in this manuscript emphasizes the independent validation period.", first_line=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    add_figure(doc, FIG_OLD / "Figure2_framework.png", 1, "Calibration-independent validation framework. Transfer functions were estimated only from 1981-2000 and applied to 2001-2014 without using validation-period observations in the correction step.")

    add_heading(doc, "3", "Results and Discussion")
    add_subheading(doc, "3.1", "Observed rainfall and model context")
    add_para(doc, "The station network captured a range of coastal rainfall regimes, with annual rainfall ranging from 944 to 1,376 mm and maximum daily rainfall ranging from 54.2 to 298.5 mm day-1. All stations had complete daily records in the analysis file. The CMIP6 models differed in calendar type, grid resolution, and effective spatial information across the province, reinforcing the need for station-level paired evaluation rather than a single regional aggregate.", first_line=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    add_figure(doc, FIG_OLD / "Figure3_observed_periods.png", 2, "Observed rainfall characteristics in the calibration and validation periods, including monthly climatology, annual rainfall, and wet-day frequency.")

    add_subheading(doc, "3.2", "Independent validation of QDM variants")
    add_para(doc, "Table 3 shows that all QDM variants improved distributional fidelity during independent validation. The mean Kolmogorov-Smirnov statistic decreased from 0.201 in raw simulations to 0.102-0.123 after correction. The strongest overall validation performance was obtained by the monthly non-parametric method: QDM_NP_monthly reduced monthly RMSE from 116.20 to 109.38 mm, reduced monthly MAE from 78.15 to 70.02 mm, increased monthly KGE from 0.229 to 0.332, and improved monthly correlation in 48 of 60 model-station combinations.", first_line=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    add_para(doc, "Upper-tail behaviour showed a slightly different ranking. QDM_NP_annual produced the lowest mean absolute q99 relative bias, reducing it from 52.98% to 24.79%, whereas QDM_NP_monthly reduced it to 27.69%. Thus, the monthly empirical method gave the best balance of temporal aggregation metrics and seasonal structure, while the annual empirical method was marginally stronger for the highest reported quantile.", first_line=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    add_caption(doc, "Table", 3, "Independent validation performance of raw simulations and four QDM variants across 60 model-station combinations.")
    add_table(doc, ["Metric", "Raw", "NP annual", "NP monthly", "P annual", "P monthly", "Best"], method_summary_rows(),
              widths=[1.45, 0.62, 0.75, 0.78, 0.68, 0.72, 0.78], font_size=8)
    add_para(doc, "Note: PBIAS and q99 bias are summarized as absolute values. For RMSE, MAE, KS D, PBIAS, and q99 bias, lower is better; for KGE and correlation metrics, higher is better.", size=10, italic=True, after=4)

    add_figure(doc, FIG_NEW / "Figure_QDM_method_comparison.png", 3, "Validation distributions of selected metrics for raw CMIP6 simulations and the four QDM variants.")
    add_figure(doc, FIG_NEW / "Figure_QDM_metric_heatmap.png", 4, "Percentage of model-station combinations improved over raw simulations during independent validation.")

    add_subheading(doc, "3.3", "Parametric distribution selection and tail diagnostics")
    add_para(doc, "Parametric QDM was feasible but less stable than empirical QDM. The generalized extreme value and lognormal distributions dominated the AIC-selected fits. For validation blocks, QDM_P_annual selected generalized extreme value distributions for 57 of 60 model-side fits, whereas QDM_P_monthly selected generalized extreme value distributions for 460 of 620 model-side monthly fits. The observed-side fits were mostly lognormal and generalized extreme value. These patterns are consistent with the skewed and heavy-tailed character of daily rainfall.", first_line=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    add_para(doc, "The diagnostic record also shows why parametric QDM must be reported with tail safeguards. During validation, P annual capped 3 output values, whereas P monthly capped 166 values and clipped 89 delta ratios. These counts were small relative to the full daily sample, but they are scientifically important because a few extrapolated parametric values can dominate extreme-value and histogram-based metrics.", first_line=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    add_caption(doc, "Table", 4, "Parametric fit diagnostics and numerical safeguards during independent validation.")
    add_table(doc, ["Method", "Observed-side distributions", "Model-side distributions", "Capped outputs", "Clipped delta ratios"], parametric_rows(),
              widths=[0.80, 1.75, 1.75, 0.72, 0.82], font_size=8)

    add_subheading(doc, "3.4", "Implications for climate-data preparation")
    for text in [
        "The results support three practical conclusions. First, distributional improvement does not imply recovery of event timing. Even the best method cannot create temporal correspondence that is absent from the free-running climate simulations. Second, seasonal calibration matters in this monsoon-influenced province: monthly empirical QDM improved monthly climatology correlation in 59 of 60 combinations and gave the best overall error-based performance. Third, parametric QDM should not be used as an automatic replacement for empirical QDM unless distribution choice, goodness of fit, and upper-tail safeguards are fully documented.",
        "For applications requiring rainfall frequency, intensity distributions, and upper-tail quantiles, the corrected series are more defensible than raw CMIP6 outputs. For applications requiring event-by-event timing, such as direct daily flood simulation without weather sequencing, the corrected series should be interpreted with caution.",
    ]:
        add_para(doc, text, first_line=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    add_heading(doc, "4", "Conclusions")
    for text in [
        "This study compared parametric and non-parametric QDM for CMIP6 daily rainfall using a strict independent temporal validation design in Prachuap Khiri Khan Province, Thailand. The principal conclusion is that empirical monthly QDM provided the most robust overall performance, improving monthly RMSE, MAE, KGE, monthly correlation, and monthly climatology correlation more consistently than the other variants.",
        "All QDM variants improved distributional agreement relative to raw simulations, but the highest-tail metric favoured the empirical annual method. Parametric QDM was useful as a comparative method but required explicit upper-tail safeguards and transparent diagnostic reporting. The split-sample framework is therefore essential: it separates construction-dependent properties from transferable validation skill and gives a more realistic basis for selecting corrected CMIP6 rainfall data for impact studies.",
    ]:
        add_para(doc, text, first_line=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY)

    add_heading(doc, "5", "Acknowledgements")
    add_para(doc, "The author thanks the data providers and institutions responsible for the observed rainfall and CMIP6 model simulations used in this study.", align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    add_mixed_para(doc, "Author Contributions: ", "S.P. conceived the study, prepared the data, developed the analysis workflow, interpreted the results, and wrote the manuscript.")
    add_mixed_para(doc, "Funding: ", "This research received no external funding.")
    add_mixed_para(doc, "Data Availability Statement: ", "The processed tables, diagnostic files, corrected series, and figure files generated by the workflow are available in the project output directory. Access to original station data is subject to the terms of the data provider.")
    add_mixed_para(doc, "Conflicts of Interest: ", "The author declares no conflict of interest.")

    add_para(doc, "References", size=12, bold=True,
             align=WD_ALIGN_PARAGRAPH.LEFT, before=8, after=2)
    refs = [
        "Eyring, V.; Bony, S.; Meehl, G.A.; Senior, C.A.; Stevens, B.; Stouffer, R.J.; Taylor, K.E. Overview of the Coupled Model Intercomparison Project Phase 6 (CMIP6) experimental design and organization. Geosci. Model Dev. 2016, 9, 1937-1958.",
        "Tebaldi, C.; Knutti, R. The use of the multi-model ensemble in probabilistic climate projections. Philos. Trans. R. Soc. A 2007, 365, 2053-2075.",
        "Maraun, D. Bias correction, quantile mapping, and downscaling: revisiting the inflation issue. J. Clim. 2013, 26, 2137-2143.",
        "Themeßl, M.J.; Gobiet, A.; Leuprecht, A. Empirical-statistical downscaling and error correction of daily precipitation from regional climate models. Int. J. Climatol. 2011, 31, 1530-1544.",
        "Cannon, A.J.; Sobie, S.R.; Murdock, T.Q. Bias correction of GCM precipitation by quantile mapping: how well do methods preserve changes in quantiles and extremes? J. Clim. 2015, 28, 6938-6959.",
        "Gudmundsson, L.; Bremnes, J.B.; Haugen, J.E.; Engen-Skaugen, T. Technical note: downscaling RCM precipitation to the station scale using statistical transformations. Hydrol. Earth Syst. Sci. 2012, 16, 3383-3390.",
        "Piani, C.; Haerter, J.O.; Coppola, E. Statistical bias correction for daily precipitation in regional climate models over Europe. Theor. Appl. Climatol. 2010, 99, 187-192.",
        "Switanek, M.B.; Troch, P.A.; Castro, C.L.; Leuprecht, A.; Chang, H.I.; Mukherjee, R.; Demaria, E.M.C. Scaled distribution mapping: a bias correction method that preserves raw climate model projected changes. Hydrol. Earth Syst. Sci. 2017, 21, 2649-2666.",
        "Perkins, S.E.; Pitman, A.J.; Holbrook, N.J.; McAneney, J. Evaluation of the AR4 climate models' simulated daily maximum temperature, minimum temperature, and precipitation over Australia using probability density functions. J. Clim. 2007, 20, 4356-4376.",
        "Murphy, A.H. Skill scores based on the mean square error and their relationships to the correlation coefficient. Mon. Weather Rev. 1988, 116, 2417-2424.",
        "Benjamini, Y.; Hochberg, Y. Controlling the false discovery rate: a practical and powerful approach to multiple testing. J. R. Stat. Soc. Ser. B 1995, 57, 289-300.",
        "Pettitt, A.N. A non-parametric approach to the change-point problem. Appl. Stat. 1979, 28, 126-135.",
        "Swart, N.C.; Cole, J.N.S.; Kharin, V.V.; Lazare, M.; Scinocca, J.F.; Gillett, N.P.; Anstey, J.; Arora, V.; Christian, J.R.; Jiao, Y.; et al. The Canadian Earth System Model version 5 (CanESM5.0.3). Geosci. Model Dev. 2019, 12, 4823-4873.",
        "Danabasoglu, G.; Lamarque, J.F.; Bacmeister, J.; Bailey, D.A.; DuVivier, A.K.; Edwards, J.; Emmons, L.K.; Fasullo, J.; Garcia, R.; Gettelman, A.; et al. The Community Earth System Model Version 2 (CESM2). J. Adv. Model. Earth Syst. 2020, 12, e2019MS001916.",
        "Döscher, R.; Acosta, M.; Alessandri, A.; Anthoni, P.; Arneth, A.; Arsouze, T.; Bergmann, T.; Bernadello, R.; Boussetta, S.; Caron, L.P.; et al. The EC-Earth3 Earth system model for the Coupled Model Intercomparison Project 6. Geosci. Model Dev. 2022, 15, 2973-3020.",
        "Tatebe, H.; Ogura, T.; Nitta, T.; Komuro, Y.; Ogochi, K.; Takemura, T.; Sudo, K.; Sekiguchi, M.; Abe, M.; Saito, F.; et al. Description and basic evaluation of simulated mean state, internal variability, and climate sensitivity in MIROC6. Geosci. Model Dev. 2019, 12, 2727-2765.",
        "Ziehn, T.; Chamberlain, M.A.; Law, R.M.; Lenton, A.; Bodman, R.W.; Dix, M.; Stevens, L.; Wang, Y.P.; Srbinovsky, J. The Australian Earth System Model: ACCESS-ESM1.5. J. South. Hemisph. Earth Syst. Sci. 2020, 70, 193-214.",
    ]
    for i, ref in enumerate(refs, 1):
        add_para(doc, f"{i}. {ref}", size=11, align=WD_ALIGN_PARAGRAPH.JUSTIFY, after=1)

    add_para(doc, "Reviewers suggestion", size=12, bold=True, before=8, after=2)
    add_para(doc, "Reviewer names, affiliations, and e-mail addresses should be entered by the corresponding author in the online submission system.", size=11, italic=True)

    doc.save(FINAL)
    print(FINAL)


if __name__ == "__main__":
    build()
