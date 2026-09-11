from pathlib import Path
import importlib.util
import sys
import types

import pandas as pd


ROOT = Path(__file__).resolve().parent
FIGURES = ROOT / "_files_zip" / "figures.py"
WORKBOOK = Path(r"C:\Users\PC\Downloads\evaluation_results.xlsx")
OUT = ROOT / "publication_figures"


sys.modules.setdefault("io_layer", types.SimpleNamespace(build_dataset=None))
sys.modules.setdefault("provenance", types.SimpleNamespace(Provenance=object))

spec = importlib.util.spec_from_file_location("figures_quality", FIGURES)
figures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(figures)

OUT.mkdir(parents=True, exist_ok=True)

metrics = pd.read_excel(WORKBOOK, "E02_primary_station_metrics")
mme = pd.read_excel(WORKBOOK, "E03_MME_monthly")

figures.figure4(metrics, OUT)
figures.figure5(metrics, OUT)
figures.figure6(metrics, mme, OUT)

print(f"Rendered available figures to {OUT}")
