from collections import Counter
from pathlib import Path
import re
from docx import Document

docx_path = Path(r"C:\MyPython\AAA_cmip6_analysis_taylor diagram_dailyMonthly\ID1558_revised_for_publication_final.docx")
doc = Document(docx_path)
paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

headings = []
for i, text in enumerate(paras):
    if re.match(r"^(\d+(\.\d+)?\s|Abstract$|บทคัดย่อ$|Methodology$|Results$|Discussion$|Conclusions$|Acknowledgments$|References$)", text):
        headings.append((i, text))

targets = [
    "อย่างไรก็ตาม",
    "ดังนั้น",
    "กล่าวคือ",
    "โดยสรุป",
    "ผลการศึกษา",
    "ผลดังกล่าว",
    "ชี้ให้เห็นว่า",
    "สอดคล้องกับ",
    "จึง",
    "การประเมิน",
    "การปรับแก้",
    "ช่วงตรวจสอบแบบอิสระ",
    "คู่การประเมิน",
    "มิได้",
    "ไม่ควร",
    "ในทุกคู่",
    "ในทุกกรณี",
]

full = "\n".join(paras)
print("COUNTS")
for t in targets:
    print(f"{t}\t{full.count(t)}")

print("\nHEADINGS")
for i, h in headings:
    print(f"{i}\t{h}")

print("\nLONG_OR_REPETITIVE_PARAGRAPHS")
for i, text in enumerate(paras):
    score = sum(text.count(t) for t in targets)
    if len(text) > 420 or score >= 4:
        section = ""
        for hi, h in headings:
            if hi <= i:
                section = h
            else:
                break
        print(f"{i}\t{section}\tlen={len(text)} score={score}\t{text[:260]}")
