"""
QC ตรวจสอบข้อมูล AgERA5 ETo ก่อนเข้าสู่ Stage 2
- ตรวจ dtype, missing, duplicates, outliers
- สรุปสถิติรายสถานี รายปี รายเดือน
- เทียบกับช่วงค่าที่สมเหตุสมผลของ ETo ในภาคอีสาน
"""

import os
import pandas as pd
import numpy as np

DAILY_CSV   = "data/agera5_eto_station_daily_arco.csv"
MONTHLY_CSV = "data/agera5_eto_station_monthly_arco.csv"

# ช่วงค่าที่สมเหตุสมผล (สำหรับ QC เท่านั้น)
DAILY_MIN, DAILY_MAX = 0.0, 12.0    # mm/day
MONTHLY_MIN, MONTHLY_MAX = 50.0, 250.0  # mm/month

# ปีที่คาดหวัง
YEARS = range(1979, 2008)
MONTHS = range(1, 13)


def section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def qc_daily():
    section("1. QC รายวัน (Daily)")
    df = pd.read_csv(DAILY_CSV, parse_dates=["time"])

    print(f"จำนวนแถวทั้งหมด: {len(df):,}")
    print(f"จำนวนสถานี: {df['stncode'].nunique()}")
    print(f"ช่วงวันที่: {df['time'].min().date()} ถึง {df['time'].max().date()}")
    print(f"dtype ของ stncode: {df['stncode'].dtype}")

    # คาดหวังจำนวนแถว
    n_sta = df["stncode"].nunique()
    n_days = (df["time"].max() - df["time"].min()).days + 1
    expected = n_sta * n_days
    print(f"คาดหวัง: {expected:,} แถว | มีจริง: {len(df):,} | ต่าง: {len(df) - expected:+,}")

    # Missing
    n_miss = df["eto_mm_day"].isna().sum()
    print(f"\nMissing (NaN): {n_miss} ({100*n_miss/len(df):.3f}%)")

    # Duplicates
    dup = df.duplicated(subset=["stncode", "time"]).sum()
    print(f"Duplicates (stncode, time): {dup}")

    # Outliers
    n_below = (df["eto_mm_day"] < DAILY_MIN).sum()
    n_above = (df["eto_mm_day"] > DAILY_MAX).sum()
    print(f"\nค่าผิดปกติ:")
    print(f"  < {DAILY_MIN} mm/day: {n_below}")
    print(f"  > {DAILY_MAX} mm/day: {n_above}")

    # สถิติรวม
    print(f"\nสถิติ ETo รายวัน (mm/day):")
    print(df["eto_mm_day"].describe().round(3))

    # สถิติรายสถานี
    print(f"\nสถิติรายสถานี (mean ± std, mm/day):")
    stat = df.groupby("stncode")["eto_mm_day"].agg(["mean", "std", "min", "max"])
    print(stat.round(3))

    # ความครบถ้วนรายปี
    df["year"] = df["time"].dt.year
    yearly = df.groupby(["stncode", "year"]).size().unstack(fill_value=0)
    print(f"\nความครบถ้วนรายปี (จำนวนวัน):")
    print(f"  min: {yearly.values.min()}")
    print(f"  max: {yearly.values.max()}")
    print(f"  ปีที่ < 365 วัน: {(yearly < 365).sum().sum()} เคส")

    return df


def qc_monthly():
    section("2. QC รายเดือน (Monthly)")
    df = pd.read_csv(MONTHLY_CSV, parse_dates=["date"])

    print(f"จำนวนแถวทั้งหมด: {len(df):,}")
    print(f"จำนวนสถานี: {df['stncode'].nunique()}")
    print(f"ช่วงเวลา: {df['date'].min().date()} ถึง {df['date'].max().date()}")
    print(f"dtype ของ stncode: {df['stncode'].dtype}")

    # คาดหวัง
    n_sta = df["stncode"].nunique()
    expected = n_sta * 29 * 12
    print(f"คาดหวัง: {expected:,} แถว | มีจริง: {len(df):,} | ต่าง: {len(df) - expected:+,}")

    # Missing
    n_miss = df["eto_mm_month"].isna().sum()
    print(f"\nMissing (NaN): {n_miss}")

    # Duplicates
    dup = df.duplicated(subset=["stncode", "year", "month"]).sum()
    print(f"Duplicates (stncode, year, month): {dup}")

    # Outliers
    n_below = (df["eto_mm_month"] < MONTHLY_MIN).sum()
    n_above = (df["eto_mm_month"] > MONTHLY_MAX).sum()
    print(f"\nค่าผิดปกติ:")
    print(f"  < {MONTHLY_MIN} mm/month: {n_below}")
    print(f"  > {MONTHLY_MAX} mm/month: {n_above}")

    # สถิติรวม
    print(f"\nสถิติ ETo รายเดือน (mm/month):")
    print(df["eto_mm_month"].describe().round(2))

    # สถิติรายสถานี
    print(f"\nสถิติรายสถานี (mean ± std, mm/month):")
    stat = df.groupby("stncode")["eto_mm_month"].agg(["mean", "std", "min", "max"])
    print(stat.round(2))

    # ค่าเฉลี่ยรายเดือน (climatology)
    print(f"\nค่าเฉลี่ย ETo รายเดือน (climatology, mm/month):")
    clim = df.groupby("month")["eto_mm_month"].mean().round(2)
    print(clim)

    # เปรียบเทียบผลรวมรายเดือน vs ผลรวมรายวัน
    return df


def cross_check(df_daily, df_monthly):
    section("3. Cross-check: ผลรวมรายวัน vs ค่ารายเดือน")
    df_daily["year"]  = df_daily["time"].dt.year
    df_daily["month"] = df_daily["time"].dt.month

    daily_sum = (
        df_daily.groupby(["stncode", "year", "month"])
        .agg(eto_from_daily=("eto_mm_day", "sum"),
             n_days=("eto_mm_day", "count"))
        .reset_index()
    )
    daily_sum = daily_sum[daily_sum["n_days"] >= 25].drop(columns="n_days")

    merged = daily_sum.merge(
        df_monthly[["stncode", "year", "month", "eto_mm_month"]],
        on=["stncode", "year", "month"],
        how="inner",
    )
    merged["diff"] = merged["eto_from_daily"] - merged["eto_mm_month"]
    merged["pct_diff"] = 100 * merged["diff"] / merged["eto_mm_month"]

    print(f"จำนวนเดือนที่เทียบได้: {len(merged)}")
    print(f"ค่า |diff| สูงสุด: {merged['diff'].abs().max():.6f} mm")
    print(f"ค่า |pct_diff| สูงสุด: {merged['pct_diff'].abs().max():.6f} %")
    print(f"ค่า |pct_diff| เฉลี่ย: {merged['pct_diff'].abs().mean():.6f} %")
    print("\n→ ถ้าค่าต่าง ≈ 0 แสดงว่ากระบวนการ aggregate ถูกต้อง")


def main():
    print("\n" + "=" * 70)
    print("QC Report: AgERA5 ETo 15 stations, 1979–2007")
    print("=" * 70)

    df_daily = qc_daily()
    df_monthly = qc_monthly()
    cross_check(df_daily, df_monthly)

    section("สรุป")
    print("✅ ถ้าทุกส่วนผ่าน (no missing, no duplicate, no outlier)")
    print("   → ข้อมูลพร้อมสำหรับ Stage 2 Analysis")
    print("\n📁 ไฟล์ที่ได้:")
    print(f"   - {os.path.abspath(DAILY_CSV)}")
    print(f"   - {os.path.abspath(MONTHLY_CSV)}")


if __name__ == "__main__":
    main()