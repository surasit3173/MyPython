from pathlib import Path
from docx import Document

docx_path = Path(r"C:\MyPython\AAA_cmip6_analysis_taylor diagram_dailyMonthly\ID1558_revised_for_publication_final.docx")
doc = Document(docx_path)

replacements = {
    "CI95%(Δ) = [ Q_{0.025}({Δ^(b)}_{b=1}^{B}), Q_{0.975}({Δ^(b)}_{b=1}^{B}) ]          (3a)":
    "CI₉₅%(Δ) = [ Q₀.₀₂₅({Δ⁽ᵇ⁾}ᵇ⁼¹,…,ᴮ), Q₀.₉₇₅({Δ⁽ᵇ⁾}ᵇ⁼¹,…,ᴮ) ]          (3a)",

    "โดยที่ Q_{0.025} และ Q_{0.975} คือควอนไทล์ลำดับที่ 0.025 และ 0.975 ของการแจกแจง bootstrap ตามลำดับ ค่า p สองด้านคำนวณจากสัดส่วนของผลต่าง bootstrap ที่อยู่คนละด้านของศูนย์กับทิศทางที่สังเกตได้ โดยใช้การแก้ไขแบบบวกหนึ่งเพื่อหลีกเลี่ยงค่า p เท่ากับศูนย์เมื่อจำนวนการสุ่มซ้ำมีจำกัด ดังสมการที่ (3b)":
    "โดยที่ Q₀.₀₂₅ และ Q₀.₉₇₅ คือควอนไทล์ลำดับที่ 0.025 และ 0.975 ของการแจกแจง bootstrap ตามลำดับ ค่า p สองด้านคำนวณจากสัดส่วนของผลต่าง bootstrap ที่อยู่คนละด้านของศูนย์กับทิศทางที่สังเกตได้ โดยใช้การแก้ไขแบบบวกหนึ่งเพื่อหลีกเลี่ยงค่า p เท่ากับศูนย์เมื่อจำนวนการสุ่มซ้ำมีจำกัด ดังสมการที่ (3b)",

    "c(m) = Σ_{i=1}^{m} 1/i,    k = max { i : p_(i) ≤ iα/[m c(m)] },    reject H_(i) for i = 1, ..., k          (3c)":
    "c(m) = Σᵢ₌₁ᵐ 1/i,    k = max { i : pᵢ ≤ iα/[m c(m)] },    reject Hᵢ for i = 1, ..., k          (3c)",
}

hits = 0
for p in doc.paragraphs:
    text = p.text.strip()
    if text in replacements:
        p.text = replacements[text]
        hits += 1

doc.save(docx_path)
print(f"replaced {hits} equation visual paragraphs")
