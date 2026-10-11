"""
ดึง ETo รายวันจาก AgERA5 ARCO Zarr (1979-2007)
สกัดค่าที่ 15 สถานีในภาคอีสาน แล้ว aggregate เป็นรายเดือน

Usage:
    python download_fao_eto_arco.py
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

STATION_FILE  = "station_coords15sta.csv"   # ต้องอยู่ในโฟลเดอร์เดียวกับสคริปต์
OUTPUT_DAILY  = "data/agera5_eto_station_daily_arco.csv"
OUTPUT_MONTHLY = "data/agera5_eto_station_monthly_arco.csv"

YEARS_START = 1979
YEARS_END   = 2007

# ชื่อตัวแปร ETo ที่ถูกต้องใน ARCO (ระบุตรง ๆ เลย ไม่ต้องค้นหา)
ETO_VAR = "ReferenceET_PenmanMonteith_FAO56"

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
    print(f"   ตัวแปร ETo: {ETO_VAR}")
    print(f"   พิกัด: {list(ds.coords)}")
    print(f"   มิติเวลา: {ds.time.min().values} ถึง {ds.time.max().values}")
    return ds


# ---------- 2) ดึงค่าที่ 15 สถานี ----------
def extract_eto_at_stations(ds, station_file=STATION_FILE):
    print(f"⏳ กำลังดึงค่า ETo ที่พิกัด 15 สถานี...")

    if not os.path.exists(station_file):
        raise FileNotFoundError(
            f"ไม่พบไฟล์ {station_file}\n"
            f"   ให้วางไฟล์นี้ไว้ใน: {os.path.abspath('.')}"
        )

    stations = pd.read_csv(station_file)
    print(f"   พบ {len(stations)} สถานี")

    if ETO_VAR not in ds.data_vars:
        raise ValueError(
            f"ไม่พบตัวแปร '{ETO_VAR}' ใน dataset\n"
            f"   ตัวแปรที่มี: {list(ds.data_vars)}"
        )

    da = ds[ETO_VAR].sel(
        time=slice(f"{YEARS_START}-01-01", f"{YEARS_END}-12-31")
    )

    units = da.attrs.get("units", "unknown")
    print(f"   หน่วยของ {ETO_VAR}: {units}")

    records = []
    for _, row in stations.iterrows():
        # ARCO ใช้ชื่อพิกัดว่า latitude / longitude
        point = da.sel(
            latitude=row["lat"],
            longitude=row["lon"],
            method="nearest",
        )
        df_pt = point.to_dataframe(name="eto").reset_index()
        df_pt["stncode"]     = row["stncode"]
        df_pt["station_lat"] = row["lat"]
        df_pt["station_lon"] = row["lon"]
        records.append(df_pt)
        print(f"   ✓ {row['stncode']} ({row['lat']}, {row['lon']})")

    result = pd.concat(records, ignore_index=True)

    # แทนค่า missing
    result["eto"] = result["eto"].replace(-9999, np.nan)

    # แปลงหน่วย m -> mm ถ้าจำเป็น
    if units.lower() in ("m", "m/day", "m day-1"):
        result["eto"] = result["eto"] * 1000.0
        print("   ⚠️ แปลงหน่วย m → mm")

    result = result.rename(columns={"eto": "eto_mm_day"})
    return result


# ---------- 3) Aggregate รายวัน -> รายเดือน ----------
def aggregate_monthly(df_daily):
    print("⏳ กำลังรวมรายวันเป็นรายเดือน...")
    df = df_daily.copy()
    df["time"]  = pd.to_datetime(df["time"])
    df["year"]  = df["time"].dt.year
    df["month"] = df["time"].dt.month

    monthly = (
        df.groupby(["stncode", "year", "month"])
        .agg(
            eto_mm_month=("eto_mm_day", "sum"),
            n_days=("eto_mm_day", "count"),
        )
        .reset_index()
    )
    # เก็บเฉพาะเดือนที่มีข้อมูล ≥ 25 วัน (ตรงกับ complete-month rule)
    monthly = monthly[monthly["n_days"] >= 25].copy()
    monthly = monthly.drop(columns=["n_days"])

    # เพิ่มคอลัมน์วันที่สำหรับ merge กับ validation ในภายหลัง
    monthly["date"] = pd.to_datetime(
        dict(year=monthly["year"], month=monthly["month"], day=1)
    )
    return monthly


# ---------- Main ----------
if __name__ == "__main__":
    ds = load_arco()

    # 1. ดึงรายวัน
    df_daily = extract_eto_at_stations(ds)
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
    print(f"   Missing (รายวัน): {df_daily['eto_mm_day'].isna().sum()}")
    print(f"   Missing (รายเดือน): {df_monthly['eto_mm_month'].isna().sum()}")