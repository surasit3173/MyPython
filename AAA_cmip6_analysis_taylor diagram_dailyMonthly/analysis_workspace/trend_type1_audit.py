from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "future_zip"))
from src.mktrend import mann_kendall, modified_mk_hamed_rao, tfpw_mk  # noqa: E402


def main():
    seed = 20260829
    rng = np.random.default_rng(seed)
    n = 20
    reps = 2000
    phi = 0.6
    counts = {"MK": 0, "Hamed-Rao": 0, "TFPW-MK": 0}
    for _ in range(reps):
        noise = rng.normal(0, 1, n)
        series = np.zeros(n)
        for i in range(1, n):
            series[i] = phi * series[i - 1] + noise[i]
        counts["MK"] += int(mann_kendall(series).significant)
        counts["Hamed-Rao"] += int(modified_mk_hamed_rao(series).significant)
        counts["TFPW-MK"] += int(tfpw_mk(series).significant)
    result = {
        "seed": seed,
        "n": n,
        "replicates": reps,
        "ar1_phi": phi,
        "nominal_alpha": 0.05,
        "false_positive_rate": {k: v / reps for k, v in counts.items()},
    }
    path = ROOT / "audit_corrected" / "trend_type1_audit.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
