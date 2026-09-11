from docx import Document
from pathlib import Path

doc = Document(Path("journal_template_work/AJSTR_template_reference.docx"))
for i in [0, 1, 2, 6, 8, 10, 20, 27]:
    p = doc.paragraphs[i]
    print("PARA", i + 1, repr(p.text[:80]))
    print("  align", p.alignment, "style", p.style.name if p.style else None)
    print("  pf", "before", p.paragraph_format.space_before, "after", p.paragraph_format.space_after, "line", p.paragraph_format.line_spacing)
    for r in p.runs[:4]:
        f = r.font
        print("  run", repr(r.text[:40]), "font", f.name, "size", f.size.pt if f.size else None, "bold", f.bold, "italic", f.italic)
