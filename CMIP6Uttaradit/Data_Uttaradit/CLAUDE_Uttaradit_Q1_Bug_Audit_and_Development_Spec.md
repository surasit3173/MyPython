# Claude Code Task Specification
# Uttaradit ETCCDI Extreme Precipitation Trend Pipeline
## Full Bug Audit, Scientific Validation, Refactoring, and Publication-Grade Hardening

วันที่จัดทำ: 2026-09-04

---

## 0. วัตถุประสงค์

ตรวจสอบและพัฒนาไฟล์

`Uttaradit_ETCCDI_MK_MMK2004_Sen_IDW_Q3.py`

ให้เป็น research-grade / publication-grade Python pipeline สำหรับการวิเคราะห์แนวโน้มฝนสุดขั้วของจังหวัดอุตรดิตถ์ โดยต้อง:

1. รันได้จริงตั้งแต่ input → calculation → output โดยไม่ต้องแก้ error แบบทีละ traceback
2. ไม่สร้างผลการวิจัยปลอมและไม่ silently repair ข้อมูล
3. ตรวจสอบความถูกต้องของสมการและ implementation ทางสถิติ
4. ตรวจสอบข้อมูลทุกขั้นตอนด้วย assertions / validation
5. ป้องกัน silent failure
6. ให้ผลลัพธ์ reproducible
7. รักษาขอบเขตวิธีวิจัยที่ล็อกไว้ ไม่เพิ่มวิธีทางสถิติที่ไม่ได้กำหนด
8. รองรับข้อมูลจริงของ Uttaradit dataset โดยไม่บังคับให้ผู้ใช้แก้ metadata เดิม

---

# 1. ขอบเขตการวิเคราะห์ที่ LOCKED — ห้ามเปลี่ยน

## 1.1 Extreme precipitation indices

ใช้เฉพาะ 11 indices ต่อไปนี้:

1. PRCPTOT
2. SDII
3. Rx1day
4. Rx5day
5. CDD
6. CWD
7. R10mm
8. R20mm
9. R50mm
10. R95p
11. R99p

ห้ามเพิ่ม:

- R1mm
- R25mm
- Rnnmm อื่น ๆ
- seasonal indices
- monthly indices
- drought indices
- Taylor diagram
- Pettitt
- FDR
- Bonferroni
- Pre-whitening
- TFPW
- Bootstrap trend test
- วิธี trend อื่นที่ไม่ได้ระบุ

หมายเหตุ: R50mm เป็น study-specific fixed-threshold index ไม่ควรเขียนว่าเป็น core ETCCDI index โดยตรง

---

# 2. Period ที่ LOCKED

Observed:

`1981–2014`

Future:

`2021–2050`

Model-consistent historical baseline สำหรับ future change:

`1995–2014`

ห้ามใช้ observed 1981–2014 เป็น baseline ของ CMIP6 future change โดยไม่มีเหตุผลและการรายงานที่ชัดเจน

---

# 3. Trend methods ที่ LOCKED

ต้องใช้เฉพาะ:

### 3.1 Standard Mann–Kendall

ต้องมี:

- S statistic
- Var(S)
- tie correction
- Z
- two-sided p-value
- alpha = 0.05
- trend direction
- n

### 3.2 Yue & Wang (2004) Modified Mann–Kendall

ชื่อ method ต้องเป็น:

`Yue-Wang (2004) MMK`

ห้ามเรียกเป็น Hamed & Rao (1998)

Reference:

Yue, S., & Wang, C. Y. (2004). The Mann-Kendall test modified by effective sample size to detect trend in serially correlated hydrological series. Water Resources Management, 18(3), 201–218. DOI: 10.1023/B:WARM.0000043140.61082.60.

Implementation ต้องตรวจให้ตรงกับหลัก effective sample size:

n/n* = 1 + 2 Σ[(1-k/n) rho_k]

k = 1 ... n-1

Var*(S) = Var(S) × (n/n*)

ต้อง:

- detrend ก่อน estimate autocorrelation
- ใช้ Sen slope เพื่อ detrending ตาม implementation ที่กำหนด
- ใช้ autocorrelation ของ detrended series
- ใช้ tie-corrected MK variance
- ตรวจ edge cases เมื่อ ESS factor < 1 หรือผิดปกติ
- ป้องกัน n_eff <= 0
- เก็บ n_eff และ correction factor ไว้ใน output
- ไม่ใช้ Hamed-Rao rank autocorrelation แทน Yue-Wang โดยไม่ตั้งใจ

### 3.3 Sen's slope

ต้องรายงาน:

- slope
- lower 95% CI
- upper 95% CI

Slope unit ต้องสะท้อน annual time step และ index unit เช่น:

- mm/year
- mm day^-1/year สำหรับ SDII
- days/year สำหรับ CDD/CWD
- events/year สำหรับ R10mm/R20mm/R50mm

ต้องรักษา actual year spacing

ห้ามสมมติว่า year spacing = 1 หากมี missing annual years

---

# 4. CURRENT CONFIRMED BUG

พบแล้ว:

```python
rx1 = float(np.nanmax(x)) if finite.any() else np.nan
```

แต่ `finite` ไม่ได้ถูกประกาศ

ต้องแก้เป็น:

```python
x = np.asarray(values, dtype=float)
finite = np.isfinite(x)
rx1 = float(np.nanmax(x)) if finite.any() else np.nan
```

แต่ห้ามหยุดแค่ bug นี้

ต้อง audit ทั้ง repository/script เพื่อค้นหา bug แบบเดียวกันทั้งหมดก่อนส่งมอบ

---

# 5. DATA INPUT / FILE DISCOVERY AUDIT

## 5.1 Station coordinates

ข้อมูลจริงใช้ schema:

```text
Station_ID
latitude
longitude
Elevation
```

ตัวอย่าง:

```text
351001  17.23  100.10  54.57
351002  17.42  100.13  62.02
...
351201  17.62  100.10  67.05
```

ต้องรองรับ `Station_ID` โดยตรง

ภายใน pipeline สามารถ normalize เป็น:

```text
station
latitude
longitude
```

ได้

ห้ามบังคับให้ผู้ใช้ rename Excel

ต้องตรวจ:

- 13 stations
- unique station IDs
- latitude range
- longitude range
- no missing coordinates
- no duplicated station IDs

Expected stations:

```text
351001
351002
351003
351004
351005
351006
351007
351008
351009
351010
351011
351012
351201
```

ต้อง assert ว่าข้อมูล observed และ coordinate table match กันครบ

---

# 6. OBSERVED RAINFALL INPUT AUDIT

ตรวจสอบ:

- date column
- date parsing
- duplicate dates
- duplicate station columns
- station ID normalization
- numeric conversion
- negative precipitation
- impossible values
- missing dates
- timezone ไม่ควรมีผลกับ daily data
- chronological sorting

ห้าม silently:

- เติมฝน
- interpolate rainfall
- ลบ extreme rainfall เพราะเป็น outlier

ฝนสุดขั้วเป็น signal ที่ต้องรักษา

หากพบ negative rainfall:

- flag
- รายงานจำนวน
- ห้ามแก้ค่าโดยอัตโนมัติ
- พิจารณา invalid เป็น NaN เฉพาะเมื่อ documentation ระบุชัดเจน

---

# 7. ANNUAL COMPLETENESS

ต้องมี annual completeness threshold:

`>= 90% valid daily observations`

หากปีใดไม่ผ่าน:

- annual indices ทั้ง 11 ของ station-year นั้น = NaN
- ห้ามคำนวณ index บางตัวจากปีนั้นแล้วปล่อยผ่านบางตัว
- ต้องมี QC output ระบุเหตุผล

ต้องเก็บ:

- n_expected_days
- n_observed
- n_valid
- completeness_pct
- status
- missing_days

ต้อง handle leap years โดยใช้จำนวนวันจริงของปี

---

# 8. EXTREME INDEX IMPLEMENTATION AUDIT

ต้องตรวจ function ที่คำนวณ 11 indices ทั้งหมดแบบ line-by-line

## PRCPTOT

Wet day:

`P >= 1 mm`

PRCPTOT:

sum precipitation on wet days

ต้องระวัง:

- NaN
- all-NaN
- incomplete year
- negative values

## SDII

`PRCPTOT / number_of_wet_days`

หาก wet days = 0 → NaN ไม่ใช่ inf

## Rx1day

maximum daily precipitation

ต้องไม่เกิด `nanmax` บน empty array

## Rx5day

maximum consecutive 5-day precipitation total

ห้ามใช้ rolling window ที่มี missing values แล้วคำนวณ partial sum โดยไม่ตั้งใจ

ต้อง:

- window = 5
- min_periods = 5
- invalid year → NaN
- ตรวจ calendar continuity

## CDD

maximum consecutive days with:

`P < 1 mm`

Missing days ต้อง break sequence

ห้ามตีความ missing เป็น dry day

## CWD

maximum consecutive days with:

`P >= 1 mm`

Missing days break sequence

## R10mm

count:

`P >= 10 mm`

## R20mm

count:

`P >= 20 mm`

## R50mm

count:

`P >= 50 mm`

ต้อง label ชัดเจนว่า study-specific threshold

## R95p

ใช้ observed baseline wet-day percentile threshold

Recommended locked threshold:

- wet days >= 1 mm
- observed period 1981–2014
- station-specific P95
- threshold fixed for future analysis

ต้องไม่ recompute P95 independently for every future model/scenario เพราะจะทำให้ comparability เสีย

## R99p

เช่นเดียวกัน:

- station-specific observed P99
- wet days >= 1 mm
- threshold fixed across future

ต้องเก็บ thresholds ใน output:

`station_thresholds.csv`

ประกอบด้วย:

```text
Station
P95_threshold_mm
P99_threshold_mm
Wet_day_definition
Baseline_period
```

---

# 9. MISSING-DATA BUGS TO PREVENT

ตรวจทุก function ว่าไม่มี:

- `np.nanmax([])`
- `np.nanmin([])`
- division by zero
- sqrt negative
- log(0)
- invalid degrees of freedom
- empty DataFrame indexing
- `.iloc[0]` เมื่อไม่มี row
- `.values[0]` เมื่อไม่มี row
- ambiguous boolean from numpy arrays
- NaN converted to int
- inf exported as numeric result

ใช้ safe helper functions เมื่อเหมาะสม

---

# 10. STANDARD MK AUDIT

ตรวจ implementation ด้วย known synthetic test series:

### Test A — constant series

Expected:

- S = 0
- slope = 0
- no significant trend

### Test B — strictly increasing

Expected:

- S > 0
- positive slope
- very small p for sufficiently long series

### Test C — strictly decreasing

Expected:

- S < 0
- negative slope

### Test D — tied values

ตรวจ tie correction

### Test E — missing years

ตรวจว่า slope ใช้ actual year values

### Test F — NaN

ตรวจว่า invalid values ถูกจัดการตาม specification และ n ถูกต้อง

---

# 11. YUE-WANG 2004 AUDIT

ต้องทำ independent unit tests

ตรวจ:

1. no autocorrelation:
   MMK ≈ MK

2. positive serial correlation:
   corrected variance should not be smaller merely because of positive autocorrelation

3. detrended series:
   autocorrelation estimation must use detrended series

4. ESS:
   `n_eff = n / (n/n_eff)`

5. correction factor:
   guard against pathological negative / zero ESS

6. all lags:
   confirm implementation follows all-lag effective sample size formulation used by the selected Yue-Wang implementation

7. ties:
   corrected variance must retain tie correction

8. continuity correction:
   verify Z calculation

9. p-value:
   two-sided normal approximation

10. output:
   `rho_1`, `n_eff`, correction factor, Z, p, S, VarS, VarS_adj

Do not silently substitute Hamed-Rao 1998.

---

# 12. SEN SLOPE 95% CI AUDIT

This is a high-priority statistical validation item.

Check:

- pairwise slope count = n(n-1)/2
- ordering of slopes
- median slope
- confidence interval indexing
- finite sample handling
- ties
- even/odd number of pairwise slopes
- alpha = 0.05
- no off-by-one indexing
- no invalid negative/positive rank

Cross-check at least 10 synthetic datasets against an established implementation where possible.

If the CI formula differs between common implementations, document the exact formula in code comments and output metadata.

---

# 13. FUTURE CMIP6 PROCESSING

Expected:

7 models × 2 scenarios

Models:

```text
ACCESS-ESM1-5
CanESM5
CESM2
EC-Earth3
FGOALS-g3
MIROC6
MRI-ESM2-0
```

Scenarios:

```text
SSP2-4.5
SSP5-8.5
```

Future:

`2021–2050`

Baseline:

`1995–2014`

CRITICAL:

Do NOT concatenate 7 models into one time series before MK/MMK.

Trend must be computed:

`model × scenario × station × index`

Then summarize across models.

Expected future trend-series count if all combinations are available:

`13 × 11 × 7 × 2 = 2002`

This must be validated.

---

# 14. CMIP6 FILE DISCOVERY

File discovery must not depend on fragile exact filenames if avoidable.

Parser must identify:

- model
- scenario
- station
- variable
- period

Must reject ambiguous matches.

If two files match the same:

`model + scenario + station`

the code must raise a clear error rather than silently choose one.

Must print a manifest:

```text
Model
Scenario
Station
File
Start date
End date
N records
```

Export:

`cmip6_file_manifest.csv`

---

# 15. FUTURE INDEX THRESHOLD CONSISTENCY

For R95p/R99p:

DO NOT calculate future-specific percentiles.

Use observed station-specific thresholds from 1981–2014.

This must be explicitly stored in metadata.

---

# 16. FUTURE TREND SUMMARIZATION

For each:

`scenario × station × index`

summarize:

- number of models
- number significant increasing
- number significant decreasing
- number non-significant
- median Sen slope
- median Z
- median p is descriptive only and must NOT be interpreted as ensemble significance
- sign agreement
- significance agreement

Recommended fields:

```text
n_models
n_sig_increasing
n_sig_decreasing
n_non_sig
median_sen_slope
median_Z
sign_agreement_pct
sig_agreement_pct
```

Do not calculate a formal ensemble p-value from the median Z unless a defensible statistical method is explicitly specified.

---

# 17. FUTURE CHANGE

For each:

`model × scenario × station × index`

calculate:

`Change = Future_2021_2050 - Historical_1995_2014`

For relative change:

`Change_pct = 100 × (Future - Historical) / Historical`

If historical baseline = 0:

- relative change = NaN
- absolute change remains valid

For count indices such as R50mm:

absolute change is more interpretable than unstable percentage change when baseline is near zero.

---

# 18. MODEL-CONSISTENT BASELINE

For each model/scenario/station/index:

historical baseline must come from the same model's historical period 1995–2014.

Do NOT subtract observed baseline directly from bias-corrected model future unless explicitly intended and documented.

Reason:

Future minus model historical gives a more internally consistent model climate-change signal.

---

# 19. 7-MODEL MEDIAN

At each station:

median across 7 models

must use NaN-aware median but also report number of contributing models.

Never hide missing models.

Output:

```text
n_models_available
median_change
min_change
max_change
```

Minimum model count for plotting should be configurable.

---

# 20. IDW AUDIT

IDW is only for spatial visualization.

It is NOT:

- downscaling
- trend detection
- ensemble significance
- physical climate model

Default:

`power = 2`

Must handle:

- duplicate coordinates
- station exactly at grid point
- zero distance
- insufficient stations
- NaN station values

If a grid cell coincides with a station:

use station value directly rather than divide by zero.

The interpolation domain should be documented.

If no province boundary shapefile exists:

do not fabricate one.

If boundary file exists, use it for clipping.

Export:

- interpolation grid
- station points
- mask information

---

# 21. SPATIAL MAP SCIENTIFIC LIMITATION

IDW maps must clearly be described as spatial interpolation of station-based changes.

Do not call them:

- downscaled maps
- dynamically simulated maps
- continuous climate model fields

unless that is actually what the data represent.

---

# 22. OBSERVED TREND OUTPUT

For each:

`station × index`

must output both:

### MK

```text
S
Var_S
Z
p_value
trend
significant
```

### Yue-Wang MMK

```text
S
Var_S
Var_S_adj
Z
p_value
rho_1
n_eff
n_over_neff
trend
significant
```

### Sen

```text
slope
slope_ci_low
slope_ci_high
```

No ambiguity between MK and MMK columns.

Recommended names:

```text
MK_Z
MK_p
MK_trend
MMK_Z
MMK_p
MMK_trend
MMK_rho1
MMK_neff
Sen_slope
Sen_CI_low
Sen_CI_high
```

---

# 23. TREND METHOD COMPARISON

Create a descriptive comparison:

```text
MK significant?
MMK significant?
Same direction?
Conclusion changed?
```

But do not label one method as "correct" merely because it produces significance.

The purpose is to show the effect of serial correlation correction.

---

# 24. DO NOT ADD MULTIPLE-TESTING CORRECTION

For this locked paper:

Do NOT add:

- FDR
- Bonferroni
- Holm

If multiple testing is discussed, report it as a limitation rather than silently modifying alpha.

---

# 25. DO NOT ADD PETTITT

No change-point detection.

Do not import Pettitt functions from the old `rainfall_trend_analysis_v5.py`.

---

# 26. DO NOT ADD PRE-WHITENING

No:

- PW
- TFPW

The older code contained these methods, but they are outside the locked methodology.

The old code explicitly includes PW/TFPW/Pettitt/FDR and therefore must NOT be copied into the new pipeline.

---

# 27. OLD CODE CONTAMINATION CHECK

Audit imports and functions.

Remove unused or legacy functions associated with:

- Hamed-Rao 1998
- PW
- TFPW
- Pettitt
- FDR
- Bonferroni
- Taylor
- seasonal analysis
- monthly analysis
- bootstrap CI

The older rainfall trend script contains all these components and should not be treated as the statistical source of truth.

---

# 28. OUTPUT VALIDATION

After successful execution, automatically validate that expected files exist.

Required:

```text
observed_indices_1981_2014.csv
observed_trend_1981_2014.csv
future_indices_2021_2050.csv
future_trend_2021_2050.csv
future_change_2021_2050.csv
station_coordinates_used.csv
station_thresholds.csv
qc_observed.csv
qc_models.csv
cmip6_file_manifest.csv
summary_by_index.csv
summary_by_model_scenario.csv
Uttaradit_Trend_Analysis.xlsx
```

If a required output is missing:

pipeline must end with FAILURE, not COMPLETE.

---

# 29. OUTPUT CONTENT VALIDATION

Check:

- expected 13 stations
- expected 11 indices
- expected 7 models
- expected 2 scenarios
- expected periods
- no duplicate keys
- no impossible p-values
- p in [0,1]
- significant flag consistent with p < 0.05
- slope CI low <= slope <= CI high when finite
- no unexpected inf
- no duplicate station-index-model-scenario combinations

---

# 30. EXPECTED ROW COUNTS

Observed indices:

approximately:

`34 years × 13 stations × 11 indices`

depending on long-format design.

Observed trend:

`13 × 11`

Future indices:

`30 years × 13 stations × 11 indices × 7 models × 2 scenarios`

Future trend:

`13 × 11 × 7 × 2`

Future change:

depending on long-format design, at minimum:

`13 × 11 × 7 × 2`

Model-median future change:

`13 × 11 × 2`

These must be asserted where appropriate.

---

# 31. DATA LEAKAGE CHECK

No future data may be used to determine:

- observed P95
- observed P99
- observed preprocessing parameters
- observed thresholds

No future values may enter observed trend calculations.

---

# 32. TEMPORAL LEAKAGE CHECK

Ensure:

- observed = 1981–2014
- model baseline = 1995–2014
- future = 2021–2050

No overlapping future years in baseline.

---

# 33. NUMERICAL STABILITY

All numerical routines must safely handle:

- all zero rainfall
- all constant series
- one valid value
- fewer than minimum trend length
- all NaN
- nearly constant series
- extreme but finite rainfall
- ties
- duplicate dates
- missing annual years

Minimum trend length:

`n >= 10`

Otherwise trend results should be NaN / not estimable with explicit status.

---

# 34. STATUS FLAGS

Do not communicate missing/failed statistics using only NaN.

Add explicit status where useful:

```text
OK
INSUFFICIENT_DATA
ALL_NAN
INVALID_INPUT
DUPLICATE_INPUT
MISSING_FILE
AMBIGUOUS_FILE
```

This is important for research auditability.

---

# 35. WARNINGS

Do NOT use:

```python
warnings.filterwarnings("ignore")
```

globally.

Warnings should be:

- specific
- justified
- logged

Never suppress warnings that could hide invalid scientific results.

---

# 36. LOGGING

Implement a clear execution log.

At minimum:

```text
INPUT
QC
STATIONS
OBSERVED INDICES
OBSERVED TREND
CMIP6 MANIFEST
FUTURE INDICES
FUTURE TREND
FUTURE CHANGE
ENSEMBLE SUMMARY
IDW
OUTPUT VALIDATION
FINAL STATUS
```

At final:

```text
SUCCESS
```

only if all mandatory validation checks pass.

Otherwise:

```text
FAILED VALIDATION
```

with a clear reason.

---

# 37. REPRODUCIBILITY

Create metadata output:

`analysis_metadata.json`

Include:

- script version
- execution timestamp
- Python version
- package versions
- input path
- output path
- observed period
- baseline period
- future period
- alpha
- annual completeness threshold
- wet-day threshold
- P95/P99 baseline
- models
- scenarios
- IDW power
- git commit if available

---

# 38. CONFIGURATION

Move methodological constants into a single configuration section/dataclass.

At minimum:

```python
OBS_START = 1981
OBS_END = 2014

BASELINE_START = 1995
BASELINE_END = 2014

FUTURE_START = 2021
FUTURE_END = 2050

ALPHA = 0.05
MIN_TREND_N = 10
ANNUAL_COMPLETENESS = 0.90
WET_DAY_THRESHOLD = 1.0
R95 = 0.95
R99 = 0.99
IDW_POWER = 2.0
```

Do not scatter these constants throughout functions.

---

# 39. TYPE SAFETY

Use:

- type hints
- clear return types
- dataclasses where appropriate
- NumPy/Pandas-compatible typing

Avoid excessive complexity.

Prefer small testable functions.

---

# 40. FUNCTION DESIGN

Recommended logical modules/functions:

```text
discover_inputs()
read_coordinates()
load_observed_rainfall()
load_cmip6_data()
validate_daily_data()
annual_completeness_qc()
compute_thresholds()
compute_indices()
standard_mk()
yue_wang_mmk_2004()
sens_slope_ci()
run_observed_analysis()
run_future_analysis()
compute_future_change()
summarize_models()
idw_interpolate()
write_outputs()
validate_outputs()
write_metadata()
```

Functions should have one clear responsibility.

---

# 41. TEST SUITE

Add lightweight internal tests or a separate:

`tests/test_statistics.py`

Tests must cover:

- MK
- Yue-Wang
- Sen
- indices
- missing data
- thresholds
- future baseline
- station matching
- IDW zero-distance handling

Do not rely only on "script ran successfully".

---

# 42. PROPERTY-BASED SANITY CHECKS

Where practical:

### Monotonic series

positive monotonic transformation should preserve MK direction.

### Station permutation

Changing station order must not change station-level results.

### Model permutation

Changing model order must not change ensemble median.

### IDW station order

Changing station order must not change interpolated grid.

### Unit scaling

Scaling rainfall by constant factor should scale amount-based indices and Sen slope accordingly, while MK p-value should generally remain invariant.

---

# 43. STATISTICAL CROSS-VALIDATION

Cross-check the implementation using independently implemented calculations where possible.

For example:

- Standard MK against a trusted reference implementation
- Yue-Wang against an established Yue-Wang implementation
- Sen slope against scipy / established package where applicable

Do not declare statistical correctness solely because unit tests pass.

---

# 44. FIGURE GENERATION

Current execution uses `--no-figures`.

Still audit figure code.

Requirements:

- no overlapping labels
- no garbled Unicode
- no unsupported symbols
- no legend inside data region when it obstructs data
- publication-quality DPI
- consistent units
- consistent station names
- colorblind-aware palette
- vector PDF/SVG where appropriate
- no excessive decorative elements

Legend should preferably be outside plot area when crowded.

No duplicated figure legends.

No scientific notation unless useful.

---

# 45. FIGURE DATA PROVENANCE

Every figure must be traceable to an output table.

Do not calculate a different statistic inside the plotting function.

Plotting functions should consume already validated result tables.

---

# 46. EXCEL OUTPUT

Excel workbook should include clear sheets, at minimum:

1. Metadata
2. Station Coordinates
3. Observed Indices
4. Observed Trend
5. Future Indices
6. Future Trend
7. Future Change
8. Model Summary
9. QC
10. File Manifest

No formulas should silently reference missing cells.

Freeze headers.

Use readable column widths.

Do not over-format.

---

# 47. RESEARCH INTERPRETATION SAFEGUARDS

The program must NOT automatically write statements such as:

- "climate change caused..."
- "significant regional trend..."
- "ensemble is significant..."

unless the statistical evidence supports that exact statement.

Trend detection ≠ attribution.

IDW interpolation ≠ downscaling.

Model median ≠ formal ensemble significance.

Future change ≠ future trend.

These distinctions must be preserved in metadata/reporting.

---

# 48. FUTURE TREND VS FUTURE CHANGE

Keep these conceptually separate:

### Trend

MK/MMK + Sen slope over:

`2021–2050`

### Change

difference between:

`2021–2050`

and

`1995–2014`

Do not use the word "trend" for future-minus-baseline maps.

---

# 49. ENSEMBLE INTERPRETATION

For each future station-index-scenario, report model agreement.

Example:

```text
7/7 increasing
5/7 significant increasing
2/7 non-significant
```

This is descriptive model agreement.

Do not convert it into a p-value without a formal ensemble statistical framework.

---

# 50. ERROR HANDLING PHILOSOPHY

Never do:

```python
except Exception:
    pass
```

Never silently skip a required file.

Never silently choose the first matching file when multiple matches exist.

Never convert an invalid dataset into a seemingly valid dataset.

Use explicit error messages with:

- station
- model
- scenario
- index
- year
- file

where relevant.

---

# 51. CLI

Support:

```bash
python Uttaradit_ETCCDI_MK_MMK2004_Sen_IDW_Q3.py --input "PATH"
```

Optional:

```bash
--output "PATH"
--idw-power 2
--no-figures
```

Add:

```bash
--validate-only
```

Recommended.

`--validate-only` should:

- discover files
- validate metadata
- validate station matching
- validate date ranges
- validate CMIP6 manifest
- report expected combinations
- not perform full analysis

---

# 52. DRY RUN

Implement a validation mode that reports:

```text
Observed:
13 stations
1981–2014
34 years

Coordinates:
13 stations

CMIP6:
7 models
2 scenarios
Expected combinations: 14 model-scenario groups

Future:
2021–2050
30 years

Indices:
11

Expected future trend series:
2002
```

Then:

```text
VALIDATION PASSED
```

or:

```text
VALIDATION FAILED
```

---

# 53. FINAL ACCEPTANCE CRITERIA

Claude must NOT report the code as complete merely because it executes without traceback.

It is complete only if:

[ ] syntax passes
[ ] imports pass
[ ] input validation passes
[ ] 13/13 stations match
[ ] observed period validated
[ ] 11 indices validated
[ ] annual completeness validated
[ ] P95/P99 thresholds validated
[ ] MK unit tests pass
[ ] Yue-Wang unit tests pass
[ ] Sen slope tests pass
[ ] future file manifest complete
[ ] 7 models detected
[ ] 2 scenarios detected
[ ] future period validated
[ ] 2002 future trend combinations validated where data are complete
[ ] baseline 1995–2014 validated
[ ] future change validated
[ ] ensemble median validated
[ ] IDW edge cases tested
[ ] output row counts validated
[ ] no duplicate keys
[ ] no impossible p-values
[ ] no unexpected infinity
[ ] required outputs exist
[ ] metadata generated
[ ] no legacy methods remain
[ ] no silent exception handling
[ ] final report states PASS/FAIL explicitly

---

# 54. IMPORTANT: DO NOT FABRICATE RESULTS

Claude must never:

- invent trend values
- invent p-values
- invent model results
- invent station data
- fill missing model results with fabricated values
- state "all 7 models available" unless manifest confirms it
- state "analysis complete" unless validation passes

---

# 55. DELIVERABLES REQUIRED FROM CLAUDE

Deliver:

## A. Corrected script

`Uttaradit_ETCCDI_MK_MMK2004_Sen_IDW_Q3_fixed.py`

or a clearly versioned replacement.

## B. Test suite

`tests/`

## C. Validation report

`VALIDATION_REPORT.md`

Must contain:

- bugs found
- bugs fixed
- statistical validation
- data validation
- remaining limitations

## D. Method metadata

`analysis_metadata.json`

## E. Requirements

`requirements.txt`

with pinned or minimum compatible versions.

## F. Change log

`CHANGELOG.md`

## G. If figures are generated

A figure QA report listing:

- filename
- dimensions
- DPI
- missing/overlap warnings
- data source

---

# 56. PRIORITY ORDER

If conflicts occur, use this order:

1. Scientific correctness
2. Data integrity
3. Statistical correctness
4. Reproducibility
5. Validation
6. Robust error handling
7. Maintainability
8. Figure aesthetics
9. Runtime optimization

Do not sacrifice scientific correctness for speed.

---

# 57. FINAL INSTRUCTION TO CLAUDE

Do a complete code audit before making isolated fixes.

Do NOT merely fix the current:

```text
NameError: name 'finite' is not defined
```

That is only the first discovered runtime bug.

Inspect the entire pipeline for latent bugs, statistical inconsistencies, incorrect assumptions, legacy methods, silent failures, and edge cases.

After modifications:

1. compile the script
2. run unit tests
3. run validation-only mode against the Uttaradit dataset
4. run the actual analysis if the dataset passes validation
5. validate all output tables
6. report every remaining limitation explicitly

The final implementation must preserve the locked methodology:

```text
Observed 1981–2014
        ↓
11 indices
        ↓
MK
        +
Yue-Wang (2004) MMK
        +
Sen slope + 95% CI

Future 2021–2050
        ↓
7 CMIP6 models × 2 SSP
        ↓
11 indices
        ↓
MK
        +
Yue-Wang (2004) MMK
        +
Sen slope + 95% CI
        ↓
model-by-model synthesis

Future change:
2021–2050 − model-consistent 1995–2014
        ↓
7-model median
        ↓
IDW spatial visualization
```

No Pettitt, FDR, Bonferroni, PW, TFPW, seasonal, monthly, Taylor diagram, or non-target indices.

The objective is not merely "code that runs."

The objective is:

**scientifically correct + statistically defensible + reproducible + auditable + publication-ready.**
