"""Build three concise main tables and the machine-readable supplement."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"
TABLES = OUTPUT / "tables"
TABLES.mkdir(parents=True, exist_ok=True)


def _format_interval(row: pd.Series) -> str:
    return f"{row.response_pct:.1f} [{row.ci_low_pct:.1f}, {row.ci_high_pct:.1f}]"


def table_1() -> pd.DataFrame:
    counts = pd.read_csv(OUTPUT / "enso_phase_sample_sizes.csv")
    phases = ["EL_NINO", "NEUTRAL", "LA_NINA", "TRANSITION_UNCLASSIFIED"]
    rows = []
    for season in ["RAINY", "HOT_DRY"]:
        observed = counts[
            (counts["source_type"] == "OBSERVED") & (counts["season_type"] == season)
        ].set_index("enso_phase")["n_seasons"]
        model = counts[
            (counts["source_type"] == "RAW") & (counts["season_type"] == season)
        ]
        model_pivot = model.pivot(index="model", columns="enso_phase", values="n_seasons").fillna(0)
        row = {
            "Season": "Rainy (May–Oct)" if season == "RAINY" else "Hot/dry (Nov–Apr)",
            "Complete years": "1981–2014 (34)" if season == "RAINY" else "1981/82–2013/14 (33)",
        }
        for phase, label in zip(phases, ["El Niño", "Neutral", "La Niña", "Transition/unclassified"], strict=True):
            values = model_pivot[phase] if phase in model_pivot else pd.Series(0, index=model_pivot.index)
            row[f"Observed {label} n"] = int(observed.get(phase, 0))
            row[f"Model {label} n range"] = f"{int(values.min())}–{int(values.max())}"
        row["Index/classification"] = "NOAA ERSSTv6 ONI for observations; exact-member CMIP6 tos Niño-3.4 for each GCM; strict majority of persistent episode windows"
        rows.append(row)
    table = pd.DataFrame(rows)
    table.to_csv(TABLES / "Paper3_Table_01_ENSO_samples.csv", index=False)
    return table


def table_2() -> pd.DataFrame:
    responses = pd.read_csv(OUTPUT / "primary_response_summary.csv")
    responses["estimate_95CI_pct"] = responses.apply(_format_interval, axis=1)
    pivot = responses.pivot(
        index=["season_type", "metric", "phase"],
        columns="source_type",
        values="estimate_95CI_pct",
    ).reset_index()
    q_values = responses.pivot(
        index=["season_type", "metric", "phase"],
        columns="source_type",
        values="permutation_p_bh_primary",
    ).reset_index()
    q_values = q_values.rename(columns={source: f"{source}_BH_q" for source in ["OBSERVED", "RAW", "QDM"]})
    table = pivot.merge(q_values, on=["season_type", "metric", "phase"])
    table = table.rename(
        columns={
            "season_type": "Season",
            "metric": "Metric",
            "phase": "Phase vs Neutral",
            "OBSERVED": "Observed response % [95% CI]",
            "RAW": "Raw ensemble response % [95% CI]",
            "QDM": "QDM ensemble response % [95% CI]",
            "OBSERVED_BH_q": "Observed BH q",
            "RAW_BH_q": "Raw BH q",
            "QDM_BH_q": "QDM BH q",
        }
    )
    for column in ["Observed BH q", "Raw BH q", "QDM BH q"]:
        table[column] = table[column].map(lambda value: f"{value:.3f}")
    table.to_csv(TABLES / "Paper3_Table_02_primary_responses.csv", index=False)
    return table


def table_3() -> pd.DataFrame:
    preservation = pd.read_csv(OUTPUT / "qdm_enso_signal_preservation.csv")
    asymmetry = pd.read_csv(OUTPUT / "enso_asymmetry_primary.csv")
    rows = []
    for season in ["RAINY", "HOT_DRY"]:
        for metric in ["PRCPTOT", "wet_day_frequency_pct", "Rx1day", "CDD"]:
            selected = preservation[
                (preservation["season_type"] == season) & (preservation["metric"] == metric)
            ].set_index("phase")
            asym = asymmetry[
                (asymmetry["season_type"] == season) & (asymmetry["metric"] == metric)
            ].set_index("source_type")
            rows.append(
                {
                    "Season": season,
                    "Metric": metric,
                    "El Niño preservation": selected.loc["EL_NINO", "category"],
                    "La Niña preservation": selected.loc["LA_NINA", "category"],
                    "El Niño QDM−raw (percentage points)": selected.loc["EL_NINO", "shift_pct_points"],
                    "La Niña QDM−raw (percentage points)": selected.loc["LA_NINA", "shift_pct_points"],
                    "Observed true asymmetry %": asym.loc["OBSERVED", "neutral_centered_asymmetry_pct"],
                    "Raw true asymmetry %": asym.loc["RAW", "neutral_centered_asymmetry_pct"],
                    "QDM true asymmetry %": asym.loc["QDM", "neutral_centered_asymmetry_pct"],
                    "Paired-model sign preservation (El/La)": (
                        f"{selected.loc['EL_NINO', 'paired_model_sign_preservation_fraction']:.2f}/"
                        f"{selected.loc['LA_NINA', 'paired_model_sign_preservation_fraction']:.2f}"
                    ),
                }
            )
    table = pd.DataFrame(rows)
    numeric = table.select_dtypes(include=[np.number]).columns
    table[numeric] = table[numeric].round(1)
    table.to_csv(TABLES / "Paper3_Table_03_preservation_asymmetry.csv", index=False)
    return table


def supplementary_workbook() -> None:
    workbook = TABLES / "Paper3_SUPPLEMENTARY_Tables.xlsx"
    sources = {
        "S1_obs_episodes": OUTPUT / "enso_episode_catalog_observed.csv",
        "S1_model_episodes": OUTPUT / "enso_episode_catalog_models.csv",
        "S2_obs_classes": OUTPUT / "season_classification_observed.csv",
        "S2_model_classes": OUTPUT / "season_classification_models.csv",
        "S3_obs_station": OUTPUT / "observed_station_primary_responses.csv",
        "S4_S5_model": OUTPUT / "model_primary_responses.csv",
        "S6_primary": OUTPUT / "primary_response_summary.csv",
        "S7_asymmetry": OUTPUT / "enso_asymmetry_primary.csv",
        "S8_preservation": OUTPUT / "qdm_enso_signal_preservation.csv",
        "S9_qdm_diagnostics": OUTPUT / "crossfit_qdm_diagnostics.csv",
        "S10_provenance": OUTPUT / "rainfall_input_provenance.csv",
        "S10_qc": OUTPUT / "observed_zero_qc_diagnostics.csv",
        "S10_gates": OUTPUT / "PAPER3_ACCEPTANCE_GATES.csv",
    }
    with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
        for sheet, path in sources.items():
            frame = pd.read_csv(path)
            frame.to_excel(writer, sheet_name=sheet[:31], index=False)
            worksheet = writer.book[sheet[:31]]
            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = worksheet.dimensions
    print(f"SUPPLEMENT_COMPLETE {workbook}")


def main() -> None:
    tables = [table_1(), table_2(), table_3()]
    supplementary_workbook()
    pd.DataFrame(
        [
            {"table": number, "rows": len(table), "columns": len(table.columns)}
            for number, table in enumerate(tables, start=1)
        ]
    ).to_csv(TABLES / "Paper3_TABLE_INDEX.csv", index=False)
    print(f"TABLES_COMPLETE {TABLES}")


if __name__ == "__main__":
    main()

