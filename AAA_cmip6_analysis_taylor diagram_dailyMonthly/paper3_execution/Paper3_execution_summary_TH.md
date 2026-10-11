# สรุปการดำเนินงาน Paper 3

## ชื่อบทความ

**ENSO-Conditioned Seasonal Rainfall Extremes and Signal Preservation after Cross-Fitted Quantile Delta Mapping over Uttaradit, Thailand**

## แนวคิดและความใหม่

งานนี้ไม่ใช้ปี ENSO ที่สังเกตได้ไปกำกับแบบจำลองภูมิอากาศแบบ free-running แต่คำนวณ Niño-3.4 จาก `tos` ของสมาชิกเดียวกับข้อมูลฝนของแต่ละ GCM แล้วทดสอบโดยตรงว่า blocked cross-fitted QDM รักษาการตอบสนองของฝนต่อ ENSO หรือไม่ การอนุมานใช้ “ปีฤดูกาลจัดการน้ำ” เป็นหน่วยสุ่มซ้ำ ไม่ใช้วันหรือสถานีเป็นตัวอย่างอิสระเทียม และแยก phase contrast ออกจาก true neutral-centred asymmetry

## ข้อมูลและวิธีหลัก

- ฝนรายวัน 13 สถานี จังหวัดอุตรดิตถ์ และ 7 CMIP6 GCM ช่วง 1981–2014
- ฤดูฝน พ.ค.–ต.ค.; ฤดูร้อน/แล้ง พ.ย.–เม.ย. โดยระบุปีจากเดือน พ.ย.
- Observed ENSO: NOAA CPC ERSSTv6 ONI ที่ตรึงสำเนาและ checksum แล้ว
- Model ENSO: exact-member `tos`, Niño-3.4 แบบถ่วงพื้นที่, climatology 1981–2010, linear detrend และค่าเฉลี่ยเคลื่อนที่ 3 เดือน
- Persistent episode: |anomaly|≥0.5°C ต่อเนื่องอย่างน้อย 5 overlapping windows; จัดฤดูด้วย strict majority
- QDM: 7 blocked folds, ไม่ใช้ observation จาก target fold, wet-day threshold 1 mm และใช้ adjacent-three-month calibration pool เฉพาะเดือนที่มี wet days ไม่ถึง 30 วัน
- ตัวชี้วัดหลัก: PRCPTOT, wet-day frequency, Rx1day และ CDD
- Bootstrap 5,000 ครั้ง; permutation 4,999 ครั้ง; Benjamini–Hochberg สำหรับ 16 primary tests

## ผลสำคัญ

- Observed rainy season: El Niño PRCPTOT −7.2% (95% CI −18.8 ถึง 4.4), Rx1day −24.3% (−40.1 ถึง 3.0), CDD +17.9% (−6.7 ถึง 41.0)
- Observed hot/dry season: El Niño PRCPTOT −28.7% (−55.5 ถึง 6.1); La Niña wet-day frequency +33.0% (0.0 ถึง 53.1)
- ไม่มี primary response ใดผ่านการปรับ multiple testing (q ต่ำสุด 0.433) จึงรายงานเป็น effect-size evidence ไม่ใช่ข้อยืนยันเชิงสถิติ
- QDM รักษาสัญญาณได้ 2/16, ลดทอน 4/16, ขยาย 3/16, กลับทิศ 1/16 และตัดสินไม่ได้เพราะ raw response ใกล้ศูนย์ 6/16
- กรณีเด่น: hot/dry El Niño PRCPTOT เปลี่ยนจาก raw −10.4% เป็น QDM +14.4% ขณะที่ observed = −28.7%
- ไม่มีหลักฐาน true neutral-centred asymmetry หลังปรับ multiple testing (observed q≥0.781)

## การตรวจสอบ

- Acceptance gates: ผ่าน 8/8
- Unit tests: ผ่าน 17/17
- QDM fits: 7,644 แถว; target-fold observation leakage = 0
- Numerical manuscript audit: ผ่าน 105/105 จุด
- ต้นฉบับ: A4, Calibri 11 pt, double spacing, continuous line numbering, 3 ตาราง, 4 รูป, 17 เอกสารอ้างอิง และ 15 หน้า
- จัดทำทั้งฉบับมีชื่อผู้เขียนและฉบับ blinded สำหรับ double-blind review

## ประเด็นที่ผู้เขียนต้องดำเนินการก่อนส่ง

1. เพิ่ม ORCID หากมี
2. นำ code/data package ไปฝากในคลังถาวร แล้วแทนข้อความ repository identifier ใน Data and Code Availability
3. ตรวจสิทธิ์เผยแพร่ข้อมูลสถานีจาก RID/TMD และระบุเงื่อนไขการเข้าถึง
4. ตรวจข้อความกิตติกรรมประกาศ ผลประโยชน์ทับซ้อน และ AI declaration ด้วยตนเอง
5. ระบบส่งบทความของ Chiang Mai Journal of Science ยังต้องใช้ cover letter และรายชื่อผู้ประเมินเสนอ 5 คน ซึ่งควรให้ผู้เขียนเลือกเพื่อหลีกเลี่ยงความขัดแย้งทางผลประโยชน์
