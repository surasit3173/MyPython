#!/usr/bin/env python3
"""
Package & Verification Script for Portable ZIP (v1.1)
=====================================================
1. Creates C:\MyPython\CMIP6PrachuapKhiriKhan_PORTABLE_Q2Q3_v1.1.zip
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
    base_dir = r"C:\MyPython\CMIP6PrachuapKhiriKhan"
    zip_path = r"C:\MyPython\CMIP6PrachuapKhiriKhan_PORTABLE_Q2Q3_v1.1.zip"

    if os.path.exists(zip_path):
        os.remove(zip_path)

    include_files = [
        "README.md",
        "config.yaml",
        "requirements.txt",
        "main.py",
        "data/README.md",
        "data/Observed_Rain_daily_198101_201412_PrachuapKhiriKhan.csv",
        "data/station_coordinates_PrachuapKhiriKhan.csv",
        "data/gis/thailand_regional_adm1.geojson",
        "docs/FINAL_EVIDENCE_FREEZE.md",
        "docs/RUN_REPORT.md",
        "output/tables/trend_results.csv",
        "output/tables/station_summary.csv",
        "output/tables/validation_report.md",
        "output/figures/Figure1_study_area_stations.png",
        "output/figures/Figure1_study_area_stations.pdf",
        "output/figures/Figure2_IDW_mean_annual_rainfall.png",
        "output/figures/Figure2_IDW_mean_annual_rainfall.pdf",
        "output/figures/Figure3_annual_rainfall_variability.png",
        "output/figures/Figure3_annual_rainfall_variability.pdf",
        "output/figures/Figure4_trend_method_comparison.png",
        "output/figures/Figure4_trend_method_comparison.pdf",
        "output/figures/Figure5_autocorrelation_effect.png",
        "output/figures/Figure5_autocorrelation_effect.pdf",
        "output/figures/figure_captions.md",
        "output/figures/figures_metadata.csv",
        "output/figures/IDW_parameters.txt",
        "output/figures/FIGURE_Q1Q2_FINAL_AUDIT.md",
        "output/figures/map_provenance.md",
        "output/manifests/run_manifest.json",
        "output/logs/pipeline.log",
        "generate_manuscript_draft.py",
        "manuscript/Project1_Prachuap_Q2Q3_Manuscript.md",
        "manuscript/Project1_Prachuap_Q2Q3_Manuscript.docx",
        "manuscript/MANUSCRIPT_AUDIT.md",
        "manuscript/TABLE_FIGURE_AUDIT.md"
    ]

    include_dirs = ["src", "tests"]

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for rel_f in include_files:
            abs_f = os.path.join(base_dir, rel_f)
            if os.path.exists(abs_f):
                arc_name = os.path.join("CMIP6PrachuapKhiriKhan_PORTABLE", rel_f)
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
                    arc_name = os.path.join("CMIP6PrachuapKhiriKhan_PORTABLE", rel_p)
                    zf.write(full_p, arc_name)

    zip_size = os.path.getsize(zip_path)
    zip_hash = compute_sha256(zip_path)

    print(f"Created ZIP: {zip_path}")
    print(f"Size       : {zip_size:,} bytes")
    print(f"SHA256     : {zip_hash}")

    test_extract_dir = tempfile.mkdtemp()
    print(f"Testing ZIP extraction into clean directory: {test_extract_dir}")

    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(test_extract_dir)

    pkg_root = os.path.join(test_extract_dir, "CMIP6PrachuapKhiriKhan_PORTABLE")

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
