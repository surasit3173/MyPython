"""
เพิ่มสถานี 354201 (Udon Thani) เข้าไฟล์ AgERA5 Precipitation
พิกัด: 17°23'00"N, 102°48'00"E = (17.3833, 102.8000)
"""

import os
import numpy as np
import pandas as pd
import xarray as xr

# ================================================================
# ตั้งค่า
# ================================================================
STATION_CODE = 354201
STATION_LAT  = 17.3833      # 17°23'00"N
STATION_LON  = 102.8000     # 102°48'00"E
STATION_NAME = "Udon Thani"

YEAR_START, YEAR_END = 1979, 2007

CDS_API_KEY = "2098ba38-a22b-4374-8ed9-22ed6e78c81d"
GEO_URL = (
    "https://arco.datastores.ecmwf.int/cadl-arco-geo-001/arco/"
    "sis_agrometeorological_indicators/all/geoChunked.zarr"
)
PRECIP_VAR = "Precipitation_Flux"

OUT_DIR    = "data"
DAILY_CSV  = os.path.join(OUT_DIR, "agera5_precip_station_daily_arco.csv")
BACKUP_CSV = os.path.join(OUT_DIR, "agera5_precip_354201_daily.csv")


# ================================================================
# 1. ดึงข้อมูลจาก ARCO Zarr
# ================================================================
def fetch_from_arco():
    print(f"⏳ กำลังเปิด ARCO Zarr store ...")

    storage_opts = None
    if CDS_API_KEY:
        storage_opts = {"headers": {"Authorization": f"Bearer {CDS_API_KEY}"}}

    ds = xr.open_zarr(GEO_URL, storage_options=storage_opts,
                      consolidated=True)
    print(f"✅ เปิดสำเร็จ")

    if PRECIP_VAR not in ds.data_vars:
        raise ValueError(f"ไม่พบตัวแปร '{PRECIP_VAR}'")

    da = ds[PRECIP_VAR].sel(
        time=slice(f"{YEAR_START}-01-01", f"{YEAR_END}-12-31"))

    print(f"⏳ ดึงข้อมูลที่พิกัด {STATION_LAT:.4f}°N, {STATION_LON:.4f}°E ...")
    point = da.sel(latitude=STATION_LAT, longitude=STATION_LON,
                   method="nearest")

    actual_lat = float(point.latitude.values)
    actual_lon = float(point.longitude.values)
    dist_km = np.sqrt((actual_lat - STATION_LAT) ** 2 +
                      (actual_lon - STATION_LON) ** 2) * 111

    print(f"   Grid ที่ใกล้สุด: ({actual_lat:.3f}, {actual_lon:.3f})")
    print(f"   ระยะห่าง: ~{dist_km:.1f} km")

    units = da.attrs.get("units", "unknown")
    print(f"   หน่วย: {units}")

    df = point.to_dataframe(name="precip_mm_day").reset_index()
    df = df.rename(columns={"time": "date"})
    df["precip_mm_day"] = df["precip_mm_day"].replace(-9999, np.nan)

    if units.lower() in ("m", "m/day", "m day-1"):
        df["precip_mm_day"] = df["precip_mm_day"] * 1000.0
        print("   ⚠️  แปลงหน่วย m → mm")

    df["stncode"]     = STATION_CODE
    df["station_lat"] = STATION_LAT
    df["station_lon"] = STATION_LON

    df = df[[
        "stncode", "date",
        "latitude", "longitude",
        "station_lat", "station_lon",
        "precip_mm_day",
    ]]
    df["stncode"] = df["stncode"].astype("int64")
    df["precip_mm_day"] = df["precip_mm_day"].astype("float64")

    return df


# ================================================================
# 2. ตรวจสอบกับ observed ก่อน merge
# ================================================================
def validate_vs_observed(new_df):
    obs_file = "data/observed_precip10sta.csv"
    if not os.path.exists(obs_file):
        print(f"   ⚠️  ไม่พบ {obs_file} — ข้ามการ validate")
        return

    from scipy import stats

    obs = pd.read_csv(obs_file)
    obs.columns = [str(c).strip() for c in obs.columns]
    date_col = obs.columns[0]
    stn_col  = str(STATION_CODE)

    if stn_col not in obs.columns:
        print(f"   ⚠️  ไม่พบคอลัมน์ {stn_col} ใน observed")
        return

    obs_df = obs[[date_col, stn_col]].copy()
    obs_df.columns = ["date", "obs"]
    obs_df["date"] = pd.to_datetime(obs_df["date"],
                                     format="%m/%d/%Y", errors="coerce")
    obs_df = obs_df.dropna()
    obs_df = obs_df[(obs_df["date"].dt.year >= YEAR_START) &
                    (obs_df["date"].dt.year <= YEAR_END)]

    merged = obs_df.merge(new_df[["date", "precip_mm_day"]], on="date",
                          how="inner").dropna()
    if len(merged) < 100:
        print(f"   ⚠️  ข้อมูลไม่พอ")
        return

    r, p = stats.pearsonr(merged["obs"], merged["precip_mm_day"])
    rmse = np.sqrt(np.mean((merged["precip_mm_day"] - merged["obs"]) ** 2))
    bias = merged["precip_mm_day"].mean() - merged["obs"].mean()
    pbias = 100 * bias / merged["obs"].mean()

    print(f"\n📊 Validation vs observed (n = {len(merged):,}):")
    print(f"   Mean obs   = {merged['obs'].mean():.3f} mm/day")
    print(f"   Mean AgERA5 = {merged['precip_mm_day'].mean():.3f} mm/day")
    print(f"   r    = {r:.3f} (p = {p:.2e})")
    print(f"   RMSE = {rmse:.3f} mm/day")
    print(f"   Bias = {bias:+.3f} mm/day ({pbias:+.1f}%)")


# ================================================================
# 3. Merge เข้าไฟล์เดิม
# ================================================================
def merge_into_existing(new_df):
    if not os.path.exists(DAILY_CSV):
        print(f"⚠️  ไม่พบ {DAILY_CSV}")
        new_df.to_csv(BACKUP_CSV, index=False)
        return

    print(f"\n⏳ Merge เข้าไฟล์เดิม ...")
    old = pd.read_csv(DAILY_CSV, parse_dates=["time"])

    if STATION_CODE in old["stncode"].unique():
        print(f"   ⚠️  สถานี {STATION_CODE} มีอยู่แล้ว — แทนที่")
        old = old[old["stncode"] != STATION_CODE]

    new_df_aligned = new_df.rename(columns={"date": "time"})
    combined = pd.concat([old, new_df_aligned], ignore_index=True)
    combined = combined.sort_values(["stncode", "time"]).reset_index(drop=True)

    combined.to_csv(DAILY_CSV, index=False)
    print(f"✅ บันทึก: {DAILY_CSV}")
    print(f"   จำนวนแถว: {len(combined):,}")
    print(f"   จำนวนสถานี: {combined['stncode'].nunique()}")

    new_df.to_csv(BACKUP_CSV, index=False)
    print(f"   สำรอง: {BACKUP_CSV}")


# ================================================================
# Main
# ================================================================
if __name__ == "__main__":
    print("=" * 70)
    print(f"เพิ่มสถานี {STATION_CODE} ({STATION_NAME}) เข้า AgERA5")
    print(f"พิกัด: {STATION_LAT}°N, {STATION_LON}°E")
    print("=" * 70)

    os.makedirs(OUT_DIR, exist_ok=True)

    new_df = fetch_from_arco()
    print(f"\n✅ ดึงสำเร็จ: {len(new_df):,} แถว")
    print(f"   Mean = {new_df['precip_mm_day'].mean():.3f} mm/day")
    print(f"   Max  = {new_df['precip_mm_day'].max():.3f} mm/day")
    print(f"   Missing = {new_df['precip_mm_day'].isna().sum()}")

    validate_vs_observed(new_df)
    merge_into_existing(new_df)

    print("\n💡 ขั้นตอนถัดไป:")
    print("   python stage2_module_e_precip_analysis.py")