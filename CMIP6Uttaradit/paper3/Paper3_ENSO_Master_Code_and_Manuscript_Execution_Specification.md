# PAPER 3 — MASTER EXECUTION SPECIFICATION
## ENSO-conditioned seasonal rainfall and climate-signal preservation over Uttaradit, Thailand

---

# 0. MANDATE

Use the uploaded project archive `files (21).zip` as the primary source for the existing data, code, results, manuscript conventions, and provenance.

The objective is to:

1. audit and improve the existing reusable Python framework;
2. add an automated, reproducible ENSO module;
3. analyse daily rainfall separately for two management-oriented seasons:
   - **Rainy season: May–October**
   - **Hot/dry season: November–April of the following year**
4. classify seasons under **El Niño, Neutral, La Niña**, while explicitly retaining **Transition/Unclassified** for mixed or ambiguous seasons;
5. compare:
   - observed rainfall,
   - raw CMIP6 rainfall,
   - QDM-corrected CMIP6 rainfall;
6. evaluate both seasonal rainfall characteristics and selected rainfall extremes;
7. quantify whether QDM preserves, attenuates, or amplifies the observed/model ENSO-conditioned response;
8. test **ENSO asymmetry** between La Niña and El Niño;
9. produce a complete Paper 3 manuscript of **≤15 pages in APST format**, including publication-quality tables, figures, supplementary material, provenance and reproducibility files.

Do not invent data, years, source information, statistical significance, physical mechanisms, or citations.

Do not modify Paper 1 results.

Do not turn Paper 3 into another generic climate-projection paper.

The central scientific question is:

> **Does bias correction preserve the seasonal ENSO-conditioned response of daily precipitation and rainfall extremes at the local scale?**

The final paper must be driven by evidence from the actual data.

---

# 1. EXISTING PROJECT CONTEXT — LOCKED COMMON FOUNDATION

The uploaded archive contains the established Paper 1 framework with:

- 13 rain gauges in Uttaradit;
- daily observations for 1981–2014;
- 7 CMIP6 models;
- historical period 1981–2014;
- SSP2-4.5 and SSP5-8.5;
- calibration 1981–2002;
- independent validation 2003–2014;
- model-consistent future baseline 1995–2014;
- QDM implementation;
- common precipitation-index definitions;
- observed-data QC;
- verified Uttaradit administrative boundary;
- reusable YAML configuration architecture.

The existing framework already separates:
- marginal precipitation characteristics,
- sequence-dependent characteristics,
- independent validation,
- model agreement,
- provenance and acceptance gates.

Preserve those principles.

Paper 3 adds an ENSO-conditioned layer. It does not replace the common data/QC/BC foundation.

---

# 2. PAPER 3 SCIENTIFIC IDENTITY

## Recommended title

**Seasonal and ENSO-Conditioned Rainfall Response in Bias-Corrected CMIP6 Daily Precipitation over Uttaradit, Thailand**

Alternative, if a stronger method-oriented title is preferred:

**Preservation of Seasonal ENSO Rainfall Signals in Bias-Corrected CMIP6 Daily Precipitation over Uttaradit, Thailand**

Do not use:
- “best method”;
- “optimal bias correction”;
- “perfect preservation”;
- unsupported causal language.

The preferred title should communicate:
- seasonal rainfall;
- ENSO conditioning;
- bias correction;
- daily precipitation;
- CMIP6;
- Uttaradit.

If APST requires acronym expansion in the title, expand CMIP6/QDM/ENSO as required by the current journal rules.

---

# 3. SCIENTIFIC GAP

Do not frame the novelty as “previous studies are wrong”.

Build the gap as a scientific question:

> Rainfall anomalies associated with ENSO are expressed through seasonal timing, intensity and extremes. Bias correction changes the statistical representation of rainfall. Therefore, a key unresolved question is whether the ENSO-conditioned rainfall response observed at local stations remains identifiable after bias correction.

The gap is therefore:

**overall climatological correction**
≠
**conditional preservation of climate variability**

The paper must distinguish:

1. correction of unconditional rainfall bias;
2. preservation of ENSO-conditioned rainfall response;
3. preservation of ENSO asymmetry;
4. preservation of derived rainfall extremes.

---

# 4. DEFINITIVE RESEARCH QUESTIONS

Use three core research questions.

### RQ1

**How does ENSO influence daily precipitation characteristics during the rainy and hot/dry seasons in Uttaradit?**

### RQ2

**To what extent do raw and QDM-corrected CMIP6 simulations reproduce the observed seasonal ENSO-conditioned rainfall response and associated extremes?**

### RQ3

**Does QDM preserve the magnitude and asymmetry of the ENSO response, or does the correction attenuate or amplify the modelled signal?**

Do not add more research questions unless the actual results show a necessary additional scientific dimension.

---

# 5. MANAGEMENT-ORIENTED SEASON DEFINITION — NON-NEGOTIABLE

Use exactly two seasons.

## Rainy season

**May–October**

Season-year:

`Rainy 2005 = 2005-05-01 through 2005-10-31`

## Hot/dry season

**November–April of the following year**

Season-year:

`Hot/dry 2005/06 = 2005-11-01 through 2006-04-30`

Never label the hot/dry season only as “2006” without explicitly retaining its start year.

The season definitions must be identical in:

- configuration;
- code;
- data output;
- tables;
- figures;
- manuscript Methods;
- Results;
- Discussion;
- Supplementary material.

The seasonal framework is intended to support interpretation for:

- water allocation;
- reservoir operation;
- irrigation planning;
- drought preparedness;
- flood preparedness;
- agricultural scheduling/crop calendars.

Do not claim that these management applications were operationally tested unless actual management data are available.

---

# 6. ENSO SOURCE — AUTOMATIC, PINNED, TRACEABLE

Use NOAA Climate Prediction Center historical ONI as the primary ENSO source.

For the historical classification used in this paper, use a clearly pinned ONI dataset/version and preserve the exact downloaded file in the project archive.

At the current NOAA CPC source, historical ONI is provided by season and uses a ±0.5°C threshold; historical El Niño/La Niña episodes are identified when the threshold is met for at least five consecutive overlapping three-month seasons. The CPC page currently provides historical ONI through the present and notes that the official operational monitoring uses RONI, but historical ONI remains available. For reproducibility, **do not silently switch between ONI and RONI**. Pin one index/version for this study and report it explicitly.

Source to use:
NOAA CPC historical Oceanic Niño Index:
https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/

Record:
- URL;
- dataset/version;
- download/access date;
- SHA-256;
- file format;
- exact rows/columns used.

Do not scrape a third-party ENSO table when NOAA CPC data are available.

---

# 7. ENSO CLASSIFICATION ARCHITECTURE

Do not assign ENSO phase to every calendar year first and then copy the annual label onto both seasons.

That would lose the seasonal information that this paper is designed to study.

Use a two-layer approach.

## Layer A — Official ENSO episode catalogue

Build an `enso_episode_catalog.csv` from the pinned NOAA ONI source.

Fields:

- episode_id
- phase
- start_season
- end_season
- threshold
- persistence_rule
- ONI_version
- source_url
- access_date
- source_hash

Phases:

- EL_NINO
- LA_NINA

Periods that do not belong to an official episode are not automatically assumed to be “Neutral” at this stage.

## Layer B — season-specific classification

For each management season, calculate the ONI evidence during the season and assign:

- EL_NINO
- NEUTRAL
- LA_NINA
- TRANSITION_UNCLASSIFIED

Do not force mixed seasons into El Niño/La Niña.

The classification rule must be deterministic and documented.

---

# 8. RECOMMENDED SEASON-SPECIFIC ENSO RULE

Use the NOAA ONI three-month values as the underlying series.

For each management season:

1. identify all ONI seasons whose temporal window overlaps the management season;
2. compute the seasonal ENSO evidence using the overlap-weighted ONI contribution;
3. determine whether the season is predominantly positive, neutral, or negative;
4. retain a Transition/Unclassified label when positive and negative ENSO evidence is materially mixed or the season is not sufficiently represented by an official persistent episode.

Important:

Do not invent an arbitrary “60%” or “75%” rule merely because it creates convenient sample sizes.

Instead, implement the rule from explicitly stated episode membership where possible.

Preferred classification hierarchy:

1. If the management season lies substantially within an official El Niño episode → EL_NINO.
2. If substantially within an official La Niña episode → LA_NINA.
3. If it does not belong to either official episode and does not contain a qualifying persistent episode → NEUTRAL only if the season is not transitional.
4. If the season crosses or materially mixes opposite phases → TRANSITION_UNCLASSIFIED.

If implementation requires a numerical overlap threshold, expose it in YAML and conduct a sensitivity analysis with one reasonable alternative threshold. Do not change the threshold after looking at results.

The chosen rule must be frozen before the main ENSO rainfall analysis.

---

# 9. DO NOT USE CALENDAR “YEAR” AS THE ONLY ENSO UNIT

Required season identifiers:

`2000_RAIN`

`2000_01_HOT_DRY`

`2001_RAIN`

`2001_02_HOT_DRY`

or a similarly unambiguous naming convention.

For every season create:

- season_id
- season_type
- season_start
- season_end
- climate_year
- ENSO_phase
- ENSO_episode_id
- ONI_mean
- ONI_min
- ONI_max
- n_ONI_seasons/observations
- classification_rule
- classification_confidence/status

---

# 10. HISTORICAL ANALYSIS PERIOD FOR ENSO

Primary ENSO comparison should use the **common period for which observed rainfall, CMIP6 historical data, and the pinned ENSO index overlap**.

Given the locked project foundation, use:

**1995–2014**

unless the actual data audit establishes a different defensible common period.

Do not silently extend the analysis using observations alone if the raw/QDM comparison cannot be made for the same years.

The final manuscript must report:

- number of rainy seasons;
- number of hot/dry seasons;
- number classified El Niño;
- number Neutral;
- number La Niña;
- number Transition/Unclassified.

Sample size must be shown for every seasonal ENSO comparison.

---

# 11. REQUIRED CODE MODULES TO ADD

Add reusable modules rather than embedding ENSO logic in one paper script.

Recommended:

```text
src/cmip6bc/enso.py
src/cmip6bc/seasonal.py
src/cmip6bc/enso_analysis.py
src/cmip6bc/enso_figures.py
scripts/run_paper3.py
scripts/build_paper3.py
config/paper3_enso.yaml
```

The modules must be reusable for another region by changing YAML configuration.

No province name should be hard-coded into `enso.py`, `seasonal.py`, or `enso_analysis.py`.

---

# 12. PROPOSED YAML CONFIGURATION

Add a configuration block such as:

```yaml
enso:
  source: NOAA_CPC_ONI
  index: ONI
  version: "PINNED_VERSION_USED_FOR_THIS_STUDY"
  url: "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/"
  threshold_c: 0.5
  persistence_seasons: 5

seasons:
  rainy:
    label: "Rainy season"
    months: [5, 6, 7, 8, 9, 10]
    cross_year: false

  hot_dry:
    label: "Hot/dry season"
    start_month: 11
    end_month: 4
    cross_year: true

enso_analysis:
  common_period: [1995, 2014]
  excluded_class: "TRANSITION_UNCLASSIFIED"
  minimum_seasons_for_composite: 3
  bootstrap_repetitions: 5000
  seed: 20260830
```

Do not hard-code these parameters in the Python module.

The actual NOAA ONI version and final classification configuration must be recorded in the manifest.

---

# 13. SEASONAL RAINFALL METRICS

Calculate the same metrics for:

### Observed

### Raw CMIP6

### QDM-corrected CMIP6

For each season and ENSO phase:

- PRCPTOT
- wet-day frequency
- SDII
- Rx1day
- Rx5day
- R20mm
- R50mm
- R95p
- R99p
- CDD
- CWD

Optional:
- q50
- q90
- q95
- q99

Do not overload the main paper with every metric. Full output can go to supplementary material.

---

# 14. IMPORTANT EXTREME-INDEX CATEGORIZATION

Keep the following conceptual distinction.

## Pointwise / marginal

- wet-day frequency
- PRCPTOT
- SDII
- q50
- q90
- q95
- q99
- Rx1day

## Multi-day / sequence-dependent

- Rx5day
- CDD
- CWD

## Threshold/tail-derived

- R20mm
- R50mm
- R95p
- R99p

Do not state that all extreme indices are equivalent.

---

# 15. PRIMARY ENSO RESPONSE METRIC

For each rainfall statistic X:

### El Niño response

```text
A_ElNino = X_ElNino - X_Neutral
```

### La Niña response

```text
A_LaNina = X_LaNina - X_Neutral
```

Use percentage anomaly as the main comparison when the neutral baseline is non-zero:

\[
A_{phase}(\%) =
100
\frac{X_{phase}-X_{neutral}}
{X_{neutral}}
\]

Also retain absolute differences in machine-readable outputs.

Do not compute percentage anomalies using an observed all-period climatology when the stated question is phase-conditioned.

---

# 16. ENSO ASYMMETRY — KEY CONTRIBUTION

Calculate:

\[
ASYM =
A_{LaNiña} - A_{ElNiño}
\]

Do this independently for:

- observed;
- raw CMIP6;
- QDM.

This directly tests whether the contrast between opposite ENSO phases is retained.

Create:

```text
enso_asymmetry.csv
```

with:

- region
- season
- statistic
- source_type
- model
- ASYM
- uncertainty bounds
- n_elnino
- n_neutral
- n_lanina
- classification_rule

Do not claim symmetry/asymmetry is significant without an appropriate inferential test.

---

# 17. QUANTIFY “PRESERVED / ATTENUATED / AMPLIFIED”

For observed ENSO response, calculate a response magnitude.

For model data:

\[
R_{model}
=
A_{phase,model}
\]

For QDM:

\[
R_{QDM}
=
A_{phase,QDM}
\]

Compare:

\[
PE_{ENSO}
=
100
\frac{R_{QDM}-R_{RAW}}
{R_{RAW}}
\]

where the denominator is not near zero.

Interpretation:

- PE_ENSO ≈ 0 → QDM approximately preserves the raw model's ENSO response;
- PE_ENSO > 0 → response amplified by correction;
- PE_ENSO < 0 → response attenuated.

Also evaluate QDM relative to observations, but do not confuse:
- QDM-vs-raw preservation
with
- QDM-vs-observation agreement.

They are different questions.

---

# 18. RESPONSE AGREEMENT SHOULD BE SEPARATED FROM SIGNAL PRESERVATION

For each ENSO-season-statistic combination, report:

### Observational response
Does observed rainfall differ between ENSO phases?

### Raw-model response
Do raw GCMs reproduce the direction/magnitude?

### QDM response
Does corrected output move toward the observed response?

### Preservation
Does QDM preserve the model's raw ENSO response?

These are four different quantities.

Do not collapse them into one score.

---

# 19. STATISTICAL INFERENCE

The historical ENSO sample is likely small.

Therefore:

1. report n for every ENSO phase;
2. do not rely on asymptotic normality without checking;
3. use permutation-based inference or an appropriate rank-based comparison where justified;
4. calculate effect size;
5. use bootstrap confidence intervals where the sample size permits;
6. report uncertainty rather than only p-values.

For El Niño vs Neutral and La Niña vs Neutral, use a pre-specified test.

For small samples:
- exact/permutation procedures are preferred;
- avoid multiple uncorrected pairwise t-tests.

If multiple statistics are tested, state whether multiplicity correction is applied. If the study is primarily descriptive/exploratory, label the results accordingly rather than manufacturing formal “significance”.

Do not select a statistical test after seeing which one gives the desired conclusion.

---

# 20. MODEL-LEVEL ENSO ANALYSIS

For every GCM:

```text
model
station
season
ENSO phase
metric
value
```

Then calculate:

- station-level ENSO anomaly;
- model-level anomaly;
- ensemble median;
- inter-model IQR;
- agreement fraction.

Do not pool all daily values across models and stations before computing the ENSO response.

The analysis must preserve the hierarchy:

`daily → season → station → model → ensemble`

---

# 21. STATION AGGREGATION

Primary regional estimate:

- compute the statistic separately at each gauge;
- calculate ENSO response per gauge;
- then summarize across gauges.

Recommended regional summary:

- median across stations;
- IQR across stations;
- model ensemble information retained separately.

Do not let stations with long records or more observations dominate the seasonal anomaly.

Because the common historical period is fixed, all stations/models should contribute under the same season definition.

---

# 22. ENSO SPATIAL ANALYSIS

Optional but useful.

For each season:

- gauge-level median ENSO anomaly;
- gauge-level model agreement;
- verified Uttaradit boundary.

Use a station-based map as the factual result.

If an interpolated map is created, treat it strictly as visualization.

Preferred:

**station points + optional IDW surface**

where:
- point = analyzed gauge;
- colour = ENSO anomaly;
- marker size = model agreement.

Do not present the surface as a climate-model field.

---

# 23. TWO SEASONAL FIGURES ARE REQUIRED

Create one central seasonal-response figure:

### Figure 1
Observed ENSO-conditioned seasonal rainfall response.

Two panels:
- (a) Rainy season May–October
- (b) Hot/dry season November–April

x-axis:
El Niño / Neutral / La Niña

show:
- median;
- uncertainty interval;
- station/model distribution where appropriate.

### Figure 2
Raw CMIP6 versus QDM ENSO response.

Same two seasons.

This directly communicates whether QDM moves model behaviour toward or away from the observed response.

---

# 24. FIGURE 3 — ENSO ASYMMETRY

Two panels:

- rainy season;
- hot/dry season.

Show:

`Observed`
`Raw CMIP6`
`QDM`

for:

\[
ASYM = A_{LaNiña}-A_{ElNiño}
\]

Use point/range or dot-whisker design.

This should be a central figure.

---

# 25. FIGURE 4 — EXTREME-RAINFALL RESPONSE

Two panels:

### Rainy season
- Rx1day
- Rx5day
- R20mm
- R50mm
- R95p
- R99p

### Hot/dry season
same indices.

Use:
- observed;
- raw;
- QDM.

Do not put CDD/CWD into this figure if it makes interpretation confusing.

---

# 26. FIGURE 5 — TEMPORAL / PERSISTENCE DIAGNOSTICS

Use:

- CDD
- CWD
- mean wet-spell length
- mean dry-spell length
- occurrence ACF(1)

Show whether ENSO-conditioned persistence is reproduced.

Label this figure:

> **Temporal-response diagnostics**

Do not present these as fully corrected projections.

---

# 27. FIGURE 6 — INTEGRATED SYNTHESIS

Create a compact heatmap:

Rows:
- PRCPTOT
- SDII
- Rx1day
- Rx5day
- R20
- R50
- R95p
- R99p
- CDD
- CWD

Columns:

`Observed ENSO response`
`Raw CMIP6`
`QDM`
`ENSO preservation error`

Separate:
- rainy season;
- hot/dry season.

This figure can become the paper's synthesis figure.

Do not overcrowd it.

---

# 28. FIGURE QUALITY REQUIREMENTS

Use the same high-quality standard established for Paper 1.

All figures:

- 600 dpi PNG;
- vector PDF where possible;
- Times New Roman or the journal-approved family;
- no overlapping labels;
- no clipped legends;
- no excessive white space;
- consistent axis ranges for directly comparable panels;
- identical method symbols across figures;
- readable at final manuscript size;
- colourblind-aware encoding;
- sufficient contrast in grayscale;
- no visual element that implies stronger spatial precision than the data support.

For any interpolated map:
- state that it is visualization only;
- display station points;
- do not hide sparse support.

---

# 29. MAIN TABLES — MAXIMUM SIX

## Table 1
ENSO seasons and sample sizes.

Columns:

- Season
- Period
- El Niño n
- Neutral n
- La Niña n
- Transition/Unclassified n
- ONI source/version
- classification rule

## Table 2
Observed seasonal ENSO response.

## Table 3
Raw versus QDM CMIP6 ENSO-conditioned response.

## Table 4
ENSO response in selected rainfall extremes.

## Table 5
ENSO asymmetry and signal-preservation error.

## Table 6
Method/model summary and sensitivity analysis, if necessary.

Full station/model outputs → supplementary.

---

# 30. SUPPLEMENTARY TABLES

Produce at least:

### S1
Complete ENSO episode catalogue.

### S2
Season-by-season ENSO classification.

### S3
Observed station-level ENSO response.

### S4
Raw CMIP6 model/station ENSO response.

### S5
QDM model/station ENSO response.

### S6
Extreme-index response.

### S7
ENSO asymmetry.

### S8
Statistical inference / bootstrap / permutation results.

### S9
Classification sensitivity.

### S10
Code/provenance manifest.

Do not cite supplementary files in the manuscript if they are not actually supplied with the submission.

---

# 31. PAPER 3 METHODS STRUCTURE

## 2. Materials and Methods

### 2.1 Study area and daily rainfall data

Keep concise.

Describe:
- Uttaradit;
- monsoon influence;
- 13 gauges;
- 1981–2014;
- two management-oriented seasons.

### 2.2 ENSO index and classification

Describe:
- NOAA CPC ONI;
- pinned version;
- ±0.5°C threshold;
- five-season historical persistence rule;
- season-specific assignment;
- transition handling.

### 2.3 CMIP6 simulations

Use the same 7-model foundation as Paper 1.

### 2.4 Bias correction

Describe QDM only.

Do not reproduce the full Paper 1 methodological discussion.

Reference the common pipeline where appropriate.

### 2.5 Seasonal rainfall and extreme indices

Define metrics.

### 2.6 ENSO-conditioned rainfall response

Define phase-minus-neutral anomaly.

### 2.7 ENSO asymmetry and signal preservation

Define ASYM and PE_ENSO.

### 2.8 Statistical inference and ensemble synthesis

Define:
- station aggregation;
- model aggregation;
- IQR;
- agreement;
- uncertainty.

---

# 32. INTRODUCTION STRUCTURE

Write the Introduction as a modern scientific narrative:

### Paragraph 1
Rainfall seasonality matters for water and agriculture.

### Paragraph 2
ENSO is an important source of interannual variability.

### Paragraph 3
ENSO effects are not necessarily uniform across seasons or rainfall characteristics.

### Paragraph 4
Bias-corrected climate data are increasingly used for local assessment.

### Paragraph 5
A corrected climatology does not automatically establish preservation of conditional ENSO behaviour.

### Paragraph 6
Uttaradit + daily data + 13 gauges + CMIP6 + QDM create a testable local framework.

### Final paragraph
Three RQs.

Do not write a literature-review catalogue.

Use literature selectively and naturally.

---

# 33. DO NOT TURN INTRODUCTION INTO A CRITIQUE OF PREVIOUS PAPERS

Avoid formulations such as:

- “previous studies failed to...”
- “previous studies incorrectly...”
- “existing studies are inadequate...”

unless a very specific documented methodological issue needs to be established.

Prefer:

> “A further question is whether...”

> “This raises the need to evaluate...”

> “The extent to which... remains important for...”

The tone should be constructive and scientific.

---

# 34. EXPECTED DISCUSSION STRUCTURE

## 4.1 ENSO effects differ by management-oriented season

Discuss how rainfall responds differently during:
- rainy;
- hot/dry.

Relate cautiously to water availability and agriculture.

## 4.2 Raw CMIP6 representation of ENSO rainfall response

Compare:
- direction;
- magnitude;
- model spread.

## 4.3 What QDM preserves and what it changes

Distinguish:
- bias reduction;
- raw-model ENSO signal preservation;
- closeness to observations.

## 4.4 ENSO asymmetry and rainfall extremes

This should be a major scientific discussion.

## 4.5 Implications for water and agriculture

Discuss:
- seasonal allocation;
- reservoir operation;
- irrigation;
- drought/flood preparedness;
- crop timing.

But do not claim operational improvement unless tested.

## 4.6 Limitations

At minimum:
- short ENSO sample;
- one model realisation;
- 13 gauges;
- model spatial resolution;
- station metadata limitations;
- QDM is marginal;
- ENSO is one climate mode among many;
- observational and model periods are limited to the common overlap.

---

# 35. IMPORTANT: DO NOT CLAIM PHYSICAL CAUSATION

The paper may state:

> rainfall is associated with ENSO phase.

It may not state:

> ENSO caused the rainfall change

unless an appropriate causal attribution framework is actually conducted.

Likewise do not claim:
- monsoon circulation changed because ENSO;
- atmospheric moisture caused the result;
- teleconnection mechanism was proven.

Those are physical interpretations that require additional atmospheric diagnostics.

---

# 36. OBSERVED IMPACT LANGUAGE

Use management relevance carefully.

Good:

> “The seasonal contrast is relevant to irrigation and reservoir planning because water availability and demand are strongly seasonal.”

Avoid:

> “The results prove that reservoir operation should be changed.”

Avoid prescribing operational decisions unless actual reservoir/irrigation simulations are performed.

---

# 37. CLIMATE-SIGNAL PRESERVATION — IMPORTANT INTERPRETATION

Keep two distinct concepts:

### QDM preservation relative to raw model

Does QDM alter the raw model's ENSO response?

### QDM agreement with observation

Does QDM reproduce the observed ENSO response?

Possible outcomes:

1. QDM preserves raw response but both raw and QDM disagree with observations.
2. QDM changes the response and moves it toward observations.
3. QDM changes the response and moves it away from observations.
4. raw and QDM differ little.

All four are scientifically meaningful.

Do not define “preservation” as automatically “good”.

---

# 38. TEST FOR DIRECTIONAL CONSISTENCY

For each:

- model;
- station;
- season;
- statistic;

calculate:

`sign(ENSO response)`

Then summarize:

- observed direction;
- raw-model agreement with observed direction;
- QDM agreement with observed direction.

This is separate from magnitude.

Create:

`enso_direction_agreement.csv`

Columns:

- season
- statistic
- phase
- source_type
- n_models
- n_stations
- agreement_with_observed_direction
- median_response
- IQR_response

---

# 39. TEST FOR MAGNITUDE PRESERVATION

Calculate:

\[
MagnitudeError =
|R_{model}-R_{obs}|
\]

and:

\[
RelativeMagnitudeError =
100
\frac{|R_{model}-R_{obs}|}
{|R_{obs}|}
\]

only where the denominator is safely non-zero.

Compare:
- raw;
- QDM.

This answers a different question from PE_ENSO.

---

# 40. MODEL AGREEMENT

Use the existing project convention if retained:

\[
Agreement =
\frac{\max(n_+, n_-)}
{n_{valid}}
\]

But do not automatically call this “robust”.

If used in Paper 3, call it:

> **ensemble directional agreement**

If a threshold is applied, state clearly whether it is:
- a study-defined interpretive threshold;
- not a universal statistical significance criterion.

---

# 41. ENSO CLASSIFICATION SENSITIVITY

Because the historical ENSO sample is small, run one pre-specified sensitivity analysis.

Example:

Primary classification:
official episode membership + season overlap.

Sensitivity:
seasonal mean ONI-based classification using the same ±0.5°C physical threshold.

Compare:
- which seasons change class;
- whether main rainfall conclusions change.

Do not tune the primary classification after seeing the results.

If the conclusion is stable:
> “The principal ENSO-season rainfall contrasts were insensitive to the alternative classification rule.”

If not:
> “The magnitude/direction is classification-sensitive.”

Do not hide sensitivity.

---

# 42. SAMPLE-SIZE GATE

Create an explicit acceptance gate:

### ENSO sample-size gate

If any ENSO-season comparison has too few events:

- calculate;
- report;
- classify as `diagnostic`;
- do not make strong generalisations.

Do not silently pool rainy and hot/dry seasons merely to increase n.

If one phase has very small n:
- use the result descriptively;
- show uncertainty;
- explicitly label it as low-sample evidence.

---

# 43. IMPORTANT DATA-INTEGRITY CHECKS

Before analysis:

### Observed
- date continuity;
- missing values;
- flagged months;
- station completeness.

### ONI
- no duplicated rows;
- no missing seasons in analysis period;
- source hash;
- version pinned.

### Season construction
- rainy seasons contain exactly May–October;
- hot/dry seasons contain exactly November–April;
- cross-year dates are correct;
- no overlapping seasons;
- no duplicated days;
- no partial season included in primary analysis.

### Model
- historical model segment matches common data;
- calendar handling consistent;
- station mapping unchanged.

### QDM
- parameters fitted only on calibration;
- frozen before historical ENSO application;
- no observations from target year used by application.

---

# 44. DO NOT USE FUTURE PROJECTIONS AS THE PRIMARY ENSO ANALYSIS

The central ENSO analysis is historical/observational and model-historical:

**1995–2014**

This establishes whether CMIP6 + QDM reproduce historical ENSO-conditioned behaviour.

Do not jump directly from historical ENSO composites to 2021–2050 future ENSO projections unless there is a separate defensible methodology for defining future ENSO states in the GCMs.

If future ENSO analysis is later attempted, treat it as a separate extension, not part of the core Paper 3.

---

# 45. RELATIONSHIP TO PAPER 1

Paper 1:
- QDM;
- independent validation;
- 2021–2050 precipitation projection.

Paper 3:
- QDM;
- historical conditional variability;
- ENSO;
- two management seasons;
- observed/raw/QDM comparison;
- ENSO asymmetry.

Paper 3 may reuse the common Methods foundation but must not duplicate the Paper 1 future-projection Results.

---

# 46. RELATIONSHIP TO PAPER 2

Paper 2:
- QM/EQM;
- DetQM;
- QDM;
- method comparison;
- climate-signal preservation.

Paper 3:
- QDM only;
- ENSO-conditioned preservation.

Do not add QM and DetQM to Paper 3 merely for completeness.

If comparative ENSO preservation across methods is desired, that belongs to Paper 2 or a separate study.

---

# 47. RELATIONSHIP TO THE SUPPLIED ENSO LITERATURE

Use the supplied Thailand ENSO study as scientific background for:
- ENSO-season rainfall linkage;
- seasonal variation;
- Thai context.

Do not reproduce its exact:
- station selection;
- seasonal definitions;
- ERA5 workflow;
- composite maps.

The present study deliberately uses:
- 13 gauges;
- daily rainfall;
- CMIP6;
- QDM;
- two water-management seasons;
- extreme indices;
- ENSO-preservation analysis.

This creates a distinct scientific question.

---

# 48. AUTOMATION / REUSABILITY REQUIREMENT

The entire Paper 3 workflow must run by changing only the area configuration.

Example:

```bash
python run_paper3.py --config config/uttaradit_enso.yaml
```

For another province:

```bash
python run_paper3.py --config config/phitsanulok_enso.yaml
```

No manual editing of:
- ENSO years;
- dates;
- province names;
- station names;
- model lists.

The ENSO module must detect applicable historical seasons automatically.

---

# 49. REQUIRED AUTOMATED OUTPUTS

Create:

```text
enso_raw_source.csv
enso_episode_catalog.csv
enso_season_classification.csv
enso_classification_sensitivity.csv

seasonal_observed.csv
seasonal_raw_cmip6.csv
seasonal_qdm.csv

enso_response_observed.csv
enso_response_raw.csv
enso_response_qdm.csv

enso_direction_agreement.csv
enso_magnitude_error.csv
enso_asymmetry.csv
enso_signal_preservation.csv
enso_extremes.csv

enso_statistics.csv
enso_sample_sizes.csv

PAPER3_ACCEPTANCE_GATES.csv
PAPER3_INTERPRETATION_SCOPE.csv

paper3_claim_audit.csv
paper3_manifest.json
paper3_file_hashes.csv
```

---

# 50. ACCEPTANCE GATES

Create explicit gates.

## P3-A — ENSO source

PASS only when:
- source retrieved;
- version pinned;
- source hash recorded.

## P3-B — Season construction

PASS only when:
- all dates map correctly;
- cross-year season is valid;
- no overlap/gap.

## P3-C — ENSO classification

PASS only when:
- deterministic rule is implemented;
- ambiguous seasons retained as unclassified;
- sample sizes reported.

## P3-D — Common data

PASS only when:
- same stations/models;
- same QC;
- same historical period.

## P3-E — QDM application

PASS only when:
- frozen parameters are used;
- target-year observations are never consulted.

## P3-F — ENSO response

PASS only when:
- observed/raw/QDM responses are independently calculated.

## P3-G — Asymmetry

PASS only when:
- La Niña and El Niño are both represented adequately;
- ASYM is reproducible.

## P3-H — Statistical inference

PASS only when:
- sample size supports the selected procedure;
- uncertainty is reported;
- exploratory results are labelled appropriately.

---

# 51. INTERPRETATION STATUS VOCABULARY

Use:

**VERIFIED**
Directly supported by the calculated dataset.

**DERIVED**
Mathematically calculated from verified values.

**DIAGNOSTIC**
Useful evidence but affected by limited sample size or methodological restrictions.

**LIMITATION**
Known constraint.

**NOT ESTABLISHED**
Evidence insufficient for the claim.

Never convert:
- ENSO association → causation;
- model agreement → significance;
- signal preservation → observational correctness;
- small sample → robust conclusion.

---

# 52. CLAIM-AUDIT TABLE

Every quantitative statement in:
- Abstract;
- Results;
- Discussion;
- Conclusion

must have a claim-audit row.

Required columns:

```text
claim_id
section
exact_claim
source_file
source_table
source_figure
season
ENSO_phase
statistic
source_type
exact_value
n
uncertainty
interpretation_status
approved_wording
```

Final manuscript cannot be generated as “FINAL” until all quantitative claims pass this audit.

---

# 53. FIGURE/TABLE NUMERICAL AUDIT

Programmatically compare:

```text
source CSV
→ analysis summary
→ table
→ figure
→ manuscript text
```

Check:
- signs;
- units;
- percentages;
- sample size;
- seasonal label;
- ENSO phase;
- model count;
- uncertainty range.

Any mismatch blocks finalization.

---

# 54. MANUSCRIPT STRUCTURE — ≤15 PAGES

## Title

Seasonal and ENSO-Conditioned Rainfall Response in Bias-Corrected CMIP6 Daily Precipitation over Uttaradit, Thailand

## Abstract

≤250 words.

## Keywords

4–11 keywords, consistent with APST.

## 1. Introduction

≈1.5–2 pages.

## 2. Materials and Methods

≈3 pages.

## 3. Results

≈4–5 pages.

## 4. Discussion

≈3 pages.

## 5. Conclusion

≈0.5 page.

Then:
- Acknowledgements;
- Ethical Approval if required;
- Author Contributions;
- AI declaration if required;
- Conflict of Interest;
- References.

Keep within the actual APST page constraint.

---

# 55. ABSTRACT — REQUIRED CONTENT

The abstract must contain:

### Background
Importance of seasonal ENSO rainfall variability.

### Objective
Assess ENSO-conditioned rainfall and preservation after QDM.

### Methods
13 gauges, 7 CMIP6 models, 1995–2014, two seasons, ONI classification, QDM.

### Results
Only the strongest findings:
- observed seasonal contrast;
- raw-vs-QDM response;
- one major extreme finding;
- ENSO asymmetry.

### Conclusion
State whether QDM:
- preserves;
- attenuates;
- amplifies;
or shows mixed behaviour.

Do not claim a single universal outcome unless supported across all statistics.

---

# 56. WRITING STYLE

Use natural academic English.

Prefer:

> “The ENSO response differed between the two management-oriented seasons.”

over:

> “This clearly demonstrates that ENSO has a profound effect...”

Prefer:

> “QDM reduced the magnitude of the model bias while preserving/attenuating the seasonal ENSO response.”

Only use the preservation verb supported by actual PE_ENSO.

Avoid:
- “proves”;
- “perfectly”;
- “highly significant” unless formally demonstrated;
- “robust” for small-sample composites;
- “caused by ENSO”;
- “universal”;
- “best method”.

---

# 57. CONCLUSION — REQUIRED LOGIC

The conclusion should answer the RQs in order.

1. ENSO-conditioned rainfall differs between rainy and hot/dry seasons.
2. Raw CMIP6 performance differs from observations in direction and/or magnitude.
3. QDM changes historical model bias but does not necessarily preserve all ENSO-conditioned characteristics equally.
4. ENSO asymmetry may be preserved for some statistics but altered for others.
5. Extreme and temporal indices require separate interpretation.
6. The findings support season-specific climate information for water and agricultural planning, while retaining the stated limitations.

Do not repeat all numerical values.

---

# 58. FINAL PAPER 3 CONTRIBUTION

The final paper should ideally deliver this scientific contribution:

> **Bias correction is not only a question of matching the rainfall distribution; it is also a question of whether management-relevant patterns of climate variability remain recognizable after correction.**

The study operationalizes this by testing:

**ENSO phase → seasonal rainfall response → extremes → QDM transformation → signal preservation**

The key contribution is not simply that:
> “El Niño decreases rainfall.”

It is:

> **whether and how the seasonal contrast between El Niño and La Niña is represented in daily rainfall, and whether that contrast survives bias correction.**

---

# 59. EXECUTION ORDER

Execute in exactly this order.

### Phase 1 — Code audit

1. Inspect existing `config/uttaradit.yaml`.
2. Inspect `src/cmip6bc/metrics.py`.
3. Inspect existing seasonal calculations.
4. Inspect existing QDM.
5. Inspect observed QC.
6. Confirm common station/model mapping.

### Phase 2 — ENSO source

7. Retrieve pinned NOAA ONI.
8. Save raw source.
9. Calculate SHA-256.
10. Build episode catalogue.
11. Verify selected episodes against NOAA historical classification.

### Phase 3 — Seasonal engine

12. Implement rainy season.
13. Implement cross-year hot/dry season.
14. Unit-test date assignments.
15. Generate season catalogue.

### Phase 4 — ENSO classification

16. Implement season-specific classification.
17. Preserve Transition/Unclassified.
18. Freeze classification rule.
19. Generate sample-size table.
20. Run classification sensitivity.

### Phase 5 — Rainfall analysis

21. Compute observed seasonal metrics.
22. Compute raw CMIP6 seasonal metrics.
23. Apply frozen QDM.
24. Compute QDM seasonal metrics.

### Phase 6 — ENSO response

25. Calculate El Niño vs Neutral.
26. Calculate La Niña vs Neutral.
27. Calculate ENSO asymmetry.
28. Calculate direction agreement.
29. Calculate magnitude error.
30. Calculate ENSO signal-preservation error.

### Phase 7 — Statistics

31. Run pre-specified permutation/rank-based tests.
32. Run bootstrap uncertainty.
33. Report n for every comparison.
34. Flag small-sample results.

### Phase 8 — Synthesis

35. Produce ensemble summaries.
36. Produce station-level summaries.
37. Produce model-level summaries.
38. Produce interpretation-status tables.

### Phase 9 — Figures

39. Figure 1 seasonal observed ENSO response.
40. Figure 2 raw vs QDM ENSO response.
41. Figure 3 ENSO asymmetry.
42. Figure 4 extreme rainfall.
43. Figure 5 temporal diagnostics.
44. Figure 6 integrated synthesis.

### Phase 10 — Manuscript

45. Write Methods from code.
46. Write Results from audited tables.
47. Write Discussion from verified evidence.
48. Write Introduction around the actual findings.
49. Write Abstract.
50. Write Conclusion.

### Phase 11 — Final audit

51. Run claim audit.
52. Run table/figure numerical audit.
53. Run source/provenance audit.
54. Run reference audit.
55. Run APST page/format audit.
56. Generate final manuscript.
57. Generate supplementary files.
58. Generate manifest and hashes.

---

# 60. FINAL OUTPUTS

Produce:

```text
Paper3_APST_manuscript_FINAL.docx
Paper3_APST_manuscript_FINAL.pdf
Paper3_APST_manuscript_FINAL.md

Paper3_MAIN_Tables.xlsx
Paper3_SUPPLEMENTARY_Tables.xlsx

Figure_P3_01_ENSO_observed.png/pdf
Figure_P3_02_ENSO_raw_vs_QDM.png/pdf
Figure_P3_03_ENSO_asymmetry.png/pdf
Figure_P3_04_ENSO_extremes.png/pdf
Figure_P3_05_ENSO_temporal.png/pdf
Figure_P3_06_ENSO_synthesis.png/pdf

enso_episode_catalog.csv
enso_season_classification.csv
enso_classification_sensitivity.csv
seasonal_observed.csv
seasonal_raw_cmip6.csv
seasonal_qdm.csv
enso_response_observed.csv
enso_response_raw.csv
enso_response_qdm.csv
enso_direction_agreement.csv
enso_magnitude_error.csv
enso_asymmetry.csv
enso_signal_preservation.csv
enso_extremes.csv
enso_statistics.csv
enso_sample_sizes.csv

PAPER3_ACCEPTANCE_GATES.csv
PAPER3_INTERPRETATION_SCOPE.csv
paper3_claim_audit.csv
paper3_manifest.json
paper3_file_hashes.csv
README_PAPER3_FINAL.md
```

---

# 61. FINAL NON-NEGOTIABLE RULES

1. Do not invent ENSO years.
2. Do not manually type ENSO years into the code.
3. Do not force ambiguous seasons into El Niño/La Niña.
4. Do not use calendar-year labels for the cross-year hot/dry season without a season-year identifier.
5. Do not alter the master observed QC.
6. Do not refit QDM on validation-period or ENSO-specific observations.
7. Do not use target-year observations when applying frozen QDM.
8. Do not equate marginal correction with temporal correction.
9. Do not interpret ENSO association as physical causation.
10. Do not interpret small ENSO samples as robust generalisations.
11. Do not rank QDM as “good” merely because it preserves the raw signal.
12. Do not call a result statistically significant without an actual pre-specified statistical test.
13. Do not create p-values only to make the paper look stronger.
14. Do not remove contradictory results.
15. Do not change the classification rule after seeing results.
16. Do not create continuous spatial fields that imply unsupported model resolution.
17. Do not duplicate Paper 1 future-projection results.
18. Do not duplicate Paper 2's three-method comparison.
19. Do not add new bias-correction methods to Paper 3.
20. Do not claim operational reservoir/agricultural benefit without testing the actual management system.

---

# 62. SUCCESS CRITERION

Paper 3 is successful when an independent reader can reproduce:

**NOAA ONI**
→ **ENSO episodes**
→ **season-specific classification**
→ **1995–2014 daily rainfall seasons**
→ **observed/raw/QDM seasonal metrics**
→ **ENSO response**
→ **ENSO asymmetry**
→ **signal preservation**
→ **uncertainty/statistical inference**
→ **final figures/tables**
→ **manuscript claims**

using the repository and configuration files alone.

The paper should leave the reader with a scientifically defensible conclusion about:

> **whether QDM preserves the seasonal ENSO-conditioned rainfall response in Uttaradit, and which rainfall characteristics remain sensitive to the correction.**

If the evidence shows that preservation varies by season and metric, report the variation. That is a substantive result, not a failure.
