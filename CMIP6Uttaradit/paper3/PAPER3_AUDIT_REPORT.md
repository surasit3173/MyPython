# PAPER 3 AUDIT REPORT

## 1. Repository Status
- **Root Repository:** Contains multiple independent sub-projects (e.g., `CMIP6Uttaradit`, `CMIP6Nan`, `CMIP6PrachuapKhiriKhan`).
- **Paper 3 Directory:** Located at `CMIP6Uttaradit/paper3/`.
- **AGENTS.md:** Present at repository root, imposing strict rules on preserving computational logic, preventing invention, and requiring validation.

## 2. LFS (Large File Storage) Status
- **Configuration:** `.gitattributes` tracks `*.zip` and `*.rar` files via LFS.
- **Current State:** LFS is initialized, but `git lfs pull` encountered permission errors in `/app/.git/lfs/objects/`.
- **Effect:** While `files (21).zip` (18.6 MB) was extracted successfully and contains the Paper 1 framework, other data archives (such as `dataUttaradit.rar` and other `.zip` files) might only exist as LFS pointers or could not be completely synced.

## 3. Paper 3 Project Structure
- **Specification:** `Paper3_ENSO_Master_Code_and_Manuscript_Execution_Specification.md` is present and sets strict constraints for a seasonal ENSO analysis.
- **Framework Archive:** `files (21).zip` contains the locked common foundation (Paper 1 framework) required for Paper 3.
- **Data Archives:** `dataUttaradit.rar` is present in the repository, but its integrity must be confirmed once LFS is fully resolved.
- **Manuscript Templates:** Formatting guidelines (`EASR+Template+2026.docx`, `แนวทาง paper3.docx`) are present.

## 4. Dependencies
- **Requirements File:** Found within the extracted framework at `CMIP6Uttaradit/paper3/files_21/framework/paper1_framework/requirements.txt`.
- **Packages:** Specifies standard Python scientific libraries (`numpy`, `pandas`, `scipy`, `matplotlib`, `PyYAML`, `XlsxWriter`, `openpyxl`, `shapely`, `pyproj`, `pyarrow`).
- **Management:** Dependencies should be installed in a sub-project specific virtual environment (`.venv`). Node.js (v18+) is also required for the `docx_build` manuscript generation step.

## 5. Data Provenance
- **Source Constraints:** Paper 3 strictly requires reusing the exact historical data, stations (13 gauges), and CMIP6 models (7 models) used in Paper 1.
- **ENSO Index:** Requires retrieving the NOAA CPC historical ONI. The specification mandates that the index must be pinned, hashed, and tracked to ensure reproducibility.
- **Validation:** Data inputs must pass rigid acceptance gates before the analysis can proceed.

## 6. Clone / Checkout Completeness
- **Partial Completeness:** The source code and specifications were cloned successfully, and the Paper 1 framework was extracted.
- **Issues:** The repository checkout is hindered by the LFS permission errors. It is unclear if all raw CMIP6 data and observed rainfall data are fully present in their uncompressed forms, as they are meant to reside in the `data/` subdirectory which may be packaged inside the `.rar` files.
