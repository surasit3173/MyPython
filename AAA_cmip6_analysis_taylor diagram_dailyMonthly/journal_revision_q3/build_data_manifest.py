from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd


ROOT = Path("C:/MyPython/AAA_cmip6_analysis_taylor diagram_dailyMonthly")
DATA = ROOT / "cmip6bc_q1_notiers_work" / "cmip6bc" / "data"
OUT = ROOT / "journal_revision_q3" / "data_provenance_manifest.csv"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    files = [
        DATA / "Observed_Rain_daily_198101_201412_Prachuap_Khiri_Khan.csv",
        *sorted(DATA.glob("pr_day_*_historical_*.csv")),
        DATA / "stations.csv",
    ]
    rows = []
    for path in files:
        name = path.name
        if name.startswith("Observed_"):
            role, model = "observed_rainfall", "TMD gauge network"
        elif name == "stations.csv":
            role, model = "station_metadata", "TMD gauge network"
        else:
            role = "raw_cmip6_precipitation"
            model = name.split("_historical_")[0].removeprefix("pr_day_")
        rows.append(
            {
                "role": role,
                "model_or_network": model,
                "filename": name,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "period": "1981-01-01/2014-12-31",
                "verification_note": "Exact analysis-ready derivative used in the publication workflow",
            }
        )
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(OUT)


if __name__ == "__main__":
    main()
