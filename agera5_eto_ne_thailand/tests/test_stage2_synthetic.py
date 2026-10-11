"""End-to-end Stage 2 on a SYNTHETIC AgERA5 extract with known imposed errors.

The synthetic data are built from the station record itself, so this test
checks the software (recovery of imposed biases, additivity, file outputs),
never the scientific result. Synthetic values must not be used in the paper.
"""
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from etoeval import fao56
from etoeval.data import load_config
from etoeval.pipeline import run_stage1, run_stage2

ROOT = Path(__file__).resolve().parents[1]
IMPOSED = {"tmax": 0.5, "tmin": -0.3, "ea_ratio": 0.95, "u_ratio": 1.2, "rs_ratio": 1.08, "pr_ratio": 1.1}


def _synthetic_daily(cfg, s1: Path) -> pd.DataFrame:
    st = pd.read_csv(s1 / "station_monthly_clean_masked.csv")
    ref = pd.read_csv(s1 / "station_reference_ensemble_masked.csv")
    base = ref[ref["member"] == "ms-1|FAO56"][["stncode", "year", "month", "ea", "rs"]].merge(
        st[["stncode", "year", "month", "tmax", "tmin", "wind_raw", "rain"]], on=["stncode", "year", "month"])
    clim = base.groupby(["stncode", "month"]).transform("mean")
    for c in ["ea", "rs", "tmax", "tmin", "wind_raw", "rain"]:
        base[c] = base[c].fillna(clim[c])
    lat = {s.code: s.lat for s in cfg.stations}
    rows = []
    for _, r in base.iterrows():
        days = pd.Period(year=int(r.year), month=int(r.month), freq="M").days_in_month
        for d in range(1, days + 1):
            rows.append((int(r.stncode), pd.Timestamp(int(r.year), int(r.month), d), r.tmax + IMPOSED["tmax"],
                         r.tmin + IMPOSED["tmin"], r.ea * IMPOSED["ea_ratio"], r.wind_raw * IMPOSED["u_ratio"],
                         r.rs * IMPOSED["rs_ratio"], r.rain * IMPOSED["pr_ratio"] / days))
    d = pd.DataFrame(rows, columns=["stncode", "date", "tmax_c", "tmin_c", "vp_kpa", "u10_ms", "rs_mj", "pr_mm_day"])
    doy = d["date"].dt.dayofyear.to_numpy()
    ra = fao56.extraterrestrial_radiation(d["stncode"].map(lat).to_numpy(), doy)
    d["eto_mm_day"] = fao56.eto_penman_monteith(d["tmax_c"], d["tmin_c"], d["vp_kpa"], fao56.wind_to_2m(d["u10_ms"], 10.0),
                                                d["rs_mj"], ra, cfg.assumed_elevation_m, 0.0)
    out = []
    rng = np.random.default_rng(0)
    for meth, noise in (("nearest", 0.0), ("bilinear", 0.01), ("idw", 0.02)):
        m = d.copy()
        m["method"] = meth
        for c in ("tmax_c", "tmin_c"):
            m[c] = m[c] + rng.normal(0, noise, len(m))
        out.append(m)
    return pd.concat(out, ignore_index=True)


@pytest.fixture(scope="module")
def stage2_outputs(tmp_path_factory) -> Path:
    tmp = tmp_path_factory.mktemp("proj")
    shutil.copytree(ROOT / "data" / "raw", tmp / "data" / "raw")
    cfg_d = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    cfg_d["statistics"]["bootstrap_n"] = 50
    (tmp / "config.yaml").write_text(yaml.safe_dump(cfg_d, allow_unicode=True), encoding="utf-8")
    cfg = load_config(tmp / "config.yaml")
    run_stage1(cfg, n_sim=199)
    daily = _synthetic_daily(cfg, cfg.out_dir / "stage1")
    run_stage2(cfg, daily, n_mc=30)
    return cfg.out_dir / "stage2"


def test_recovers_imposed_input_errors(stage2_outputs: Path) -> None:
    m = pd.read_csv(stage2_outputs / "tables" / "input_metrics.csv")
    near = m[m["method"] == "nearest"]
    assert near[near.variable == "tmax"]["mbe"].mean() == pytest.approx(IMPOSED["tmax"], abs=0.02)
    assert near[near.variable == "tmin"]["mbe"].mean() == pytest.approx(IMPOSED["tmin"], abs=0.02)
    assert near[near.variable == "ea"]["pbias"].mean() == pytest.approx(-5.0, abs=0.3)
    assert near[(near.variable == "rs") & (near.variant == "FAO56")]["pbias"].mean() == pytest.approx(8.0, abs=0.3)
    assert near[(near.variable == "u2") & (near.variant == "m s-1")]["pbias"].mean() == pytest.approx(20.0, abs=0.5)


def test_precip_ratio_and_outputs(stage2_outputs: Path) -> None:
    p = pd.read_csv(stage2_outputs / "tables" / "precip_metrics.csv")
    ann = p[(p.method == "nearest") & (p.level == "annual")]
    assert ann["pbias"].iloc[0] == pytest.approx(10.0, abs=0.5)
    for f in ("fig_input_accuracy", "fig_bias_station_month", "fig_annual_scatter", "fig_seasonal_cycle",
              "fig_attribution", "fig_error_propagation", "fig_nir_adjustment"):
        assert (stage2_outputs / "figures" / f"{f}.png").exists()


def test_shapley_rows_additive(stage2_outputs: Path) -> None:
    a = pd.read_csv(stage2_outputs / "tables" / "attribution_rows.csv")
    phi = a[[c for c in a.columns if c.startswith("phi_")]].sum(axis=1)
    assert np.allclose(phi, a["delta"], atol=1e-8)
