# PAPER 3 BLOCKERS

## 1. Git LFS Permissions Issue
- **Description:** Attempts to execute `git lfs pull` to download missing large files resulted in permission denied errors (`mkdir /app/.git/lfs/objects: permission denied`).
- **Impact:** Certain `.zip` and `.rar` data files (e.g., `dataUttaradit.rar`) might only be pointer files rather than actual data. This prevents access to raw CMIP6 or observed data required for the analysis.
- **Resolution Required:** Repository permissions for the `.git/lfs/` directory need to be fixed, or the required data needs to be provided via another mechanism.

## 2. Missing Test Suite
- **Description:** Attempting to run `python3 -m unittest discover tests/` within the extracted Paper 1 framework directory (`CMIP6Uttaradit/paper3/files_21/framework/paper1_framework/`) failed because the `tests/` directory is missing.
- **Impact:** Cannot verify the correctness of the foundational framework before beginning Paper 3 implementations.
- **Resolution Required:** The `tests/` directory needs to be restored from the repository history or extracted properly if it was missing from `files (21).zip`.

## 3. Data Archive Extraction
- **Description:** The `dataUttaradit.rar` file requires extraction, but `unrar` or a suitable tool might be missing in the environment, and its integrity is uncertain due to the LFS issue.
- **Impact:** The required `data/` subdirectory for the framework execution is incomplete.
- **Resolution Required:** Resolve the LFS issue, install a `.rar` extraction utility, and successfully unpack the data into the correct directory structure as expected by `run_paper1.py`.

## 4. NOAA ONI Accessibility
- **Description:** Attempting to programmatically access the NOAA CPC ONI website resulted in an HTTP 403 Forbidden error.
- **Impact:** The automated ENSO module cannot scrape or download the required ONI index directly from the CPC server using standard Python HTTP libraries without spoofing user agents or utilizing an alternative download method.
- **Resolution Required:** A workaround for downloading the NOAA ONI data (e.g., setting specific headers in the request) or manual provision of the pinned index file is required.
