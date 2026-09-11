from pathlib import Path
from zipfile import ZipFile
import shutil
import tempfile

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.text import WD_BREAK
from docx.shared import Inches


TARGET = Path(r"D:\วารสารบูรพา\Evaluation of Quantile Delta Mapping for Bias Correction of CMIP6 Daily Rainfall Using Independent Temporal Cross-Validation in Prachuap Khiri Khan Province.docx")
BASE = Path(r"D:\วารสารบูรพา\ID1558_Manuscript_BSJ (11).docx")
OUT = Path(r"C:\MyPython\AAA_cmip6_analysis_taylor diagram_dailyMonthly\ID1558_revised_for_publication.docx")


REPLACEMENTS = {
    "การประเมินวิธีควอนไทล์เดลตาแมปปิงเพื่อปรับแก้อคติข้อมูลฝนรายวันจากแบบจำลอง CMIP6": "การประเมินวิธี Quantile Delta Mapping สำหรับการปรับแก้อคติข้อมูลฝนรายวันจากแบบจำลอง CMIP6",
    "ด้วยการกันข้อมูลช่วงเวลาอิสระในจังหวัดประจวบคีรีขันธ์": "ด้วยการตรวจสอบด้วยช่วงเวลาอิสระในจังหวัดประจวบคีรีขันธ์",
    "การกันข้อมูลช่วงเวลาอิสระ": "การตรวจสอบด้วยช่วงเวลาอิสระ",
    "การตรวจสอบความถูกต้องข้ามช่วงเวลาแบบอิสระ": "การตรวจสอบด้วยช่วงเวลาอิสระ",
    "2.3 การออกแบบการตรวจสอบด้วยช่วงเวลาอิสระ": "2.3 กรอบการวิจัยและการตรวจสอบด้วยช่วงเวลาอิสระ",
    "ที่กันข้อมูลตรวจวัดไว้": "ที่แยกไว้สำหรับตรวจสอบ",
    "ข้อสรุปนี้จำกัดอยู่ที่การกันข้อมูลช่วงเวลาเพียงรูปแบบเดียว": "ข้อสรุปนี้จำกัดอยู่ที่การตรวจสอบด้วยช่วงเวลาอิสระเพียงรูปแบบเดียว",
    "ทดสอบนัยสำคัญด้วยการสุ่มซ้ำแบบบล็อกรายปีจำนวน 2,000 ครั้ง พร้อมควบคุมอัตราการค้นพบเท็จ และประเมินทั้งรายแบบจำลองและกลุ่มแบบจำลองเฉลี่ยแบบไม่ถ่วงน้ำหนัก": "ทดสอบนัยสำคัญด้วยการสุ่มซ้ำแบบบล็อกรายปีจำนวน 2,000 ครั้ง โดยใช้การควบคุมอัตราการค้นพบเท็จด้วยวิธี Benjamini-Yekutieli เป็นหลัก และรายงานผล Benjamini-Hochberg ประกอบในวงเล็บ พร้อมประเมินทั้งรายแบบจำลองและกลุ่มแบบจำลองเฉลี่ยแบบไม่ถ่วงน้ำหนัก",
    "Significance was assessed by a 2,000-replicate year-block bootstrap with Benjamini-Hochberg false discovery rate control. Individual model performance and an unweighted multi-model ensemble were assessed separately.": "Significance was assessed by a 2,000-replicate year-block bootstrap using Benjamini-Yekutieli false discovery rate control as the primary procedure, with Benjamini-Hochberg results reported in parentheses. Individual model performance and an unweighted multi-model ensemble were assessed separately.",
    "/Journal of the Royal Statistical Society: Series B, 57/(1)": "Journal of the Royal Statistical Society: Series B, 57(1)",
    "/The Annals of Statistics, 29/(4)": "The Annals of Statistics, 29(4)",
    "/Journal of Advances in Modeling Earth Systems, 12/(2)": "Journal of Advances in Modeling Earth Systems, 12(2)",
    "/Geoscientific Model Development, 15/(7)": "Geoscientific Model Development, 15(7)",
    "/Environmental Research Letters, 16/(2)": "Environmental Research Letters, 16(2)",
    "/Journal of the Royal Statistical Society: Series C, 28/(2)": "Journal of the Royal Statistical Society: Series C, 28(2)",
    "/Journal of Water and Climate Change, 13/(1)": "Journal of Water and Climate Change, 13(1)",
    "/Geoscientific Model Development, 12/(11)": "Geoscientific Model Development, 12(11)",
    "/Geoscientific Model Development, 12/(7)": "Geoscientific Model Development, 12(7)",
    "/Climate Dynamics, 57/(5-6)": "Climate Dynamics, 57(5-6)",
    "/Journal of Southern Hemisphere Earth Systems Science, 70/(1)": "Journal of Southern Hemisphere Earth Systems Science, 70(1)",
    "Splitting the monthly mean square error exactly into an annual-cycle component and an anomaly component showed that the difference between the configurations lies predominantly in the annual-cycle component, which accounts for about 95% of it, which changed by -3,202 and +412 (mm month⁻¹)² respectively, whereas the anomaly component deteriorated by a similar amount under both, at +2,132 and +2,319.": "Splitting the monthly mean square error exactly into an annual-cycle component and an anomaly component showed that the difference between the configurations lies predominantly in the annual-cycle component, which accounted for about 95% of the total contrast; this component changed by -3,202 and +412 (mm month⁻¹)², respectively, whereas the anomaly component deteriorated by a similar amount under both configurations, at +2,132 and +2,319.",
    "independent temporal holdout": "independent temporal holdout",
}


def delete_paragraph(paragraph):
    p = paragraph._element
    p.getparent().remove(p)
    paragraph._p = paragraph._element = None


def remove_supplementary_section(doc):
    paragraphs = doc.paragraphs
    start = None
    end = None
    for i, p in enumerate(paragraphs):
        if p.text.strip() == "Supplementary Material":
            start = i
        elif start is not None and p.text.strip() == "Acknowledgments":
            end = i
            break
    if start is not None and end is not None:
        for p in list(paragraphs[start:end]):
            delete_paragraph(p)


def replace_text_preserving_first_run(paragraph, replacements):
    text = paragraph.text
    new_text = text
    for old, new in replacements.items():
        new_text = new_text.replace(old, new)
    if new_text == text:
        return
    if paragraph.runs:
        paragraph.runs[0].text = new_text
        for run in paragraph.runs[1:]:
            run.text = ""
    else:
        paragraph.add_run(new_text)


def extract_first_figure(target_docx, out_path):
    with ZipFile(target_docx) as zf:
        data = zf.read("word/media/image1.jpg")
    out_path.write_bytes(data)


def add_figure1(doc, image_path):
    insertion = None
    for p in doc.paragraphs:
        if p.text.strip().startswith("2.2 "):
            insertion = p
            break
    if insertion is None:
        raise RuntimeError("Cannot find section 2.2 insertion point")

    image_para = insertion.insert_paragraph_before("")
    image_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    image_para.add_run().add_picture(str(image_path), width=Inches(6.3))

    caption = insertion.insert_paragraph_before("Figure 1  The study area in Prachuap Khiri Khan Province")
    caption.alignment = WD_ALIGN_PARAGRAPH.CENTER


def page_break_before_result_tables(doc):
    for p in doc.paragraphs:
        if p.text.strip().startswith(("Table 4 ", "Table 5 ")):
            pb = p.insert_paragraph_before("")
            pb.add_run().add_break(WD_BREAK.PAGE)


def improve_body_alignment(doc):
    for i, p in enumerate(doc.paragraphs):
        text = p.text.strip()
        if not text:
            continue
        if i < 10:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            continue
        if len(text) < 80:
            continue
        if text.startswith(("Figure ", "Table ", "รูปที่", "ตารางที่")):
            continue
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT


def main():
    shutil.copyfile(BASE, OUT)
    with tempfile.TemporaryDirectory() as tmp:
        fig1 = Path(tmp) / "figure1.jpg"
        extract_first_figure(TARGET, fig1)
        doc = Document(OUT)

        for paragraph in doc.paragraphs:
            replace_text_preserving_first_run(paragraph, REPLACEMENTS)

        remove_supplementary_section(doc)
        add_figure1(doc, fig1)
        page_break_before_result_tables(doc)
        improve_body_alignment(doc)

        # Final polish: publication draft should not carry the removed supplement in availability text.
        for paragraph in doc.paragraphs:
            replace_text_preserving_first_run(
                paragraph,
                {
                    "Data and Code Availability": "Data and Code Availability",
                    "Data and Code Availability": "Data and Code Availability",
                },
            )

        doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
