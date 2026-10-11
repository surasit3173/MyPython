from pathlib import Path
from docx import Document
import re

path = Path(r"D:\วารสารบูรพา\Evaluation of Quantile Delta Mapping for Bias Correction of CMIP6 Daily Rainfall Using Independent Temporal Holdout.docx")
doc = Document(path)
paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
ref_i = next(i for i, t in enumerate(paras) if t == "References")
body = "\n".join(paras[:ref_i])
refs = paras[ref_i+1:]

print("REF_USAGE")
for ref in refs:
    m = re.match(r"([A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ'’\-]+)", ref)
    y = re.search(r"\((\d{4}[a-z]?)\)", ref)
    surname = m.group(1) if m else ""
    year = y.group(1) if y else ""
    used = (surname in body and (year[:4] in body if year else True))
    print(("USED" if used else "CHECK") + f"\t{surname}\t{year}\t{ref[:180]}")
