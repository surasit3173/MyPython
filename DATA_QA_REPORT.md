# DATA QA REPORT — MARKOV RAINFALL ANALYSIS (NORTHEASTERN THAILAND)

**Audit Date**: 2026-09-17
**Primary File**: `data/raw/Observed_Rain_daily_196101_202010_TMD10_raw_Markovchaindataset.csv`
**Metadata File**: `data/metadata/Latitude10Sta.docx`
**Gate 1 Audit Status**: **PASS**

## Executive Summary
A comprehensive forensic data audit was performed across all 10 Thai Meteorological Department (TMD) rainfall stations for the period 1 January 1961 – 30 September 2020 (21,823 total calendar days).

## Station Network & Completeness Audit
- Total Expected Calendar Days per station: 21,823
- Minimum Completeness: 97.98% (Station 405201, Roi Et)
- Maximum Completeness: 99.99% (Stations 407501, 432201)
- Missingness Handling: Primary analysis does **NOT** impute missing values. Markov transitions are strictly calculated across adjacent observed calendar days ($t$ and $t+1$).
- Negative / Invalid Values: 0 invalid or negative rainfall values detected across all 218,230 station-day observations.

| Station ID | Station Name | Latitude (DD) | Longitude (DD) | Altitude (m) | Actual Records | Missing Records | Missing % | Max Rain (mm) |
|---|---|---|---|---|---|---|---|---|
| 353201 | Loei | 17.4500 | 101.7333 | 253 | 21,810 | 13 | 0.06% | 164.1 |
| 354201 | Udon Thani | 17.3833 | 102.8000 | 177 | 21,819 | 4 | 0.02% | 274.5 |
| 356201 | Sakon Nakhon | 17.1500 | 104.1333 | 171 | 21,817 | 6 | 0.03% | 457.1 |
| 357201 | Nakhon Phanom | 17.4167 | 104.7833 | 145 | 21,504 | 319 | 1.46% | 459.2 |
| 381201 | Khon Kaen | 16.4633 | 102.7867 | 165 | 21,769 | 54 | 0.25% | 221.9 |
| 403201 | Chaiyaphum | 15.8000 | 102.0333 | 180 | 21,815 | 8 | 0.04% | 162.5 |
| 405201 | Roi Et | 16.0500 | 103.6833 | 140 | 21,382 | 441 | 2.02% | 242.3 |
| 407501 | Ubon Ratchathani | 15.2500 | 104.8667 | 131 | 21,821 | 2 | 0.01% | 203.9 |
| 431201 | Nakhon Ratchasima | 14.9628 | 102.0767 | 187 | 21,802 | 21 | 0.10% | 152.8 |
| 432201 | Surin | 14.8833 | 103.5000 | 146 | 21,821 | 2 | 0.01% | 279.5 |
