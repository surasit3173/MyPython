#!/usr/bin/env python3
"""
Package & Verification Script for Portable ZIP (Project 2: Uttaradit v1.0)
========================================================================
1. Creates C:\MyPython\CMIP6Uttaradit_PORTABLE_Q2Q3_v1.0.zip
2. Computes ZIP SHA256 checksum.
3. Performs extraction and clean execution verification.
"""

import sys
import os
import zipfile
import tempfile
import shutil
import subprocess
import hashlib

def compute_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def create_zip_package():
    base_dir = r"C:\MyPython\CMIP6Uttaradit"
    zip_path = r"C:\MyPython\CMIP6Uttaradit_PORTABLE_Q2Q3_v1.0.zip"

    if os.path.exists(zip_path):
        os.remove(zip_path)

    include_files = [
        "README.md",
        "requirements.txt",
        "main.py",
        "generate_manuscript_draft.py",
        "config/config.yaml",
        "docs/FINAL_EVIDENCE_FREEZE.md",
        "Data_Uttaradit/station_coordinates_Uttaradit.csv",
        "Data_Uttaradit/Observed_Rain_daily_198101_201412_Uttaradit.csv",
        "data/gis/thailand_regional_adm1.geojson",
        "output/tables/station_metadata.csv",
        "output/tables/seasonal_climatology.csv",
        "output/tables/observed_etccdi_1995_2014.csv",
        "output/tables/baseline_sensitivity_comparison.csv",
        "output/tables/gcm_evaluation_bias.csv",
        "output/tables/future_projections_ssp.csv",
        "output/tables/supplementary_stn_etccdi.csv",
        "output/tables/validation_report.md",
        "output/figures/Figure1_study_area_stations.png",
        "output/figures/Figure1_study_area_stations.pdf",
        "output/figures/Figure2_IDW_mean_annual_rainfall.png",
        "output/figures/Figure2_IDW_mean_annual_rainfall.pdf",
        "output/figures/Figure3_observed_etccdi_indices.png",
        "output/figures/Figure3_observed_etccdi_indices.pdf",
        "output/figures/Figure4_model_bias_evaluation.png",
        "output/figures/Figure4_model_bias_evaluation.pdf",
        "output/figures/Figure5_projected_extremes_ssp.png",
        "output/figures/Figure5_projected_extremes_ssp.pdf",
        "output/figures/figure_captions.md",
        "output/figures/figures_metadata.csv",
        "output/figures/IDW_parameters.txt",
        "output/figures/map_provenance.md",
        "output/figures/FIGURE_Q1Q2_FINAL_AUDIT.md",
        "output/manifests/run_manifest_project2.json",
        "manuscript/Project2_Uttaradit_Q1Q2_Manuscript.md",
        "manuscript/Project2_Uttaradit_Q1Q2_Manuscript.docx",
        "manuscript/MANUSCRIPT_AUDIT.md",
        "manuscript/TABLE_FIGURE_AUDIT.md"
    ]

    include_dirs = ["src", "tests"]

    # Also include the 7 GCM directories inside Data_Uttaradit
    gcms = ['ACCESS-ESM1-5', 'CESM2', 'CanESM5', 'EC-Earth3', 'FGOALS-g3', 'MIROC6', 'MRI-ESM2-0']
    for g in gcms:
        include_dirs.append(os.path.join("Data_Uttaradit", g))

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for rel_f in include_files:
            abs_f = os.path.join(base_dir, rel_f)
            if os.path.exists(abs_f):
                arc_name = os.path.join("CMIP6Uttaradit_PORTABLE", rel_f)
                zf.write(abs_f, arc_name)
            else:
                print(f"WARNING: File not found for packaging: {rel_f}")

        for rel_d in include_dirs:
            abs_d = os.path.join(base_dir, rel_d)
            for root, dirs, files in os.walk(abs_d):
                if "__pycache__" in root:
                    continue
                for f in files:
                    if f.endswith('.pyc'):
                        continue
                    full_p = os.path.join(root, f)
                    rel_p = os.path.relpath(full_p, base_dir)
                    arc_name = os.path.join("CMIP6Uttaradit_PORTABLE", rel_p)
                    zf.write(full_p, arc_name)

    zip_size = os.path.getsize(zip_path)
    zip_hash = compute_sha256(zip_path)

    print(f"Created ZIP: {zip_path}")
    print(f"Size       : {zip_size:,} bytes")
    print(f"SHA256     : {zip_hash}")

    # Perform clean extraction verification
    test_extract_dir = tempfile.mkdtemp()
    print(f"Testing ZIP extraction into clean directory: {test_extract_dir}")

    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(test_extract_dir)

    pkg_root = os.path.join(test_extract_dir, "CMIP6Uttaradit_PORTABLE")

    print("Running unit tests in extracted directory...")
    test_proc = subprocess.run([sys.executable, "-m", "unittest", "discover", "tests/"], cwd=pkg_root, capture_output=True, text=True)
    print(f"Extracted Test Suite Status: Exit Code {test_proc.returncode}")
    if test_proc.returncode != 0:
        print("TEST STDOUT:", test_proc.stdout)
        print("TEST STDERR:", test_proc.stderr)

    print("Running main.py in extracted directory...")
    main_proc = subprocess.run([sys.executable, "main.py"], cwd=pkg_root, capture_output=True, text=True)
    print(f"Extracted main.py Status    : Exit Code {main_proc.returncode}")
    if main_proc.returncode != 0:
        print("MAIN STDOUT:", main_proc.stdout)
        print("MAIN STDERR:", main_proc.stderr)

    print("Running generate_manuscript_draft.py in extracted directory...")
    manu_proc = subprocess.run([sys.executable, "generate_manuscript_draft.py"], cwd=pkg_root, capture_output=True, text=True)
    print(f"Extracted Manuscript Status : Exit Code {manu_proc.returncode}")
    if manu_proc.returncode != 0:
        print("MANU STDOUT:", manu_proc.stdout)
        print("MANU STDERR:", manu_proc.stderr)

    shutil.rmtree(test_extract_dir)

    if test_proc.returncode == 0 and main_proc.returncode == 0 and manu_proc.returncode == 0:
        print("\n=======================================================")
        print("  PORTABLE PACKAGE STATUS: PASS")
        print("=======================================================")
        return True, zip_path, zip_size, zip_hash
    else:
        print("\n=======================================================")
        print("  PORTABLE PACKAGE STATUS: HOLD")
        print("=======================================================")
        return False, zip_path, zip_size, zip_hash

if __name__ == '__main__':
    create_zip_package()
