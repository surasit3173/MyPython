from pathlib import Path

from docx import Document


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "manuscript" / "Paper3_CMJS_manuscript.docx"
OUT = ROOT / "manuscript" / "Paper3_CMJS_manuscript_BLINDED.docx"


def delete_paragraph(paragraph) -> None:
    element = paragraph._element
    element.getparent().remove(element)
    paragraph._p = paragraph._element = None


doc = Document(SOURCE)
remove_section = False
for paragraph in list(doc.paragraphs):
    text = paragraph.text.strip()
    if (
        text.startswith("Surasit Punyawansiri")
        or text.startswith("1Office of Water Management")
        or text.startswith("*Corresponding author:")
    ):
        delete_paragraph(paragraph)
        continue
    if paragraph.style.name.startswith("Heading"):
        remove_section = text in {"Acknowledgements", "Author Contributions"}
        if remove_section:
            delete_paragraph(paragraph)
            continue
    if remove_section:
        delete_paragraph(paragraph)

doc.core_properties.author = ""
doc.core_properties.last_modified_by = ""
doc.save(OUT)
print(f"BLINDED_DOCX_COMPLETE {OUT}")
