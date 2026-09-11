# คู่มือการรัน — CMIP6 Bias-Correction Framework (Paper 1)

กรอบงานนี้รันได้ด้วยคำสั่งเดียว และย้ายไปใช้กับจังหวัดอื่นได้โดยแก้ไฟล์ YAML ไฟล์เดียว
**ไม่มีไฟล์โค้ดใดเลยที่มีชื่อจังหวัด รหัสสถานี หรือปี ฝังอยู่**

---

## 1. ติดตั้ง

### 1.1 Python (จำเป็น)

ต้องใช้ Python 3.11 ขึ้นไป

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 1.2 Node.js (เฉพาะขั้นสร้างไฟล์ Word)

ต้องใช้ Node.js 18 ขึ้นไป ถ้าไม่ติดตั้ง ขั้นตอน `docx` จะถูกข้ามโดยอัตโนมัติ
และผลลัพธ์อื่นทั้งหมดยังออกครบ

```bash
cd docx_build
npm install
cd ..
```

---

## 2. วางข้อมูล

```
data/
├─ observed/
│   └─ Observed_Rain_daily_198101_201412_Uttaradit.csv
├─ cmip6_raw/
│   ├─ ACCESS-ESM1-5/pr_day_ACCESS-ESM1-5_historical_....csv
│   ├─ ACCESS-ESM1-5/pr_day_ACCESS-ESM1-5_ssp245_....csv
│   └─ ...  (ค้นหาแบบ recursive จะจัดโฟลเดอร์อย่างไรก็ได้)
└─ gis/
    └─ station_coordinates.xlsx
```

**รูปแบบไฟล์ฝนตรวจวัด** — คอลัมน์ `YEAR, MONTH, DAY` ตามด้วยคอลัมน์รหัสสถานี หน่วยเป็น มม./วัน

**รูปแบบไฟล์ CMIP6** — โครงเดียวกัน ชื่อไฟล์ต้องขึ้นต้นด้วย `pr_day_` และมีชื่อโมเดลกับ
`historical`/`sspXXX` อยู่ในชื่อไฟล์ ตามธรรมเนียม CMIP6

> ⚠️ ไฟล์ที่ชื่อขึ้นต้นด้วย `bc_` หรือมีคำว่า `bias`, `qdm`, `corrected`
> **จะถูกปฏิเสธโดยอัตโนมัติ** เพราะ framework จะสร้าง bias correction เองจาก raw
> เพื่อให้ตรวจสอบย้อนกลับได้ทั้งสาย

**ตารางพิกัดสถานี** — ต้องมีคอลัมน์ `station`, `latitude`, `longitude`
ระบบจะคัดเฉพาะสถานีที่อยู่ทั้งในไฟล์ฝนและในตารางพิกัด

**ขอบเขตการปกครอง** — ไม่ต้องเตรียม ระบบดาวน์โหลดและตรวจสอบให้เองในขั้น Gate F

---

## 3. รัน

### 3.1 รันทั้งหมดด้วยคำสั่งเดียว

```bash
python run_paper1.py --config config/uttaradit.yaml --figure1 figures/Uttaradit.png
```

`--figure1` ใส่หรือไม่ใส่ก็ได้ ถ้าใส่ ระบบจะใช้แผนที่ที่เตรียมไว้เป็น Figure 1
ถ้าไม่ใส่ ระบบจะวาดแผนที่พื้นฐานจากขอบเขตที่ตรวจสอบแล้วให้เอง

ใช้เวลาประมาณ **3–4 นาที** สำหรับ 13 สถานี × 7 โมเดล × 2 ฉากทัศน์

### 3.2 รันทีละขั้น

```bash
python run_paper1.py --config config/uttaradit.yaml --only gate_f
python run_paper1.py --config config/uttaradit.yaml --only pipeline
python run_paper1.py --config config/uttaradit.yaml --from manuscript
```

| ขั้น | ทำอะไร | เวลา |
|---|---|---|
| `gate_f` | ดาวน์โหลดและตรวจสอบขอบเขตการปกครอง (ชื่อ พื้นที่ CRS geometry สถานีอยู่ในเขต) | ~20 วิ |
| `gate_h` | ตรวจสายข้อมูล raw หาความผิดปกติ (หน่วย ปฏิทิน การต่อไฟล์ กริด) | ~60 วิ |
| `pipeline` | QC ข้อมูลตรวจวัด → fit-freeze-apply → ดัชนี → ensemble → acceptance gates | ~145 วิ |
| `trace` | วินิจฉัยเชิงลึกช่วงเวลาที่ถูก flag (ถ้ามี) | ~30 วิ |
| `manuscript` | ตาราง 4 ตาราง + supplementary 8 ชีต + รูป 6 รูป | ~40 วิ |
| `finalize` | สรุปสถานะ gate + ขอบเขตการตีความ + SHA-256 ของทุกไฟล์ | ~20 วิ |
| `docx` | เอกสาร Word ตามรูปแบบ APST | ~15 วิ |

---

## 4. ย้ายไปใช้จังหวัดอื่น

```bash
cp config/uttaradit.yaml config/nan.yaml
```

แก้เพียงสองบล็อกใน `config/nan.yaml`:

```yaml
area:
  name: Nan
  country: Thailand
  adm1_name: Nan                 # ชื่อตามที่ปรากฏในชุดข้อมูล ADM1
  country_iso3: THA
  reference_area_km2: 11472.1    # พื้นที่อ้างอิงสำหรับตรวจความสมเหตุสมผล
  stations: null                 # null = หาเองจาก observed ∩ ตารางพิกัด

paths:
  observed: data/nan/observed/Observed_Rain_daily_Nan.csv
  cmip6_raw: data/nan/cmip6_raw
  gis: data/nan/gis
  output: output_nan
```

แล้วรัน

```bash
python run_paper1.py --config config/nan.yaml
```

**สิ่งที่ระบบทำเองทั้งหมด**

- หาสถานีจาก `คอลัมน์ในไฟล์ฝน ∩ ตารางพิกัด`
- ค้นหาโมเดลและฉากทัศน์จากชื่อไฟล์
- ตรวจปฏิทินของแต่ละโมเดลจากข้อมูลจริง (noleap / Gregorian / 360-day)
- ตรวจหน่วย (ตรวจจับกรณีลืมคูณ 86400)
- ดาวน์โหลดและตรวจสอบขอบเขตการปกครองตามชื่อใน YAML
- เรียงลำดับช่วงเวลาในรูปตาม `periods.future` ไม่ใช่เรียงตามตัวอักษร

**สิ่งที่ปรับได้ใน YAML โดยไม่ต้องแตะโค้ด**

| กลุ่ม | ปรับอะไรได้ |
|---|---|
| `periods` | ช่วง calibration / validation / baseline / future |
| `scenarios` | รายชื่อ SSP |
| `models` | `null` = ใช้ทุกโมเดลที่เจอ หรือระบุรายชื่อ |
| `bias_correction` | เกณฑ์วันฝน, frequency adaptation, plotting position, กฎ extrapolation, จำนวนวันฝนขั้นต่ำ, วิธี (qm / detqm / qdm) |
| `indices` | ชุดดัชนีและช่วงอ้างอิงเปอร์เซ็นไทล์ |
| `ensemble` | เกณฑ์ agreement |
| `observed_qc` | เกณฑ์ทั้ง 6 ตัวชี้วัดของ zero-QC |
| `figures` | dpi, ความกว้างคอลัมน์, ฟอนต์ |
| `seed` | เมล็ดสุ่ม |

### เปลี่ยนช่วงอนาคต

```yaml
periods:
  future:
    Near: [2021, 2050]
```

ทุกสถิติจะถูก **คำนวณใหม่จากอนุกรมรายวัน** ในช่วงที่ระบุ ไม่ใช่การเฉลี่ยผลของช่วงย่อย
ถ้าต้องการหลายช่วงก็เพิ่มบรรทัดได้ ระบบรองรับอัตโนมัติ

---

## 5. ผลลัพธ์

```
output/
├─ qc/                          OBS_ZERO_QC.xlsx, QC_flags.csv,
│                               Observed_Rain_daily_QC.csv, station_homogeneity.csv
├─ results/                     ~30 ตาราง csv พร้อมใช้เชิงเครื่อง
│   ├─ acceptance_gates.csv     สถานะ 8 gate พร้อมฟิลด์ limitation
│   ├─ gate_status_definitions.csv
│   ├─ performance.csv          MAB ราย metric ราย method ราย period
│   ├─ future_changes.csv       การเปลี่ยนแปลงราย model × station × index
│   ├─ ensemble_regional.csv    median / IQR / agreement
│   ├─ temporal_bias.csv        สถิติลำดับวัน
│   └─ variance_decomposition.csv
├─ paper1_manuscript/
│   ├─ Paper1_APST_manuscript.md      ต้นฉบับ (แก้ข้อความที่นี่)
│   ├─ Paper1_APST_manuscript.docx    เอกสาร Word ตามรูปแบบ APST
│   ├─ Paper1_MAIN_Tables.xlsx        Table 1–4
│   ├─ Paper1_SUPPLEMENTARY_Tables.xlsx  S1–S8
│   ├─ Paper1_CAPTIONS.csv
│   └─ figures/                       6 รูป PNG + PDF ที่ 600 dpi
├─ final/                       GATE_F_H_FINAL_STATUS.xlsx,
│                               INTERPRETATION_SCOPE.csv, SHA256SUMS.txt
└─ manifest/run_manifest.json   config + hash ของ input ทุกไฟล์ + เวอร์ชันไลบรารี + seed
```

### แก้ข้อความในบทความ

แก้ที่ `output/paper1_manuscript/Paper1_APST_manuscript.md` แล้วสร้าง Word ใหม่

```bash
python run_paper1.py --config config/uttaradit.yaml --only docx
```

ไม่ต้องแก้ใน Word โดยตรง เพราะจะถูกเขียนทับเมื่อสร้างใหม่

---

## 6. Acceptance gates

ทุก gate มีสถานะแบบไล่ระดับ ไม่ใช่ผ่าน/ไม่ผ่าน และมีฟิลด์ `limitation` เขียนข้อจำกัดไว้ตรง ๆ

| Gate | ตรวจอะไร |
|---|---|
| A | คุณภาพข้อมูลตรวจวัด — ศูนย์ที่น่าจะเป็น missing, ความเป็นเนื้อเดียวของสถานี |
| B | การปรับแก้ในช่วง calibration (marginal distribution) |
| C | การทวนสอบอิสระ — ต้องดีกว่า raw GCM |
| D | นิยามสัญญาณอนาคต — บังคับใช้ baseline ของโมเดลเดียวกันในโค้ด |
| E | ความครบถ้วนของการเปรียบเทียบวิธี |
| F | ขอบเขตการปกครองและผลเชิงพื้นที่ |
| G | ความสัมพันธ์เชิงเวลา (วินิจฉัยเท่านั้น ไม่มีเกณฑ์ตัวเลข) |
| H | ความสมเหตุสมผลของข้อมูล raw |

| สถานะ | ความหมาย |
|---|---|
| `PASS` | ผ่านเกณฑ์ ไม่มีข้อจำกัดสำคัญ |
| `PASS WITH RESIDUAL BIAS` | ดีกว่า raw แต่ยังมีความคลาดเคลื่อนเชิงระบบเหลืออยู่ |
| `PASS (MARGINAL ONLY)` | ผ่านเฉพาะการแจกแจงส่วนขอบ ห้ามตีความว่าครอบคลุมโครงสร้างเชิงเวลา |
| `DIAGNOSTIC PASS` | วัดและรายงานแล้ว ไม่ใช่การรับรองสมรรถนะการทำนาย |
| `VERIFIED RAW ANOMALY` | ความผิดปกติมาจากข้อมูลต้นทาง ไม่ใช่ความผิดของวิธี แต่ห้ามตีความเชิงกายภาพ |
| `BLOCKED` | ห้ามใช้ผล |

`output/final/INTERPRETATION_SCOPE.csv` ระบุทุกข้อความว่าเป็น
VERIFIED / DERIVED / DIAGNOSTIC / LIMITATION / QUARANTINED / EXCLUDED / NOT ESTABLISHED
**ให้ถือไฟล์นี้เป็นตัวกำหนดขอบเขตการเขียน ไม่ใช่ตีความจากตัวเลขในตารางเพียงอย่างเดียว**

---

## 7. ปัญหาที่พบบ่อย

| อาการ | สาเหตุและวิธีแก้ |
|---|---|
| `no raw CMIP6 files found` | ชื่อไฟล์ไม่ขึ้นต้นด้วย `pr_day_` หรือ `paths.cmip6_raw` ผิด |
| `refused N legacy bias-corrected file(s)` | ปกติ — เป็นการปฏิเสธไฟล์ `bc_*` โดยตั้งใจ |
| `unit check failed` | ยังไม่ได้แปลง `kg m⁻² s⁻¹` เป็น มม./วัน (ต้องคูณ 86400) |
| `too few wet days` | สถานี-โมเดลนั้นมีวันฝนน้อยกว่า `min_wet_days` จะถูกข้ามและมี warning |
| Gate F `BLOCKED` | หาขอบเขตไม่พบ หรือ polygon เป็นสี่เหลี่ยม — ตรวจ `area.adm1_name` ให้ตรงกับชื่อในชุดข้อมูล |
| ขั้น `docx` ถูกข้าม | ไม่ได้ติดตั้ง Node.js — ติดตั้งแล้วรัน `--only docx` |
| ไม่มีอินเทอร์เน็ต | Gate F ดาวน์โหลดขอบเขตไม่ได้ — วางไฟล์ `*_adm1_verified.geojson` ใน `data/gis/` เองแล้วข้ามขั้น `gate_f` |

---

## 8. การทำซ้ำได้

ทุกครั้งที่รัน `run_manifest.json` จะบันทึก

- ค่าคอนฟิกทั้งหมดที่ใช้จริง
- SHA-256 ของไฟล์นำเข้าทุกไฟล์
- เวอร์ชันของ Python และไลบรารีทุกตัว
- เมล็ดสุ่ม
- สถานะ gate ทุกข้อ

`output/final/SHA256SUMS.txt` ครอบคลุมทั้งไฟล์นำเข้าและไฟล์ผลลัพธ์
ใช้เป็น Data Availability Statement ได้โดยตรง

---

## 9. โครงสร้างโค้ด

```
src/cmip6bc/
├─ config.py        โหลด YAML, hash, manifest
├─ io_data.py       ค้นหาไฟล์, โหลด, ปฏิทิน, หน่วย, จับคู่สถานี
├─ qc_observed.py   zero-QC 6 ตัวชี้วัด จัด 3 ระดับ
├─ boundary.py      ดาวน์โหลดและตรวจสอบขอบเขต ADM1
├─ bc.py            QM / DetQM / QDM ภายใต้ API เดียว
├─ metrics.py       ดัชนี ETCCDI และสถิติการแจกแจง
├─ temporal.py      สถิติลำดับวัน (มิติที่ quantile mapping ไม่แก้)
├─ analysis.py      signal preservation, ensemble, variance decomposition, gates
└─ figures.py       รูปสำหรับตีพิมพ์ + ทะเบียนเลขรูปที่ออกเลขซ้ำไม่ได้
```

หลักการที่บังคับใช้ในโค้ด

1. พารามิเตอร์ประมาณค่าจากช่วง calibration เท่านั้น แล้วแช่แข็งใน `Fit`
   `bc.apply()` เข้าถึงข้อมูลตรวจวัดของช่วงเป้าหมายไม่ได้เลย
2. สัญญาณอนาคตคือ `BC_future / BC_historical` ของโมเดลและวิธีเดียวกัน
   ถ้าไม่มี `BC_HIST` ระบบจะ **raise** ไม่ยอมถอยไปใช้ค่าตรวจวัดเป็นตัวหาร
3. ทั้งสามวิธีใช้ occurrence model, quantile machinery, การจับคู่สถานี
   และโค้ดดัชนีชุดเดียวกัน ความต่างจึงเป็นของวิธีล้วน ๆ
4. agreement คือ **สัดส่วนต่อเนื่อง** ไม่เคยนำค่าบูลีนไป interpolate
5. เลขรูปออกจากทะเบียนกลางที่ออกเลขซ้ำไม่ได้เชิงโครงสร้าง

---

## 10. ข้อจำกัดที่ต้องรู้ก่อนใช้ผล

- ขอบเขตการปกครองมาจากแหล่งเดียว (Natural Earth 10 m) ซึ่งเป็นชุดข้อมูลเชิงแผนที่แบบ generalised
- ไม่มี metadata ประวัติสถานี จึงทำ formal homogenisation test ไม่ได้
- แต่ละโมเดลมี realisation เดียว แยก forced signal จาก internal variability ไม่ได้
- ข้อมูลตรวจวัด 34 ปี สั้นสำหรับการตรวจจับแนวโน้มฝน
- ข้อมูล raw ของแต่ละโมเดลให้อนุกรมที่ต่างกันเพียง 3–15 ชุดทั่วทั้งจังหวัด
  ผลเชิงพื้นที่จึงเป็นการ interpolate ระหว่างสถานี ไม่ใช่โครงสร้างที่แบบจำลองแยกแยะได้
- CDD, CWD และ Rx5day เป็น **ปริมาณเชิงวินิจฉัย** ห้ามเรียกว่าผ่านการปรับแก้แล้ว
