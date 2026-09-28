# BLOCKERS BEFORE SUBMISSION

| Severity | Issue | Evidence | Affected Output | Required Correction | Status |
|---|---|---|---|---|---|
| **CRITICAL** | Primary Empirical Dataset Missing | `Observed_Rain_daily_196101_202010_TMD10_raw_Markovchaindataset.csv` not found anywhere in workspace, git branches, or archives. | All Markov transition matrices, state frequencies, persistence probabilities ($P_{DD}, P_{WW}, P_{RR}$), spell statistics, entropy calculations, and long-term trends (1961–2019). | Upload `Observed_Rain_daily_196101_202010_TMD10_raw_Markovchaindataset.csv` to repository workspace. | **BLOCKED** |
| **CRITICAL** | Station Metadata Source Missing | `Latitude10Sta.docx` not found anywhere in workspace, git branches, or archives. | Station network audit (GATE 0 / GATE 1), latitude/longitude/elevation verification for stations 353201, 354201, 356201, 357201, 381201, 403201, 405201, 407501, 431201, 432201, and spatial analysis. | Upload `Latitude10Sta.docx` to repository workspace. | **BLOCKED** |
| **HIGH** | Methodological Reference PDF Missing | `Application of Markov chain on daily rainfall data in Paraíba-Brazil from 1995-2015.pdf` not found in workspace or archives. | Formal methodological provenance and reference review for 3-state Markov chain classification. | Upload reference PDF to repository workspace. | **BLOCKED** |

## Rule Compliance Statement
Per repository operating rules in `AGENTS.md`:
- **Section 2 ("DO NOT INVENT")**: Synthetic data generation, empirical observation fabrication, or numerical rounding/estimating is strictly prohibited.
- **Section 8 ("Input Validation & Data Integrity")**: Raw observations are treated as immutable and must originate from audited empirical files.
- **Section 13 ("Validation Gate")**: Gate 0 (File/Provenance) and Gate 1 (Data Integrity) cannot pass without the authoritative input dataset. All downstream manuscript drafting and results generation are HALTED.
