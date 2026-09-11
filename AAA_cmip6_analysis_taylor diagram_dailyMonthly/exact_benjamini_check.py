from pathlib import Path
from docx import Document

path = Path(r"D:\วารสารบูรพา\Evaluation of Quantile Delta Mapping for Bias Correction of CMIP6 Daily Rainfall Using Independent Temporal Holdout.docx")
doc = Document(path)

paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

print(f"FILE: {path}")
print(f"PARAGRAPHS: {len(paras)}")
print()

for needle in [
    "Benjamini",
    "Benjamini-Hochberg",
    "Benjamini–Hochberg",
    "Benjamini-Yekutieli",
    "Benjamini–Yekutieli",
    "Hochberg",
    "Yekutieli",
]:
    hits = [(i, t) for i, t in enumerate(paras) if needle in t]
    print(f"SEARCH: {needle} => {len(hits)} hit(s)")
    for i, t in hits:
        print(f"  paragraph {i}: {t}")
    print()

print("ABSTRACT-RELATED PARAGRAPHS")
for i, t in enumerate(paras[:25]):
    print(f"{i}: {t}")
