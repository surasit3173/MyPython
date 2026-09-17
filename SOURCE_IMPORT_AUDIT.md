# SOURCE IMPORT AUDIT — FORENSIC MARKOV RAINFALL ANALYSIS

**Import Timestamp**: 2026-09-17 00:06:19 UTC
**Audit Status**: **PASS (GATE 0 PASSED)**

## 1. Verified Source Files

### A. Primary Empirical Dataset
- **Original Filename**: `Observed_Rain_daily_196101_202010_TMD10_raw_Markovchaindataset.csv`
- **Repository Path**: `data/raw/Observed_Rain_daily_196101_202010_TMD10_raw_Markovchaindataset.csv`
- **File Size**: 804,826 bytes
- **SHA-256 Checksum**: `5f17abe3935bd43316d120e8d8371ea299cea73f1812e00da8f08975df37bbe3`
- **File Type**: CSV (Comma-Separated Values)
- **Readability Check**: PASS
- **Dataset Dimensions**: 21,823 rows x 13 columns
- **Date Column**: `DAY`
- **Station Columns (10)**: 353201, 354201, 356201, 357201, 381201, 403201, 405201, 407501, 431201, 432201

### B. Primary Station Metadata
- **Original Filename**: `Latitude10Sta.docx`
- **Repository Path**: `data/metadata/Latitude10Sta.docx`
- **File Size**: 14,846 bytes
- **SHA-256 Checksum**: `ec5c1a7bbe2bb0556cda57048415e1c070aedddc0bb28ebd924de715e47d2351`
- **File Type**: DOCX (Microsoft Word Document)
- **Readability Check**: PASS
- **Extracted Metadata Content**:
```
 |  |  |  |
No. | Station | Latitude | Longitude | Altitude
 |  | (degree) | (degree) | (m, Mean Sea-Level)
1 | 353201 | 17º27’00” | 101º44’00” | 253
2 | 354201 | 17º23’00” | 102º48’00” | 177
3 | 356201 | 17º09’00” | 104º08’00” | 171
4 | 357201 | 17º25’00” | 104º47’00” | 145
5 | 381201 | 16º27’48” | 102º47’12” | 165
6 | 403201 | 15º48’00” | 102º02’00” | 180
7 | 405201 | 16º03’00” | 103º41’00” | 140
8 | 407501 | 15º15’00” | 104º52’00” | 131
9 | 431201 | 14º57’46” | 102º04’36” | 187
10 | 432201 | 14º53’00” | 103º30’00” | 146
```

### C. Methodological Reference
- **Original Filename**: `Application of Markov chain on daily rainfall data in Paraíba-Brazil from 1995-2015.pdf`
- **Repository Path**: `data/references/Application of Markov chain on daily rainfall in Paraíba-Brazil from 1995-2015.pdf`
- **File Size**: 1,701,563 bytes
- **SHA-256 Checksum**: `060ccc9b6e7b0b4b97201f7c2f4691e57f3fa8b7d7e395196cd2516466a8d6b6`
- **File Type**: PDF (Portable Document Format)
- **Readability Check**: PASS

## 2. Integrity Confirmation
- All three source files match the authoritative repository state.
- Raw CSV observations have **NOT** been modified, cleaned, imputed, or overwritten.
- Metadata and reference files are stored in immutable source directories (`data/raw/`, `data/metadata/`, `data/references/`).
- **Gate 0 Verification Result**: **PASS — SOURCE IMPORT READY**
