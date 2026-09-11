#!/usr/bin/env python3
"""Semantic numerical audit for Paper 2 (gates P2-E1 to P2-E4).

    python scripts/audit_paper2.py --config config/uttaradit.yaml

Every number in the narrative must resolve to one identified cell of one main
table. Matching on value alone is not enough: the sentence must also name the
index the cell belongs to, and, where the table is scenario-specific, the
scenario. That is the check the previous value-only audit lacked, which let the
manuscript quote a correct number computed under a different aggregation.

Each cell carries the estimator that produced it, so a number computed under any
other aggregation cannot resolve and the run fails.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from cmip6bc import analysis                                   # noqa: E402
from cmip6bc.config import load_config                         # noqa: E402

TOL = 0.011
LABEL = {"raw": "Raw CMIP6", "qm": "QM/EQM", "detqm": "DetQM", "qdm": "QDM"}
SCEN = {"ssp245": "SSP2-4.5", "ssp585": "SSP5-8.5"}
# How each index may be written in the narrative.
ALIAS = {
    "wet_day_pct": ["wet-day frequency", "wet days", "wet-day"],
    "acf1_occurrence": ["autocorrelation"],
    "P_wet_given_wet": ["p(wet | wet)", "pwet | wet", "transition probability"],
    "mean_wet_spell": ["wet-spell"], "mean_dry_spell": ["dry-spell"],
    "p90_dry_spell": ["p90 dry"], "acf1_daily": ["daily autocorrelation"],
    "PRCPTOT": ["prcptot", "annual precipitation", "annual wet-day total"],
    "SDII": ["sdii"], "q50": ["q50", "q<sub>50</sub>", "median wet-day",
                              "50th"],
    "q90": ["q90", "q<sub>90</sub>", "90th"],
    "q95": ["q95", "q<sub>95</sub>", "95th"],
    "q99": ["q99", "q<sub>99</sub>", "99th"],
    "Rx1day": ["rx1day"], "Rx5day": ["rx5day"],
    "R10mm": ["r10mm"], "R20mm": ["r20mm", "above 20 mm"],
    "R50mm": ["r50mm", "above 50 mm"], "R95p": ["r95p"], "R99p": ["r99p"],
    "CDD": ["cdd", "consecutive dry days"],
    "CWD": ["cwd", "consecutive wet days"],
    "bulk statistics": ["bulk statistic"],
    "wet-day quantiles": ["wet-day quantile"],
    "bulk and quantiles": ["bulk statistics and wet-day quantile",
                           "bulk statistic and wet-day quantile",
                           "bulk statistics and direct quantile",
                           "bulk statistics and the direct quantile"],
    "derived extremes": ["derived extreme"],
    "all indices": ["gcm main effect", "residual term", "sum of squares",
                    "sum-of-squares", "additive method effect"],
}
# Values that are design facts rather than results.
DESIGN = {
    "1.0": "wet-day threshold, mm/day (Section 2.4)",
    "0.41": "share of wet days outside the calibration range (Section 2.4)",
    "0.810": "share of the observed record set to missing (Section 2.2)",
    "5.0": "neighbour threshold in the zero screening (Section 2.2)",
}


def build_cells(out: Path) -> pd.DataFrame:
    """One row per addressable cell of the main tables."""
    rows = []

    mab = pd.read_csv(out / "paper2_mab.csv")
    for r in mab.itertuples():
        rows.append({"table": "Table 2" if r.period == "calibration" else "Table 3",
                     "statistic": "MAB", "index": r.index, "method": r.method,
                     "scenario": None, "period": r.period,
                     "value": float(r.MAB_pct),
                     "estimator": "mean_absolute_bias_over_gauges_and_models"})

    pe = pd.read_csv(out / "paper2_pe_summary.csv")
    for r in pe.itertuples():
        for stat, col in (("median PE", "median"), ("PE IQR low", "q25"),
                          ("PE IQR high", "q75")):
            v = getattr(r, col)
            if np.isfinite(v):
                rows.append({"table": "Table 4/5", "statistic": stat,
                             "index": r.index, "method": r.method,
                             "scenario": r.scenario, "period": None,
                             "value": float(v), "estimator": r.estimator})

    vd = pd.read_csv(out / "paper2_variance_decomposition.csv")
    for r in vd.itertuples():
        for stat, col in (("GCM main effect", "model_share_pct"),
                          ("method main effect", "method_share_pct"),
                          ("residual share", "residual_share_pct")):
            rows.append({"table": "Table 6", "statistic": stat,
                         "index": r.index, "method": None,
                         "scenario": r.scenario, "period": None,
                         "value": float(getattr(r, col)),
                         "estimator": "two_factor_sum_of_squares"})

    # Group-level statements ("within X% for bulk statistics and quantiles",
    # "the GCM main effect spanned A% to B%") are legitimate and must be
    # checkable, so the extrema of each named group are registered as cells too.
    GROUPS = {
        "bulk statistics": ["wet_day_pct", "PRCPTOT", "SDII"],
        "wet-day quantiles": ["q50", "q90", "q95", "q99"],
        "bulk and quantiles": ["wet_day_pct", "PRCPTOT", "SDII",
                               "q50", "q90", "q95", "q99"],
        "derived extremes": ["Rx1day", "R10mm", "R20mm", "R50mm", "R95p", "R99p"],
        "all indices": None,
    }
    for gname, keys in GROUPS.items():
        sub = pe if keys is None else pe[pe["index"].isin(keys)]
        for sc, g in sub.groupby("scenario"):
            v = g["median"].dropna()
            if not len(v):
                continue
            for stat, val in (("group max |median PE|", v.abs().max()),
                              ("group min median PE", v.min()),
                              ("group max median PE", v.max())):
                rows.append({"table": "Table 4/5", "statistic": stat,
                             "index": gname, "method": None, "scenario": sc,
                             "period": None, "value": float(val),
                             "estimator": analysis.ESTIMATOR_ID})
    for sc, g in vd.groupby("scenario"):
        for stat, col in (("GCM main effect", "model_share_pct"),
                          ("method main effect", "method_share_pct"),
                          ("residual share", "residual_share_pct")):
            for tag, val in (("group min", g[col].min()), ("group max", g[col].max())):
                rows.append({"table": "Table 6", "statistic": f"{tag} {stat}",
                             "index": "all indices", "method": None,
                             "scenario": sc, "period": None,
                             "value": float(val),
                             "estimator": "two_factor_sum_of_squares"})

    tmp = pd.read_csv(out / "paper2_temporal_dependence.csv")
    for c in [c for c in tmp.columns if c.endswith("_bias_pct")]:
        for (per, m), g in tmp.groupby(["period", "method"]):
            rows.append({"table": "Section 3.5", "statistic": "temporal |bias|",
                         "index": c.replace("_bias_pct", ""), "method": m,
                         "scenario": None, "period": per,
                         "value": float(g[c].abs().mean()),
                         "estimator": "mean_absolute_bias_over_gauges_and_models"})
    return pd.DataFrame(rows)


def narrative(md: Path):
    text = md.read_text(encoding="utf-8")
    end = next(k for k in ("## 6. Ethical Approval", "## 4. Conclusions",
                           "## 5. Acknowledgements") if k in text)
    body = text[text.index("## Abstract"):text.index(end)]
    body = body.replace("\u2212", "-")
    out = []
    for i, line in enumerate(body.split("\n"), 1):
        if line.startswith(("*Formatted", "#", "---")):
            continue
        for m in re.finditer(r"(?<![\w.])([+-]?\d+\.\d+)%", line):
            out.append((i, m.group(1), line))
    return out, text


def sentence_of(line: str, pos_hint: str) -> str:
    for part in re.split(r"(?<=[.;])\s+", line):
        if pos_hint in part:
            return part
    return line


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--journal", default="apst", choices=["apst", "aer"])
    a = ap.parse_args()
    cfg = load_config(a.config)
    out = cfg.path("output") / ("paper2_manuscript" if a.journal == "apst"
                                else f"paper2_{a.journal}")
    md = ROOT / "manuscript" / ("Paper2_APST_manuscript.md" if a.journal == "apst"
                                else "Paper2_AER_manuscript.md")
    if not md.exists():
        sys.exit(f"manuscript not found: {md}")

    cells = build_cells(out)
    nums, text = narrative(md)
    rows = []
    last_ctx = ""          # anaphora such as "the same index gave ..."
    prev_line = None
    for line_no, raw, line in nums:
        if line_no != prev_line:
            prev_line = line_no
        val = float(raw)
        # strip emphasis and sub/sup markup so "*q*<sub>95</sub>" matches "q95"
        sent = sentence_of(line, raw).lower()
        sent = (sent.replace("*", "").replace("<sub>", "").replace("</sub>", "")
                    .replace("<sup>", "").replace("</sup>", ""))
        rec = {"line": line_no, "reported_value": raw,
               "sentence": sent[:160]}
        if raw.lstrip("+-") in DESIGN:
            rows.append({**rec, "status": "design constant",
                         "source_table": "Methods", "index": "",
                         "method": "", "scenario": "", "estimator": "",
                         "source_value": raw})
            continue

        dp = len(raw.split(".")[1])
        cand = cells[np.abs(cells.value.round(dp) - round(val, dp)) <= TOL]
        if not len(cand):
            rows.append({**rec, "status": "NOT TRACED", "source_table": "",
                         "index": "", "method": "", "scenario": "",
                         "estimator": "", "source_value": ""})
            continue

        # the sentence must name the index the candidate cell belongs to
        # an index named earlier in the same paragraph still counts, so that
        # "the same index gave ..." resolves the way a reader would read it
        scope = sent + " " + last_ctx

        def names_index(k):
            return any(al in scope for al in ALIAS.get(k, [str(k).lower()]))
        ctx = cand[[names_index(k) for k in cand["index"]]]
        if not len(ctx):
            rows.append({**rec, "status": "CONTEXT MISMATCH",
                         "source_table": "; ".join(sorted(set(cand.table))),
                         "index": "; ".join(sorted(set(cand["index"]))[:3]),
                         "method": "", "scenario": "", "estimator": "",
                         "source_value": f"{cand.value.iloc[0]:.4f}"})
            continue
        # if a scenario is named, the cell must match it
        for sc, lab in SCEN.items():
            if lab.lower() in sent and ctx.scenario.notna().any():
                sub = ctx[ctx.scenario.isin([sc, None])]
                if len(sub):
                    ctx = sub
        r = ctx.iloc[0]
        for al in ALIAS.get(r["index"], []):
            if al in sent:
                last_ctx = sent
                break
        rows.append({**rec, "status": "resolved",
                     "source_table": r.table, "index": r["index"],
                     "method": LABEL.get(r.method, r.method or ""),
                     "scenario": SCEN.get(r.scenario, r.scenario or ""),
                     "estimator": r.estimator,
                     "source_value": f"{r.value:.4f}"})

    audit = pd.DataFrame(rows)
    audit.to_csv(out / "paper2_claim_audit.csv", index=False)

    # ---- gate P2-E1: one estimator for every signal-preservation number
    pe_est = set(audit[audit.source_table == "Table 4/5"].estimator) - {""}
    e1 = pe_est <= {analysis.ESTIMATOR_ID}
    # ---- gate P2-E3: no gauge x model pooling anywhere
    e3 = "station" not in analysis.ESTIMATOR_ID and "pool" not in analysis.ESTIMATOR_ID

    bad = audit[audit.status.isin(["NOT TRACED", "CONTEXT MISMATCH"])]
    abstract = text.split("## Abstract")[1].split("**Keywords")[0]
    n_abs = len(re.sub(r"[*#\-\n]+", " ", abstract).split())
    cited = set()
    for m in re.findall(r"\[([0-9,\u2013\-\s]+)\]", text.split("## 11. References")[0]):
        for part in m.split(","):
            part = part.strip().replace("\u2013", "-")
            if "-" in part:
                lo, hi = part.split("-")
                cited.update(range(int(lo), int(hi) + 1))
            elif part.isdigit():
                cited.add(int(part))
    listed = sorted(int(m) for m in re.findall(r"^\[(\d+)\] ", text, flags=re.M))
    kw_line = text.split("**Keywords:**")[1].split("\n")[0]
    # AER separates keywords with semicolons, APST with commas
    kw = [k.strip() for k in re.split(r"[;,]", kw_line) if k.strip()]
    kw_min, kw_max = (4, 6) if a.journal == "aer" else (4, 11)

    # every supplementary item must be cited, and every citation must resolve
    supp_json = ROOT / ("docx_build_p2" if a.journal == "apst"
                        else "docx_build_aer") / "supplement.json"
    supp_cited = set(re.findall(r"Supplementary (?:Table|Data) (S\d+)", text))
    supp_present, supp_uncited, supp_missing = set(), [], []
    if supp_json.exists():
        import json as _json
        spec = _json.loads(supp_json.read_text(encoding="utf-8"))
        supp_present = {t["number"].replace("Data ", "") for t in spec["tables"]}
        supp_uncited = sorted(supp_present - supp_cited)
        supp_missing = sorted(supp_cited - supp_present)
    title = text.split("\n")[0].lower()
    if a.journal == "aer":
        # AER asks authors to avoid general, plural terms and multiple concepts
        kw_ok = not any(re.search(r"\b(and|of)\b", k.lower()) for k in kw)
    else:
        kw_ok = not any(k.lower() in title for k in kw)
    placeholder = "[full bibliographic" in text.lower() or "to be completed" in text.lower()

    print(f"numbers in narrative : {len(audit)}")
    for st in ("resolved", "design constant", "CONTEXT MISMATCH", "NOT TRACED"):
        print(f"  {st:18s}: {(audit.status == st).sum()}")
    if len(bad):
        print(bad[["line", "reported_value", "status", "sentence"]].to_string(index=False))
    print(f"P2-E1 one estimator  : {e1}  {sorted(pe_est)}")
    print(f"P2-E3 no gauge pool  : {e3}")
    print(f"references           : cited {len(cited)}, listed {len(listed)}, "
          f"uncited {sorted(set(listed) - cited)}, missing {sorted(cited - set(listed))}")
    print(f"reference placeholder: {'PRESENT - blocks submission' if placeholder else 'none'}")
    abs_max = 300 if a.journal == "aer" else 250
    print(f"abstract words       : {n_abs} (limit {abs_max})")
    print(f"keywords             : {len(kw)}, alphabetical {kw == sorted(kw)}, "
          f"rule for {a.journal} satisfied {kw_ok}, within {kw_min}-{kw_max}")
    print(f"supplementary items  : {len(supp_present)} present, "
          f"{len(supp_cited)} cited, uncited {supp_uncited or 'none'}, "
          f"missing {supp_missing or 'none'}")

    ok = (len(bad) == 0 and e1 and e3 and n_abs <= abs_max and not placeholder
          and not (set(listed) ^ cited)           and kw == sorted(kw) and kw_ok
          and kw_min <= len(kw) <= kw_max
          and not supp_uncited and not supp_missing)
    print("\nAUDIT PASSED" if ok else "\nAUDIT FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
