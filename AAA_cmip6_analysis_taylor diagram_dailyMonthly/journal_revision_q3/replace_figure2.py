from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
from pathlib import Path

from PIL import Image


ROOT = Path(r"C:\MyPython\AAA_cmip6_analysis_taylor diagram_dailyMonthly")
OUT = ROOT / "journal_revision_q3"
MAIN = OUT / "AJSTR_QDM_CMIP6_Q3_SUBMISSION_MAIN.docx"
FIG_DIR = OUT / "submission_figures"
GENERATED = Path(r"C:\Users\PC\.codex\generated_images\01a04026-5449-7553-b7ea-89341992be73\exec-839f5a2d-c3f5-42b0-b563-6265bebf155f.png")
NEW_PNG = FIG_DIR / "Figure_2_framework_Q1Q2.png"
NEW_TIFF = FIG_DIR / "Figure_2.tiff"
OLD_TIFF = FIG_DIR / "Figure_2_framework_original.tiff"


def replace_embedded_framework() -> None:
    FIG_DIR.mkdir(exist_ok=True)
    shutil.copyfile(GENERATED, NEW_PNG)
    if not OLD_TIFF.exists() and NEW_TIFF.exists():
        shutil.copyfile(NEW_TIFF, OLD_TIFF)
    with Image.open(GENERATED) as image:
        image.convert("RGB").save(NEW_TIFF, dpi=(600, 600), compression="tiff_lzw")

    # In the prepared manuscript, Figure 2 is the second body image and is
    # stored as word/media/image2.png. Replace only that binary part so all
    # captions, equations, and document structure remain unchanged.
    entries = []
    with zipfile.ZipFile(MAIN, "r") as source:
        for item in source.infolist():
            data = GENERATED.read_bytes() if item.filename == "word/media/image2.png" else source.read(item.filename)
            entries.append((item, data))
    fd, temp_name = tempfile.mkstemp(suffix=".docx", dir=MAIN.parent)
    os.close(fd)
    temp_path = Path(temp_name)
    try:
            with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_DEFLATED) as target:
                for item, data in entries:
                    target.writestr(item, data)
            os.replace(temp_path, MAIN)
    finally:
        if temp_path.exists():
            temp_path.unlink()


if __name__ == "__main__":
    replace_embedded_framework()
    print(NEW_PNG)
    print(NEW_TIFF)
    print(MAIN)
