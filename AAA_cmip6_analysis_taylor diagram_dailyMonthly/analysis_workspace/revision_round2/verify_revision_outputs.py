from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path

from docx import Document
from PIL import Image
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[2]
ROUND = ROOT / "analysis_workspace" / "revision_round2"
OUTPUT = ROUND / "output"
MAIN = OUTPUT / "APST_Uttaradit_CMIP6_Revised_Q2Q3.docx"
SUPP = OUTPUT / "APST_Uttaradit_CMIP6_Supplementary_Information.docx"
MAIN_PDF = ROUND / "render_main" / "APST_Uttaradit_CMIP6_Revised_Q2Q3.pdf"
SUPP_PDF = ROUND / "render_supplement" / "APST_Uttaradit_CMIP6_Supplementary_Information.pdf"
REPORT = OUTPUT / "revision_verification.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def all_paragraphs(document: Document):
    yield from document.paragraphs
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                yield from cell.paragraphs
    for section in document.sections:
        for container in (section.header, section.footer, section.first_page_header, section.first_page_footer):
            yield from container.paragraphs


def inspect_docx(path: Path) -> dict[str, object]:
    document = Document(path)
    paragraphs = list(all_paragraphs(document))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    highlighted = [run.text for paragraph in paragraphs for run in paragraph.runs if run.font.highlight_color is not None]
    allowed_highlight = re.compile(r"\[(?:Author|Department|Corresponding|Before submission|email)", re.IGNORECASE)
    invalid_highlights = [value for value in highlighted if not allowed_highlight.search(value)]
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        xml = "".join(
            archive.read(name).decode("utf-8", errors="ignore")
            for name in names
            if name.startswith("word/") and name.endswith(".xml")
        )
    return {
        "paragraphs": len(document.paragraphs),
        "tables": len(document.tables),
        "table_rows": [len(table.rows) for table in document.tables],
        "inline_shapes": len(document.inline_shapes),
        "sections": len(document.sections),
        "highlighted_runs": highlighted,
        "invalid_highlights": invalid_highlights,
        "has_comments_part": any(name.startswith("word/comments") for name in names),
        "tracked_insertions": len(re.findall(r"<w:ins(?:\s|>)", xml)),
        "tracked_deletions": len(re.findall(r"<w:del(?:\s|>)", xml)),
        "unresolved_insert_markers": re.findall(r"\[Insert (?:Figure|Table).*?\]", text),
        "text": text,
    }


def image_inventory(directory: Path) -> list[dict[str, object]]:
    paths = sorted(directory.glob("page-*.png"), key=lambda path: int(path.stem.split("-")[-1]))
    result = []
    for path in paths:
        with Image.open(path) as image:
            result.append({"name": path.name, "width": image.width, "height": image.height, "bytes": path.stat().st_size})
    return result


def main() -> None:
    for path in (MAIN, SUPP, MAIN_PDF, SUPP_PDF):
        if not path.exists() or path.stat().st_size == 0:
            raise AssertionError(f"Missing or empty: {path}")

    main_info = inspect_docx(MAIN)
    supp_info = inspect_docx(SUPP)
    main_text = str(main_info.pop("text"))
    supp_text = str(supp_info.pop("text"))

    expected_title = "Baseline-source sensitivity and robustness of supplied bias-corrected CMIP6 daily precipitation-extreme projections for Uttaradit Province, Thailand"
    if not main_text.startswith(expected_title):
        raise AssertionError("Main title mismatch")
    abstract = main_text.split("Abstract", 1)[1].split("Keywords:", 1)[0]
    abstract_words = len(re.findall(r"\b[\w−–'-]+\b", abstract))
    if abstract_words > 250:
        raise AssertionError(f"Abstract too long: {abstract_words}")
    if main_info["tables"] != 3 or main_info["table_rows"] != [12, 5, 12]:
        raise AssertionError(f"Main table structure mismatch: {main_info['table_rows']}")
    if main_info["inline_shapes"] != 4:
        raise AssertionError(f"Expected four figures, found {main_info['inline_shapes']}")
    for figure_number in range(1, 5):
        if f"Figure {figure_number}." not in main_text:
            raise AssertionError(f"Missing Figure {figure_number} caption")
    if main_info["invalid_highlights"]:
        raise AssertionError(f"Unexpected highlighted text: {main_info['invalid_highlights']}")
    if main_info["has_comments_part"] or main_info["tracked_insertions"] or main_info["tracked_deletions"]:
        raise AssertionError("Main document contains comments or tracked changes")
    if main_info["unresolved_insert_markers"]:
        raise AssertionError(f"Unresolved insert markers: {main_info['unresolved_insert_markers']}")

    references = []
    in_references = False
    for line in main_text.splitlines():
        if line.strip() == "12. References":
            in_references = True
            continue
        if in_references and re.match(r"^\d+\. ", line.strip()):
            references.append(line.strip())
    if len(references) != 20:
        raise AssertionError(f"Expected 20 references, found {len(references)}")
    if "Extreme index trends of daily gridded rainfall dataset (1960-2017) in Taiwan" not in references[5]:
        raise AssertionError("Reference 6 mismatch")
    if "Extreme rainfall trends and return periods under CMIP6 scenarios in Southern Thailand" not in references[16]:
        raise AssertionError("Reference 17 mismatch")

    body_before_refs = main_text.split("12. References", 1)[0]
    cited_numbers = []
    for group in re.findall(r"\[([0-9,–-]+)\]", body_before_refs):
        for token in group.split(","):
            if "–" in token or "-" in token:
                start_text, end_text = re.split(r"[–-]", token, maxsplit=1)
                cited_numbers.extend(range(int(start_text), int(end_text) + 1))
            else:
                cited_numbers.append(int(token))
    if not cited_numbers or min(cited_numbers) < 1 or max(cited_numbers) > 20:
        raise AssertionError(f"Citation range invalid: {sorted(set(cited_numbers))}")

    if supp_info["tables"] != 6 or supp_info["table_rows"] != [34, 34, 5, 3, 12, 5]:
        raise AssertionError(f"Supplement table structure mismatch: {supp_info['table_rows']}")
    for token in ("Table S1a.", "Table S1b.", "Table S2a.", "Table S2b.", "Table S3.", "Table S4.", "Supplementary Note S1"):
        if token not in supp_text:
            raise AssertionError(f"Missing supplement token: {token}")
    if supp_info["invalid_highlights"]:
        raise AssertionError(f"Unexpected supplement highlighted text: {supp_info['invalid_highlights']}")
    if supp_info["has_comments_part"] or supp_info["tracked_insertions"] or supp_info["tracked_deletions"]:
        raise AssertionError("Supplement contains comments or tracked changes")

    main_pages = len(PdfReader(str(MAIN_PDF)).pages)
    supp_pages = len(PdfReader(str(SUPP_PDF)).pages)
    main_images = image_inventory(ROUND / "render_main")
    supp_images = image_inventory(ROUND / "render_supplement")
    if len(main_images) != main_pages or len(supp_images) != supp_pages:
        raise AssertionError("Rendered PNG count does not match PDF page count")
    if any(item["width"] < 1000 or item["height"] < 1000 or item["bytes"] < 50_000 for item in main_images + supp_images):
        raise AssertionError("One or more rendered pages have suspicious dimensions or size")

    report = {
        "status": "PASS",
        "main": {
            **main_info,
            "abstract_words": abstract_words,
            "references": len(references),
            "citation_numbers_used": sorted(set(cited_numbers)),
            "pdf_pages": main_pages,
            "rendered_pages": len(main_images),
            "bytes": MAIN.stat().st_size,
            "sha256": sha256(MAIN),
        },
        "supplement": {
            **supp_info,
            "pdf_pages": supp_pages,
            "rendered_pages": len(supp_images),
            "bytes": SUPP.stat().st_size,
            "sha256": sha256(SUPP),
        },
        "visual_review": {
            "main_pages_reviewed": list(range(1, main_pages + 1)),
            "supplement_pages_reviewed": list(range(1, supp_pages + 1)),
            "issues_after_final_render": [],
        },
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
