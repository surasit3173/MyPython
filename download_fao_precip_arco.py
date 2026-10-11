"""
ดึงข้อมูลฝนรายวัน (Precipitation) จาก AgERA5 ARCO Zarr (1979-2007)
สกัดค่าที่ 15 สถานีในภาคอีสาน แล้ว aggregate เป็นรายเดือน

Variable: Precipitation_Flux (mm/day)
Units: mm day-1 (ไม่ต้องแปลงหน่วย)

Usage:
    python download_fao_precip_arco.py
"""

import os
import xarray as xr
import pandas as pd
import numpy as np

# ---------- ตั้งค่า ----------
CDS_API_KEY = "2098ba38-a22b-4374-8ed9-22ed6e78c81d"

GEO_URL = (
    "https://arco.datastores.ecmwf.int/cadl-arco-geo-001/arco/"
    "sis_agrometeorological_indicators/all/geoChunked.zarr"
)

STATION_FILE   = "station_coords15sta.csv"
OUTPUT_DAILY   = "data/agera5_precip_station_daily_arco.csv"
OUTPUT_MONTHLY = "data/agera5_precip_station_monthly_arco.csv"

YEARS_START = 1979
YEARS_END   = 2007

# ชื่อตัวแปรฝนใน AgERA5 ARCO
PRECIP_VAR = "Precipitation_Flux"

os.makedirs("data", exist_ok=True)


# ---------- 1) เปิด ARCO store ----------
def load_arco():
    print("⏳ กำลังเปิด ARCO Zarr store...")

    storage_options = None
    if CDS_API_KEY:
        storage_options = {"headers": {"Authorization": f"Bearer {CDS_API_KEY}"}}

    ds = xr.open_zarr(
        GEO_URL,
        storage_options=storage_options,
        consolidated=True,
    )
    print(f"✅ เปิดสำเร็จ")
    print(f"   ตัวแปรฝน: {PRECIP_VAR}")
    print(f"   พิกัด: {list(ds.coords)}")
    print(f"   มิติเวลา: {ds.time.min().values} ถึง {ds.time.max().values}")
    return ds


# ---------- 2) อ่านไฟล์สถานี ----------
def read_stations(path=STATION_FILE):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"ไม่พบไฟล์ {path}\n"
            f"   ให้วางไฟล์นี้ไว้ใน: {os.path.abspath('.')}"
        )
    stations = pd.read_csv(
        path,
        dtype={"stncode": "int64", "lat": "float64", "lon": "float64"},
    )
    required = {"stncode", "lat", "lon"}
    missing = required - set(stations.columns)
    if missing:
        raise ValueError(f"ไฟล์ {path} ขาดคอลัมน์: {missing}")
    return stations


# ---------- 3) ดึงค่าฝนที่ 15 สถานี ----------
def extract_precip_at_stations(ds, station_file=STATION_FILE):
    print(f"⏳ กำลังดึงค่าฝนที่พิกัด 15 สถานี...")

    stations = read_stations(station_file)
    print(f"   พบ {len(stations)} สถานี")

    if PRECIP_VAR not in ds.data_vars:
        raise ValueError(
            f"ไม่พบตัวแปร '{PRECIP_VAR}' ใน dataset\n"
            f"   ตัวแปรที่มี: {list(ds.data_vars)}"
        )

    da = ds[PRECIP_VAR].sel(
        time=slice(f"{YEARS_START}-01-01", f"{YEARS_END}-12-31")
    )

    units = da.attrs.get("units", "unknown")
    print(f"   หน่วยของ {PRECIP_VAR}: {units}")

    records = []
    for _, row in stations.iterrows():
        point = da.sel(
            latitude=row["lat"],
            longitude=row["lon"],
            method="nearest",
        )
        df_pt = point.to_dataframe(name="precip").reset_index()
        df_pt["stncode"]     = int(row["stncode"])
        df_pt["station_lat"] = float(row["lat"])
        df_pt["station_lon"] = float(row["lon"])
        records.append(df_pt)
        print(f"   ✓ {int(row['stncode'])} ({row['lat']}, {row['lon']})")

    result = pd.concat(records, ignore_index=True)

    # แทนค่า missing
    result["precip"] = result["precip"].replace(-9999, np.nan)

    # ตรวจหน่วย: ปกติเป็น mm/day; ถ้าเป็น m/day ให้คูณ 1000
    if units.lower() in ("m", "m/day", "m day-1"):
        result["precip"] = result["precip"] * 1000.0
        print("   ⚠️ แปลงหน่วย m → mm")

    result = result.rename(columns={"precip": "precip_mm_day"})

    # บังคับ dtype
    result["stncode"]     = result["stncode"].astype("int64")
    result["station_lat"] = result["station_lat"].astype("float64")
    result["station_lon"] = result["station_lon"].astype("float64")
    result["precip_mm_day"] = result["precip_mm_day"].astype("float64")
    result["latitude"]    = result["latitude"].astype("float64")
    result["longitude"]   = result["longitude"].astype("float64")

    result = result[[
        "stncode", "time",
        "latitude", "longitude",
        "station_lat", "station_lon",
        "precip_mm_day",
    ]]

    return result


# ---------- 4) Aggregate รายวัน -> รายเดือน ----------
def aggregate_monthly(df_daily):
    print("⏳ กำลังรวมรายวันเป็นรายเดือน...")
    df = df_daily.copy()
    df["time"]  = pd.to_datetime(df["time"])
    df["year"]  = df["time"].dt.year.astype("int64")
    df["month"] = df["time"].dt.month.astype("int64")

    monthly = (
        df.groupby(["stncode", "year", "month"])
        .agg(
            precip_mm_month=("precip_mm_day", "sum"),
            n_days=("precip_mm_day", "count"),
            n_wet_days=("precip_mm_day", lambda x: (x >= 0.1).sum()),
        )
        .reset_index()
    )

    # เก็บเฉพาะเดือนที่มีข้อมูล ≥ 25 วัน
    monthly = monthly[monthly["n_days"] >= 25].copy()
    monthly = monthly.drop(columns=["n_days"])

    # เพิ่มคอลัมน์วันที่
    monthly["date"] = pd.to_datetime(
        dict(year=monthly["year"], month=monthly["month"], day=1)
    )

    # บังคับ dtype
    monthly["stncode"]        = monthly["stncode"].astype("int64")
    monthly["year"]           = monthly["year"].astype("int64")
    monthly["month"]          = monthly["month"].astype("int64")
    monthly["precip_mm_month"] = monthly["precip_mm_month"].astype("float64")
    monthly["n_wet_days"]     = monthly["n_wet_days"].astype("int64")

    monthly = monthly[[
        "stncode", "date", "year", "month",
        "precip_mm_month", "n_wet_days",
    ]]

    return monthly


# ---------- Main ----------
if __name__ == "__main__":
    ds = load_arco()

    # 1. ดึงรายวัน
    df_daily = extract_precip_at_stations(ds)
    df_daily.to_csv(OUTPUT_DAILY, index=False)
    print(f"\n✅ บันทึกรายวัน: {OUTPUT_DAILY} ({len(df_daily)} แถว)")

    # 2. รวมรายเดือน
    df_monthly = aggregate_monthly(df_daily)
    df_monthly.to_csv(OUTPUT_MONTHLY, index=False)
    print(f"✅ บันทึกรายเดือน: {OUTPUT_MONTHLY} ({len(df_monthly)} แถว)")

    # 3. สรุป
    print(f"\n📊 ตัวอย่างข้อมูลรายวัน:")
    print(df_daily.head())
    print(f"\n📊 ตัวอย่างข้อมูลรายเดือน:")
    print(df_monthly.head())

    print(f"\n📈 สรุป:")
    print(f"   จำนวนสถานี: {df_daily['stncode'].nunique()}")
    print(f"   ช่วงวันที่: {df_daily['time'].min()} ถึง {df_daily['time'].max()}")
    print(f"   Missing (รายวัน): {df_daily['precip_mm_day'].isna().sum()}")
    print(f"   Missing (รายเดือน): {df_monthly['precip_mm_month'].isna().sum()}")
    print(f"   ฝนเฉลี่ยรายวัน: {df_daily['precip_mm_day'].mean():.3f} mm/day")
    print(f"   ฝนเฉลี่ยรายเดือน: {df_monthly['precip_mm_month'].mean():.2f} mm/month")