"""
แก้คอลัมน์ stncode จาก float เป็น int ในไฟล์ CSV ของ AgERA5 ARCO

Usage:
    python fix_stncode.py
"""

import os
import pandas as pd

# ---------- ตั้งค่า ----------
DATA_DIR = "data"
FILES = [
    "agera5_eto_station_daily_arco.csv",
    "agera5_eto_station_monthly_arco.csv",
]

# คอลัมน์ที่ต้องแปลงเป็น int
INT_COLS = ["stncode"]


def fix_csv(path, int_cols=INT_COLS):
    """อ่าน CSV, แปลงคอลัมน์ที่ระบุเป็น int, บันทึกทับ"""
    if not os.path.exists(path):
        print(f"⚠️  ไม่พบไฟล์: {path} (ข้าม)")
        return None

    print(f"⏳ กำลังแก้ไข: {path}")
    df = pd.read_csv(path)

    # บันทึกค่าเดิมไว้เทียบ
    before = df[int_cols[0]].dtype
    print(f"   ก่อนแก้: dtype = {before}")
    print(f"   ตัวอย่าง: {df[int_cols[0]].head(3).tolist()}")

    # แปลงเป็น int (ปัดเศษก่อนกันปัญหาทศนิยมเพี้ยน)
    for col in int_cols:
        if col in df.columns:
            # เก็บ NaN ไว้ถ้ามี
            mask = df[col].notna()
            df.loc[mask, col] = df.loc[mask, col].round().astype(int)
            # ถ้าคอลัมน์ไม่มี NaN จริง ๆ ให้เป็น int ทั้งคอลัมน์
            if df[col].isna().sum() == 0:
                df[col] = df[col].astype(int)

    after = df[int_cols[0]].dtype
    print(f"   หลังแก้: dtype = {after}")
    print(f"   ตัวอย่าง: {df[int_cols[0]].head(3).tolist()}")

    # บันทึกทับ (ไม่เก็บ index)
    df.to_csv(path, index=False)
    print(f"   ✅ บันทึกแล้ว ({len(df)} แถว)\n")

    return df


def main():
    print("=" * 60)
    print("Fix stncode: float → int")
    print("=" * 60 + "\n")

    for fname in FILES:
        path = os.path.join(DATA_DIR, fname)
        fix_csv(path)

    print("=" * 60)
    print("เสร็จสิ้น")
    print("=" * 60)


if __name__ == "__main__":
    main()