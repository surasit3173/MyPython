from pathlib import Path
from docx import Document

paths = [
    Path(r"D:\วารสารบูรพา\Evaluation of Quantile Delta Mapping for Bias Correction of CMIP6 Daily Rainfall Using Independent Temporal Cross-Validation in Prachuap Khiri Khan Province.docx"),
    Path(r"C:\MyPython\AAA_cmip6_analysis_taylor diagram_dailyMonthly\ID1558_revised_for_publication_final.docx"),
]

def section(paras, start_prefixes, end_prefixes):
    start = None
    end = None
    for i, t in enumerate(paras):
        if start is None and any(t.startswith(p) for p in start_prefixes):
            start = i
        elif start is not None and any(t.startswith(p) for p in end_prefixes):
            end = i
            break
    if start is None:
        return []
    return paras[start:end]

for path in paths:
    doc = Document(path)
    paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    sec = section(paras, ["Methodology", "2.1"], ["Results", "3.1"])
    print("=" * 80)
    print(path)
    for i, t in enumerate(sec):
        print(f"{i:03d}: {t}")
