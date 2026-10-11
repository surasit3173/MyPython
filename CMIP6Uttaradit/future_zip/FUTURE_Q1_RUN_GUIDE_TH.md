# คู่มือ: การรัน `future_q1` (CMIP6 future projection Q1) แบบใช้ซ้ำหลายพื้นที่

โมดูล `src/future_q1.py` สร้างชุดรูป/ตารางระดับ Q1 สำหรับการฉายภาพฝนอนาคต CMIP6
พร้อมดัชนี ETCCDI 11 ตัว, การควบคุม multiplicity ด้วย BH-FDR, การสื่อสารความไม่แน่นอน
แบบ IPCC (ensemble sign agreement) และแผนที่ GIS มาตรฐานสิ่งพิมพ์

---

## 1) หลักการใช้ซ้ำ (สำคัญที่สุด)

**ไฟล์ observed rainfall คือ authority ของชุดสถานี** ชุดสถานีที่วิเคราะห์ =
คอลัมน์สถานีในไฟล์ observed ∩ ตารางพิกัด ดังนั้น

- ประจวบคีรีขันธ์ (12 สถานี) → เพชรบุรี (15 สถานี): เปลี่ยนแค่ไฟล์ข้อมูล ไม่ต้องแก้โค้ด
- ตารางพิกัดจะเป็นตารางระดับประเทศ (128 สถานี) ก็ได้ โค้ดเลือกเฉพาะสถานีที่อยู่ในไฟล์ observed

การค้นหาไฟล์อาศัย **โครงสร้างข้อมูล ไม่ใช่ชื่อไฟล์** จึงรองรับชื่อไฟล์ภาษาไทย/อังกฤษ
และนามสกุล `.csv/.xlsx/.xls`

## 2) ข้อมูลที่ต้องใช้

### 2.1 ไฟล์ observed baseline
Wide daily table รูปแบบใดรูปแบบหนึ่ง:
- `YEAR, MONTH, DAY, <station...>` หรือ
- `DATE, <station...>` (รองรับคอลัมน์ `วันที่` ด้วย)

ชื่อไฟล์ **ต้องไม่มี** token ของโมเดล/สถานการณ์ (`ssp`, `rcp`, `bc`, `historical`,
`pr_day`, ...) เพื่อไม่ให้สับสนกับไฟล์ GCM — ระบบจะหยุดพร้อมรายการถ้าเจอ 0 หรือหลายไฟล์

### 2.2 ไฟล์ future projection
- Wide daily table เหมือน observed
- ชื่อไฟล์ต้องมี scenario เช่น `ssp245`, `ssp585`
- ไฟล์ที่มี `bc/bias/qdm/corrected` จะถูกเลือกก่อนไฟล์ raw ของคู่ (model, scenario) เดียวกัน
- ชื่อโมเดลอ่านจากชื่อโฟลเดอร์ (เช่น `CESM2/...`) หรือ parse จากชื่อไฟล์

### 2.3 GIS
โฟลเดอร์ต้องมีขอบเขต shapefile 1 ชุด (`.shp` + `.prj`; ชื่อไฟล์อะไรก็ได้ เช่น
`boundary.shp`, `75_pbound.shp` — ถ้ามีหลาย `.shp` ระบบใช้ไฟล์แรกและแจ้งเตือน)
และตารางพิกัด (`.csv/.xlsx/.xls`)
ที่มีคอลัมน์ระบุ station id + latitude + longitude (รองรับ alias ไทย/อังกฤษ:
`station/สถานี`, `latitude/lat/ละติจูด`, `longitude/lon/ลองจิจูด`)

> boundary เป็น UTM (projected) หรือ lon/lat ก็ได้ — โค้ดตรวจและแปลงเป็น lon/lat ให้เอง
> (ไม่ต้องติดตั้ง geopandas/pyproj) ตั้ง `UTM_CENTRAL_MERIDIAN` ใน `config.py` ให้ตรงโซน

## 3) ดัชนี 11 ตัว
`PRCPTOT, SDII, Rx1day, Rx5day, CDD, CWD, R10mm, R20mm, R50mm, R95p, R99p`
- Wet day ≥ 1 mm
- R95p/R99p ใช้ percentile ของ observed wet days รายสถานี (ตรวจ residual bias ในตาราง 09)
- CDD/CWD/Rx5day คำนวณภายในปีปฏิทิน

## 4) วิธีรัน

```bash
python main.py --future-q1-only
```

หรือระบุเอง (รองรับ path ภาษาไทย):

```bash
python main.py --future-q1-only \
  --future-source "/path/to/gcm_data" \
  --future-gis-dir "/path/to/gis" \
  --future-area "Phetchaburi"
```

เปลี่ยนพื้นที่โดยแก้ `config.py` เฉพาะ `FUTURE_SOURCE_DIR`, `FUTURE_GIS_DIR`,
`STUDY_AREA_NAME`, `UTM_CENTRAL_MERIDIAN` (หรือใช้ env var `TFPW_FUTURE_SOURCE`,
`TFPW_FUTURE_GIS`, `TFPW_STUDY_AREA`)

## 5) ผลลัพธ์

ตาราง `output/future_q1/tables/` (ทุกไฟล์มีชีต `Info` + `results` + `Significant`):

| ไฟล์ | เนื้อหา |
|---|---|
| `TABLE_00_yearly_index_cube.parquet` (หรือ `.csv`) | ดัชนีรายปีทุกสถานี/โมเดล/สถานการณ์ |
| `TABLE_01_INDEX_REGISTRY` | นิยาม 11 ดัชนี |
| `TABLE_02_BASELINE_STATION_SUMMARY` | baseline observed รายสถานี |
| `TABLE_03_FUTURE_MODEL_WINDOW_SUMMARY` | ค่าเฉลี่ย + Δ รายโมเดล/หน้าต่าง |
| `TABLE_04_FUTURE_ENSEMBLE_STATION_SUMMARY` | ensemble รายสถานี + spread + agreement |
| `TABLE_05_FUTURE_TREND_RESULTS_BY_MODEL` | TFPW-MK รายโมเดล + BH-FDR |
| `TABLE_06_REGIONAL_ENSEMBLE_SUMMARY` | ระดับภูมิภาค + model IQR + agreement |
| `TABLE_07_FRAMEWORK_VALIDATION` | cross-check เทียบ framework (ถ้ามี) |
| `TABLE_08_SOURCE_FILE_INVENTORY` | ไฟล์ที่ค้นพบและบทบาท |
| `TABLE_09_BC_HISTORICAL_RESIDUAL_BIAS` | QC: bc-historical เทียบ observed |

รูป `output/future_q1/figures/` (600 dpi PNG + PDF):
- `FIGURE_01_study_area` — แผนที่พื้นที่ + inset ประเทศไทย + graticule องศา-ลิปดา
- `FIGURE_02_projection_overview_heatmap` — Δ% ทุกดัชนี × สถานการณ์ × หน้าต่าง
- `FIGURE_03_regional_projection_profiles` — ensemble mean + model IQR
- `FIGURE_04..14` — แผนที่ Δ รายดัชนี (6 panel) + hatching เมื่อ model agreement < 80%

## 6) การควบคุมคุณภาพเชิงวิธีวิทยา

- **BH-FDR** รายครอบครัว (index, scenario) — ควบคุม false discovery จากการทดสอบหลายพันครั้ง
- **Ensemble sign agreement** — hatching บนแผนที่เมื่อโมเดลเห็นทิศทางไม่ตรงกัน (< 80%)
  แทนการใช้ดาว/ขนาดวงกลม (ตามแนว IPCC AR6)
- **Residual-bias QC** — ยืนยันว่าใช้ threshold จาก observed กับอนุกรมโมเดลได้
- **SSP-only** — ไม่มีการต่ออนุกรม historical→SSP ข้ามขอบ 2014/2015

## 7) การตรวจสอบ (reproducibility)

```bash
pytest -q tests/test_future_q1.py            # known-answer + guard tests
# end-to-end regression (ต้องมีข้อมูล staged):
TFPW_TEST_SOURCE="/path/to/gcm_data" TFPW_TEST_GIS="/path/to/gis" \
  pytest -q tests/test_future_q1.py
```

## 8) เพิ่มดัชนีใหม่ภายหลัง
แก้ 2 จุด: `INDEX_SPECS` (นิยาม+หน่วย) และสูตรใน `_station_yearly_indices`
รูป/ตารางจะรวมดัชนีใหม่อัตโนมัติ
