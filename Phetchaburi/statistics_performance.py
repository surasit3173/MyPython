"""
===============================================================================
  Descriptive Statistics & Model Performance Metrics
  Observed vs Raw CMIP6 vs Bias-Corrected (QDM)
  Daily & Monthly Scale — Export to Excel
  มาตรฐานวารสาร Q2-Q3 / TCI1
-------------------------------------------------------------------------------
  Input (ในโฟลเดอร์เดียวกับ script):
    • Observed     → ชื่อไฟล์มีคำว่า  "Observed"  (case-insensitive)
    • Raw CMIP6    → ชื่อไฟล์ขึ้นต้นด้วย  "pr"
    • BC / QDM     → ชื่อไฟล์ขึ้นต้นด้วย  "bc"
  Output:
    • Output_Statistics_<obs_basename>.xlsx  (ในโฟลเดอร์เดียวกัน)

  อ้างอิง:
    Nash & Sutcliffe (1970) J. Hydrol. 10:282–290
    Gupta et al. (2009) J. Hydrol. 377:80–91  [KGE]
    Cannon et al. (2015) J. Climate 28:6938–6959  [QDM]
    Teutschbein & Seibert (2012) Hydrol. Earth Syst. Sci. 16:3391–3314
===============================================================================
"""

import os, sys, math, warnings
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats as sps
from openpyxl import Workbook
from openpyxl.styles import (
    PatternFill, Font, Alignment, Border, Side, GradientFill
)
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import ColorScaleRule, DataBarRule
from openpyxl.styles.numbers import FORMAT_NUMBER_00

warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════════════════════════════════════
# 0.  COLOUR PALETTE & STYLE HELPERS
# ═══════════════════════════════════════════════════════════════════════════
# Excel hex colours (no '#')
XL = dict(
    hdr_dark   = "1F4E79",   # deep blue   – main header
    hdr_mid    = "2E75B6",   # medium blue – sub-header
    hdr_obs    = "1B5E20",   # dark green  – Observed header
    hdr_raw    = "B71C1C",   # dark red    – Raw CMIP6 header
    hdr_bc     = "0D47A1",   # dark blue   – QDM header
    row_obs    = "E8F5E9",   # light green
    row_raw    = "FFEBEE",   # light red
    row_bc     = "E3F2FD",   # light blue
    row_alt    = "F5F5F5",   # light grey (alternating)
    best_fill  = "FFF9C4",   # yellow highlight – best value
    best_font  = "E65100",   # orange bold – best cell font
    improve    = "C8E6C9",   # green – improvement row
    warn       = "FFCCBC",   # orange – degraded
    white      = "FFFFFF",
    title_bg   = "13293D",   # very dark navy – sheet title
    section    = "37474F",   # dark grey – section header
    note_bg    = "ECEFF1",   # very light blue-grey
    font_white = "FFFFFF",
    font_dark  = "1A1A1A",
    font_grey  = "616161",
)

THIN  = Side(style="thin",   color="BDBDBD")
MED   = Side(style="medium", color="9E9E9E")
THICK = Side(style="medium", color="1F4E79")

def thin_b():  return Border(left=THIN,  right=THIN,  top=THIN,  bottom=THIN)
def thick_b(): return Border(left=THICK, right=THICK, top=THICK, bottom=THICK)
def med_b():   return Border(left=MED,   right=MED,   top=MED,   bottom=MED)

def fill(hex_color):
    return PatternFill("solid", fgColor=hex_color)

def sc(ws, r, c, value=None, bold=False, italic=False,
       fc=None, bg=None, align="center", wrap=True,
       border=None, sz=10, num_fmt=None, font_name="Calibri"):
    """Style cell helper."""
    cell = ws.cell(row=r, column=c)
    if value is not None:
        cell.value = value
    cell.font = Font(
        bold=bold, italic=italic,
        color=fc if fc else XL["font_dark"],
        name=font_name, size=sz
    )
    cell.alignment = Alignment(
        horizontal=align, vertical="center", wrap_text=wrap
    )
    if bg:
        cell.fill = fill(bg)
    if border is not None:
        cell.border = border
    if num_fmt:
        cell.number_format = num_fmt
    return cell

def set_col_width(ws, col, width):
    ws.column_dimensions[get_column_letter(col)].width = width

def merge_sc(ws, r, c1, c2, value, bold=True, fc=None, bg=None,
             align="center", sz=10, italic=False):
    ws.merge_cells(
        start_row=r, start_column=c1, end_row=r, end_column=c2
    )
    cell = sc(ws, r, c1, value, bold=bold, fc=fc, bg=bg,
               align=align, sz=sz, italic=italic)
    return cell

# ═══════════════════════════════════════════════════════════════════════════
# 1.  FILE DISCOVERY
# ═══════════════════════════════════════════════════════════════════════════

def find_csv_files(folder: str):
    all_csv = list(Path(folder).glob("*.csv"))
    obs = [f for f in all_csv if "observed" in f.name.lower()]
    raw = [f for f in all_csv if f.name.lower().startswith("pr")]
    bc  = [f for f in all_csv if f.name.lower().startswith("bc")]

    def pick(lst, label):
        if not lst:
            return None
        if len(lst) > 1:
            print(f"  ⚠  {label}: พบหลายไฟล์ – ใช้ {lst[0].name}")
        return str(lst[0])

    return pick(obs, "Observed"), pick(raw, "Raw CMIP6"), pick(bc, "BC/QDM")

# ═══════════════════════════════════════════════════════════════════════════
# 2.  DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════

MISSING_FLAGS = [-99, -999, -9999, -9.99e+20, 9.99e+20, 1e+20, -1e+20]

def load_daily(csv_path: str, label: str):
    """Return daily DataFrame: index = DatetimeIndex, columns = station IDs."""
    if csv_path is None or not os.path.isfile(csv_path):
        print(f"  ✗  ไม่พบไฟล์ {label}")
        return None, []
    df = pd.read_csv(csv_path)
    for mv in MISSING_FLAGS:
        df.replace(mv, np.nan, inplace=True)
    num_cols = df.select_dtypes(include=[np.number]).columns
    df[num_cols] = df[num_cols].where(df[num_cols] >= 0)
    stns = [c for c in df.columns if c not in ("YEAR", "MONTH", "DAY")]
    try:
        df["date"] = pd.to_datetime(
            {"year": df["YEAR"], "month": df["MONTH"], "day": df["DAY"]}
        )
        df = df.set_index("date")[stns]
    except Exception:
        df.index = range(len(df))
        df = df[stns]
    print(f"    {label:15s}: {len(df):,} rows × {len(stns)} stations  "
          f"({df.index[0]} → {df.index[-1]})" if hasattr(df.index[0], 'year')
          else f"    {label:15s}: {len(df):,} rows × {len(stns)} stations")
    return df, stns


def to_monthly(daily_df: pd.DataFrame) -> pd.DataFrame:
    if daily_df is None:
        return None
    return daily_df.resample("MS").apply(
        lambda g: g.sum(min_count=int(0.8 * len(g)))
    )

# ═══════════════════════════════════════════════════════════════════════════
# 3.  DESCRIPTIVE STATISTICS
# ═══════════════════════════════════════════════════════════════════════════

WET_THRESHOLD = 1.0   # mm/day – standard WMO threshold

def wet_day_freq(series: np.ndarray) -> float:
    v = series[~np.isnan(series)]
    if len(v) == 0:
        return np.nan
    return float(np.sum(v >= WET_THRESHOLD) / len(v) * 100)

def descriptive_stats(series: np.ndarray, label: str, stn: str,
                      scale: str = "Daily") -> dict:
    v = series[~np.isnan(series)]
    if len(v) < 2:
        return {}
    mean_   = float(np.mean(v))
    std_    = float(np.std(v, ddof=1))
    cv_     = std_ / mean_ * 100 if mean_ != 0 else np.nan
    skew_   = float(sps.skew(v))
    kurt_   = float(sps.kurtosis(v, fisher=True))
    p25_    = float(np.percentile(v, 25))
    p50_    = float(np.percentile(v, 50))
    p75_    = float(np.percentile(v, 75))
    p95_    = float(np.percentile(v, 95))
    p99_    = float(np.percentile(v, 99))
    max_    = float(np.max(v))
    wdf_    = wet_day_freq(v) if scale == "Daily" else np.nan
    return {
        "Dataset": label, "Station": stn, "Scale": scale,
        "N":        len(v),
        "Mean":     mean_,
        "Std":      std_,
        "CV (%)":   cv_,
        "Skewness": skew_,
        "Kurtosis": kurt_,
        "P25":      p25_,
        "P50 (Median)": p50_,
        "P75":      p75_,
        "P95":      p95_,
        "P99":      p99_,
        "Max":      max_,
        "Wet-day freq (%)": wdf_,
    }

# ═══════════════════════════════════════════════════════════════════════════
# 4.  PERFORMANCE METRICS
# ═══════════════════════════════════════════════════════════════════════════

def compute_metrics(obs: np.ndarray, sim: np.ndarray,
                    label: str, stn: str, scale: str) -> dict:
    """
    Compute RMSE, MAE, NSE, KGE, r, MBE, Pbias on paired non-NaN values.
    NSE: Nash & Sutcliffe (1970)
    KGE: Gupta et al. (2009)
    """
    mask = ~np.isnan(obs) & ~np.isnan(sim)
    o, s = obs[mask].astype(float), sim[mask].astype(float)
    n = len(o)
    if n < 5:
        return {k: np.nan for k in
                ["Dataset","Station","Scale","N_pairs",
                 "RMSE","MAE","MBE","Pbias (%)",
                 "r (Pearson)","NSE","KGE","KGE_r","KGE_alpha","KGE_beta"]}

    residuals = s - o
    rmse_  = float(np.sqrt(np.mean(residuals**2)))
    mae_   = float(np.mean(np.abs(residuals)))
    mbe_   = float(np.mean(residuals))
    pbias_ = 100 * np.sum(residuals) / np.sum(o) if np.sum(o) != 0 else np.nan

    # Pearson r
    r_     = float(np.corrcoef(o, s)[0, 1])

    # NSE
    nse_   = 1 - np.sum(residuals**2) / np.sum((o - np.mean(o))**2) \
             if np.sum((o - np.mean(o))**2) != 0 else np.nan

    # KGE (Gupta et al. 2009)
    alpha_ = np.std(s, ddof=1) / np.std(o, ddof=1) \
             if np.std(o, ddof=1) != 0 else np.nan
    beta_  = np.mean(s) / np.mean(o) if np.mean(o) != 0 else np.nan
    kge_   = 1 - math.sqrt((r_-1)**2 + (alpha_-1)**2 + (beta_-1)**2) \
             if not (np.isnan(alpha_) or np.isnan(beta_)) else np.nan

    return {
        "Dataset":     label,
        "Station":     stn,
        "Scale":       scale,
        "N_pairs":     n,
        "RMSE":        round(rmse_,  3),
        "MAE":         round(mae_,   3),
        "MBE":         round(mbe_,   3),
        "Pbias (%)":   round(pbias_, 2),
        "r (Pearson)": round(r_,     4),
        "NSE":         round(float(nse_),   4),
        "KGE":         round(float(kge_),   4),
        "KGE_r":       round(r_,            4),
        "KGE_alpha":   round(float(alpha_), 4),
        "KGE_beta":    round(float(beta_),  4),
    }

# ═══════════════════════════════════════════════════════════════════════════
# 5.  ALIGN TWO SERIES ON COMMON DATES
# ═══════════════════════════════════════════════════════════════════════════

def align(df1: pd.DataFrame, df2: pd.DataFrame, stn: str):
    """Return paired numpy arrays for a given station on common index."""
    if df1 is None or df2 is None:
        return np.array([]), np.array([])
    if stn not in df1.columns or stn not in df2.columns:
        return np.array([]), np.array([])
    common = df1.index.intersection(df2.index)
    if len(common) == 0:
        return np.array([]), np.array([])
    return df1.loc[common, stn].values, df2.loc[common, stn].values

# ═══════════════════════════════════════════════════════════════════════════
# 6.  EXCEL WRITER
# ═══════════════════════════════════════════════════════════════════════════

METRIC_COLS   = ["RMSE","MAE","MBE","Pbias (%)","r (Pearson)","NSE","KGE",
                 "KGE_r","KGE_alpha","KGE_beta"]
# For these metrics: lower abs value = better
LOWER_BETTER  = {"RMSE","MAE","MBE","Pbias (%)"}
# For these: higher = better
HIGHER_BETTER = {"r (Pearson)","NSE","KGE"}

DESC_COLS = ["N","Mean","Std","CV (%)","Skewness","Kurtosis",
             "P25","P50 (Median)","P75","P95","P99","Max",
             "Wet-day freq (%)"]


def write_desc_sheet(wb: Workbook, desc_rows: list, scale: str):
    """Write one descriptive-statistics sheet (Daily or Monthly)."""
    ws = wb.create_sheet(f"Descriptive Stats ({scale})")
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "D5"

    # ── Title ──────────────────────────────────────────────────────────
    n_cols = 3 + len(DESC_COLS)
    merge_sc(ws, 1, 1, n_cols,
             f"Descriptive Statistics of Rainfall — {scale} Scale  "
             f"(Observed vs Raw CMIP6 vs Bias-Corrected / QDM)",
             bold=True, fc=XL["font_white"], bg=XL["title_bg"], sz=12)
    ws.row_dimensions[1].height = 26

    merge_sc(ws, 2, 1, n_cols,
             f"Wet-day threshold: ≥ {WET_THRESHOLD} mm day⁻¹  │  "
             "CV = Coefficient of Variation  │  "
             "P25/P50/P75/P95/P99 = Percentiles  │  "
             "All rainfall values in mm",
             bold=False, italic=True,
             fc=XL["font_white"], bg=XL["hdr_mid"], sz=8.5)
    ws.row_dimensions[2].height = 16

    # ── Column headers ─────────────────────────────────────────────────
    header_row = ["Dataset", "Station", "Scale"] + DESC_COLS
    for ci, h in enumerate(header_row, 1):
        sc(ws, 4, ci, h, bold=True,
           fc=XL["font_white"], bg=XL["hdr_dark"],
           border=thin_b(), sz=9, wrap=True)
    ws.row_dimensions[4].height = 36

    # ── Data rows ──────────────────────────────────────────────────────
    dataset_bg = {
        "Observed":         XL["row_obs"],
        "Raw CMIP6":        XL["row_raw"],
        "Bias-Corrected":   XL["row_bc"],
    }
    dataset_fc = {
        "Observed":         XL["hdr_obs"],
        "Raw CMIP6":        XL["hdr_raw"],
        "Bias-Corrected":   XL["hdr_bc"],
    }

    prev_stn = None
    for ri, row in enumerate(desc_rows, 5):
        ds    = row.get("Dataset", "")
        stn   = row.get("Station", "")
        bg    = dataset_bg.get(ds, XL["white"])
        fc_ds = dataset_fc.get(ds, XL["font_dark"])

        # separator between stations
        if stn != prev_stn and prev_stn is not None:
            ws.row_dimensions[ri-1].height = 4

        for ci, key in enumerate(header_row, 1):
            val = row.get(key, "")
            if isinstance(val, float) and np.isnan(val):
                val = "—"
            elif isinstance(val, float):
                val = round(val, 2)
            cell = sc(ws, ri, ci, val,
                      bg=bg, border=thin_b(), sz=9,
                      align="left" if ci <= 3 else "center")
            if ci == 1:   # Dataset label
                cell.font = Font(bold=True, color=fc_ds,
                                 name="Calibri", size=9)
        ws.row_dimensions[ri].height = 16
        prev_stn = stn

    # ── Column widths ──────────────────────────────────────────────────
    widths = [16, 9, 8] + [10]*len(DESC_COLS)
    for ci, w in enumerate(widths, 1):
        set_col_width(ws, ci, w)

    _add_footnote(ws, len(desc_rows)+6, n_cols,
        "Skewness: positive = right-skewed (heavy rainfall tail).  "
        "Kurtosis: Fisher definition (normal = 0).  "
        "Wet-day freq only computed for daily scale.")


def write_metrics_sheet(wb: Workbook, met_rows: list, scale: str,
                        improve_rows: list = None):
    """Write one model-performance sheet (Daily or Monthly)."""
    ws = wb.create_sheet(f"Model Performance ({scale})")
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "D6"

    disp_metrics = ["RMSE","MAE","MBE","Pbias (%)","r (Pearson)","NSE","KGE",
                    "KGE_r","KGE_alpha","KGE_beta"]
    header_row   = ["Dataset","Station","Scale","N_pairs"] + disp_metrics

    n_cols = len(header_row)

    # ── Title ──────────────────────────────────────────────────────────
    merge_sc(ws, 1, 1, n_cols,
             f"Model Performance Metrics — {scale} Scale  "
             "(Observed vs Raw CMIP6 vs Bias-Corrected / QDM)",
             bold=True, fc=XL["font_white"], bg=XL["title_bg"], sz=12)
    ws.row_dimensions[1].height = 26

    merge_sc(ws, 2, 1, n_cols,
             "RMSE = Root Mean Square Error (mm)  │  "
             "MAE = Mean Absolute Error (mm)  │  "
             "MBE = Mean Bias Error (mm)  │  "
             "Pbias = Percent Bias (%)  │  "
             "NSE = Nash–Sutcliffe Efficiency  │  "
             "KGE = Kling–Gupta Efficiency",
             bold=False, italic=True,
             fc=XL["font_white"], bg=XL["hdr_mid"], sz=8.5)
    ws.row_dimensions[2].height = 16

    merge_sc(ws, 3, 1, n_cols,
             "Perfect model: RMSE=0, MAE=0, MBE=0, Pbias=0, r=1, NSE=1, KGE=1  │  "
             "★ = Best value per station & metric  │  "
             "Highlighted cells (yellow) = best performer",
             bold=False, italic=True, fc=XL["hdr_dark"],
             bg=XL["note_bg"], sz=8)
    ws.row_dimensions[3].height = 14

    # ── Sub-headers ────────────────────────────────────────────────────
    sub_groups = [
        (1, 4,  "Identification"),
        (5, 7,  "Error Metrics (lower = better)"),
        (8, 9,  "Correlation"),
        (10, 11,"Efficiency (higher = better)"),
        (12, 14,"KGE Components"),
    ]
    for c1, c2, lbl in sub_groups:
        merge_sc(ws, 4, c1, c2, lbl, bold=True,
                 fc=XL["font_white"], bg=XL["section"], sz=8.5)
    ws.row_dimensions[4].height = 18

    for ci, h in enumerate(header_row, 1):
        sc(ws, 5, ci, h, bold=True,
           fc=XL["font_white"], bg=XL["hdr_dark"],
           border=thin_b(), sz=8.5, wrap=True)
    ws.row_dimensions[5].height = 38

    # ── Collect best values per station+metric ──────────────────────
    # Group by station → for each metric find best row index
    best_cells = {}   # (row_in_excel, col_in_excel)
    stns_seen  = sorted(set(r["Station"] for r in met_rows))

    for stn in stns_seen:
        stn_rows = [(i, r) for i, r in enumerate(met_rows) if r["Station"] == stn]
        for met in disp_metrics:
            vals = [(i, r[met]) for i, r in stn_rows
                    if not (isinstance(r[met], float) and np.isnan(r[met]))]
            if not vals:
                continue
            if met in LOWER_BETTER:
                best_i = min(vals, key=lambda x: abs(x[1]))[0]
            elif met in HIGHER_BETTER:
                best_i = max(vals, key=lambda x: x[1])[0]
            else:
                continue
            excel_row = best_i + 6   # data starts at row 6
            excel_col = header_row.index(met) + 1
            best_cells[(excel_row, excel_col)] = True

    # ── Data rows ──────────────────────────────────────────────────────
    dataset_bg = {
        "Raw CMIP6":      XL["row_raw"],
        "Bias-Corrected": XL["row_bc"],
    }
    dataset_fc = {
        "Raw CMIP6":      XL["hdr_raw"],
        "Bias-Corrected": XL["hdr_bc"],
    }

    prev_stn = None
    for ri, row in enumerate(met_rows, 6):
        ds  = row.get("Dataset", "")
        stn = row.get("Station", "")
        bg  = dataset_bg.get(ds, XL["white"])

        if stn != prev_stn and prev_stn is not None:
            ws.row_dimensions[ri-1].height = 5

        for ci, key in enumerate(header_row, 1):
            val = row.get(key, "")
            if isinstance(val, float) and np.isnan(val):
                val = "—"
            elif isinstance(val, float):
                val = round(val, 4 if ci >= 5 else 2)

            is_best = (ri, ci) in best_cells
            cell_bg = XL["best_fill"] if is_best else bg
            cell = sc(ws, ri, ci, val,
                      bg=cell_bg, border=thin_b(), sz=9,
                      align="left" if ci <= 3 else "center")
            if ci == 1:
                cell.font = Font(bold=True,
                                 color=dataset_fc.get(ds, XL["font_dark"]),
                                 name="Calibri", size=9)
            if is_best:
                cell.font = Font(bold=True, color=XL["best_font"],
                                 name="Calibri", size=9)
                # add ★ prefix to value
                if val not in ("", "—"):
                    cell.value = f"★ {val}"

        ws.row_dimensions[ri].height = 16
        prev_stn = stn

    # ── Improvement summary ────────────────────────────────────────────
    if improve_rows:
        next_r = len(met_rows) + 7
        merge_sc(ws, next_r, 1, n_cols,
                 "Average Improvement after Bias Correction (QDM vs Raw CMIP6)",
                 bold=True, fc=XL["font_white"], bg=XL["hdr_mid"], sz=10)
        ws.row_dimensions[next_r].height = 20
        next_r += 1

        imp_hdr = ["Metric","Raw (mean)","QDM (mean)",
                   "Absolute Improvement","Relative Improvement (%)","Direction"]
        for ci, h in enumerate(imp_hdr, 1):
            sc(ws, next_r, ci, h, bold=True,
               fc=XL["font_white"], bg=XL["hdr_dark"],
               border=thin_b(), sz=9)
        ws.row_dimensions[next_r].height = 22
        next_r += 1

        for imp in improve_rows:
            rel = imp.get("Relative Improvement (%)", np.nan)
            direction = imp.get("Direction", "")
            row_bg = XL["improve"] if direction == "Improved" else \
                     (XL["warn"] if direction == "Degraded" else XL["white"])
            for ci, key in enumerate(imp_hdr, 1):
                val = imp.get(key, "")
                if isinstance(val, float) and np.isnan(val):
                    val = "—"
                elif isinstance(val, float):
                    val = round(val, 3)
                cell = sc(ws, next_r, ci, val,
                          bg=row_bg, border=thin_b(), sz=9,
                          align="center")
                if key == "Direction":
                    col = XL["hdr_obs"] if val == "Improved" else \
                          (XL["hdr_raw"] if val == "Degraded" else XL["font_dark"])
                    cell.font = Font(bold=True, color=col,
                                     name="Calibri", size=9)
            ws.row_dimensions[next_r].height = 16
            next_r += 1

    # ── Column widths ──────────────────────────────────────────────────
    widths = [16, 9, 8, 8] + [11]*len(disp_metrics)
    for ci, w in enumerate(widths, 1):
        set_col_width(ws, ci, w)

    _add_footnote(ws, ws.max_row + 2, n_cols,
        "Nash–Sutcliffe Efficiency (NSE): Nash & Sutcliffe (1970).  "
        "Kling–Gupta Efficiency (KGE): Gupta et al. (2009).  "
        "KGEα = std ratio; KGEβ = mean ratio.  "
        "★ = best value per station and metric.  "
        "Bias correction: QDM – Cannon et al. (2015).")


def write_method_sheet(wb: Workbook, obs_period: str,
                       sim_period: str, n_stns: int):
    """Reference & method sheet."""
    ws = wb.create_sheet("Method & References")
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 28
    ws.column_dimensions["C"].width = 72

    merge_sc(ws, 1, 1, 3,
             "Statistical Methods & References",
             bold=True, fc=XL["font_white"], bg=XL["title_bg"], sz=13)
    ws.row_dimensions[1].height = 26

    rows = [
        ("Period",    "Data Periods",
         f"Observed: {obs_period}  │  CMIP6/QDM: {sim_period}  │  "
         f"Stations: {n_stns}"),
        ("Wet day",   "Wet-day Threshold",
         f"≥ {WET_THRESHOLD} mm day⁻¹ (WMO standard)."),
        ("CV",        "Coefficient of Variation",
         "CV = (σ/μ) × 100 (%). Measures relative variability."),
        ("Skewness",  "Skewness",
         "Fisher-Pearson standardised skewness. "
         "Positive = right-skewed (heavy rainfall tail). "
         "SciPy: scipy.stats.skew(x)."),
        ("Kurtosis",  "Excess Kurtosis",
         "Fisher definition (normal distribution = 0). "
         "SciPy: scipy.stats.kurtosis(x, fisher=True)."),
        ("RMSE",      "Root Mean Square Error",
         "RMSE = √[Σ(sim−obs)² / n].  Units: mm.  "
         "Sensitive to large errors."),
        ("MAE",       "Mean Absolute Error",
         "MAE = Σ|sim−obs| / n.  Units: mm.  "
         "More robust to outliers than RMSE."),
        ("MBE",       "Mean Bias Error",
         "MBE = Σ(sim−obs) / n.  Units: mm.  "
         "Positive = model overestimates."),
        ("Pbias",     "Percent Bias",
         "Pbias = 100 × Σ(sim−obs) / Σobs (%).  "
         "Optimal: 0%.  Positive = wet bias."),
        ("r",         "Pearson Correlation Coefficient",
         "r ∈ [−1, 1]. Measures linear association. "
         "Perfect: r = 1."),
        ("NSE",       "Nash–Sutcliffe Efficiency",
         "NSE = 1 − Σ(sim−obs)² / Σ(obs−obs̄)².  "
         "Range (−∞, 1]. Perfect: NSE = 1. "
         "NSE > 0.65: good; 0.50–0.65: satisfactory.  "
         "Ref: Nash & Sutcliffe (1970) J. Hydrol. 10:282–290."),
        ("KGE",       "Kling–Gupta Efficiency",
         "KGE = 1 − √[(r−1)² + (α−1)² + (β−1)²], "
         "where α = σ_sim/σ_obs (variability ratio), "
         "β = μ_sim/μ_obs (bias ratio).  "
         "Range (−∞, 1]. Perfect: KGE = 1.  "
         "Ref: Gupta et al. (2009) J. Hydrol. 377:80–91."),
        ("QDM",       "Quantile Delta Mapping",
         "Bias correction method preserving relative changes in quantiles. "
         "Ref: Cannon et al. (2015) J. Climate 28:6938–6959."),
        ("",          "Further References",
         "Teutschbein C. & Seibert J. (2012) Bias correction of regional "
         "climate model simulations for hydrological climate-change impact "
         "studies. Hydrol. Earth Syst. Sci. 16:3391–3314.\n"
         "Maraun D. (2016) Bias Correcting Climate Change Simulations – "
         "a Critical Review. Curr. Clim. Chang. Rep. 2:211–220."),
    ]

    alt = [
        PatternFill("solid", fgColor="DEEAF1"),
        PatternFill("solid", fgColor="FFFFFF"),
    ]
    for ri, (abbr, term, desc) in enumerate(rows, 3):
        fl = alt[ri % 2]
        sc(ws, ri, 1, abbr, bold=True, sz=9, align="center").fill = fl
        sc(ws, ri, 2, term, bold=True, sz=9, align="left",
           border=thin_b()).fill = fl
        cell = sc(ws, ri, 3, desc, sz=9, align="left",
                  border=thin_b())
        cell.fill = fl
        cell.alignment = Alignment(horizontal="left", vertical="top",
                                    wrap_text=True)
        ws.row_dimensions[ri].height = 48


def _add_footnote(ws, row, n_cols, text):
    ws.merge_cells(
        start_row=row, start_column=1, end_row=row, end_column=n_cols
    )
    cell = ws.cell(row=row, column=1, value=f"Note: {text}")
    cell.font = Font(italic=True, color=XL["font_grey"],
                     name="Calibri", size=7.5)
    cell.alignment = Alignment(horizontal="left", vertical="center",
                                wrap_text=True)
    cell.fill = fill(XL["note_bg"])
    ws.row_dimensions[row].height = 28


# ═══════════════════════════════════════════════════════════════════════════
# 7.  COMPUTE IMPROVEMENT SUMMARY
# ═══════════════════════════════════════════════════════════════════════════

def improvement_summary(raw_rows: list, bc_rows: list) -> list:
    """Compute mean metric values across stations and improvement %."""
    metrics_to_compare = ["RMSE","MAE","MBE","Pbias (%)","r (Pearson)","NSE","KGE"]
    results = []
    for met in metrics_to_compare:
        raw_vals = [r[met] for r in raw_rows
                    if not (isinstance(r[met], float) and np.isnan(r[met]))]
        bc_vals  = [r[met] for r in bc_rows
                    if not (isinstance(r[met], float) and np.isnan(r[met]))]
        if not raw_vals or not bc_vals:
            continue
        raw_mean = float(np.mean(raw_vals))
        bc_mean  = float(np.mean(bc_vals))

        if met in LOWER_BETTER:
            # improvement = reduction in absolute value
            abs_imp  = abs(raw_mean) - abs(bc_mean)
            rel_imp  = abs_imp / abs(raw_mean) * 100 \
                       if raw_mean != 0 else np.nan
            direction = "Improved" if abs_imp > 0 else \
                        ("No change" if abs_imp == 0 else "Degraded")
        else:
            abs_imp  = bc_mean - raw_mean
            rel_imp  = abs_imp / abs(raw_mean) * 100 \
                       if raw_mean != 0 else np.nan
            direction = "Improved" if abs_imp > 0 else \
                        ("No change" if abs_imp == 0 else "Degraded")

        results.append({
            "Metric":                    met,
            "Raw (mean)":                round(raw_mean, 4),
            "QDM (mean)":                round(bc_mean, 4),
            "Absolute Improvement":      round(abs_imp, 4),
            "Relative Improvement (%)":  round(rel_imp, 2)
                                         if not np.isnan(rel_imp) else np.nan,
            "Direction":                 direction,
        })
    return results

# ═══════════════════════════════════════════════════════════════════════════
# 8.  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def find_work_dir():
    try:
        return str(Path(os.path.abspath(__file__)).parent)
    except NameError:
        return os.getcwd()


def main():
    banner = "=" * 72
    print(banner)
    print("  Descriptive Statistics & Model Performance Metrics")
    print("  Observed vs Raw CMIP6 vs Bias-Corrected (QDM)")
    print("  มาตรฐานวารสาร Q2-Q3 / TCI1")
    print(banner)

    # ── โฟลเดอร์ทำงาน ─────────────────────────────────────────────────
    work_dir = sys.argv[1].strip('"').strip("'") \
               if len(sys.argv) > 1 else find_work_dir()
    print(f"  โฟลเดอร์ : {work_dir}")

    obs_path, raw_path, bc_path = find_csv_files(work_dir)
    if obs_path is None:
        sys.exit("  ✗  ไม่พบไฟล์ Observed (ชื่อต้องมีคำว่า 'Observed')")

    print(f"  Observed : {Path(obs_path).name}")
    print(f"  Raw CMIP6: {Path(raw_path).name if raw_path else '(ไม่พบ)'}")
    print(f"  BC/QDM   : {Path(bc_path).name  if bc_path  else '(ไม่พบ)'}")
    print("-" * 72)

    # ── โหลดข้อมูล ────────────────────────────────────────────────────
    print("  กำลังโหลดข้อมูล ...")
    obs_d, stns = load_daily(obs_path, "Observed")
    raw_d, _    = load_daily(raw_path, "Raw CMIP6")
    bc_d,  _    = load_daily(bc_path,  "BC/QDM")

    obs_m = to_monthly(obs_d)
    raw_m = to_monthly(raw_d)
    bc_m  = to_monthly(bc_d)

    def period(df):
        if df is None or len(df) == 0:
            return "N/A"
        try:
            return f"{df.index[0].year}–{df.index[-1].year}"
        except Exception:
            return "N/A"

    obs_period = period(obs_d)
    sim_period = period(raw_d) if raw_d is not None else period(bc_d)
    print(f"  สถานี {len(stns)} สถานี  │  "
          f"Obs: {obs_period}  │  Sim: {sim_period}")
    print("-" * 72)

    # ── วิเคราะห์รายสถานี ─────────────────────────────────────────────
    print("  กำลังคำนวณสถิติและ metrics ...")

    desc_daily_rows = []
    desc_mon_rows   = []
    met_daily_rows  = []
    met_mon_rows    = []

    for stn in stns:
        stn = str(stn)

        def get_col(df, col):
            if df is None or col not in df.columns:
                return np.array([np.nan])
            return df[col].values.astype(float)

        # ── Descriptive stats ──────────────────────────────────────────
        for label, df_d, df_m in [
            ("Observed",       obs_d, obs_m),
            ("Raw CMIP6",      raw_d, raw_m),
            ("Bias-Corrected", bc_d,  bc_m),
        ]:
            if df_d is not None:
                desc_daily_rows.append(
                    descriptive_stats(get_col(df_d, stn),
                                      label, stn, "Daily"))
            if df_m is not None:
                desc_mon_rows.append(
                    descriptive_stats(get_col(df_m, stn),
                                      label, stn, "Monthly"))

        # ── Performance metrics ────────────────────────────────────────
        for sim_label, sim_d, sim_m in [
            ("Raw CMIP6",      raw_d, raw_m),
            ("Bias-Corrected", bc_d,  bc_m),
        ]:
            o_d, s_d = align(obs_d, sim_d, stn)
            o_m, s_m = align(obs_m, sim_m, stn)
            if len(o_d) > 0:
                met_daily_rows.append(
                    compute_metrics(o_d, s_d, sim_label, stn, "Daily"))
            if len(o_m) > 0:
                met_mon_rows.append(
                    compute_metrics(o_m, s_m, sim_label, stn, "Monthly"))

        print(f"    ✓  Station {stn}")

    # ── Improvement summary ────────────────────────────────────────────
    raw_d_rows  = [r for r in met_daily_rows if r["Dataset"] == "Raw CMIP6"]
    bc_d_rows   = [r for r in met_daily_rows if r["Dataset"] == "Bias-Corrected"]
    raw_m_rows  = [r for r in met_mon_rows   if r["Dataset"] == "Raw CMIP6"]
    bc_m_rows   = [r for r in met_mon_rows   if r["Dataset"] == "Bias-Corrected"]

    imp_daily = improvement_summary(raw_d_rows, bc_d_rows)
    imp_mon   = improvement_summary(raw_m_rows, bc_m_rows)

    # ── Write Excel ────────────────────────────────────────────────────
    print("-" * 72)
    print("  กำลังสร้างไฟล์ Excel ...")

    wb = Workbook()
    wb.remove(wb.active)   # remove default empty sheet

    write_desc_sheet(wb, desc_daily_rows, "Daily")
    write_desc_sheet(wb, desc_mon_rows,   "Monthly")
    write_metrics_sheet(wb, met_daily_rows, "Daily",   imp_daily)
    write_metrics_sheet(wb, met_mon_rows,   "Monthly", imp_mon)
    write_method_sheet(wb, obs_period, sim_period, len(stns))

    # ── Output path ────────────────────────────────────────────────────
    base_name = Path(obs_path).stem
    out_xlsx  = Path(work_dir) / f"Output_Statistics_{base_name}.xlsx"
    wb.save(str(out_xlsx))

    print(f"  ✓  บันทึกแล้ว: {out_xlsx}")
    print()
    print(banner)
    print("  สรุปผล Improvement (Daily, across all stations):")
    print(f"  {'Metric':<18} {'Raw':>10} {'QDM':>10} "
          f"{'Abs Improve':>14} {'Rel %':>10} Direction")
    print("  " + "-" * 68)
    for imp in imp_daily:
        print(f"  {imp['Metric']:<18} "
              f"{imp['Raw (mean)']:>10.4f} "
              f"{imp['QDM (mean)']:>10.4f} "
              f"{imp['Absolute Improvement']:>14.4f} "
              f"{imp['Relative Improvement (%)']:>10.2f}%  "
              f"{imp['Direction']}")
    print(banner)
    print("  เสร็จสิ้น ✓")


if __name__ == "__main__":
    main()
