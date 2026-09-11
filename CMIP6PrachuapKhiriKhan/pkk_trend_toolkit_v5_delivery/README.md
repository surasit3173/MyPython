# Rainfall Trend Toolkit v5

รุ่น Major revision สำหรับวิเคราะห์แนวโน้มฝนรายสถานีและค่าเฉลี่ยเครือข่ายสถานี โดยแยก input contract, period completeness, effect size, dependence sensitivity, multiplicity, bootstrap, simulation และรายงานออกจากกันอย่างตรวจสอบย้อนกลับได้

## จุดสำคัญ

- Production run เป็นแบบ fail-closed: ไฟล์หาย, schema ผิด, วันที่ผิด, station key ไม่ตรง, ค่าฝนติดลบหรือไม่เป็น finite จะหยุดทันที ไม่มี synthetic fallback
- รองรับ daily CSV ทั้ง wide (`YEAR, MONTH, DAY, <station columns>`) และ long (`date, station_id, rain_mm`) ผ่าน JSON config
- วิเคราะห์ครบทุกสถานีที่ผ่านเกณฑ์ และเก็บ raw p-value, BH q-value, family definition และสถานะของวิธี
- Annual = มกราคม–ธันวาคม; wet = พฤษภาคม–ตุลาคม; dry = พฤศจิกายนปีก่อน–เมษายนของปี label
- ใช้เฉพาะ period ที่ครบตาม `completeness_threshold`; สำหรับข้อมูลตัวอย่าง dry ที่ไม่ครบปี 1981 และ 2015 ถูกตัดออก
- รายงาน MK, HR-MMK-3, PW-MK และ TFPW-MK แยกกัน ไม่เลือกผลที่ให้ p-value ต่ำที่สุด
- Bootstrap สุ่ม detrended residual blocks แล้วประกอบกลับบนแกนปีเดิม
- Monte Carlo FDR คำนวณ FDP = `V / max(R, 1)` ในแต่ละ replicate ก่อนเฉลี่ย
- Run directory ใช้ fingerprint ของ config และ observational inputs; manifest เก็บ SHA-256, parameters, environment และ output hashes

## ติดตั้งและทดสอบ

ใช้ Python 3.12:

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
```

ผลที่ตรวจในชุดส่งมอบนี้: 23 tests passed และ independent checks ยืนยัน Standard MK/Sen slope กับ `pymannkendall` ทั้ง annual, wet และ dry รวมถึง BH literal

## รันพื้นที่ประจวบคีรีขันธ์

```powershell
python run_analysis.py --config configs/prachuap.json --output-root .
```

ผลจะอยู่ใน `runs/<area>_<fingerprint>/` ประกอบด้วย CSV tables, figures และ `run_manifest.json` การสร้าง workbook และบทความจาก run เดียวกันใช้:

```powershell
node tools/build_results_workbook.mjs runs/<run_id>
python tools/build_manuscripts.py runs/<run_id>
python validation/validate_artifacts.py runs/<run_id>
python tools/finalize_run.py runs/<run_id>
```

## ใช้กับพื้นที่อื่น

1. วาง rainfall CSV และ station metadata CSV ในโฟลเดอร์ `data/` หรือระบุ relative path อื่น
2. คัดลอก `configs/template_long.json` หรือ `configs/prachuap.json`
3. เปลี่ยนชื่อพื้นที่, column mapping, wet/dry months และเกณฑ์ completeness
4. รันคำสั่งเดิมด้วย config ใหม่

Station IDs ถูกเก็บเป็นข้อความเพื่อไม่ทำเลขศูนย์นำหน้าหาย Elevation ยอมรับค่าว่าง/`NS` เป็น missing metadata แต่ latitude และ longitude ต้องเป็นตัวเลขที่ถูกต้อง การรวมค่า network เป็นค่าเฉลี่ยสถานีแบบน้ำหนักเท่ากัน จึงไม่ควรเรียกว่า areal mean หากยังไม่มี spatial weights

## ขอบเขตการตีความ

HR-MMK-3 คือ Hamed–Rao variant ที่กำหนดล่วงหน้าให้พิจารณาเฉพาะ lag 1–3 และ significant residual-rank ACF เท่านั้น ไม่ใช่การรับรองว่าคุม Type I error ได้ทุกกรณี Simulation ในชุดนี้แสดงความคลาดเคลื่อนของหลายวิธีใน short records จึงต้องอ่าน effect size, interval, q-value, calibration และ method disagreement ร่วมกัน

ไฟล์ legacy ต้นฉบับไม่ได้ถูกแก้ไขหรือเขียนทับ
