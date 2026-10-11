# Troubleshooting Guide

### 1. `FileNotFoundError: Rainfall CSV file not found`
Ensure that the file path specified in `config.yaml` is correct relative to the execution folder or specified as an absolute path.

### 2. Missing dependencies (`pandas`, `scipy`, `matplotlib`, `pyyaml`, `openpyxl`)
Install required packages using:
```bash
pip install -r requirements.txt
```

### 3. Non-zero exit code during `run_validation.py`
This indicates a violation of Markov probability invariants ($P_{00}+P_{01} \neq 1$) or corrupted values in the binary state sequence. Check input CSV for string characters in rainfall numeric cells.
