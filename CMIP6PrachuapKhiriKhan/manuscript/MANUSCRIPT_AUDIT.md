# MANUSCRIPT QUALITY-CONTROL & REPRODUCIBILITY AUDIT REPORT

**Target Manuscript:** `manuscript/Project1_Prachuap_Q2Q3_Manuscript.md` & `.docx`  
**Authoritative Source:** `output/tables/trend_results.csv`  
**Execution Timestamp:** 2026-09-09T09:32:05.026752  
**Production Run Timestamp:** N/A  

---

## 1. AUTHORITATIVE EVIDENCE SOURCE & CRYPTOGRAPHIC HASHES

| File / Component | Relative Path | Cryptographic SHA-256 Checksum |
|---|---|---|
| **Authoritative Trend Results** | `output/tables/trend_results.csv` | `0c7c29e04cfadd5a1c2b0e1012b6dfec63973fa44e06b31490fb161ff042132c` |
| **Authoritative Station Summary** | `output/tables/station_summary.csv` | `bb6e424869e2a4fd4c0e2f9a157b2b19310a64080b85a15e4dde0023396b69b4` |
| **Run Manifest** | `output/manifests/run_manifest.json` | `a1ac762966069b51d1fd2853adc6d632db1c837050bba153e71b586d4a6ea239` |
| **Configuration File** | `config.yaml` | `5e40eb8d247649744b21da2a8c551a4a41d1d1593f367ad64fc6b21942e53ebd` |

---

## 2. EXHAUSTIVE STATION-BY-STATION NUMERICAL COMPARISON MATRIX

| Station ID | Mean Rain (mm) | Sen Slope (mm/yr) | Standard MK S | Standard MK Z | Standard MK p | Yue-Wang r1 | Correction Ratio n/ns* | Yue-Wang Z | Yue-Wang p | Status | Audit Result |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `500001` | 983.66 | +7.410 | +78.0 | +1.142 | 0.2536 | +0.2290 | 1.0000 | +1.142 | 0.2536 | VALID | **MATCH (PASS)** |
| `500002` | 1376.19 | +9.175 | +153.0 | +2.253 | 0.0242 | -0.1386 | 1.0000 | +2.253 | 0.0242 | VALID | **MATCH (PASS)** |
| `500003` | 1100.02 | -5.933 | -99.0 | -1.453 | 0.1463 | +0.4551 | 2.5801 | -0.904 | 0.3658 | VALID | **MATCH (PASS)** |
| `500004` | 1106.00 | +2.355 | +37.0 | +0.534 | 0.5936 | +0.1891 | 1.0000 | +0.534 | 0.5936 | VALID | **MATCH (PASS)** |
| `500005` | 1147.21 | -1.090 | -17.0 | -0.237 | 0.8125 | +0.4048 | 2.2930 | -0.157 | 0.8755 | VALID | **MATCH (PASS)** |
| `500006` | 1203.06 | +1.354 | +37.0 | +0.534 | 0.5936 | +0.1717 | 1.0000 | +0.534 | 0.5936 | VALID | **MATCH (PASS)** |
| `500007` | 1133.56 | -2.254 | -57.0 | -0.830 | 0.4064 | +0.1531 | 1.0000 | -0.830 | 0.4064 | VALID | **MATCH (PASS)** |
| `500008` | 1206.31 | -0.650 | -19.0 | -0.267 | 0.7896 | +0.0177 | 1.0000 | -0.267 | 0.7896 | VALID | **MATCH (PASS)** |
| `500009` | 1176.53 | +0.583 | +32.0 | +0.460 | 0.6458 | +0.1699 | 1.0000 | +0.460 | 0.6458 | VALID | **MATCH (PASS)** |
| `500201` | 1108.24 | +3.511 | +43.0 | +0.623 | 0.5335 | +0.0542 | 1.0000 | +0.623 | 0.5335 | VALID | **MATCH (PASS)** |
| `500202` | 944.14 | -4.376 | -79.0 | -1.156 | 0.2476 | -0.3619 | 0.4800 | -1.669 | 0.0951 | VALID | **MATCH (PASS)** |
| `500301` | 1064.85 | -0.621 | -21.0 | -0.296 | 0.7669 | -0.1054 | 1.0000 | -0.296 | 0.7669 | VALID | **MATCH (PASS)** |

---

## 3. 18-POINT QUALITY CONTROL CHECKLIST

| Gate ID | Check Description | Status | Evidence / Verification Notes |
|---|---|---|---|
| **[1]** | Numerical results match production outputs | **PASS** | 100% exact numerical agreement across all 12 stations. |
| **[2]** | No unsupported numerical result appears | **PASS** | Zero fabricated numbers. |
| **[3]** | No Project 2 (Uttaradit) content appears | **PASS** | Scope strictly isolated to Prachuap Khiri Khan. |
| **[4]** | No Hamed-Rao result presented as valid production | **PASS** | Hamed-Rao documented only as motivation for AR(1) selection. |
| **[5]** | Station 500202 handled correctly | **PASS** | Yue-Wang result ($r_1 = -0.3619, n/n_s^* = 0.4800, Z = -1.669, p = 0.0951$) reported. |
| **[6]** | Yue & Wang consistently identified as primary | **PASS** | Identified as primary method across all sections. |
| **[7]** | Standard MK identified as reference | **PASS** | Identified as reference benchmark. |
| **[8]** | TFPW identified as sensitivity/reference | **PASS** | Identified as reference sensitivity check. |
| **[9]** | No synthetic data used as research results | **PASS** | 100% authentic observations (1981–2014). |
| **[10]** | No causal claims without evidence | **PASS** | No unfounded climate driver attributions. |
| **[11]** | No fabricated references | **PASS** | All citations correspond to published papers. |
| **[12]** | Units consistent | **PASS** | mm, mm/year, days defined. |
| **[13]** | Decimal precision consistent | **PASS** | Slopes (3 decimals), $p$-values (4 decimals). |
| **[14]** | Table numbering consistent | **PASS** | Tables 1, 2, 3, S1 numbered sequentially. |
| **[15]** | Figure numbering consistent | **PASS** | Figures 1 to 5 cited in text. |
| **[16]** | Every table/figure cited in text | **PASS** | Referenced in Results and Discussion. |
| **[17]** | Abstract numbers match Results | **PASS** | Abstract numbers programmatically generated from production CSV. |
| **[18]** | Limitations explicitly disclosed | **PASS** | Disclosed finite-sample autocorrelation limitations. |

```text
=======================================================
  MANUSCRIPT NUMERICAL RECONCILIATION — PASS
=======================================================
```
