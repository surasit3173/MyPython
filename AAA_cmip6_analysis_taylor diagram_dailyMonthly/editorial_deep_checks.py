from pathlib import Path
import re, zipfile
from docx import Document

docx_path = Path(r"D:\วารสารบูรพา\Evaluation of Quantile Delta Mapping for Bias Correction of CMIP6 Daily Rainfall Using Independent Temporal Holdout.docx")
doc = Document(docx_path)
paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
full = "\n".join(paras)

print("BASIC")
print("has_comments_xml", end="\t")
with zipfile.ZipFile(docx_path) as z:
    names = set(z.namelist())
    print("word/comments.xml" in names)
    tracked = False
    for n in names:
        if n.startswith("word/") and n.endswith(".xml"):
            data = z.read(n).decode("utf-8", errors="ignore")
            if "<w:ins" in data or "<w:del" in data:
                tracked = True
                break
    print("has_tracked_changes\t", tracked)

print("\nFIG_TABLE_CAPTIONS")
for i, t in enumerate(paras):
    if t.startswith("Figure ") or t.startswith("Table "):
        print(f"{i}\t{t[:300]}")

print("\nKEY_INCONSISTENCIES")
patterns = [
    ("BH_in_abstract", r"Benjamini[–-]Hochberg"),
    ("BY_in_body", r"Benjamini[–-]Yekutieli"),
    ("thai_holdout_variants", r"ตรวจสอบด้วยช่วงเวลาที่เป็นอิสระ|ตรวจสอบด้วยช่วงเวลาอิสระ|ช่วงตรวจสอบแบบอิสระ|ช่วงตรวจสอบอิสระ|ตรวจสอบข้ามช่วงเวลาแบบอิสระ"),
    ("calibration_terms", r"ปรับเทียบ|สอบเทียบ|ปรับแก้"),
    ("units_suspicious_mse", r"มิลลิเมตรกำลังสองต่อเดือนกำลังสอง|\(มม\. ต่อเดือน\)\^2|\(มม\. ต่อเดือน\)2"),
]
for label, pat in patterns:
    matches = re.findall(pat, full)
    print(label, len(matches), sorted(set(matches))[:20])

print("\nDOI_PATTERNS")
for m in re.finditer(r"https?://doi\.org/\S+", full):
    print(m.group(0)[:180])

print("\nIN_TEXT_CITATION_NAMES")
names = sorted(set(re.findall(r"\(([A-Z][A-Za-zÀ-ÖØ-öø-ÿ\-]+(?:\s*&\s*[A-Z][A-Za-zÀ-ÖØ-öø-ÿ\-]+| et al\.)?,\s*(?:19|20)\d{2}[a-z]?)\)", full)))
for n in names:
    print(n)
