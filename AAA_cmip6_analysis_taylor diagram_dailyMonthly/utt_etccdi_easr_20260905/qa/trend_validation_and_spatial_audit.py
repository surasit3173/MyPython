"""Reproducible sensitivity audit for the Uttaradit manuscript.

It does not select a method by its significance rate.  It evaluates the
retained full-lag Yue-Wang sensitivity procedure at the record lengths used in
this paper and performs leave-one-out validation of the PRCPTOT IDW display.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "outputs" / "full_with_figures" / "results"
SOURCE = ROOT / "Uttaradit_ETCCDI_MK_MMK2004_Sen_IDW_Q3_fixed.py"
OUT = ROOT / "manuscript" / "supplementary_data"
OUT.mkdir(parents=True, exist_ok=True)


def load_module():
    spec = importlib.util.spec_from_file_location("utt_validation_pipeline", SOURCE)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def ar1(n: int, rho: float, slope: float, rng: np.random.Generator) -> np.ndarray:
    eps = rng.normal(size=n)
    x = np.empty(n)
    x[0] = eps[0] / np.sqrt(max(1 - rho**2, 1e-9))
    for i in range(1, n):
        x[i] = rho * x[i - 1] + eps[i]
    return x + slope * np.arange(n)


def trend_audit(mod, reps: int = 1000, seed: int = 20260905) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for n in (30, 34):
        years = np.arange(n, dtype=float)
        for rho in (0.0, 0.1, 0.2, 0.3, 0.5):
            for label, slope in (("null", 0.0), ("positive_trend", 0.12), ("negative_trend", -0.12)):
                mk_rej = mmk_rej = valid = 0
                for _ in range(reps):
                    x = ar1(n, rho, slope, rng)
                    mk = mod.standard_mk(years, x)
                    mmk = mod.yue_wang_2004_mmk(years, x)
                    mk_rej += int(np.isfinite(mk["p"]) and mk["p"] < 0.05)
                    if np.isfinite(mmk.get("MMK_p", np.nan)):
                        valid += 1
                        mmk_rej += int(mmk["MMK_p"] < 0.05)
                rows.append({
                    "n_years": n, "ar1_rho": rho, "scenario": label, "replicates": reps,
                    "standard_mk_rejection_rate": mk_rej / reps,
                    "full_lag_yue_wang_rejection_rate": mmk_rej / max(valid, 1),
                    "full_lag_valid_replicates": valid,
                })
    return pd.DataFrame(rows)


def loocv_idw(mod) -> pd.DataFrame:
    coords = pd.read_csv(RESULTS / "station_coordinates_used.csv", dtype={"station": str})
    changes = pd.read_csv(RESULTS / "future_change_2021_2050.csv", dtype={"Station": str})
    rows = []
    for scenario in ("SSP2-4.5", "SSP5-8.5"):
        values = changes.loc[(changes.Index == "PRCPTOT") & (changes.Scenario == scenario)].groupby("Station").Absolute_change.median()
        values.index = values.index.astype(str)
        for station in values.index:
            train = coords.loc[coords.station.astype(str) != station, ["station", "latitude", "longitude"]]
            target = coords.loc[coords.station.astype(str) == station].iloc[0]
            lon, lat, grid = mod.idw_grid(train, values.drop(station), power=2.0, nx=80, ny=80)
            ix = int(np.abs(lon[0, :] - target.longitude).argmin())
            iy = int(np.abs(lat[:, 0] - target.latitude).argmin())
            pred = float(grid[iy, ix])
            obs = float(values.loc[station])
            rows.append({"Scenario": scenario, "Station": station, "observed_mm": obs, "predicted_mm": pred, "error_mm": pred - obs, "abs_error_mm": abs(pred - obs)})
    return pd.DataFrame(rows)


def bh_fdr(p: pd.Series) -> pd.Series:
    p = p.to_numpy(float)
    order = np.argsort(p)
    ranked = p[order] * len(p) / np.arange(1, len(p) + 1)
    adjusted = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty_like(adjusted)
    out[order] = np.minimum(adjusted, 1.0)
    return pd.Series(out)


def main() -> None:
    mod = load_module()
    simulation = trend_audit(mod)
    simulation.to_csv(OUT / "Table_S9_trend_simulation.csv", index=False)
    cv = loocv_idw(mod)
    cv.to_csv(OUT / "Table_S10_idw_loocv.csv", index=False)
    metrics = cv.groupby("Scenario").agg(MAE_mm=("abs_error_mm", "mean"), RMSE_mm=("error_mm", lambda x: float(np.sqrt(np.mean(np.square(x))))), Bias_mm=("error_mm", "mean"), n=("Station", "size")).reset_index()
    metrics.to_csv(OUT / "Table_S10_idw_loocv_metrics.csv", index=False)
    observed = pd.read_csv(RESULTS / "observed_trend_1981_2014.csv")
    observed["MK_p_FDR_BH"] = bh_fdr(observed["p_MK"])
    observed["MK_significant_FDR_BH"] = observed["MK_p_FDR_BH"] < 0.05
    observed.to_csv(OUT / "Table_S5_observed_MK_FDR.csv", index=False)
    print("AUDIT_OK")
    print(metrics.to_string(index=False))
    print(simulation.loc[simulation.scenario == "null"].to_string(index=False))


if __name__ == "__main__":
    main()
