from pathlib import Path

import pandas as pd
from docx import Document

ROOT = Path(".")
OUT = ROOT / "qdm_p_np_publication_out"

summary = pd.read_csv(OUT / "summary.csv")
diag = pd.read_csv(OUT / "fit_diagnostics.csv")
metrics = pd.read_csv(OUT / "station_metrics.csv")

keep_metrics = ["PBIAS", "KS_D", "q95_relbias_pct", "q99_relbias_pct", "mRMSE", "mMAE", "mNSE", "mKGE", "mr", "clim_r", "annual_r"]
val = summary[(summary.period == "validation") & (summary.metric.isin(keep_metrics))]
print("\nVALIDATION METHOD SUMMARY")
print(val[["method", "metric", "raw_mean", "corrected_mean", "n_improved", "n_total", "pct_improved"]].round(3).to_string(index=False))

print("\nBEST METHODS BY METRIC")
for metric in keep_metrics:
    d = val[val.metric == metric].copy()
    if d.empty:
        continue
    d["score"] = d["corrected_mean"].abs() if metric in {"PBIAS", "q95_relbias_pct", "q99_relbias_pct"} else d["corrected_mean"]
    if metric in {"KS_D", "mRMSE", "mMAE"} or metric in {"PBIAS", "q95_relbias_pct", "q99_relbias_pct"}:
        best = d.sort_values("score").iloc[0]
    else:
        best = d.sort_values("score", ascending=False).iloc[0]
    print(metric, best.method, round(float(best.corrected_mean), 3), round(float(best.pct_improved), 1))

print("\nDISTRIBUTION FREQUENCY (parametric, validation rows deduplicated by cal fit)")
pdiag = diag[(diag.family == "parametric") & (diag.period == "validation")].drop_duplicates(["method", "model", "station", "group"])
for col in ["obs_dist", "mod_dist"]:
    print(col)
    print(pdiag.groupby(["method", col]).size().unstack(fill_value=0).to_string())

print("\nCAP SUMMARY")
print(diag.groupby(["method", "period"])[["n_output_capped", "n_delta_clipped_low", "n_delta_clipped_high"]].sum().astype(int).to_string())

print("\nTABLES FROM EXISTING MANUSCRIPT")
doc = Document(ROOT / "cmip6bc_q1_editable" / "ID1558_Manuscript_BSJ.docx")
for i, table in enumerate(doc.tables[:2], 1):
    print(f"\nTABLE {i}")
    for row in table.rows:
        print(" | ".join(cell.text.replace("\n", " ").strip() for cell in row.cells))
