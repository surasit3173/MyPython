from docx import Document
from pathlib import Path

docx_path = Path(r"C:\MyPython\AAA_cmip6_analysis_taylor diagram_dailyMonthly\ID1558_revised_for_publication_final.docx")
doc = Document(docx_path)

paras = doc.paragraphs
heading_idx = next(i for i, p in enumerate(paras) if p.text.strip().startswith("2.7 "))

# Remove the accidental duplicate MSE-method block immediately before heading 2.7.
start_idx = None
for i in range(heading_idx - 1, -1, -1):
    if paras[i].text.strip().startswith("การแยกส่วนทั้งสองระดับใช้เป็นเครื่องมือวินิจฉัย"):
        start_idx = i
        break

if start_idx is None:
    raise SystemExit("duplicate block not found")

for p in paras[start_idx:heading_idx]:
    p._element.getparent().remove(p._element)

doc.save(docx_path)
print(f"removed duplicate paragraphs {start_idx}-{heading_idx - 1}")
