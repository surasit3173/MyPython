"""
ดึง AgERA5 (ETo + Precip) สำหรับทุกสถานีจากพิกัดจริง
ใช้ ARCO Zarr store โดยตรง — ไม่ map ไม่ใช้ station อื่น

Stations: 16 (15 ต้นฉบับ + 354201 Udon Thani)
Output:
  - data/agera5_eto_all_stations_daily.csv
  - data/agera5_precip_all_stations_daily.csv
  - data/station_grid_report.csv  (ระยะห่างจาก grid ที่ใกล้สุด)
"""

import os
import sys
import numpy as np
import pandas as pd
import xarray as xr

# ================================================================
# ตั้งค่า
# ================================================================
CDS_API_KEY = os.environ.get("CDSAPI_KEY", "").strip()
if not CDS_API_KEY:
    CDS_API_KEY = "2098ba38-a22b-4374-8ed9-22ed6e78c81d"   # ← hardcode
GEO_URL = (
    "https://arco.datastores.ecmwf.int/cadl-arco-geo-001/arco/"
    "sis_agrometeorological_indicators/all/geoChunked.zarr"
)

ETO_VAR    = "ReferenceET_PenmanMonteith_FAO56"
PRECIP_VAR = "Precipitation_Flux"

YEAR_START = 1979
YEAR_END   = 2007

OUT_DIR     = "data"
ETO_OUT     = os.path.join(OUT_DIR, "agera5_eto_all_stations_daily.csv")
PRECIP_OUT  = os.path.join(OUT_DIR, "agera5_precip_all_stations_daily.csv")
REPORT_OUT  = os.path.join(OUT_DIR, "station_grid_report.csv")

# ================================================================
# ✅ 16 สถานี พร้อมพิกัดจริง (จาก TMD)
# ================================================================
STATIONS = {
    # stncode: (name, lat, lon)
    352201: ("Nong Khai",         17.863, 102.752),
    353201: ("Loei",              17.448, 101.732),
    354201: ("Udon Thani",        17.383, 102.800),  # ← 17°23'00"N, 102°48'00"E
    356201: ("Sakon Nakhon",      17.151, 104.137),
    357201: ("Nakhon Phanom",     17.410, 104.782),
    381201: ("Khon Kaen",         16.457, 102.790),
    383201: ("Mukdahan",          16.542, 104.729),
    387401: ("Kosum Phisai",      16.241, 103.070),
    403201: ("Chaiyaphum",        15.807, 102.030),
    405201: ("Roi Et",            16.052, 103.664),
    407501: ("Ubon Ratchathani",  15.242, 104.876),
    431201: ("Nakhon Ratchasima", 14.963, 102.087),
    431401: ("Chok Chai",         14.733, 102.170),
    432201: ("Surin",             14.872, 103.500),
    432401: ("Tha Tum",           15.315, 103.681),
    436401: ("Nang Rong",         14.627, 102.723),
}


def _get_cds_key():
    """อ่าน token: hardcode → env var → .cdsapirc"""
    # 1. ✅ ใช้ CDS_API_KEY ที่ประกาศไว้บนสุดก่อน (รวม hardcode)
    if CDS_API_KEY:
        return CDS_API_KEY

    # 2. env var
    key = os.environ.get("CDSAPI_KEY", "").strip()
    if key:
        return key

    # 3. .cdsapirc
    for path in [os.path.join(os.path.expanduser("~"), ".cdsapirc"),
                 os.path.join(os.environ.get("USERPROFILE", ""), ".cdsapirc")]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("key:"):
                        return line.split(":", 1)[1].strip()
    return ""

# ================================================================
# 1. เปิด ARCO store
# ================================================================
def open_arco():
    print("⏳ กำลังเปิด ARCO Zarr store ...")
    key = _get_cds_key()
    if not key:
        print("⚠️  ไม่พบ CDS API key")
        print("   ตั้ง env var: setx CDSAPI_KEY \"your-token\"")
        sys.exit(1)

    storage_options = {"headers": {"Authorization": f"Bearer {key}"}}
    ds = xr.open_zarr(GEO_URL, storage_options=storage_options,
                       consolidated=True)
    print(f"✅ เปิดสำเร็จ")
    print(f"   ตัวแปร: ETo = {ETO_VAR}")
    print(f"          Precip = {PRECIP_VAR}")
    print(f"   พิกัด: {list(ds.coords)}")
    print(f"   มิติเวลา: {ds.time.min().values} ถึง {ds.time.max().values}")
    return ds


# ================================================================
# 2. ดึงข้อมูล 1 ตัวแปร ณ พิกัดเดียว
# ================================================================
def extract_point(ds, var_name, lat, lon):
    """ดึง time series ที่จุดใกล้สุดจากพิกัด"""
    da = ds[var_name].sel(
        time=slice(f"{YEAR_START}-01-01", f"{YEAR_END}-12-31"))

    # ใช้ nearest
    point = da.sel(latitude=lat, longitude=lon, method="nearest")

    # ดึงพิกัด grid จริงที่ถูกใช้
    grid_lat = float(point.latitude.values)
    grid_lon = float(point.longitude.values)

    # คำนวณระยะห่าง (haversine approx.)
    dlat = (grid_lat - lat) * 111.0
    dlon = (grid_lon - lon) * 111.0 * np.cos(np.deg2rad(lat))
    dist_km = np.sqrt(dlat**2 + dlon**2)

    # แปลงเป็น DataFrame
    df = point.to_dataframe(name=var_name).reset_index()
    df = df.rename(columns={"time": "date"})

    # ตรวจหน่วย
    units = da.attrs.get("units", "").lower()
    if units in ("m", "m/day", "m day-1"):
        df[var_name] = df[var_name] * 1000.0

    # แทน missing
    df[var_name] = df[var_name].replace(-9999, np.nan)

    df["latitude"]  = grid_lat
    df["longitude"] = grid_lon

    return df, grid_lat, grid_lon, dist_km


# ================================================================
# 3. ดึงทุกสถานี
# ================================================================
def fetch_all(ds):
    eto_all     = []
    precip_all  = []
    report      = []

    print(f"\n⏳ ดึงข้อมูลสำหรับ {len(STATIONS)} สถานี ...\n")

    # Header
    print(f"   {'stncode':<8s} {'station':<20s} "
          f"{'grid_lat':>9s} {'grid_lon':>9s} {'dist (km)':>10s}")
    print(f"   {'-'*8} {'-'*20} {'-'*9} {'-'*9} {'-'*10}")

    for stncode, (name, lat, lon) in STATIONS.items():
        # ETo
        eto_df, glat, glon, dist = extract_point(
            ds, ETO_VAR, lat, lon)
        eto_df["stncode"] = stncode
        eto_df["station"] = name
        eto_df["station_lat"] = lat
        eto_df["station_lon"] = lon

        # Precip (จุดเดียวกัน)
        prec_df, _, _, _ = extract_point(ds, PRECIP_VAR, lat, lon)
        prec_df["stncode"] = stncode
        prec_df["station"] = name
        prec_df["station_lat"] = lat
        prec_df["station_lon"] = lon

        eto_all.append(eto_df)
        precip_all.append(prec_df)

        report.append({
            "stncode": stncode,
            "station": name,
            "station_lat": lat,
            "station_lon": lon,
            "grid_lat": glat,
            "grid_lon": glon,
            "dist_km": dist,
        })

        print(f"   {stncode:<8d} {name:<20s} "
              f"{glat:>9.3f} {glon:>9.3f} {dist:>10.2f}")

    # Combine
    eto_df_all = pd.concat(eto_all, ignore_index=True)
    prec_df_all = pd.concat(precip_all, ignore_index=True)
    report_df = pd.DataFrame(report)

    return eto_df_all, prec_df_all, report_df


# ================================================================
# 4. Reformat ให้เข้ากับ schema เดิม
# ================================================================
def reformat(eto_df, prec_df):
    # ETo
    eto_df = eto_df.rename(columns={ETO_VAR: "eto_mm_day"})
    eto_df = eto_df[[
        "stncode", "station", "date",
        "latitude", "longitude",
        "station_lat", "station_lon",
        "eto_mm_day",
    ]]
    eto_df = eto_df.sort_values(["stncode", "date"]).reset_index(drop=True)

    # Precip
    prec_df = prec_df.rename(columns={PRECIP_VAR: "precip_mm_day"})
    prec_df = prec_df[[
        "stncode", "station", "date",
        "latitude", "longitude",
        "station_lat", "station_lon",
        "precip_mm_day",
    ]]
    prec_df = prec_df.sort_values(["stncode", "date"]).reset_index(drop=True)

    return eto_df, prec_df


# ================================================================
# Main
# ================================================================
if __name__ == "__main__":
    print("=" * 70)
    print("ดึง AgERA5 (ETo + Precip) สำหรับ 16 สถานี จากพิกัดจริง")
    print("=" * 70)

    os.makedirs(OUT_DIR, exist_ok=True)

    # 1. เปิด store
    ds = open_arco()

    # 2. ดึงทุกสถานี
    eto_df, prec_df, report_df = fetch_all(ds)

    # 3. Reformat
    eto_df, prec_df = reformat(eto_df, prec_df)

    # 4. บันทึก
    print(f"\n💾 บันทึก ...")
    eto_df.to_csv(ETO_OUT, index=False)
    print(f"   ✅ {ETO_OUT}")
    print(f"      {len(eto_df):,} rows | {eto_df['stncode'].nunique()} stations")

    prec_df.to_csv(PRECIP_OUT, index=False)
    print(f"   ✅ {PRECIP_OUT}")
    print(f"      {len(prec_df):,} rows | {prec_df['stncode'].nunique()} stations")

    report_df.to_csv(REPORT_OUT, index=False, float_format="%.3f")
    print(f"   ✅ {REPORT_OUT}")

    # 5. สรุป
    print(f"\n📊 สรุป:")
    print(f"   Mean dist to grid: {report_df['dist_km'].mean():.2f} km")
    print(f"   Max dist:          {report_df['dist_km'].max():.2f} km "
          f"({report_df.loc[report_df['dist_km'].idxmax(), 'station']})")
    print(f"   Min dist:          {report_df['dist_km'].min():.2f} km")

    print(f"\n   ETo:")
    print(f"      Mean    = {eto_df['eto_mm_day'].mean():.3f} mm/day")
    print(f"      Range   = [{eto_df['eto_mm_day'].min():.3f}, "
          f"{eto_df['eto_mm_day'].max():.3f}]")
    print(f"      Missing = {eto_df['eto_mm_day'].isna().sum()}")

    print(f"\n   Precip:")
    print(f"      Mean    = {prec_df['precip_mm_day'].mean():.3f} mm/day")
    print(f"      Range   = [{prec_df['precip_mm_day'].min():.3f}, "
          f"{prec_df['precip_mm_day'].max():.3f}]")
    print(f"      Missing = {prec_df['precip_mm_day'].isna().sum()}")

    print("=" * 70)
    print("💡 ขั้นตอนถัดไป:")
    print("   ตรวจสอบ station_grid_report.csv ว่าทุกสถานี dist < 8 km")
    print("=" * 70)