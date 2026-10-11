# Portable ETCCDI MK/MMK/Sen/IDW package

ชุดนี้ประกอบด้วย scientific core ฉบับเต็มและ `portable_runner.py` ซึ่งอ่านการตั้งค่าจาก JSON ทำให้เปลี่ยนจังหวัด ช่วงเวลา จำนวนสถานี รายชื่อโมเดล และขอบเขตแผนที่ได้โดยไม่ต้องแก้ algorithm

## 1. ติดตั้ง

```powershell
python -m pip install -r requirements.txt
```

แนะนำ Python 3.10 ขึ้นไป และควรใช้ virtual environment ของแต่ละโครงการ

## 2. รูปแบบข้อมูล

โฟลเดอร์ input ต้องมีอย่างน้อย

```text
<input>/
  observed_daily.csv                 # YEAR, MONTH, DAY, <station columns>
  station_coordinates.xlsx            # station (หรือ Station_ID), latitude, longitude
  cmip6/
    bc_<model>_historical_*.csv
    bc_<model>_ssp245_*.csv
    bc_<model>_ssp585_*.csv
  boundary.shp/.shx/.dbf              # optional; configure boundary_filter when needed
```

ทุกไฟล์ฝนต้องมี `YEAR`, `MONTH`, `DAY` และคอลัมน์สถานีเดียวกับ workbook พิกัด ค่า missing ที่ใช้ใน core คือ `-99.9`, `-99.99`, `-999`, `-999.9`, `-9999`.

## 3. ตั้งค่าจังหวัดใหม่

คัดลอก `config_template.json` เป็นไฟล์ใหม่ เช่น `config_chiangrai.json` แล้วแก้:

- `province_name`
- `input.observed_file`, `input.coordinates_file`, และ `input.boundary_file`
- `input.station_ids` หรือ `input.station_prefix` หาก workbook พิกัดรวมหลายจังหวัด
- `models` ให้ตรงกับ token ในชื่อไฟล์ CMIP6
- `periods` ให้ตรงกับข้อมูลจริง
- `scenarios` หากใช้รหัส scenario อื่น
- `settings` เฉพาะเมื่อมีเหตุผลทางวิชาการและบันทึกไว้ใน Methods

หาก `cmip6.files` ไม่ได้ระบุไว้ โปรแกรมจะค้นหาไฟล์ `bc_*.csv` อัตโนมัติ โดยต้องพบ exactly one file ต่อ model และ period เพื่อป้องกันการเลือกไฟล์ผิดจากลำดับชื่อไฟล์ หากต้องการควบคุมเอง ให้เพิ่ม:

```json
"cmip6": {
  "files": {
    "ModelA": {
      "historical": "cmip6/bc_ModelA_historical.csv",
      "ssp245": "cmip6/bc_ModelA_ssp245.csv",
      "ssp585": "cmip6/bc_ModelA_ssp585.csv"
    }
  }
}
```

สำหรับ shapefile ที่รวมหลายจังหวัด ให้ตั้ง `input.boundary_filter` เป็นรายการ `{field, value}`; โปรแกรมใช้ OR ระหว่างรายการ ตัวอย่าง Uttaradit ใช้ `PROV_CODE=53` หรือ `PROV_NAME=UTTARADIT`.
หาก DBF ของ shapefile ใช้ encoding อื่น ให้ระบุ `input.boundary_encoding` เช่น `utf-8` หรือ `cp874`.

## 4. ตรวจข้อมูลก่อนคำนวณ

```powershell
python portable_runner.py `
  --config config_chiangrai.json `
  --input C:\data\ChiangRai `
  --output output_chiangrai `
  --validate-only
```

## 5. รันเต็ม

```powershell
python portable_runner.py `
  --config config_chiangrai.json `
  --input C:\data\ChiangRai `
  --output output_chiangrai
```

ใช้ `--no-figures` หากต้องการเฉพาะตารางและ workbook ผลลัพธ์อยู่ใน `output_chiangrai/results`; แผนที่ IDW และแผนที่แนวโน้มอยู่ใน `output_chiangrai/figures`.

สำหรับข้อมูล Uttaradit ที่ใช้ตรวจสอบแล้ว:

```powershell
python portable_runner.py `
  --config config_uttaradit.json `
  --input C:\MyPython\CMIP6Uttaradit\Data_Uttaradit `
  --output output_uttaradit_portable
```

สำหรับไฟล์ตัวอย่างเพชรบุรีที่รวมพิกัดหลายจังหวัด ให้ใช้ `config_phetchaburi.json`
ซึ่งกรองสถานี `465xxx` และขอบเขต `PRV_CODE=76` ไว้แล้ว

## 6. หลักวิชาการและข้อควรระวัง

- PRCPTOT, SDII, Rx1day, Rx5day, CDD, CWD, R10mm, R20mm, R50mm, R95p และ R99p คำนวณตาม core ที่ตรวจ regression แล้ว
- แนวโน้มรายปีรายสถานีใช้ standard MK, Yue–Wang (2004) MMK และ Sen slope พร้อมช่วงความเชื่อมั่น 95%
- R95p/R99p ใช้ percentile threshold แบบ station-specific จากช่วงสังเกตการณ์ที่กำหนด
- IDW เป็นการแสดงค่าการเปลี่ยนแปลงที่อ้างอิงสถานี ไม่ใช่ dynamical downscaling หรือข้อมูลกริดที่สังเกตโดยตรง
- ส่วนของแผนที่ที่อยู่นอก station convex hull เป็น extrapolation ต้องระบุในบทความและตีความอย่างระมัดระวัง
- โปรแกรมหยุดทันทีเมื่อวันซ้ำ ชุดสถานีไม่ตรง ไฟล์ CMIP6 ขาด/ซ้ำ หรือช่วงเวลาครอบคลุมไม่ครบ

`Uttaradit_ETCCDI_MK_MMK2004_Sen_IDW_Q3_fixed.py` คือ scientific core ฉบับเต็ม ส่วน `portable_runner.py` เป็นชั้น configuration/orchestration สำหรับนำไปใช้ซ้ำ
