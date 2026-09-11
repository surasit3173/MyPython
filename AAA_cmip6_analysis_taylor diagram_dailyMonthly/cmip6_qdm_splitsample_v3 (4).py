#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  cmip6_qdm_splitsample_v3.py                                        v3.0     ║
║  CMIP6 rainfall bias correction — INDEPENDENT TEMPORAL VALIDATION            ║
║  Prachuap Khiri Khan, Thailand · 12 rain gauges · 1981–2014                  ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  แกนที่ต่างจาก pipeline เดิม (ตอบข้อท้วงติงของผู้ประเมิน)                      ║
║   • calibration 1981–2000  →  QDM fitting                                    ║
║     independent validation 2001–2014  →  apply, ห้าม refit                   ║
║     ข้อมูลสังเกตการณ์ 2001–2014 ไม่เข้าสู่ขั้นตอน fitting ใด ๆ  [C3,10,12,13,19]║
║   • QDM ของแท้: delta = F_mp(2001–2014) / F_mh(1981–2000) ≠ 1        [C11]   ║
║     + EQM เป็น reference method (delta = 1) เพื่อเทียบตรง ๆ                    ║
║   • ระดับรายวันใช้ดัชนีเชิงการแจกแจง/ค่าสุดขั้ว                                ║
║     r/NSE/KGE/d ใช้ที่ระดับรายเดือน  (รายวันเก็บไว้ supplementary)     [C14]  ║
║   • MME สามนิยาม: metric-median / monthly-series / daily-mean(diagnostic)     ║
║   • Wilcoxon signed-rank จับคู่ 12 สถานี + rank-biserial + BH-FDR      [C17]  ║
║     + moving-block bootstrap 95% CI                                          ║
║   • ตรวจ grid-cell footprint จากลายเซ็นข้อมูลดิบ                       [C8]   ║
║   • QC/homogeneity: Pettitt, Mann–Kendall, smoothing diagnostics       [C7]  ║
║   • เทียบกับไฟล์ bc_* เดิม (full-period QDM) เพื่อวัดขนาด optimistic bias      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Input (auto-discovered จากโฟลเดอร์)                                          ║
║    Observed        : *Observed*.csv                                          ║
║    Raw GCM         : pr_day_<MODEL>_historical_<variant>_<grid>_*.csv        ║
║    Legacy BC (opt) : bc_pr_day_<MODEL>_*.csv                                 ║
║    รูปแบบไฟล์      : YEAR,MONTH,DAY,<station_id...>   หน่วย mm/day            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  การใช้งาน                                                                    ║
║    python cmip6_qdm_splitsample_v3.py --inspect  --dir "D:\\ClaudeWork\\..."   ║
║    python cmip6_qdm_splitsample_v3.py --run      --dir "D:\\ClaudeWork\\..." \\ ║
║           --out "D:\\ClaudeWork\\out_v3" --cal 1981-2000 --val 2001-2014      ║
║    python cmip6_qdm_splitsample_v3.py --selftest                             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  References                                                                  ║
║    Cannon, Sobie & Murdock (2015) J.Climate 28:6938–6959        [QDM]        ║
║    Gudmundsson et al. (2012) HESS 16:3383–3390                  [QM eval]    ║
║    Themeßl et al. (2012) Climatic Change 112:449–468            [freq adapt] ║
║    Gupta et al. (2009) J.Hydrol. 377:80–91                      [KGE]        ║
║    Nash & Sutcliffe (1970) J.Hydrol. 10:282–290                 [NSE]        ║
║    Willmott (1981) Phys.Geogr. 2:184–194                        [d]          ║
║    Perkins et al. (2007) J.Climate 20:4356–4376                 [PSS]        ║
║    Pettitt (1979) Appl.Stat. 28:126–135                         [change pt]  ║
║    Wilcoxon (1945) Biometrics Bull. 1:80–83                     [test]       ║
║    Benjamini & Hochberg (1995) JRSS-B 57:289–300                [FDR]        ║
║    Taylor (2001) J.Geophys.Res. 106:7183–7192                   [Taylor dia] ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import re
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sps

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

# ═══════════════════════════════════════════════════════════════════════════
#  §0  CONFIG
# ═══════════════════════════════════════════════════════════════════════════

DPI = 600


@dataclass
class Config:
    cal: tuple[int, int] = (1981, 2000)     # calibration period
    val: tuple[int, int] = (2001, 2014)     # independent validation period
    wet: float = 1.0                        # mm/day, ETCCDI wet-day threshold
    window_days: int = 30                   # moving window ±days รอบวันกลางเดือน
    n_quantiles: int = 200
    delta_clip: tuple[float, float] = (0.2, 5.0)
    boot_n: int = 500
    block_len: int = 20                     # moving-block bootstrap (วัน)
    fdr_q: float = 0.05
    seed: int = 20260821
    min_fit_days: int = 300
    # เกณฑ์ตรวจจับอนุกรมที่ถูกทำให้เรียบ/แจกแจงย้อนหลัง
    flag_lag1: float = 0.45
    flag_wetfreq: float = 0.55
    save_pdf: bool = False
    stations: list[str] = field(default_factory=list)
    models: list[str] = field(default_factory=list)


CFG = Config()

STYLE = {
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"],
    "font.size": 11,
    "axes.titlesize": 12, "axes.titleweight": "bold",
    "axes.labelsize": 11.5, "axes.labelweight": "bold",
    "xtick.labelsize": 10, "ytick.labelsize": 10,
    "legend.fontsize": 9.5,
    "figure.titlesize": 13,
    "lines.linewidth": 1.6,
    "axes.linewidth": 1.2,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.linestyle": "--", "grid.linewidth": 0.45,
    "grid.alpha": 0.45, "grid.color": "#B0BEC5",
    "savefig.dpi": DPI, "savefig.bbox": "tight", "savefig.pad_inches": 0.15,
    "figure.dpi": 110, "mathtext.fontset": "stix",
    "pdf.fonttype": 42, "ps.fonttype": 42,
}

C_OBS, C_RAW, C_QDM, C_EQM, C_LEG = "#212121", "#C62828", "#1565C0", "#2E7D32", "#8E24AA"


def set_style():
    plt.rcParams.update(STYLE)


def savefig(fig, stem: str) -> str:
    fig.savefig(stem + ".png", dpi=DPI, bbox_inches="tight", pad_inches=0.15)
    if CFG.save_pdf:
        fig.savefig(stem + ".pdf", bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    print(f"    ✓ {Path(stem).name}.png")
    return stem + ".png"


# ═══════════════════════════════════════════════════════════════════════════
#  §1  FILE DISCOVERY & LOADING
# ═══════════════════════════════════════════════════════════════════════════

_RE_MODEL = re.compile(
    r"(?:^|_)pr_day_(?P<model>.+?)_(?P<exp>historical|ssp\d{3})_"
    r"(?P<variant>r\d+i\d+p\d+f\d+)_(?P<grid>g[nr]\d*)_", re.IGNORECASE)


def parse_model_meta(fname: str) -> dict | None:
    m = _RE_MODEL.search(fname)
    if not m:
        return None
    d = m.groupdict()
    d["legacy_bc"] = Path(fname).name.lower().startswith("bc_")
    return d


def discover(folder: str | Path) -> dict:
    folder = Path(folder)
    files = sorted(folder.glob("*.csv"))
    out = {"obs": None, "raw": {}, "legacy": {}, "meta": {}, "folder": str(folder)}
    for f in files:
        n = f.name
        if "observed" in n.lower():
            out["obs"] = f
            continue
        meta = parse_model_meta(n)
        if meta is None:
            continue
        key = meta["model"]
        out["meta"][key] = {k: meta[k] for k in ("exp", "variant", "grid")}
        (out["legacy"] if meta["legacy_bc"] else out["raw"])[key] = f
    return out


def load_ymd_csv(path: str | Path) -> pd.DataFrame:
    """อ่านไฟล์รูปแบบ YEAR,MONTH,DAY,<station...> คืน DataFrame index เป็นวันที่"""
    df = pd.read_csv(path)
    cols = {c.strip().upper(): c for c in df.columns}
    for req in ("YEAR", "MONTH", "DAY"):
        if req not in cols:
            raise ValueError(f"{Path(path).name}: ไม่พบคอลัมน์ {req}")
    idx = pd.to_datetime(dict(year=df[cols["YEAR"]],
                              month=df[cols["MONTH"]],
                              day=df[cols["DAY"]]))
    data = df.drop(columns=[cols["YEAR"], cols["MONTH"], cols["DAY"]])
    data.columns = [str(c).strip() for c in data.columns]
    return data.set_index(idx).astype(float).sort_index()


def load_all(folder: str | Path, cfg: Config = CFG) -> dict:
    disc = discover(folder)
    if disc["obs"] is None:
        raise FileNotFoundError("ไม่พบไฟล์ observed (*Observed*.csv)")
    obs = load_ymd_csv(disc["obs"])
    raw = {m: load_ymd_csv(p).reindex(obs.index) for m, p in disc["raw"].items()}
    leg = {m: load_ymd_csv(p).reindex(obs.index) for m, p in disc["legacy"].items()}
    if not raw:
        raise FileNotFoundError("ไม่พบไฟล์ raw GCM (pr_day_*.csv)")
    common = [c for c in obs.columns if all(c in d.columns for d in raw.values())]
    obs = obs[common]
    raw = {m: d[common] for m, d in raw.items()}
    leg = {m: d[common] for m, d in leg.items() if set(common) <= set(d.columns)}
    cfg.stations = list(common)
    cfg.models = sorted(raw)
    return {"obs": obs, "raw": raw, "legacy": leg,
            "meta": disc["meta"], "files": disc}


# ═══════════════════════════════════════════════════════════════════════════
#  §2  QC & DATA INTEGRITY   [reviewer comment 7, 16]
# ═══════════════════════════════════════════════════════════════════════════

def pettitt_test(x: np.ndarray) -> dict:
    """Pettitt (1979) non-parametric change-point test"""
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = x.size
    if n < 10:
        return {"K": np.nan, "p_value": np.nan, "cp_index": np.nan}
    r = sps.rankdata(x)
    U = 2 * np.cumsum(r) - np.arange(1, n + 1) * (n + 1)
    k = int(np.argmax(np.abs(U)))
    K = float(np.abs(U[k]))
    p = float(min(1.0, 2.0 * np.exp(-6.0 * K ** 2 / (n ** 3 + n ** 2))))
    return {"K": K, "p_value": p, "cp_index": k}


def mann_kendall(x: np.ndarray) -> dict:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = x.size
    if n < 8:
        return {"Z": np.nan, "p_value": np.nan}
    s = int(np.sum(np.sign(x[None, :] - x[:, None])[np.triu_indices(n, 1)]))
    _, cnt = np.unique(x, return_counts=True)
    tie = np.sum(cnt * (cnt - 1) * (2 * cnt + 5))
    var = (n * (n - 1) * (2 * n + 5) - tie) / 18.0
    z = 0.0 if s == 0 else (s - np.sign(s)) / np.sqrt(var)
    return {"Z": float(z), "p_value": float(2 * (1 - sps.norm.cdf(abs(z))))}


def max_identical_run(v: np.ndarray) -> int:
    best = cur = 0
    prev = None
    for x in v:
        if prev is not None and x == prev and x > 0:
            cur += 1
        else:
            cur = 1
        best = max(best, cur)
        prev = x
    return int(best)


def qc_report(obs: pd.DataFrame, cfg: Config = CFG) -> pd.DataFrame:
    """
    รายงาน QC รายสถานี พร้อมธงเตือนอนุกรมที่มีลักษณะถูกทำให้เรียบ
    (wet-day frequency สูงผิดปกติ + lag-1 autocorrelation สูง + ค่าสุดขั้วต่ำผิดปกติ)
    """
    rows = []
    for c in obs.columns:
        s = obs[c]
        wet = s[s >= cfg.wet]
        ann = s.groupby(s.index.year).sum()
        pet = pettitt_test(ann.values)
        mk = mann_kendall(ann.values)
        cp_year = int(ann.index[pet["cp_index"]]) if np.isfinite(pet["cp_index"]) else np.nan
        # ธงสำหรับสัดส่วนวันแห้งรายปีที่กระโดด
        zy = (s == 0).groupby(s.index.year).mean()
        pet_zero = pettitt_test(zy.values)
        rows.append({
            "station": c,
            "n_days": int(s.size),
            "missing_pct": float(s.isna().mean() * 100),
            "zero_pct": float((s == 0).mean() * 100),
            "wet_freq": float((s >= cfg.wet).mean()),
            "SDII": float(wet.mean()) if wet.size else np.nan,
            "sd_daily": float(s.std(ddof=1)),
            "max_daily": float(s.max()),
            "p99_wet": float(np.quantile(wet, 0.99)) if wet.size else np.nan,
            "lag1_acf": float(s.autocorr(1)),
            "annual_mean": float(ann.mean()),
            "annual_sd": float(ann.std(ddof=1)),
            "max_identical_run": max_identical_run(s.values),
            "n_negative": int((s < 0).sum()),
            "pettitt_annual_p": pet["p_value"],
            "pettitt_annual_cp_year": cp_year,
            "pettitt_zerofrac_p": pet_zero["p_value"],
            "pettitt_zerofrac_cp_year": (int(zy.index[pet_zero["cp_index"]])
                                         if np.isfinite(pet_zero["cp_index"]) else np.nan),
            "MK_Z_annual": mk["Z"],
            "MK_p_annual": mk["p_value"],
        })
    df = pd.DataFrame(rows).set_index("station")
    med_sd = df["sd_daily"].median()
    med_max = df["max_daily"].median()
    df["flag_smoothed"] = ((df["lag1_acf"] > cfg.flag_lag1) &
                           (df["wet_freq"] > cfg.flag_wetfreq) &
                           (df["max_daily"] < 0.6 * med_max))
    df["flag_low_variance"] = df["sd_daily"] < 0.6 * med_sd
    df["flag_inhomogeneous"] = df["pettitt_zerofrac_p"] < 0.05
    df["flag_any"] = df[["flag_smoothed", "flag_low_variance",
                         "flag_inhomogeneous"]].any(axis=1)
    return df


def classify_stations(qc: pd.DataFrame, pc: pd.DataFrame,
                      cfg: Config = CFG) -> pd.DataFrame:
    """
    จำแนกสถานีด้วย 2 เกณฑ์ที่เป็นอิสระต่อกัน (ห้ามรวมเป็นเกณฑ์เดียว)

      เกณฑ์ที่ 1  ความสมเหตุสมผลของการแจกแจงรายวัน
                  SDII >= 8 mm/wet-day, lag-1 ACF < 0.30,
                  max_daily >= 0.5 x median(max_daily)
                  ตกเกณฑ์นี้ = อนุกรมน่าจะถูกแจกแจงจากค่าสะสม -> Tier C

      เกณฑ์ที่ 2  ความสม่ำเสมอเชิงเวลาคร่อมรอยต่อ cal/val
                  Pettitt(zero-fraction) p > 0.05  และ
                  |wetfreq_val - wetfreq_cal| / wetfreq_cal < 0.20
                  ตกเกณฑ์นี้ = ไม่สม่ำเสมอ -> Tier B

      Tier A = ผ่านทั้งสองเกณฑ์  (แกนหลักของการวิเคราะห์)
      Tier B = แจกแจงสมเหตุสมผล แต่ไม่สม่ำเสมอเชิงเวลา
      Tier C = การแจกแจงรายวันไม่น่าเชื่อถือ ไม่ควรใช้ในการประเมินรายวัน
    """
    med_max = qc["max_daily"].median()
    d = pd.DataFrame(index=qc.index)
    d["SDII"] = qc["SDII"]
    d["lag1_acf"] = qc["lag1_acf"]
    d["max_daily"] = qc["max_daily"]
    d["pettitt_p"] = qc["pettitt_zerofrac_p"]
    d["wetfreq_cal"] = pc["wetfreq_cal"]
    d["wetfreq_val"] = pc["wetfreq_val"]
    d["wetfreq_rel_change"] = ((pc["wetfreq_val"] - pc["wetfreq_cal"]).abs()
                               / pc["wetfreq_cal"])

    d["ok_distribution"] = ((d["SDII"] >= 8.0) & (d["lag1_acf"] < 0.30) &
                            (d["max_daily"] >= 0.5 * med_max))
    d["ok_homogeneity"] = ((d["pettitt_p"] > 0.05) & (d["wetfreq_rel_change"] < 0.20))

    def _tier(r):
        if not r["ok_distribution"]:
            return "C"
        return "A" if r["ok_homogeneity"] else "B"

    d["tier"] = d.apply(_tier, axis=1)

    def _why(r):
        why = []
        if r["SDII"] < 8.0:
            why.append(f"SDII={r['SDII']:.1f} ต่ำผิดปกติ")
        if r["lag1_acf"] >= 0.30:
            why.append(f"lag1={r['lag1_acf']:.2f} สูงผิดปกติ")
        if r["max_daily"] < 0.5 * med_max:
            why.append(f"max={r['max_daily']:.0f} mm ต่ำผิดปกติ")
        if r["pettitt_p"] <= 0.05:
            why.append(f"Pettitt p={r['pettitt_p']:.3f}")
        if r["wetfreq_rel_change"] >= 0.20:
            why.append(f"wet-freq เปลี่ยน {100*r['wetfreq_rel_change']:.0f}%")
        return "; ".join(why) if why else "ผ่านทุกเกณฑ์"

    d["reason"] = d.apply(_why, axis=1)
    return d.round(4)


def yearly_zero_fraction(obs: pd.DataFrame) -> pd.DataFrame:
    return (obs == 0).groupby(obs.index.year).mean()


# ═══════════════════════════════════════════════════════════════════════════
#  §3  GRID-CELL FOOTPRINT   [reviewer comment 8]
# ═══════════════════════════════════════════════════════════════════════════

def grid_footprint(raw: dict[str, pd.DataFrame], n_probe: int = 800) -> pd.DataFrame:
    """
    ตรวจว่าสถานีใดใช้จุดกริดเดียวกันของแต่ละแบบจำลอง โดยดูลายเซ็นอนุกรม
    ไม่ต้องใช้ไฟล์ NetCDF ต้นทางหรือ GIS
    """
    rows = []
    for mdl, df in raw.items():
        sig = {}
        for c in df.columns:
            key = tuple(np.round(df[c].values[:n_probe], 6))
            sig.setdefault(key, []).append(c)
        for i, (_, cols) in enumerate(sorted(sig.items(),
                                             key=lambda kv: kv[1][0]), 1):
            for c in cols:
                rows.append({"model": mdl, "station": c,
                             "grid_cell_id": f"{mdl}_cell{i}",
                             "n_stations_in_cell": len(cols)})
    df = pd.DataFrame(rows)
    return df


def grid_footprint_summary(fp: pd.DataFrame, meta: dict) -> pd.DataFrame:
    g = fp.groupby("model").agg(
        n_unique_cells=("grid_cell_id", "nunique"),
        n_stations=("station", "nunique"),
        max_stations_per_cell=("n_stations_in_cell", "max"))
    g["variant"] = [meta.get(m, {}).get("variant", "") for m in g.index]
    g["grid_label"] = [meta.get(m, {}).get("grid", "") for m in g.index]
    g["effective_spatial_dof"] = g["n_unique_cells"]
    return g[["variant", "grid_label", "n_stations", "n_unique_cells",
              "max_stations_per_cell", "effective_spatial_dof"]]


# ═══════════════════════════════════════════════════════════════════════════
#  §4  PERIOD CONTRAST  (validation ท้าทายจริงหรือไม่)
# ═══════════════════════════════════════════════════════════════════════════

def period_contrast(obs: pd.DataFrame, cfg: Config = CFG) -> pd.DataFrame:
    yr = obs.index.year
    mc = (yr >= cfg.cal[0]) & (yr <= cfg.cal[1])
    mv = (yr >= cfg.val[0]) & (yr <= cfg.val[1])
    rows = []
    for c in obs.columns:
        a, b = obs[c][mc], obs[c][mv]
        aa = a.groupby(a.index.year).sum()
        bb = b.groupby(b.index.year).sum()
        aw, bw = a[a >= cfg.wet], b[b >= cfg.wet]
        try:
            u_p = sps.mannwhitneyu(aa.values, bb.values, alternative="two-sided")[1]
        except ValueError:
            u_p = np.nan
        ks_p = sps.ks_2samp(aw.values, bw.values)[1] if aw.size and bw.size else np.nan
        rows.append({
            "station": c,
            "annual_cal": float(aa.mean()), "annual_val": float(bb.mean()),
            "annual_diff_pct": float(100 * (bb.mean() - aa.mean()) / aa.mean()),
            "annual_sd_cal": float(aa.std(ddof=1)), "annual_sd_val": float(bb.std(ddof=1)),
            "wetfreq_cal": float((a >= cfg.wet).mean()),
            "wetfreq_val": float((b >= cfg.wet).mean()),
            "q95wet_cal": float(np.quantile(aw, 0.95)) if aw.size else np.nan,
            "q95wet_val": float(np.quantile(bw, 0.95)) if bw.size else np.nan,
            "MWU_p_annual": float(u_p),
            "KS_p_wetday": float(ks_p),
        })
    return pd.DataFrame(rows).set_index("station")


# ═══════════════════════════════════════════════════════════════════════════
#  §5  BIAS CORRECTION — QDM (ของแท้) + EQM (reference)
# ═══════════════════════════════════════════════════════════════════════════

def _quantiles(x: np.ndarray, q: np.ndarray) -> np.ndarray:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return np.quantile(x, q) if x.size else np.full_like(q, np.nan)


def _dry_threshold(obs_cal: np.ndarray, mod_cal: np.ndarray, wet: float) -> float:
    """frequency adaptation — ประมาณจาก calibration เท่านั้น (Themeßl et al. 2012)"""
    p_dry = float(np.mean(np.asarray(obs_cal, float) < wet))
    m = np.asarray(mod_cal, float)
    return float(np.quantile(m, np.clip(p_dry, 0, 1))) if m.size else 0.0


def _correct_block(obs_cal, mod_cal, mod_tgt, cfg: Config, mode: str):
    """
    mode='qdm' : x̂ = F⁻¹_o,h(τ) · [F⁻¹_m,p(τ) / F⁻¹_m,h(τ)] , τ = F_m,p(x)
    mode='eqm' : x̂ = F⁻¹_o,h(F_m,h(x))                        (delta ≡ 1)
    ทั้งสองโหมดใช้ข้อมูลสังเกตการณ์เฉพาะช่วง calibration
    """
    q = np.linspace(0.005, 0.995, cfg.n_quantiles)
    thr = _dry_threshold(obs_cal, mod_cal, cfg.wet)
    mc = np.where(np.asarray(mod_cal, float) <= thr, 0.0, mod_cal)
    mt = np.where(np.asarray(mod_tgt, float) <= thr, 0.0, mod_tgt)

    oq = _quantiles(obs_cal, q)
    hq = _quantiles(mc, q)
    info = {"dry_threshold": thr,
            "obs_wetfrac_cal": float(np.mean(np.asarray(obs_cal, float) >= cfg.wet))}

    if mode == "eqm":
        tau = np.interp(mt, hq, q, left=q[0], right=q[-1])
        out = np.interp(tau, q, oq)
        hi = mt > hq[-1]
        if np.any(hi) and hq[-1] > 0:
            out[hi] = oq[-1] * (mt[hi] / hq[-1])
        info.update(delta_med=1.0, delta_q95=1.0, delta_min=1.0, delta_max=1.0)
    else:
        pq = _quantiles(mt, q)
        with np.errstate(divide="ignore", invalid="ignore"):
            delta = np.where(hq > 0, pq / hq, 1.0)
        delta = np.clip(np.nan_to_num(delta, nan=1.0, posinf=1.0, neginf=1.0),
                        *cfg.delta_clip)
        tau = np.interp(mt, pq, q, left=q[0], right=q[-1])
        out = np.interp(tau, q, oq) * np.interp(tau, q, delta)
        hi = mt > pq[-1]
        if np.any(hi) and pq[-1] > 0:
            out[hi] = oq[-1] * delta[-1] * (mt[hi] / pq[-1])
        info.update(delta_med=float(np.median(delta)),
                    delta_q95=float(np.interp(0.95, q, delta)),
                    delta_min=float(delta.min()), delta_max=float(delta.max()))

    out = np.where(mt <= 0, 0.0, np.maximum(out, 0.0))
    return out, info


def correct_station_model(obs: pd.Series, mod: pd.Series, cfg: Config = CFG,
                          mode: str = "qdm") -> tuple[pd.Series, pd.DataFrame]:
    """fit บนช่วง cal เท่านั้น แล้วใช้กับทั้ง cal (in-sample) และ val (independent)"""
    idx = obs.index
    yr, doy = idx.year.values, idx.dayofyear.values
    in_cal = (yr >= cfg.cal[0]) & (yr <= cfg.cal[1])
    in_val = (yr >= cfg.val[0]) & (yr <= cfg.val[1])
    out = np.full(len(idx), np.nan)
    logs = []

    for month in range(1, 13):
        centre = pd.Timestamp(2001, month, 15).dayofyear
        d = np.abs(doy - centre)
        d = np.minimum(d, 365 - d)
        win = d <= cfg.window_days
        fit = in_cal & win
        if fit.sum() < cfg.min_fit_days:
            continue
        o_fit, m_fit = obs.values[fit], mod.values[fit]

        tgt_v = (idx.month == month) & in_val
        if tgt_v.sum():
            # F_m,p ประเมินจากแบบจำลองในหน้าต่างเดียวกันของช่วง validation
            src_p = mod.values[in_val & win]
            cv, info = _correct_block_with_pdist(o_fit, m_fit, mod.values[tgt_v],
                                                 src_p, cfg, mode)
            out[tgt_v] = cv
            logs.append({"month": month, "period": "validation",
                         "n_fit": int(fit.sum()), **info})

        tgt_c = (idx.month == month) & in_cal
        if tgt_c.sum():
            cc, infc = _correct_block(o_fit, m_fit, mod.values[tgt_c], cfg, "eqm")
            out[tgt_c] = cc
            logs.append({"month": month, "period": "calibration",
                         "n_fit": int(fit.sum()), **infc})

    return pd.Series(out, index=idx), pd.DataFrame(logs)


def _correct_block_with_pdist(obs_cal, mod_cal, mod_tgt, mod_pdist,
                              cfg: Config, mode: str):
    """เหมือน _correct_block แต่ระบุชุดข้อมูลที่ใช้ประมาณ F_m,p แยกต่างหาก"""
    if mode == "eqm":
        return _correct_block(obs_cal, mod_cal, mod_tgt, cfg, "eqm")
    q = np.linspace(0.005, 0.995, cfg.n_quantiles)
    thr = _dry_threshold(obs_cal, mod_cal, cfg.wet)
    mc = np.where(np.asarray(mod_cal, float) <= thr, 0.0, mod_cal)
    mp = np.where(np.asarray(mod_pdist, float) <= thr, 0.0, mod_pdist)
    mt = np.where(np.asarray(mod_tgt, float) <= thr, 0.0, mod_tgt)

    oq, hq, pq = _quantiles(obs_cal, q), _quantiles(mc, q), _quantiles(mp, q)
    with np.errstate(divide="ignore", invalid="ignore"):
        delta = np.where(hq > 0, pq / hq, 1.0)
    delta = np.clip(np.nan_to_num(delta, nan=1.0, posinf=1.0, neginf=1.0),
                    *cfg.delta_clip)
    tau = np.interp(mt, pq, q, left=q[0], right=q[-1])
    out = np.interp(tau, q, oq) * np.interp(tau, q, delta)
    hi = mt > pq[-1]
    if np.any(hi) and pq[-1] > 0:
        out[hi] = oq[-1] * delta[-1] * (mt[hi] / pq[-1])
    out = np.where(mt <= 0, 0.0, np.maximum(out, 0.0))
    return out, {"dry_threshold": thr,
                 "obs_wetfrac_cal": float(np.mean(np.asarray(obs_cal, float) >= cfg.wet)),
                 "delta_med": float(np.median(delta)),
                 "delta_q95": float(np.interp(0.95, q, delta)),
                 "delta_min": float(delta.min()), "delta_max": float(delta.max())}


def assert_no_leakage(cfg: Config = CFG) -> None:
    assert cfg.cal[1] < cfg.val[0], "calibration ต้องมาก่อนและห้ามซ้อนทับ validation"


# ═══════════════════════════════════════════════════════════════════════════
#  §6  METRICS
# ═══════════════════════════════════════════════════════════════════════════

def classic_metrics(o: np.ndarray, s: np.ndarray) -> dict:
    o, s = np.asarray(o, float), np.asarray(s, float)
    m = np.isfinite(o) & np.isfinite(s)
    o, s = o[m], s[m]
    if o.size < 12 or o.sum() <= 0:
        return {}
    e = s - o
    ob, sdo, sds = o.mean(), o.std(ddof=1), s.std(ddof=1)
    den = ((o - ob) ** 2).sum()
    r = float(np.corrcoef(o, s)[0, 1]) if sdo > 0 and sds > 0 else np.nan
    kge = (1 - np.sqrt((r - 1) ** 2 + (sds / sdo - 1) ** 2 + (s.mean() / ob - 1) ** 2)
           if np.isfinite(r) and sdo > 0 and ob > 0 else np.nan)
    dd = ((np.abs(s - ob) + np.abs(o - ob)) ** 2).sum()
    return {"RMSE": float(np.sqrt((e ** 2).mean())), "MAE": float(np.abs(e).mean()),
            "MBE": float(e.mean()), "PBIAS": float(100 * e.sum() / o.sum()),
            "r": r, "NSE": float(1 - (e ** 2).sum() / den) if den > 0 else np.nan,
            "KGE": float(kge), "d": float(1 - (e ** 2).sum() / dd) if dd > 0 else np.nan,
            "RSR": float(np.sqrt((e ** 2).mean()) / sdo) if sdo > 0 else np.nan}


def perkins_ss(o: np.ndarray, s: np.ndarray, nbins: int = 60) -> float:
    hi = float(max(np.nanmax(o), np.nanmax(s)))
    if hi <= 0:
        return np.nan
    ed = np.linspace(0, hi, nbins + 1)
    ho, _ = np.histogram(o, bins=ed)
    hs, _ = np.histogram(s, bins=ed)
    if ho.sum() == 0 or hs.sum() == 0:
        return np.nan
    return float(np.minimum(ho / ho.sum(), hs / hs.sum()).sum())


def ks_distance(o: np.ndarray, s: np.ndarray) -> float:
    so, ss = np.sort(o), np.sort(s)
    a = np.union1d(so, ss)
    return float(np.max(np.abs(np.searchsorted(so, a, "right") / so.size -
                               np.searchsorted(ss, a, "right") / ss.size)))


def dist_metrics(o: np.ndarray, s: np.ndarray, cfg: Config = CFG) -> dict:
    o, s = np.asarray(o, float), np.asarray(s, float)
    m = np.isfinite(o) & np.isfinite(s)
    o, s = o[m], s[m]
    if o.size < 60 or o.sum() <= 0:
        return {}
    ow, sw = o[o >= cfg.wet], s[s >= cfg.wet]
    out = {"mean": float(s.mean()),
           "PBIAS": float(100 * (s.sum() - o.sum()) / o.sum()),
           "sd_ratio": float(s.std(ddof=1) / o.std(ddof=1)),
           "wet_freq": float(np.mean(s >= cfg.wet)),
           "wetfreq_bias": float(np.mean(s >= cfg.wet) - np.mean(o >= cfg.wet)),
           "SDII": float(sw.mean()) if sw.size else np.nan,
           "PSS": perkins_ss(o, s), "KS_D": ks_distance(o, s)}
    for qq in (0.50, 0.90, 0.95, 0.99):
        a = float(np.quantile(ow, qq)) if ow.size else np.nan
        b = float(np.quantile(sw, qq)) if sw.size else np.nan
        out[f"q{int(qq*100)}_relbias_pct"] = 100 * (b - a) / a if a and a > 0 else np.nan
    return out


def _max_dry_spell(v: np.ndarray, wet: float) -> int:
    best = cur = 0
    for dry in (v < wet):
        cur = cur + 1 if dry else 0
        best = max(best, cur)
    return int(best)


def extreme_indices(series: np.ndarray, dates: pd.DatetimeIndex,
                    p95_ref: float | None = None, cfg: Config = CFG) -> dict:
    s = pd.Series(np.asarray(series, float), index=dates).dropna()
    if s.empty:
        return {}
    wet = s[s >= cfg.wet]
    if p95_ref is None:
        p95_ref = float(np.quantile(wet, 0.95)) if wet.size else np.nan
    g = s.groupby(s.index.year)
    rx5 = s.rolling(5, min_periods=5).sum().groupby(s.index.year).max()
    return {"PRCPTOT": float(g.sum().mean()), "Rx1day": float(g.max().mean()),
            "Rx5day": float(rx5.mean()),
            "R20mm": float(g.apply(lambda v: int((v >= 20).sum())).mean()),
            "R95pTOT": float(g.apply(lambda v: float(v[v >= p95_ref].sum())).mean())
            if np.isfinite(p95_ref) else np.nan,
            "CDD": float(g.apply(lambda v: _max_dry_spell(v.values, cfg.wet)).mean()),
            "_p95_ref": p95_ref}


def temporal_metrics(o: pd.Series, s: pd.Series) -> dict:
    om, sm = o.resample("MS").sum(), s.resample("MS").sum()
    ok = om.notna() & sm.notna()
    om, sm = om[ok], sm[ok]
    if om.size < 24:
        return {}
    co = om.groupby(om.index.month).mean()
    cs = sm.groupby(sm.index.month).mean()
    ao = (om - om.index.month.map(co).values).values
    as_ = (sm - sm.index.month.map(cs).values).values
    ao_, as__ = ao[np.isfinite(ao) & np.isfinite(as_)], as_[np.isfinite(ao) & np.isfinite(as_)]
    an_o = om.groupby(om.index.year).sum()
    an_s = sm.groupby(sm.index.year).sum()
    return {"clim_bias": float(np.mean(cs.values - co.values)),
            "clim_RMSE": float(np.sqrt(np.mean((cs.values - co.values) ** 2))),
            "clim_r": float(np.corrcoef(co.values, cs.values)[0, 1]),
            "monthly_r_raw": float(np.corrcoef(om.values, sm.values)[0, 1]),
            "monthly_r_anom": float(np.corrcoef(ao_, as__)[0, 1]) if ao_.size > 3 else np.nan,
            "annual_r": float(np.corrcoef(an_o.values, an_s.values)[0, 1]),
            "annual_sd_ratio": float(an_s.std(ddof=1) / an_o.std(ddof=1))}


# ═══════════════════════════════════════════════════════════════════════════
#  §7  STATISTICS
# ═══════════════════════════════════════════════════════════════════════════

def wilcoxon_paired(a: np.ndarray, b: np.ndarray, lower_better: bool = True) -> dict:
    """
    จับคู่รายสถานี (b = corrected, a = raw)
    คืนคีย์ครบทุกกรณีเสมอ: n, n_improved, median_diff, W, p_value, rank_biserial
    ถ้าจำนวนคู่ < 6 จะไม่คำนวณ p-value เพราะ Wilcoxon ไม่มีกำลังทดสอบเพียงพอ
    (n = 5 ให้ p ต่ำสุดได้เพียง 0.0625 จึงไม่มีทางถึง 0.05)
    ข้อจำกัด: สถานีไม่เป็นอิสระเชิงพื้นที่ ค่า p เป็น anti-conservative
    """
    out = {"n": 0, "n_improved": np.nan, "median_diff": np.nan,
           "W": np.nan, "p_value": np.nan, "p_min_attainable": np.nan,
           "rank_biserial": np.nan, "test_valid": False, "note": ""}
    a, b = np.asarray(a, float), np.asarray(b, float)
    m = np.isfinite(a) & np.isfinite(b)
    a, b = a[m], b[m]
    n = a.size
    out["n"] = int(n)
    # ค่า p ต่ำสุดที่เป็นไปได้ของ Wilcoxon สองทางเมื่อมี n คู่
    out["p_min_attainable"] = float(2.0 / (2 ** n)) if 0 < n < 25 else 0.0
    if n == 0:
        out["note"] = "ไม่มีคู่ข้อมูล"
        return out

    diff = b - a
    out["n_improved"] = int((diff < 0).sum()) if lower_better else int((diff > 0).sum())
    out["median_diff"] = float(np.median(diff))

    nz = diff[diff != 0]
    if n < 6:
        out["note"] = (f"n={n} < 6 ไม่คำนวณ p-value "
                       "ให้รายงานสัดส่วนสถานีที่ดีขึ้นและขนาดการเปลี่ยนแปลงแทน")
        return out
    if nz.size < 3:
        out["note"] = "ผลต่างเป็นศูนย์เกือบทั้งหมด"
        return out

    try:
        W, p = sps.wilcoxon(b, a, zero_method="wilcox", alternative="two-sided")
    except ValueError as e:
        out["note"] = f"wilcoxon error: {e}"
        return out
    rk = sps.rankdata(np.abs(nz))
    wp, wn = float(rk[nz > 0].sum()), float(rk[nz < 0].sum())
    tot = wp + wn
    out.update(W=float(W), p_value=float(p), test_valid=True,
               rank_biserial=float((wp - wn) / tot) if tot else np.nan)
    return out


def benjamini_hochberg(p, q: float = 0.05) -> np.ndarray:
    p = np.asarray(p, float)
    m = p.size
    order = np.argsort(p)
    ok = p[order] <= q * np.arange(1, m + 1) / m
    out = np.zeros(m, bool)
    k = np.where(ok)[0]
    if k.size:
        out[order[:k.max() + 1]] = True
    return out


def block_bootstrap_delta(o, a, b, fn, cfg: Config = CFG) -> dict:
    rng = np.random.default_rng(cfg.seed)
    o, a, b = map(lambda x: np.asarray(x, float), (o, a, b))
    N = o.size
    L = min(cfg.block_len, max(2, N // 10))
    nb = int(np.ceil(N / L))
    d = np.empty(cfg.boot_n)
    for i in range(cfg.boot_n):
        st = rng.integers(0, N - L, size=nb)
        idx = np.concatenate([np.arange(s, s + L) for s in st])[:N]
        d[i] = fn(o[idx], b[idx]) - fn(o[idx], a[idx])
    lo, hi = np.percentile(d, [2.5, 97.5])
    return {"delta": float(fn(o, b) - fn(o, a)), "ci_low": float(lo),
            "ci_high": float(hi),
            "p_value": float(min(1.0, 2 * min(np.mean(d <= 0), np.mean(d >= 0))))}



# ═══════════════════════════════════════════════════════════════════════════
#  §7B  ADDITIONS v3.1 — ปิดข้อท้วงติงที่เหลือ
#       [C3] extreme/hydrological performance · [C8] station–grid distance
#       [C9] variance decomposition · [C15] ensemble spread cal vs val
#       [C2,4,5] single-source-of-truth ของตัวเลขในบทคัดย่อ
# ═══════════════════════════════════════════════════════════════════════════

SW_MONSOON = (5, 6, 7, 8, 9, 10)      # ลมมรสุมตะวันตกเฉียงใต้
NE_MONSOON = (11, 12, 1, 2, 3, 4)     # ลมมรสุมตะวันออกเฉียงเหนือ


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0088
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp, dl = p2 - p1, np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return float(2 * R * np.arcsin(np.sqrt(a)))


NODATA_ABS = 1e6          # ค่าที่มากกว่านี้ถือเป็น NoData (ESRI FLT_MAX = 1.70141e38)
ELEV_RANGE = (-10.0, 3000.0)

_ALIAS = {
    "code": ("code", "station", "station_id", "stn", "id", "รหัส"),
    "lat":  ("lat", "latitude", "y", "lat_n", "latitude_n"),
    "lon":  ("lon", "long", "longitude", "x", "lon_e", "longitude_e"),
    "elev_m": ("elev_m", "elev", "elevation", "z", "alt", "altitude", "dem"),
    "dist_coast_km": ("dist_coast_km", "dist_coast", "coast_km"),
    "topography": ("topography", "topo", "class", "terrain"),
}


def load_station_meta(folder: str | Path, verbose: bool = True) -> pd.DataFrame | None:
    """
    stations.csv (ไม่บังคับ) — รองรับชื่อคอลัมน์หลายแบบ
    บังคับ: รหัสสถานี, ละติจูด, ลองจิจูด    ไม่บังคับ: ความสูง, ระยะจากชายฝั่ง, ประเภทภูมิประเทศ
    ค่า NoData ของ raster (เช่น 1.70141e+38) และค่าความสูงนอกช่วงสมเหตุสมผล
    จะถูกแปลงเป็น NaN พร้อมรายงาน ไม่ถูกแปลงเป็นศูนย์
    """
    f = None
    for name in ("stations.csv", "station_metadata.csv", "Stations.csv",
                 "stations_template.csv"):
        if (Path(folder) / name).exists():
            f = Path(folder) / name
            break
    if f is None:
        return None

    df = pd.read_csv(f)
    df.columns = [str(c).strip().lower() for c in df.columns]
    ren, used = {}, set()
    for std, alts in _ALIAS.items():
        for a in alts:
            if a in df.columns and a not in used:
                ren[a] = std
                used.add(a)
                break
    df = df.rename(columns=ren)

    if "code" not in df.columns:
        df = df.rename(columns={df.columns[0]: "code"})
    missing = [c for c in ("lat", "lon") if c not in df.columns]
    if missing:
        print(f"    [เตือน] {f.name}: ไม่พบคอลัมน์ {missing} → ข้ามการคำนวณเชิงพื้นที่")
        return None

    df["code"] = df["code"].astype(str).str.strip()
    df = df.drop_duplicates("code").set_index("code")

    for c in ("lat", "lon", "elev_m", "dist_coast_km"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
            df.loc[df[c].abs() > NODATA_ABS, c] = np.nan

    if "elev_m" in df.columns:
        bad = ~df["elev_m"].between(*ELEV_RANGE) & df["elev_m"].notna()
        df.loc[bad, "elev_m"] = np.nan
    bad_ll = ~(df["lat"].between(-90, 90) & df["lon"].between(-180, 180))
    df.loc[bad_ll, ["lat", "lon"]] = np.nan
    return df


def station_meta_report(meta: pd.DataFrame | None, stations: list[str]) -> pd.DataFrame:
    """ตรวจความครบถ้วนของ metadata เทียบกับสถานีที่ใช้จริง"""
    rows = []
    for s in stations:
        if meta is None or s not in meta.index:
            rows.append({"station": s, "in_metadata": False, "lat": np.nan,
                         "lon": np.nan, "elev_m": np.nan, "issue": "ไม่พบใน stations.csv"})
            continue
        r = meta.loc[s]
        issues = []
        if pd.isna(r.get("lat")) or pd.isna(r.get("lon")):
            issues.append("พิกัดไม่สมบูรณ์")
        if "elev_m" not in meta.columns or pd.isna(r.get("elev_m")):
            issues.append("ความสูงเป็น NoData ต้องดึงใหม่จาก DEM")
        rows.append({"station": s, "in_metadata": True,
                     "lat": r.get("lat"), "lon": r.get("lon"),
                     "elev_m": r.get("elev_m") if "elev_m" in meta.columns else np.nan,
                     "issue": "; ".join(issues) if issues else "ครบถ้วน"})
    return pd.DataFrame(rows).set_index("station")


def within_cell_geometry(fp: pd.DataFrame, meta: pd.DataFrame | None) -> pd.DataFrame:
    """
    หลักฐานเชิงปริมาณสำหรับ comment 8
    ระยะห่างสูงสุดระหว่างสถานีที่ถูกจัดอยู่ในจุดกริดเดียวกันของแต่ละแบบจำลอง
    = ขอบล่างของขนาดกริดที่แท้จริง โดยไม่ต้องเปิดไฟล์ NetCDF
    """
    rows = []
    for (mdl, cell), g in fp.groupby(["model", "grid_cell_id"]):
        stns = sorted(g.station)
        rec = {"model": mdl, "grid_cell_id": cell, "n_stations": len(stns),
               "stations": ", ".join(stns), "max_separation_km": np.nan,
               "centroid_lat": np.nan, "centroid_lon": np.nan}
        if meta is not None and all(s in meta.index for s in stns) and len(stns) > 1:
            pts = [(float(meta.loc[s, "lat"]), float(meta.loc[s, "lon"])) for s in stns]
            rec["max_separation_km"] = round(max(
                haversine_km(*a, *b) for i, a in enumerate(pts) for b in pts[i + 1:]), 2)
            rec["centroid_lat"] = round(float(np.mean([p[0] for p in pts])), 4)
            rec["centroid_lon"] = round(float(np.mean([p[1] for p in pts])), 4)
        rows.append(rec)
    return pd.DataFrame(rows).set_index(["model", "grid_cell_id"])


def annual_maxima(series: np.ndarray, dates: pd.DatetimeIndex,
                  ndays: int = 1) -> pd.Series:
    s = pd.Series(np.asarray(series, float), index=dates).dropna()
    if ndays > 1:
        s = s.rolling(ndays, min_periods=ndays).sum()
    return s.groupby(s.index.year).max().dropna()


def gumbel_lmoments(x: np.ndarray) -> tuple[float, float]:
    """ประมาณพารามิเตอร์ Gumbel ด้วย L-moments (Hosking & Wallis 1997)"""
    x = np.sort(np.asarray(x, float))
    n = x.size
    if n < 5:
        return np.nan, np.nan
    b0 = x.mean()
    b1 = np.sum(np.arange(n) * x) / (n * (n - 1))
    l1, l2 = b0, 2 * b1 - b0
    alpha = l2 / np.log(2.0)
    xi = l1 - 0.5772156649 * alpha
    return float(xi), float(alpha)


def return_levels(series: np.ndarray, dates: pd.DatetimeIndex,
                  periods=(2, 5, 10, 20), ndays: int = 1) -> dict:
    """
    ระดับฝนตามคาบการเกิดซ้ำ จากอนุกรมค่าสูงสุดรายปี
    ใช้ Gumbel-L-moments  หมายเหตุ: ช่วง validation 14 ปี -> คาบ 20 ปี
    มีความไม่แน่นอนสูง ต้องรายงานพร้อมข้อจำกัด
    """
    ams = annual_maxima(series, dates, ndays)
    out = {"n_years": int(ams.size), "AMS_mean": float(ams.mean()) if ams.size else np.nan}
    xi, al = gumbel_lmoments(ams.values)
    for T in periods:
        y = -np.log(-np.log(1 - 1.0 / T))
        out[f"RL{T}yr"] = float(xi + al * y) if np.isfinite(xi) else np.nan
        out[f"RL{T}yr_emp"] = (float(np.quantile(ams.values, 1 - 1.0 / T))
                               if ams.size >= 5 else np.nan)
    return out


def seasonal_totals(series: np.ndarray, dates: pd.DatetimeIndex) -> dict:
    """ปริมาณฝนรายฤดูมรสุม — ดัชนีที่เกี่ยวข้องกับการบริหารจัดการน้ำโดยตรง"""
    s = pd.Series(np.asarray(series, float), index=dates).dropna()
    sw = s[s.index.month.isin(SW_MONSOON)]
    ne = s[s.index.month.isin(NE_MONSOON)]
    n_yr = max(1, s.index.year.nunique())
    return {"SW_monsoon_mm_yr": float(sw.sum()) / n_yr,
            "NE_monsoon_mm_yr": float(ne.sum()) / n_yr,
            "SW_fraction": float(sw.sum() / s.sum()) if s.sum() > 0 else np.nan,
            "onset_month_wettest": int(s.groupby(s.index.month).sum().idxmax())}


def evaluate_extremes_hydro(obs: pd.DataFrame, raw: dict, corrected: dict,
                            mask: dict, cfg: Config = CFG) -> pd.DataFrame:
    """[C3] ประเมินค่าสุดขั้วและดัชนีเชิงอุทกวิทยา ทั้ง cal และ val"""
    rows = []
    for st in obs.columns:
        o = obs[st]
        for per, mk in mask.items():
            base = {"station": st, "period": per}
            rows.append({**base, "model": "obs", "dataset": "obs",
                         **return_levels(o.values[mk], o.index[mk]),
                         **{f"Rx5_{k}": v for k, v in
                            return_levels(o.values[mk], o.index[mk], ndays=5).items()
                            if k.startswith("RL")},
                         **seasonal_totals(o.values[mk], o.index[mk])})
            for mdl in raw:
                for tag, ser in (("raw", raw[mdl][st]), ("QDM", corrected[st][mdl])):
                    rows.append({**base, "model": mdl, "dataset": tag,
                                 **return_levels(ser.values[mk], o.index[mk]),
                                 **{f"Rx5_{k}": v for k, v in
                                    return_levels(ser.values[mk], o.index[mk],
                                                  ndays=5).items()
                                    if k.startswith("RL")},
                                 **seasonal_totals(ser.values[mk], o.index[mk])})
    return pd.DataFrame(rows)


def ensemble_spread_table(obs: pd.DataFrame, raw: dict, corrected: dict,
                          mask: dict, cfg: Config = CFG) -> pd.DataFrame:
    """
    [C15] การหดตัวของ ensemble spread ต้องเทียบระหว่างช่วง cal กับ val
    ถ้า spread หดเฉพาะในช่วง cal = spread contraction ไม่ใช่การลด structural uncertainty
    """
    rows = []
    for st in obs.columns:
        for per, mk in mask.items():
            o = obs[st][mk]
            ann_o = o.groupby(o.index.year).sum()
            for tag, src in (("raw", {m: raw[m][st] for m in raw}),
                             ("QDM", corrected[st])):
                ann = pd.DataFrame({m: s[mk].groupby(s[mk].index.year).sum()
                                    for m, s in src.items()})
                spread = (ann.max(axis=1) - ann.min(axis=1)).mean()
                sd_across = ann.std(axis=1, ddof=1).mean()
                rows.append({"station": st, "period": per, "dataset": tag,
                             "mean_annual_range_mm": float(spread),
                             "mean_sd_across_models_mm": float(sd_across),
                             "obs_annual_mean_mm": float(ann_o.mean()),
                             "spread_rel_obs_pct": float(100 * spread / ann_o.mean())})
    df = pd.DataFrame(rows)
    piv = df.pivot_table(index=["station", "period"], columns="dataset",
                         values="mean_sd_across_models_mm")
    piv["contraction_pct"] = 100 * (piv["QDM"] - piv["raw"]) / piv["raw"]
    return df.merge(piv["contraction_pct"].reset_index(),
                    on=["station", "period"], how="left")


def variance_decomposition(classic: pd.DataFrame, metric: str, models: list,
                           scale="monthly", period="validation",
                           dataset="QDM") -> dict:
    """[C9] แยกความแปรปรวนของดัชนีเป็นส่วนของสถานี กับ ส่วนของแบบจำลอง"""
    d = classic.query("scale==@scale and period==@period and dataset==@dataset "
                      "and model in @models")
    piv = d.pivot_table(index="station", columns="model", values=metric).dropna()
    if piv.empty or piv.shape[1] < 2:
        return {}
    g = piv.values.mean()
    ss_st = piv.shape[1] * ((piv.mean(axis=1) - g) ** 2).sum()
    ss_md = piv.shape[0] * ((piv.mean(axis=0) - g) ** 2).sum()
    ss_tot = ((piv.values - g) ** 2).sum()
    return {"metric": metric,
            "pct_station": round(100 * ss_st / ss_tot, 1),
            "pct_model": round(100 * ss_md / ss_tot, 1),
            "pct_interaction": round(100 * (ss_tot - ss_st - ss_md) / ss_tot, 1)}


def _safe_num(p: pd.DataFrame, col: str):
    if len(p) and col in p.columns and pd.notna(p[col].iloc[0]):
        return round(float(p[col].iloc[0]), 4)
    return np.nan


def _safe_flag(p: pd.DataFrame, col: str):
    if len(p) and col in p.columns and pd.notna(p[col].iloc[0]):
        return bool(p[col].iloc[0])
    return None


def _safe_ratio(p: pd.DataFrame) -> str:
    if len(p) and {"n_improved", "n"} <= set(p.columns):
        ni, n = p["n_improved"].iloc[0], p["n"].iloc[0]
        if pd.notna(ni) and pd.notna(n):
            return f"{int(ni)}/{int(n)}"
    return ""


def abstract_numbers(classic: pd.DataFrame, daily: pd.DataFrame,
                     paired: pd.DataFrame, cfg: Config = CFG) -> pd.DataFrame:
    """
    [C2, C4, C5] แหล่งตัวเลขเดียวสำหรับบทคัดย่อ/ผลการวิจัย/ข้อสรุป
    คัดลอกจากตารางนี้เท่านั้น เพื่อไม่ให้เกิดตัวเลขไม่ตรงกันระหว่างส่วนต่าง ๆ อีก
    """
    rows = []
    q = "period=='validation' and scale=='monthly' and model=='MME_monthly_series'"
    d = classic.query(q)
    for met, unit in (("RMSE", "mm month-1"), ("MAE", "mm month-1"),
                      ("MBE", "mm month-1"), ("PBIAS", "%"),
                      ("r", "-"), ("NSE", "-"), ("KGE", "-"), ("d", "-")):
        piv = d.pivot_table(index="station", columns="dataset", values=met)
        if "raw" not in piv or "QDM" not in piv:
            continue
        p = (paired.query("model=='MME_monthly_series' and metric==@met")
             if not paired.empty else pd.DataFrame())
        rows.append({
            "scale": "monthly", "metric": met, "unit": unit,
            "raw": round(piv["raw"].mean(), 3),
            "QDM": round(piv["QDM"].mean(), 3),
            "change": round(piv["QDM"].mean() - piv["raw"].mean(), 3),
            "pct_change": (round(100 * (piv["QDM"].mean() - piv["raw"].mean())
                                 / abs(piv["raw"].mean()), 1)
                           if met in ("RMSE", "MAE") else None),
            "n_improved_of_n": _safe_ratio(p),
            "p_value": _safe_num(p, "p_value"),
            "FDR_primary": _safe_flag(p, "fdr_primary"),
            "FDR_within_metric": _safe_flag(p, "fdr_within_metric"),
            "p_min_attainable": _safe_num(p, "p_min_attainable"),
            "note": (str(p["note"].iloc[0]) if len(p) and "note" in p.columns
                     and pd.notna(p["note"].iloc[0]) else ""),
        })
    dd = daily.query("period=='validation'")
    for met, unit in (("PBIAS", "%"), ("wet_freq", "-"), ("SDII", "mm day-1"),
                      ("PSS", "-"), ("sd_ratio", "-")):
        piv = dd.pivot_table(index="station", columns="dataset", values=met)
        if "raw" not in piv or "QDM" not in piv:
            continue
        rows.append({"scale": "daily", "metric": met, "unit": unit,
                     "raw": round(piv["raw"].mean(), 3),
                     "QDM": round(piv["QDM"].mean(), 3),
                     "change": round(piv["QDM"].mean() - piv["raw"].mean(), 3),
                     "pct_change": None, "n_improved_of_n": "", "p_value": np.nan,
                     "FDR_primary": None, "FDR_within_metric": None,
                     "p_min_attainable": np.nan, "note": "distribution metric"})
    out = pd.DataFrame(rows)
    out.attrs["note"] = (f"ทุกค่าเป็นผลช่วง independent validation "
                         f"{cfg.val[0]}-{cfg.val[1]} เท่านั้น")
    return out.set_index(["scale", "metric"])


def check_dois(path: str) -> pd.DataFrame:
    """
    [C20-22] ตรวจ DOI ทุกรายการกับ Crossref  ไฟล์นำเข้า: 1 DOI ต่อบรรทัด
    (ต้องต่ออินเทอร์เน็ต)
    """
    import urllib.request
    rows = []
    for line in Path(path).read_text(encoding="utf8").splitlines():
        doi = line.strip().strip(",;")
        if not doi or doi.startswith("#"):
            continue
        doi = doi.replace("https://doi.org/", "").strip()
        rec = {"doi": doi, "status": "", "title": "", "container": "",
               "year": "", "first_author": ""}
        try:
            req = urllib.request.Request(
                f"https://api.crossref.org/works/{urllib.parse.quote(doi)}",
                headers={"User-Agent": "ID1558-refcheck/1.0 (mailto:user@example.com)"})
            with urllib.request.urlopen(req, timeout=20) as r:
                msg = json.loads(r.read().decode())["message"]
            rec["status"] = "FOUND"
            rec["title"] = (msg.get("title") or [""])[0]
            rec["container"] = (msg.get("container-title") or [""])[0]
            parts = msg.get("issued", {}).get("date-parts", [[""]])[0]
            rec["year"] = parts[0] if parts else ""
            au = msg.get("author", [{}])[0]
            rec["first_author"] = f"{au.get('family','')}, {au.get('given','')}".strip(", ")
        except Exception as e:
            rec["status"] = f"NOT FOUND / ERROR: {type(e).__name__}"
        rows.append(rec)
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════════
#  §8  MAIN ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

def run_analysis(data: dict, cfg: Config = CFG, verbose: bool = True) -> dict:
    assert_no_leakage(cfg)
    obs, raw, legacy = data["obs"], data["raw"], data["legacy"]
    yr = obs.index.year.values
    mask = {"calibration": (yr >= cfg.cal[0]) & (yr <= cfg.cal[1]),
            "validation": (yr >= cfg.val[0]) & (yr <= cfg.val[1])}

    corrected: dict[str, dict[str, pd.Series]] = {}
    corrected_eqm: dict[str, dict[str, pd.Series]] = {}
    rows_d, rows_c, rows_e, rows_t, rows_delta, rows_boot = [], [], [], [], [], []

    for st in obs.columns:
        o = obs[st]
        corrected[st], corrected_eqm[st] = {}, {}
        ov = o[mask["validation"]]
        p95ref = float(np.quantile(ov[ov >= cfg.wet], 0.95))

        for mdl in sorted(raw):
            mser = raw[mdl][st]
            q_s, q_log = correct_station_model(o, mser, cfg, "qdm")
            e_s, _ = correct_station_model(o, mser, cfg, "eqm")
            corrected[st][mdl], corrected_eqm[st][mdl] = q_s, e_s
            rows_delta.append(q_log.assign(station=st, model=mdl))

            sets = {"raw": mser, "QDM": q_s, "EQM": e_s}
            if mdl in legacy:
                sets["QDM_legacy_fullperiod"] = legacy[mdl][st]

            for per, mk in mask.items():
                for tag, ser in sets.items():
                    dm = dist_metrics(o.values[mk], ser.values[mk], cfg)
                    if dm:
                        rows_d.append({"station": st, "model": mdl, "dataset": tag,
                                       "period": per, **dm})
                    cm = classic_metrics(o.values[mk], ser.values[mk])
                    if cm:
                        rows_c.append({"station": st, "model": mdl, "dataset": tag,
                                       "period": per, "scale": "daily", **cm})
                    om = o[mk].resample("MS").sum()
                    sm = ser[mk].resample("MS").sum()
                    cmm = classic_metrics(om.values, sm.values)
                    if cmm:
                        rows_c.append({"station": st, "model": mdl, "dataset": tag,
                                       "period": per, "scale": "monthly", **cmm})
                    ex = extreme_indices(ser.values[mk], o.index[mk],
                                         p95ref if per == "validation" else None, cfg)
                    if ex:
                        rows_e.append({"station": st, "model": mdl, "dataset": tag,
                                       "period": per, **ex})
                    tm = temporal_metrics(o[mk], ser[mk])
                    if tm:
                        rows_t.append({"station": st, "model": mdl, "dataset": tag,
                                       "period": per, **tm})
                ex_o = extreme_indices(o.values[mk], o.index[mk],
                                       p95ref if per == "validation" else None, cfg)
                if ex_o:
                    rows_e.append({"station": st, "model": mdl, "dataset": "obs",
                                   "period": per, **ex_o})

            mk = mask["validation"]
            rows_boot.append({"station": st, "model": mdl, "metric": "PSS",
                              **block_bootstrap_delta(o.values[mk], mser.values[mk],
                                                      q_s.values[mk], perkins_ss, cfg)})
        if verbose:
            print(f"    ✓ station {st}")

    daily = pd.DataFrame(rows_d)
    classic = pd.DataFrame(rows_c)
    extremes = pd.DataFrame(rows_e)
    temporal = pd.DataFrame(rows_t)
    delta = pd.concat(rows_delta, ignore_index=True) if rows_delta else pd.DataFrame()
    boot = pd.DataFrame(rows_boot)
    if not boot.empty:
        boot["fdr_pass"] = benjamini_hochberg(boot["p_value"].values, cfg.fdr_q)

    classic = _append_ensembles(classic, obs, raw, corrected, corrected_eqm, mask, cfg)
    mme_diag = _mme_diagnostic(obs, corrected, mask["validation"], cfg)

    return {"daily": daily, "classic": classic, "extremes": extremes,
            "temporal": temporal, "delta": delta, "bootstrap": boot,
            "mme_diagnostic": mme_diag, "corrected": corrected,
            "corrected_eqm": corrected_eqm, "mask": mask}


def _append_ensembles(classic, obs, raw, corr, corr_eqm, mask, cfg):
    """MME สามนิยาม — metric-median / monthly-series / (daily-mean เป็น diagnostic)"""
    rows = []
    for st in obs.columns:
        for per, mk in mask.items():
            om = obs[st][mk].resample("MS").sum()
            for tag, src in (("raw", {m: raw[m][st] for m in raw}),
                             ("QDM", corr[st]), ("EQM", corr_eqm[st])):
                mm = pd.DataFrame({m: s[mk].resample("MS").sum() for m, s in src.items()})
                cm = classic_metrics(om.values, mm.mean(axis=1).values)
                if cm:
                    rows.append({"station": st, "model": "MME_monthly_series",
                                 "dataset": tag, "period": per,
                                 "scale": "monthly", **cm})
    out = pd.concat([classic, pd.DataFrame(rows)], ignore_index=True)
    mem = out[out.model.isin(raw.keys())]
    med = (mem.groupby(["station", "dataset", "period", "scale"])
              .median(numeric_only=True).reset_index())
    med["model"] = "MME_metric_median"
    return pd.concat([out, med], ignore_index=True)


def _mme_diagnostic(obs, corr, mv, cfg):
    rows = []
    for st in obs.columns:
        mem = pd.DataFrame(corr[st])[mv]
        o = obs[st][mv]
        daily_mean = mem.mean(axis=1)
        daily_med = mem.median(axis=1)
        rows.append({
            "station": st,
            "obs_wetfreq": float((o >= cfg.wet).mean()),
            "obs_sd": float(o.std(ddof=1)),
            "obs_Rx1day": float(o.groupby(o.index.year).max().mean()),
            "member_wetfreq_mean": float((mem >= cfg.wet).mean().mean()),
            "member_sd_mean": float(mem.std(ddof=1).mean()),
            "member_Rx1day_mean": float(
                mem.groupby(mem.index.year).max().mean().mean()),
            "MMEdaily_mean_wetfreq": float((daily_mean >= cfg.wet).mean()),
            "MMEdaily_mean_sd": float(daily_mean.std(ddof=1)),
            "MMEdaily_mean_Rx1day": float(
                daily_mean.groupby(daily_mean.index.year).max().mean()),
            "MMEdaily_median_wetfreq": float((daily_med >= cfg.wet).mean()),
            "MMEdaily_median_sd": float(daily_med.std(ddof=1)),
        })
    return pd.DataFrame(rows).set_index("station")


# ═══════════════════════════════════════════════════════════════════════════
#  §9  TABLES
# ═══════════════════════════════════════════════════════════════════════════

METS = ["RMSE", "MAE", "MBE", "PBIAS", "r", "NSE", "KGE", "d"]
LOWER_BETTER = {"RMSE", "MAE", "KS_D"}


def table_paired(classic: pd.DataFrame, scale="monthly", period="validation",
                 base="raw", test="QDM", cfg: Config = CFG) -> pd.DataFrame:
    d = classic.query("scale==@scale and period==@period")
    rows = []
    for mdl in d.model.unique():
        sub = d[d.model == mdl]
        for met in METS:
            piv = sub.pivot_table(index="station", columns="dataset", values=met)
            if base not in piv or test not in piv:
                continue
            lb = met in LOWER_BETTER or met in ("MBE", "PBIAS")
            a = piv[base].abs() if met in ("MBE", "PBIAS") else piv[base]
            b = piv[test].abs() if met in ("MBE", "PBIAS") else piv[test]
            rows.append({"model": mdl, "metric": met,
                         **wilcoxon_paired(a.values, b.values, lower_better=lb)})
    cols = ["model", "metric", "n", "n_improved", "median_diff", "W",
            "p_value", "p_min_attainable", "rank_biserial", "test_valid", "note"]
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=cols + ["fdr_within_metric", "fdr_primary"])
    for c in cols:
        if c not in df.columns:
            df[c] = np.nan
    df = df[cols]

    # ── การควบคุม FDR ต้องกำหนด family ของสมมติฐานไว้ล่วงหน้า ──────────────
    # การรวมทุก model x metric เป็น family เดียว (56 การทดสอบ) เข้มเกินไป
    # เมื่อจำนวนสถานีน้อย เพราะค่า p ต่ำสุดที่เป็นไปได้ถูกจำกัดโดย n
    # จึงแยกเป็น (1) family ตามดัชนี ข้ามแบบจำลอง  (2) family หลักที่กำหนดไว้ก่อน
    df["fdr_within_metric"] = pd.Series([pd.NA] * len(df), dtype="object")
    for met, g in df.groupby("metric"):
        v = g["p_value"].notna()
        if v.any():
            df.loc[g.index[v], "fdr_within_metric"] = list(
                benjamini_hochberg(g.loc[v, "p_value"].values, cfg.fdr_q))

    PRIMARY_MODEL, PRIMARY_METRICS = "MME_monthly_series", ("RMSE", "PBIAS", "NSE")
    prim = df[(df.model == PRIMARY_MODEL) & (df.metric.isin(PRIMARY_METRICS))]
    df["fdr_primary"] = pd.Series([pd.NA] * len(df), dtype="object")
    v = prim["p_value"].notna()
    if v.any():
        df.loc[prim.index[v], "fdr_primary"] = list(
            benjamini_hochberg(prim.loc[v, "p_value"].values, cfg.fdr_q))
    # คงชื่อเดิมไว้เพื่อความเข้ากันได้ย้อนหลัง
    df["fdr_pass"] = df["fdr_within_metric"]
    return df


def table3_raw_validation(classic, scale="monthly") -> pd.DataFrame:
    return (classic.query("dataset=='raw' and period=='validation' and scale==@scale")
                   .groupby("model")[METS + ["RSR"]].mean().round(3))


def table4_change(classic, paired, scale="monthly") -> pd.DataFrame:
    d = classic.query("period=='validation' and scale==@scale")
    piv = d.pivot_table(index="model", columns="dataset", values=METS)
    out = pd.DataFrame(index=piv.index)
    for met in METS:
        if (met, "raw") not in piv or (met, "QDM") not in piv:
            continue
        out[f"{met}_raw"] = piv[(met, "raw")].round(3)
        out[f"{met}_QDM"] = piv[(met, "QDM")].round(3)
        out[f"{met}_Δ"] = (piv[(met, "QDM")] - piv[(met, "raw")]).round(3)
    if not paired.empty:
        for met in ("RMSE", "PBIAS", "NSE"):
            p = paired.query("metric==@met").set_index("model")
            for src, dst in (("n_improved", f"{met}_n_improved"),
                             ("p_value", f"{met}_p"),
                             ("fdr_within_metric", f"{met}_FDR")):
                out[dst] = p[src] if src in p.columns else np.nan
    return out


def table5_spread_vs_mme(classic, models, scale="monthly") -> pd.DataFrame:
    d = classic.query("dataset=='QDM' and period=='validation' and scale==@scale")
    mem = d[d.model.isin(models)]
    rows = []
    for met in METS:
        bm = mem.groupby("model")[met].mean()
        rows.append({"metric": met, "model_min": round(bm.min(), 3),
                     "model_median": round(bm.median(), 3),
                     "model_max": round(bm.max(), 3),
                     "model_range": round(bm.max() - bm.min(), 3),
                     "MME_metric_median": round(
                         d.query("model=='MME_metric_median'")[met].mean(), 3),
                     "MME_monthly_series": round(
                         d.query("model=='MME_monthly_series'")[met].mean(), 3)})
    return pd.DataFrame(rows).set_index("metric")


def table_insample_vs_independent(classic, scale="monthly") -> pd.DataFrame:
    """ขนาดของ optimistic bias — เปรียบเทียบ calibration กับ independent validation"""
    d = classic.query("dataset in ['QDM','QDM_legacy_fullperiod'] and scale==@scale")
    piv = d.pivot_table(index=["dataset", "model"], columns="period", values=METS)
    rows = []
    for (ds, mdl), r in piv.iterrows():
        rec = {"dataset": ds, "model": mdl}
        for met in METS:
            try:
                c, v = r[(met, "calibration")], r[(met, "validation")]
            except KeyError:
                continue
            rec[f"{met}_cal"] = round(c, 3)
            rec[f"{met}_val"] = round(v, 3)
            rec[f"{met}_degradation"] = round(v - c, 3)
        rows.append(rec)
    return pd.DataFrame(rows).set_index(["dataset", "model"])


def table_delta_summary(delta: pd.DataFrame) -> pd.DataFrame:
    d = delta.query("period=='validation'")
    if d.empty:
        return pd.DataFrame()
    return (d.groupby("model")[["delta_med", "delta_q95", "delta_min", "delta_max"]]
             .agg(["mean", "min", "max"]).round(4))


# ═══════════════════════════════════════════════════════════════════════════
#  §10  FIGURES
# ═══════════════════════════════════════════════════════════════════════════

def fig_design_timeline(cfg, stem) -> str:
    fig, ax = plt.subplots(figsize=(9.0, 2.4))
    c0, c1, v0, v1 = *cfg.cal, *cfg.val
    ax.barh(0, c1 - c0 + 1, left=c0, height=0.5, color="#90CAF9",
            edgecolor="k", lw=1.1)
    ax.barh(0, v1 - v0 + 1, left=v0, height=0.5, color="#FFAB91",
            edgecolor="k", lw=1.1)
    ax.text((c0 + c1) / 2, 0, f"Calibration {c0}–{c1}\nQDM transfer function fitted",
            ha="center", va="center", fontsize=10)
    ax.text((v0 + v1) / 2, 0,
            f"Independent validation {v0}–{v1}\nQDM applied · no refitting",
            ha="center", va="center", fontsize=10)
    ax.annotate("", xy=(v0 + 0.6, 0.46), xytext=(c1 - 0.6, 0.46),
                arrowprops=dict(arrowstyle="-|>", lw=1.3, color="#37474F"))
    ax.text((c1 + v0) / 2, 0.58, "observed rainfall 2001–2014 never used in fitting",
            ha="center", fontsize=9, style="italic", color="#37474F")
    ax.set_ylim(-0.55, 0.85); ax.set_yticks([]); ax.set_xlim(c0 - 1, v1 + 1)
    ax.set_xlabel("Year"); ax.grid(False)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    return savefig(fig, stem)


def fig_obs_periods(obs, cfg, stem) -> str:
    yr = obs.index.year
    mc = (yr >= cfg.cal[0]) & (yr <= cfg.cal[1])
    mv = (yr >= cfg.val[0]) & (yr <= cfg.val[1])
    fig, ax = plt.subplots(1, 2, figsize=(11.5, 3.8))
    cc = obs[mc].resample("MS").sum().groupby(lambda t: t.month).mean().mean(axis=1)
    vv = obs[mv].resample("MS").sum().groupby(lambda t: t.month).mean().mean(axis=1)
    ax[0].plot(range(1, 13), cc.values, "o-", color="#1565C0",
               label=f"Calibration {cfg.cal[0]}–{cfg.cal[1]}")
    ax[0].plot(range(1, 13), vv.values, "s--", color="#E65100",
               label=f"Validation {cfg.val[0]}–{cfg.val[1]}")
    ax[0].set_xticks(range(1, 13)); ax[0].set_xlabel("Month")
    ax[0].set_ylabel(r"Rainfall (mm month$^{-1}$)")
    ax[0].set_title("(a) Observed monthly climatology", loc="left")
    ax[0].legend(frameon=False)
    ann = obs.groupby(obs.index.year).sum().mean(axis=1)
    ax[1].bar(ann.index, ann.values,
              color=["#90CAF9" if y <= cfg.cal[1] else "#FFAB91" for y in ann.index],
              edgecolor="k", lw=0.5)
    ax[1].axvline(cfg.cal[1] + 0.5, color="k", ls="--", lw=1.2)
    ax[1].set_xlabel("Year"); ax[1].set_ylabel("Annual rainfall (mm)")
    ax[1].set_title("(b) Regional-mean annual rainfall", loc="left")
    fig.tight_layout()
    return savefig(fig, stem)


def fig_raw_vs_qdm(classic, models, stem, metric="RMSE", scale="monthly") -> str:
    d = classic.query("period=='validation' and scale==@scale and model in @models")
    piv = d.pivot_table(index="model", columns="dataset", values=metric)
    keep = [c for c in ("raw", "EQM", "QDM") if c in piv.columns]
    fig, ax = plt.subplots(figsize=(9.0, 4.0))
    x = np.arange(len(piv)); w = 0.8 / len(keep)
    cols = {"raw": C_RAW, "EQM": C_EQM, "QDM": C_QDM}
    for i, k in enumerate(keep):
        ax.bar(x + (i - (len(keep) - 1) / 2) * w, piv[k], w, label=k,
               color=cols[k], edgecolor="k", lw=0.6)
    ax.set_xticks(x); ax.set_xticklabels(piv.index, rotation=12, ha="right")
    ax.set_ylabel(f"{metric} ({'mm month$^{-1}$' if metric in ('RMSE','MAE','MBE') else '-'})")
    ax.set_title(f"Independent validation performance by model — {metric}, {scale}",
                 loc="left")
    ax.legend(frameon=False)
    fig.tight_layout()
    return savefig(fig, stem)


def fig_spatial(classic, models, stem, metric="PBIAS", scale="monthly") -> str:
    d = classic.query("period=='validation' and scale==@scale and model in @models")
    piv = d.pivot_table(index="station", columns="dataset", values=metric)
    order = list(piv.index)
    fig, ax = plt.subplots(figsize=(11.0, 4.0))
    x = np.arange(len(order)); w = 0.38
    ax.bar(x - w / 2, piv.loc[order, "raw"], w, label="Raw", color=C_RAW,
           edgecolor="k", lw=0.5)
    ax.bar(x + w / 2, piv.loc[order, "QDM"], w, label="QDM", color=C_QDM,
           edgecolor="k", lw=0.5)
    ax.axhline(0, color="k", lw=1.0)
    ax.set_xticks(x); ax.set_xticklabels(order, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel(f"{metric} (%)" if metric == "PBIAS" else metric)
    ax.set_title(f"Spatial variation of {metric} across stations — "
                 "independent validation", loc="left")
    ax.legend(frameon=False)
    fig.tight_layout()
    return savefig(fig, stem)


def fig_spread_vs_mme(classic, models, stem, metric="RMSE", scale="monthly") -> str:
    d = classic.query("dataset=='QDM' and period=='validation' and scale==@scale")
    mem = d[d.model.isin(models)]
    stns = list(dict.fromkeys(mem.station))
    data = [mem.query("station==@s")[metric].dropna().values for s in stns]
    mme = [d.query("station==@s and model=='MME_monthly_series'")[metric].mean()
           for s in stns]
    fig, ax = plt.subplots(figsize=(11.0, 4.0))
    bp = ax.boxplot(data, positions=np.arange(len(stns)), widths=0.55,
                    patch_artist=True, medianprops=dict(color="k", lw=1.2))
    for b in bp["boxes"]:
        b.set_facecolor("#BBDEFB"); b.set_edgecolor("k"); b.set_linewidth(0.8)
    ax.plot(np.arange(len(stns)), mme, "D", ms=7, color=C_RAW,
            label="Unweighted MME", zorder=5)
    ax.set_xticks(np.arange(len(stns)))
    ax.set_xticklabels(stns, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel(metric)
    ax.set_title(f"Individual-model spread versus unweighted MME — {metric}, "
                 f"{scale}, independent validation", loc="left")
    ax.legend(frameon=False)
    fig.tight_layout()
    return savefig(fig, stem)


def fig_mme_artefact(md, stem) -> str:
    fig, ax = plt.subplots(1, 3, figsize=(13.5, 3.8))
    x = np.arange(len(md)); w = 0.26
    trip = [("obs_wetfreq", "member_wetfreq_mean", "MMEdaily_mean_wetfreq",
             "Wet-day frequency", "(a)"),
            ("obs_sd", "member_sd_mean", "MMEdaily_mean_sd",
             r"Daily SD (mm day$^{-1}$)", "(b)"),
            ("obs_Rx1day", "member_Rx1day_mean", "MMEdaily_mean_Rx1day",
             r"Rx1day (mm day$^{-1}$)", "(c)")]
    for a, (co, cm, cd, lab, tag) in zip(ax, trip):
        a.bar(x - w, md[co], w, label="Observed", color=C_OBS)
        a.bar(x, md[cm], w, label="QDM members (mean)", color=C_QDM)
        a.bar(x + w, md[cd], w, label="Daily arithmetic MME", color=C_RAW)
        a.set_xticks(x); a.set_xticklabels(md.index, rotation=90, fontsize=7)
        a.set_ylabel(lab); a.set_title(tag, loc="left")
    ax[0].legend(frameon=False, fontsize=8.5)
    fig.suptitle("Artefacts of averaging daily rainfall across free-running GCMs "
                 "(independent validation period)")
    fig.tight_layout()
    return savefig(fig, stem)


def fig_cdf(obs, raw, cor, mask, station, stem, cfg) -> str:
    def wc(v):
        w = np.sort(v[v >= cfg.wet])
        return w, np.linspace(0, 1, w.size)
    fig, ax = plt.subplots(1, 2, figsize=(11.0, 3.9))
    for a, (lo, hi, t) in zip(ax, [(0, 1, "(a) Wet-day distribution"),
                                   (0.9, 1.0, "(b) Upper tail")]):
        o, po = wc(obs.values[mask])
        a.plot(o, po, "-", color=C_OBS, lw=2.2, label="Observed", zorder=6)
        for i, m in enumerate(sorted(raw)):
            r, pr = wc(raw[m].values[mask])
            a.plot(r, pr, "--", color=f"C{i}", lw=0.9, alpha=0.55)
            c, pc = wc(cor[m].values[mask])
            a.plot(c, pc, "-", color=f"C{i}", lw=1.2, label=m if a is ax[0] else None)
        a.set_xlabel(r"Daily rainfall on wet days (mm day$^{-1}$)")
        a.set_ylabel("Cumulative probability")
        a.set_ylim(lo, hi); a.set_xlim(left=0); a.set_title(t, loc="left")
    ax[0].legend(frameon=False, fontsize=8, loc="lower right")
    fig.suptitle(f"Station {station} — independent validation "
                 "(dashed = raw, solid = QDM)")
    fig.tight_layout()
    return savefig(fig, stem)


def fig_cal_vs_val(classic, stem, metric="RMSE", scale="monthly") -> str:
    d = classic.query("dataset=='QDM' and scale==@scale")
    piv = d.pivot_table(index="station", columns="period", values=metric)
    fig, ax = plt.subplots(figsize=(5.4, 5.2))
    ax.scatter(piv["calibration"], piv["validation"], s=55, c=C_QDM,
               edgecolor="k", lw=0.6, zorder=3)
    for s, r in piv.iterrows():
        ax.annotate(s, (r["calibration"], r["validation"]), fontsize=7,
                    xytext=(3, 3), textcoords="offset points")
    lo = float(min(piv.min())); hi = float(max(piv.max()))
    pad = max((hi - lo) * 0.12, 1e-3)
    ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad], "k--", lw=1.0, label="1:1")
    ax.set_xlim(lo - pad, hi + pad); ax.set_ylim(lo - pad, hi + pad)
    ax.set_xlabel(f"{metric} — calibration (in-sample)")
    ax.set_ylabel(f"{metric} — independent validation")
    ax.set_title("In-sample versus independent performance", loc="left")
    ax.legend(frameon=False)
    fig.tight_layout()
    return savefig(fig, stem)


def fig_taylor_climatology(obs, raw, cor, mask, stem, cfg) -> str:
    """Taylor diagram ที่ระดับ monthly climatology เท่านั้น (ตามข้อจำกัดเชิงวิธี)"""
    def clim(df_or_s):
        m = df_or_s[mask].resample("MS").sum()
        return m.groupby(m.index.month).mean().values

    ref = clim(obs.mean(axis=1))
    sref = ref.std(ddof=1)
    fig = plt.figure(figsize=(6.4, 6.0))
    ax = fig.add_subplot(111, projection="polar")
    ax.set_thetamin(0); ax.set_thetamax(90)
    for rr in np.arange(0.5, 2.6, 0.5) * sref:
        ax.plot(np.linspace(0, np.pi / 2, 100), [rr] * 100, ":", color="#B0BEC5", lw=0.6)
    for cc in (0.2, 0.4, 0.6, 0.8, 0.9, 0.95, 0.99):
        ax.plot([np.arccos(cc)] * 2, [0, 2.6 * sref], ":", color="#CFD8DC", lw=0.6)
        ax.text(np.arccos(cc), 2.62 * sref, f"{cc}", fontsize=7.5, ha="center")
    ax.plot(0, sref, "*", ms=16, color=C_OBS, zorder=6, label="Observed")
    for i, m in enumerate(sorted(raw)):
        for ser, mk, lbl in ((raw[m], "^", "raw"), (cor[m], "o", "QDM")):
            s = clim(ser.mean(axis=1) if isinstance(ser, pd.DataFrame) else ser)
            r = float(np.corrcoef(ref, s)[0, 1])
            ax.plot(np.arccos(np.clip(r, -1, 1)), s.std(ddof=1), mk, ms=7,
                    color=f"C{i}", mec="k", mew=0.5,
                    alpha=0.55 if lbl == "raw" else 1.0,
                    label=f"{m} ({lbl})")
    ax.set_rmax(2.7 * sref)
    ax.set_xlabel(r"Standard deviation (mm month$^{-1}$)")
    ax.set_title("Taylor diagram — monthly climatology, independent validation\n"
                 "(triangles = raw, circles = QDM; Taylor 2001)",
                 fontsize=10, loc="left")
    ax.legend(loc="upper right", bbox_to_anchor=(1.42, 1.06), frameon=False, fontsize=7)
    return savefig(fig, stem)


def fig_qc_flags(qc, zfrac, stem, cfg) -> str:
    fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.0))
    x = np.arange(len(qc))
    cols = ["#C62828" if f else "#1565C0" for f in qc["flag_any"]]
    ax[0].bar(x, qc["lag1_acf"], color=cols, edgecolor="k", lw=0.5)
    ax[0].axhline(cfg.flag_lag1, color="k", ls="--", lw=1.0,
                  label=f"flag threshold {cfg.flag_lag1}")
    ax[0].set_xticks(x); ax[0].set_xticklabels(qc.index, rotation=45,
                                               ha="right", fontsize=8)
    ax[0].set_ylabel("Lag-1 autocorrelation (daily)")
    ax[0].set_title("(a) Temporal smoothing diagnostic", loc="left")
    ax[0].legend(frameon=False)
    im = ax[1].imshow(zfrac.T.values, aspect="auto", cmap="RdYlBu_r",
                      vmin=0, vmax=1,
                      extent=[zfrac.index.min() - .5, zfrac.index.max() + .5,
                              len(zfrac.columns) - .5, -.5])
    ax[1].set_yticks(range(len(zfrac.columns)))
    ax[1].set_yticklabels(zfrac.columns, fontsize=8)
    ax[1].axvline(cfg.cal[1] + 0.5, color="k", lw=1.6)
    ax[1].set_xlabel("Year"); ax[1].grid(False)
    ax[1].set_title("(b) Annual fraction of zero-rainfall days", loc="left")
    fig.colorbar(im, ax=ax[1], fraction=0.03, pad=0.02)
    fig.tight_layout()
    return savefig(fig, stem)


# ═══════════════════════════════════════════════════════════════════════════
#  §11  EXPORT
# ═══════════════════════════════════════════════════════════════════════════

def _writable(path: Path) -> tuple[bool, str]:
    """ตรวจว่าเขียนไฟล์ปลายทางได้หรือไม่ ก่อนเริ่มวิเคราะห์"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            with open(path, "ab"):
                pass
        else:
            with open(path, "wb"):
                pass
            path.unlink()
        return True, ""
    except PermissionError:
        return False, ("ไฟล์ถูกล็อก — น่าจะเปิดค้างอยู่ใน Excel "
                       "ให้ปิดโปรแกรมแล้วรันใหม่")
    except OSError as e:
        return False, f"{type(e).__name__}: {e}"


def preflight_output_check(outdir: str | Path) -> None:
    """เรียกก่อนเริ่มวิเคราะห์ เพื่อไม่ให้เสียเวลารันแล้วเขียนไฟล์ไม่ได้"""
    target = Path(outdir) / "ID1558_results_v3.xlsx"
    ok, msg = _writable(target)
    if not ok:
        print("\n" + "!" * 74)
        print(f"  หยุดก่อนเริ่มวิเคราะห์: {target}")
        print(f"  {msg}")
        print("!" * 74 + "\n")
        raise SystemExit(1)


def export_excel(outdir: Path, sheets: dict) -> str:
    """
    เขียน workbook  ถ้าไฟล์ถูกล็อก (เปิดค้างใน Excel) จะไม่ทิ้งผลรัน
    แต่จะบันทึกเป็นไฟล์ชื่อใหม่พร้อมเวลากำกับ และสำรองชีตสำคัญเป็น CSV
    """
    from datetime import datetime
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / "ID1558_results_v3.xlsx"

    def _write(target: Path) -> None:
        with pd.ExcelWriter(target, engine="openpyxl") as xl:
            for name, df in sheets.items():
                if isinstance(df, pd.DataFrame) and not df.empty:
                    df.to_excel(xl, sheet_name=name[:31])

    try:
        _write(path)
        print(f"    ✓ {path.name}")
        return str(path)
    except PermissionError:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        alt = outdir / f"ID1558_results_v3_{stamp}.xlsx"
        print(f"    ⚠ เขียน {path.name} ไม่ได้ (ไฟล์เปิดค้างใน Excel)")
        try:
            _write(alt)
            print(f"    ✓ บันทึกเป็น {alt.name} แทน — ผลรันไม่สูญหาย")
            return str(alt)
        except PermissionError:
            csvdir = outdir / f"csv_backup_{stamp}"
            csvdir.mkdir(parents=True, exist_ok=True)
            for name, df in sheets.items():
                if isinstance(df, pd.DataFrame) and not df.empty:
                    df.to_csv(csvdir / f"{name[:40]}.csv", encoding="utf-8-sig")
            print(f"    ✓ สำรองเป็น CSV ที่ {csvdir.name} — ผลรันไม่สูญหาย")
            return str(csvdir)


# ═══════════════════════════════════════════════════════════════════════════
#  §12  DRIVER
# ═══════════════════════════════════════════════════════════════════════════

def cmd_inspect(folder: str, cfg: Config) -> None:
    print("═" * 78)
    print("  INSPECT — สำรวจข้อมูลก่อนวิเคราะห์")
    print("═" * 78)
    data = load_all(folder, cfg)
    obs = data["obs"]
    print(f"\nโฟลเดอร์ : {folder}")
    print(f"สถานี    : {len(cfg.stations)} → {', '.join(cfg.stations)}")
    print(f"แบบจำลอง : {len(cfg.models)} → {', '.join(cfg.models)}")
    print(f"ช่วงเวลา : {obs.index.min().date()} ถึง {obs.index.max().date()} "
          f"({len(obs)} วัน)")
    print(f"legacy BC: {', '.join(data['legacy']) if data['legacy'] else '— ไม่มี —'}")

    print("\n[Table 2 metadata] variant / grid label ที่สกัดจากชื่อไฟล์")
    print(pd.DataFrame(data["meta"]).T.to_string())

    print("\n[QC] รายงานคุณภาพข้อมูลสังเกตการณ์")
    qc = qc_report(obs, cfg)
    show = ["missing_pct", "zero_pct", "wet_freq", "SDII", "sd_daily", "max_daily",
            "lag1_acf", "annual_mean", "pettitt_zerofrac_p",
            "pettitt_zerofrac_cp_year", "flag_smoothed", "flag_inhomogeneous"]
    print(qc[show].round(3).to_string())

    flagged = qc.index[qc["flag_any"]].tolist()
    if flagged:
        print(f"\n  ⚠ สถานีที่ติดธงเตือน: {', '.join(flagged)}")
        print("    ต้องตรวจสอบต้นทางก่อนนำผลไปตีความเชิงภูมิประเทศ")

    print("\n[Station metadata] ตรวจความครบถ้วนของพิกัด/ความสูง")
    smeta = load_station_meta(folder)
    srep = station_meta_report(smeta, cfg.stations)
    print(srep.round(4).to_string())
    nbad = int((srep["issue"] != "ครบถ้วน").sum())
    if nbad:
        print(f"    ⚠ {nbad} สถานีมีปัญหา metadata — ห้ามแทนค่า NoData ด้วย 0")

    print("\n[Grid footprint] สถานีที่ใช้จุดกริดเดียวกันของแต่ละแบบจำลอง")
    fp = grid_footprint(data["raw"])
    print(grid_footprint_summary(fp, data["meta"]).to_string())
    geo = within_cell_geometry(fp, smeta)
    print(geo[["n_stations", "max_separation_km", "stations"]].to_string())

    print("\n[Period contrast] calibration เทียบ independent validation")
    pc = period_contrast(obs, cfg)
    print(pc[["annual_cal", "annual_val", "annual_diff_pct", "wetfreq_cal",
              "wetfreq_val", "MWU_p_annual", "KS_p_wetday"]].round(3).to_string())
    print("\n[Station tiers] จำแนกด้วย 2 เกณฑ์อิสระ")
    tiers = classify_stations(qc, pc, cfg)
    print(tiers[["SDII", "lag1_acf", "max_daily", "pettitt_p",
                 "wetfreq_rel_change", "tier", "reason"]].to_string())
    for t in ("A", "B", "C"):
        g = tiers.index[tiers.tier == t].tolist()
        print(f"    Tier {t}: {len(g)} สถานี → {', '.join(g) if g else '—'}")
    print("\nพร้อมรัน --run แล้ว\n")


def cmd_run(folder: str, out: str, cfg: Config,
            homogeneous_only: bool = False, exclude: list[str] | None = None,
            tier_filter: str | None = None) -> None:
    outdir = Path(out)
    outdir.mkdir(parents=True, exist_ok=True)
    preflight_output_check(outdir)
    figdir = outdir / "figures"
    figdir.mkdir(exist_ok=True)
    set_style()

    print("═" * 78)
    print(f"  RUN — calibration {cfg.cal[0]}–{cfg.cal[1]} · "
          f"independent validation {cfg.val[0]}–{cfg.val[1]}")
    print("═" * 78)
    data = load_all(folder, cfg)
    obs, raw = data["obs"], data["raw"]

    print("\n§1 QC และ data integrity")
    qc_full = qc_report(obs, cfg)
    zfrac = yearly_zero_fraction(obs)
    print(f"    สถานีติดธงเตือน: {', '.join(qc_full.index[qc_full['flag_any']]) or '— ไม่มี —'}")

    pc_full = period_contrast(obs, cfg)
    tiers = classify_stations(qc_full, pc_full, cfg)
    for t in ("A", "B", "C"):
        g = tiers.index[tiers.tier == t].tolist()
        print(f"    Tier {t}: {len(g)} สถานี → {', '.join(g) if g else '—'}")

    drop = list(exclude or [])
    if tier_filter:
        keep_t = set(tier_filter.upper())
        drop += [s for s in tiers.index if tiers.loc[s, "tier"] not in keep_t
                 and s not in drop]
    if homogeneous_only:
        drop += [s for s in tiers.index[tiers.tier != "A"] if s not in drop]
    if drop:
        keep = [s for s in obs.columns if s not in drop]
        if len(keep) < 3:
            raise SystemExit("เหลือสถานีน้อยเกินไปหลังการคัดออก")
        print(f"    [sensitivity] ตัดออก {len(drop)} สถานี: {', '.join(drop)}")
        print(f"    [sensitivity] คงเหลือ {len(keep)} สถานี: {', '.join(keep)}")
        obs = obs[keep]
        raw = {m: d[keep] for m, d in raw.items()}
        data["obs"], data["raw"] = obs, raw
        data["legacy"] = {m: d[keep] for m, d in data["legacy"].items()}
        cfg.stations = keep
    qc = qc_full.loc[cfg.stations]

    print("\n§2 Grid footprint")
    fp = grid_footprint(raw)
    fps = grid_footprint_summary(fp, data["meta"])
    print(fps.to_string())
    smeta = load_station_meta(folder)
    srep = station_meta_report(smeta, cfg.stations)
    geo = within_cell_geometry(fp, smeta)
    if smeta is None:
        print("    [หมายเหตุ] ไม่พบ stations.csv → ไม่คำนวณระยะห่างภายในกริด")
    else:
        v = geo["max_separation_km"].dropna()
        if len(v):
            print(f"    ระยะห่างสูงสุดภายในกริดเดียวกัน: {v.max():.1f} km "
                  f"(มัธยฐาน {v.median():.1f} km)")
        nbad = int((srep["issue"] != "ครบถ้วน").sum())
        if nbad:
            print(f"    ⚠ {nbad} สถานีมี metadata ไม่ครบ (ดูชีต T23)")

    print("\n§3 Period contrast")
    pc = period_contrast(obs, cfg)
    tiers = tiers.loc[cfg.stations]

    print("\n§4 Bias correction + evaluation")
    res = run_analysis(data, cfg)

    print("\n§5 Statistical tests")
    _pfloor = 2.0 / (2 ** len(cfg.stations))
    print(f"    จำนวนคู่ (สถานี) = {len(cfg.stations)} → ค่า p ต่ำสุดที่เป็นไปได้ "
          f"ของ Wilcoxon = {_pfloor:.4f}")
    if len(cfg.stations) < 6:
        print(f"    ⚠ เหลือ {len(cfg.stations)} สถานี — Wilcoxon signed-rank "
              "ไม่มีกำลังทดสอบเพียงพอ (n<6 ให้ p ต่ำสุดได้ 0.0625)")
        print("      ให้รายงานสัดส่วนสถานีที่ดีขึ้นและขนาดการเปลี่ยนแปลงพร้อม "
              "bootstrap CI แทนค่า p")
    paired = table_paired(res["classic"], "monthly", "validation", "raw", "QDM", cfg)
    paired_eqm = table_paired(res["classic"], "monthly", "validation", "EQM", "QDM", cfg)

    print("\n§5b ค่าสุดขั้ว / ดัชนีเชิงอุทกวิทยา และ ensemble spread")
    exh = evaluate_extremes_hydro(obs, raw, res["corrected"], res["mask"], cfg)
    spr = ensemble_spread_table(obs, raw, res["corrected"], res["mask"], cfg)
    vdec = pd.DataFrame([variance_decomposition(res["classic"], m, cfg.models)
                         for m in ("RMSE", "PBIAS", "NSE", "KGE")
                         if variance_decomposition(res["classic"], m, cfg.models)])
    print(vdec.to_string(index=False) if not vdec.empty else "    (ข้ามการแยกความแปรปรวน)")
    sc = spr.query("dataset=='QDM'").groupby("period")["contraction_pct"].mean()
    for per, v in sc.items():
        print(f"    ensemble spread หลัง QDM เทียบ raw ({per}): {v:+.1f}%")

    print("\n§6 Tables")
    t3 = table3_raw_validation(res["classic"])
    t4 = table4_change(res["classic"], paired)
    t5 = table5_spread_vs_mme(res["classic"], cfg.models)
    t6 = table_insample_vs_independent(res["classic"])
    t7 = table_delta_summary(res["delta"])
    abst = abstract_numbers(res["classic"], res["daily"], paired, cfg)
    print(t3.to_string())
    print("\n    [ตัวเลขสำหรับบทคัดย่อ — คัดลอกจากตารางนี้เท่านั้น]")
    print(abst.to_string())

    print("\n§7 Figures")
    mv = res["mask"]["validation"]
    fig_design_timeline(cfg, str(figdir / "F02_design_timeline"))
    fig_obs_periods(obs, cfg, str(figdir / "F03_observed_periods"))
    fig_raw_vs_qdm(res["classic"], cfg.models, str(figdir / "F04_model_performance"))
    fig_spatial(res["classic"], cfg.models, str(figdir / "F05_spatial_PBIAS"))
    fig_spread_vs_mme(res["classic"], cfg.models, str(figdir / "F06_spread_vs_MME"))
    fig_cal_vs_val(res["classic"], str(figdir / "F07_cal_vs_val"))
    fig_mme_artefact(res["mme_diagnostic"], str(figdir / "S01_MME_artefact"))
    fig_qc_flags(qc_full, zfrac, str(figdir / "S02_QC_diagnostics"), cfg)
    st0 = cfg.stations[0]
    fig_cdf(obs[st0], {m: raw[m][st0] for m in raw},
            res["corrected"][st0], mv, st0, str(figdir / "S03_CDF"), cfg)
    fig_taylor_climatology(obs, raw,
                           {m: pd.DataFrame({s: res["corrected"][s][m]
                                             for s in cfg.stations}) for m in raw},
                           mv, str(figdir / "S04_taylor_climatology"), cfg)

    print("\n§8 Export")
    xls = export_excel(outdir, {
        "T01_QC_stations": qc_full,
        "T01b_station_tiers": classify_stations(qc_full, pc_full, cfg),
        "T02_grid_footprint": fp.set_index(["model", "station"]),
        "T02b_grid_summary": fps,
        "T03_period_contrast": pc,
        "T04_raw_validation": t3,
        "T05_change_after_QDM": t4,
        "T06_spread_vs_MME": t5,
        "T07_insample_vs_indep": t6,
        "T08_QDM_delta": t7,
        "T09_wilcoxon_raw_QDM": paired.set_index(["model", "metric"]),
        "T10_wilcoxon_EQM_QDM": paired_eqm.set_index(["model", "metric"]),
        "T11_daily_distribution": res["daily"],
        "T12_classic_metrics": res["classic"],
        "T13_extreme_indices": res["extremes"],
        "T14_monthly_annual": res["temporal"],
        "T15_bootstrap": res["bootstrap"],
        "T16_MME_diagnostic": res["mme_diagnostic"],
        "T17_zero_fraction": zfrac,
        "T18_extremes_hydro": exh,
        "T19_ensemble_spread": spr,
        "T20_variance_decomp": vdec,
        "T21_grid_geometry": geo,
        "T23_station_metadata": srep,
        "T22_ABSTRACT_NUMBERS": abst,
    })
    with open(outdir / "run_config.json", "w", encoding="utf8") as f:
        json.dump({"cal": cfg.cal, "val": cfg.val, "wet_threshold": cfg.wet,
                   "window_days": cfg.window_days, "n_quantiles": cfg.n_quantiles,
                   "delta_clip": cfg.delta_clip, "bootstrap_n": cfg.boot_n,
                   "block_len_days": cfg.block_len, "fdr_q": cfg.fdr_q,
                   "stations": cfg.stations, "models": cfg.models,
                   "model_meta": data["meta"]}, f, indent=2, ensure_ascii=False)
    print(f"\nเสร็จสมบูรณ์ → {outdir}\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="CMIP6 QDM split-sample pipeline v3.0")
    ap.add_argument("--dir", help="โฟลเดอร์ข้อมูล")
    ap.add_argument("--out", default="./out_v3")
    ap.add_argument("--cal", default="1981-2000")
    ap.add_argument("--val", default="2001-2014")
    ap.add_argument("--window", type=int, default=30)
    ap.add_argument("--boot", type=int, default=500)
    ap.add_argument("--pdf", action="store_true")
    ap.add_argument("--homogeneous-only", action="store_true",
                    help="ใช้เฉพาะสถานีที่ผ่านการทดสอบความสม่ำเสมอ (sensitivity run)")
    ap.add_argument("--exclude", default="",
                    help="รหัสสถานีที่ต้องการตัดออก คั่นด้วยจุลภาค")
    ap.add_argument("--tier", default="",
                    help="เลือก tier ที่ใช้ เช่น A, AB, ABC (ว่าง = ใช้ทุกสถานี)")
    ap.add_argument("--inspect", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--check-dois", default="",
                    help="ไฟล์ .txt ที่มี DOI บรรทัดละรายการ (ต้องต่ออินเทอร์เน็ต)")
    ap.add_argument("--make-station-template", action="store_true",
                    help="สร้าง stations_template.csv สำหรับกรอกพิกัด/ความสูง")
    a = ap.parse_args()

    CFG.cal = tuple(int(v) for v in a.cal.split("-"))
    CFG.val = tuple(int(v) for v in a.val.split("-"))
    CFG.window_days = a.window
    CFG.boot_n = a.boot
    CFG.save_pdf = a.pdf

    if a.check_dois:
        df = check_dois(a.check_dois)
        out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
        df.to_csv(out / "doi_check.csv", index=False, encoding="utf-8-sig")
        print(df.to_string(index=False))
        print(f"\n→ {out/'doi_check.csv'}")
        return
    if a.make_station_template:
        d = load_all(a.dir or ".", CFG)
        tpl = pd.DataFrame({"code": CFG.stations, "lat": "", "lon": "",
                            "elev_m": "", "dist_coast_km": "", "topography": "",
                            "source_agency": "", "verified_from": ""})
        tpl.to_csv(Path(a.dir or ".") / "stations_template.csv",
                   index=False, encoding="utf-8-sig")
        print("สร้าง stations_template.csv แล้ว — กรอกพิกัดและความสูงจาก DEM "
              "แล้วเปลี่ยนชื่อเป็น stations.csv")
        return
    if a.selftest:
        cmd_inspect(a.dir or ".", CFG)
    elif a.inspect:
        cmd_inspect(a.dir, CFG)
    elif a.run:
        cmd_run(a.dir, a.out, CFG, homogeneous_only=a.homogeneous_only,
                exclude=[x.strip() for x in a.exclude.split(",") if x.strip()],
                tier_filter=a.tier or None)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
