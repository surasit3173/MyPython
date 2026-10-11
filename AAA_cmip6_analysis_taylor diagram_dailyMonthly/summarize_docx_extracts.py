import json
from pathlib import Path


FILES = [
    "docx_extracts/ID1558_Manuscript_BSJ_(11).json",
    "docx_extracts/ID1558_correction_plan_(1).json",
    "docx_extracts/Evaluation_of_Quantile_Delta_Mapping_for_Bias_Correction_of_CMIP6_Daily_Rainfall.json",
]


def is_heading_or_caption(text, style):
    low = text.lower()
    return (
        style.lower().startswith("heading")
        or low.startswith(("table", "figure", "ตาราง", "ภาพ", "รูป"))
        or len(text) < 145
    )


for file in FILES:
    data = json.loads(Path(file).read_text(encoding="utf-8"))
    print("=" * 80)
    print(data["file"])
    print(f"paragraphs={data['paragraphs']} tables={data['tables']} images={data['images']}")
    for block in data["blocks"]:
        if block["type"] == "p":
            text = block["text"].replace("\n", " ")
            style = block.get("style", "")
            if is_heading_or_caption(text, style):
                print(f"P{block['n']:03d} [{style}] {text}")
        elif block["type"] == "table":
            rows = block["rows"]
            print(f"TABLE {block['n']} rows={len(rows)} cols={len(rows[0]) if rows else 0}")
            for row in rows[:5]:
                print("  | ".join(row))
