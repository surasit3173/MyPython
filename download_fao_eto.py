import os
import glob
import zipfile
import cdsapi
import xarray as xr
import pandas as pd
import numpy as np

# ---------- ค่าคงที่ ----------
CDS_URL     = "https://cds.climate.copernicus.eu/api"
CDS_KEY     = "2098ba38-a22b-4374-8ed9-22ed6e78c81d"   # ถ้าไม่ตั้ง จะอ่านจาก ~/.cdsapirc
DATASET     = "sis-agrometeorological-indicators"
VARIABLE    = "reference_evapotranspiration"
STATISTIC   = "day_time"        # ค่าที่ถูกต้องของ AgERA5 (ไม่ใช่ 'monthly')
VERSION     = "2_0"
YEARS       = list(range(1979, 2008))
MONTHS      = [f"{m:02d}" for m in range(1, 13)]

# พื้นที่คร่อม 15 สถานี (lon_min, lat_min, lon_max, lat_max)
# ช่วยลดขนาดไฟล์และเวลาโหลด (ถ้าไม่ใส่ จะโหลดทั้งโลก)
AREA        = [18.5, 100.5, 13.5, 105.5]

RAW_DIR     = "data/raw_daily"
MONTHLY_NC  = "data/agera5_eto_monthly_1979_2007.nc"


# ---------- Client ----------
def get_client():
    """สร้าง CDS client (env var ก่อน, fallback ไป .cdsapirc)"""
    if CDS_KEY:
        return cdsapi.Client(url=CDS_URL, key=CDS_KEY)
    return cdsapi.Client()


# ---------- Helper: แตก zip ถ้าจำเป็น ----------
def _ensure_netcdf(path):
    """
    ตรวจว่า path เป็น netcdf หรือ zip
    ถ้าเป็น zip -> แตกไฟล์ .nc ออกมา แล้วคืน path ของ .nc
    """
    if zipfile.is_zipfile(path):
        out_dir = os.path.dirname(path)
        with zipfile.ZipFile(path) as z:
            nc_names = [n for n in z.namelist() if n.lower().endswith(".nc")]
            z.extractall(out_dir, members=nc_names)
        # ลบ zip ทิ้ง
        os.remove(path)
        # คืน path ของ .nc (สมมติว่ามีไฟล์เดียว)
        return os.path.join(out_dir, nc_names[0])
    return path


# ---------- 1) ดาวน์โหลดรายวันเป็น batch รายปี ----------
def _download_daily_year(client, year, out_path):
    """ดาวน์โหลดข้อมูล ETo รายวัน 1 ปี"""
    if os.path.exists(out_path):
        print(f"   ↳ ปี {year}: มีไฟล์อยู่แล้ว ข้าม")
        return out_path

    print(f"   ↳ ปี {year}: กำลังดาวน์โหลด...")
    client.retrieve(
        DATASET,
        {
            "variable":  VARIABLE,
            "statistic": STATISTIC,
            "year":      str(year),
            "month":     MONTHS,
            "day":       [f"{d:02d}" for d in range(1, 32)],
            "version":   VERSION,
            "area":      AREA,
            "format":    "netcdf",
        },
        out_path,
    )
    return _ensure_netcdf(out_path)


# ---------- 2) Aggregate daily → monthly ----------
def _daily_to_monthly(nc_paths):
    """
    อ่าน NetCDF รายวันหลายไฟล์ -> resample เป็นรายเดือน
    โดยใช้ผลรวม (sum) ของ ETo รายวัน (mm/day -> mm/month)
    """
    print("⏳ กำลังรวมข้อมูลรายวันเป็นรายเดือน...")

    datasets = [xr.open_dataset(p) for p in nc_paths]
    ds = xr.concat(datasets, dim="time").sortby("time")

    # หาชื่อตัวแปร ETo
    eto_var = next(
        (v for v in ds.data_vars
         if "evapotranspiration" in v.lower() or "eto" in v.lower()),
        list(ds.data_vars)[0],
    )

    da = ds[eto_var]

    # แปลงหน่วย m -> mm ถ้าจำเป็น
    units = da.attrs.get("units", "").lower()
    if units in ("m", "m/day", "m day-1"):
        da = da * 1000.0
        da.attrs["units"] = "mm/day"

    # แทนค่า missing
    da = da.where(da != -9999)

    # รวมรายวัน -> รายเดือน (ผลรวม mm/day = mm/month)
    monthly = da.resample(time="1MS").sum(skipna=True)
    monthly.attrs["units"] = "mm/month"
    monthly.name = "eto_mm_month"

    # ปิดไฟล์ต้นทาง
    for d in datasets:
        d.close()

    return monthly


# ---------- 3) ฟังก์ชันหลัก ----------
def download_eto_monthly(
    years=YEARS,
    raw_dir=RAW_DIR,
    out_nc=MONTHLY_NC,
    overwrite=False,
):
    """
    ดาวน์โหลด ETo รายวันจาก AgERA5 v2.0 แล้ว aggregate เป็นรายเดือน

    Parameters
    ----------
    years      : list[int]  ปีที่ต้องการ (default 1979-2007)
    raw_dir    : str        โฟลเดอร์เก็บไฟล์รายวัน
    out_nc     : str        ไฟล์ NetCDF ผลลัพธ์รายเดือน
    overwrite  : bool       ถ้า True จะลบและดาวน์โหลดใหม่

    Returns
    -------
    xarray.DataArray  ETo รายเดือน (mm/month)
    """
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(os.path.dirname(out_nc) or ".", exist_ok=True)

    if os.path.exists(out_nc) and not overwrite:
        print(f"✅ พบไฟล์ {out_nc} แล้ว โหลดกลับมาใช้")
        return xr.open_dataarray(out_nc)

    # ---- 1. ดาวน์โหลดรายวัน ----
    client = get_client()
    print(f"⏳ เริ่มดาวน์โหลดข้อมูลรายวัน ({years[0]}-{years[-1]}) ...")
    nc_paths = []
    for y in years:
        zip_path = os.path.join(raw_dir, f"agera5_eto_{y}.zip")
        nc = _download_daily_year(client, y, zip_path)
        nc_paths.append(nc)

    # ---- 2. Aggregate รายเดือน ----
    monthly = _daily_to_monthly(nc_paths)

    # ---- 3. บันทึก ----
    monthly.to_dataset(name="eto_mm_month").to_netcdf(out_nc)
    print(f"✅ บันทึกไฟล์รายเดือน: {out_nc}")

    return monthly
# ---------- Main ----------
if __name__ == "__main__":
    import sys

    # ตรวจว่าเป็นรันแบบทดลองหรือเต็ม
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("🧪 โหมดทดลอง: ดาวน์โหลดแค่ปี 1979")
        monthly = download_eto_monthly(years=[1979])
    else:
        print("🚀 โหมดเต็ม: ดาวน์โหลด 1979-2007")
        monthly = download_eto_monthly()

    print("\n📊 สรุปข้อมูลที่ได้:")
    print(f"   มิติ: {monthly.dims}")
    print(f"   รูปร่าง: {monthly.shape}")
    print(f"   ช่วงเวลา: {monthly.time.min().values} ถึง {monthly.time.max().values}")
    print(f"   หน่วย: {monthly.attrs.get('units')}")
    print(f"\n   ตัวอย่าง 5 ค่าแรก:\n{monthly.isel(time=slice(0, 5)).values}")