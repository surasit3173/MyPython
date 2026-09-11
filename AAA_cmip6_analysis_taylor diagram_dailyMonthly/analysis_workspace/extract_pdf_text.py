from pathlib import Path
from pypdf import PdfReader

source = Path(r"C:\MyPython\CMIP6Uttaradit\Extreme index trends of daily gridded.pdf")
target = Path(r"C:\MyPython\AAA_cmip6_analysis_taylor diagram_dailyMonthly\analysis_workspace\reference_pdf.txt")
reader = PdfReader(str(source))
chunks = []
for page_no, page in enumerate(reader.pages, start=1):
    chunks.append(f"\n\n===== PAGE {page_no} =====\n\n{page.extract_text() or ''}")
target.write_text("".join(chunks), encoding="utf-8")
print(f"pages={len(reader.pages)} chars={sum(len(x) for x in chunks)} target={target}")
