from docx import Document

doc = Document(r"C:\MyPython\AAA_cmip6_analysis_taylor diagram_dailyMonthly\ID1558_revised_for_publication_final.docx")
for i, p in enumerate(doc.paragraphs):
    text = p.text.strip()
    if text.startswith(("2.", "3.", "4.", "Results", "Methodology", "Discussion", "Conclusions")):
        print(i, text)
