# Project 1 Final Portable Run Report

## 1. Environment
- **Python Version:** 3.14.0a4 (x86-64)
- **Operating System:** Microsoft Windows 11 / Windows Server
- **Execution Command:** `py -3 main.py`
- **Unit Test Command:** `py -3 -m unittest discover tests/`

## 2. Test Suite Execution
- **Command:** `py -3 -m unittest discover tests/`
- **Number of Tests Passed:** 14 / 14
- **Number of Failures:** 0
- **Final Test Status:** `PASS`

## 3. Production Run Execution
- **Command:** `py -3 main.py`
- **Station Count:** 12 stations
- **Study Period:** 1981–2014 (34 years, $N=12,418$ daily records per station)
- **Primary Method:** Yue & Wang (2004) AR(1) Modified Mann-Kendall (`yue_wang_2004`)
- **Reference Method:** Standard Mann-Kendall (`standard_mk`)
- **Sensitivity Method:** Trend-Free Pre-Whitening (`tfpw_mk`)
- **Final Execution Status:** `PASS`

## 4. Key Reproduced Results
- **Station 500002 (Significant Upward Trend):**
  - Standard MK: $Z = +2.253, p = 0.0242$, Sen's slope $= +9.175$ mm/year (Statistically significant at $\alpha = 0.05$).
  - Yue & Wang (2004) AR(1) MMK: $r_1 = -0.1386, n/n_s^* = 1.0000 \implies Z = +2.253, p = 0.0242$.
- **Station 502002 (Negative Autocorrelation Adjustment):**
  - Standard MK: $Z = -1.156, p = 0.2476$, Sen's slope $= -4.376$ mm/year.
  - Yue & Wang (2004) AR(1) MMK: $r_1 = -0.3619, n/n_s^* = 0.4800 \implies Z = -1.669, p = 0.0951$, Status = `VALID`.
- **All 12 Stations Production Status:** 100% `VALID` results.

## 5. Output Files & Production Artifacts
- `output/tables/trend_results.csv`
- `output/tables/station_summary.csv`
- `output/tables/validation_report.md`
- `output/figures/station_sen_slopes.png`
- `output/manifests/run_manifest.json`
- `output/logs/pipeline.log`

## 6. Provenance Checksums (SHA256)
- **Observed Rainfall CSV (`data/Observed_Rain_daily_198101_201412_PrachuapKhiriKhan.csv`):** `abdec5e39458b3441bcce139517b3eacc8855f85f2ec5e6ce06e295a280e31ed`
- **Station Coordinates CSV (`data/station_coordinates_PrachuapKhiriKhan.csv`):** `852ac008480f934f29d65f0ed7bbc2f563cc21c4915b346bb7fc26dd205872d1`
- **Config YAML (`config.yaml`):** `1747a2d7118c192ed4dcaffc9b22d230a11158c86018797a0f029bf90321a5b5`

## 7. Evidence Status
Referenced to `docs/FINAL_EVIDENCE_FREEZE.md`. All results strictly match frozen production outputs.
