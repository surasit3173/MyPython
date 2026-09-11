import pandas as pd
import numpy as np
import glob
import os
from scipy.stats import norm, rankdata

class RainfallTrendAnalyzer:
    """
    เอนจินหลักสำหรับการคำนวณสถิติ MK, MMK และ Sen's Slope
    """
    def __init__(self, data, alpha=0.05):
        # ล้างข้อมูล: ลบ NaN และแปลงเป็น Numpy Array
        self.data = np.array(data, dtype=float)
        self.data = self.data[~np.isnan(self.data)]
        self.n = len(self.data)
        self.alpha = alpha

    def standard_mk(self):
        """คำนวณ Standard Mann-Kendall Test"""
        n = self.n
        x = self.data
        s = 0
        for i in range(n - 1):
            s += np.sum(np.sign(x[i+1:] - x[i]))

        # จัดการค่าซ้ำ (Ties)
        unique_x, counts = np.unique(x, return_counts=True)
        tie_sum = np.sum(counts * (counts - 1) * (2 * counts + 5))
        var_s = (n * (n - 1) * (2 * n + 5) - tie_sum) / 18.0

        # คำนวณ Z-statistic
        if s > 0:
            z = (s - 1) / np.sqrt(var_s)
        elif s < 0:
            z = (s + 1) / np.sqrt(var_s)
        else:
            z = 0
            
        p = 2 * (1 - norm.cdf(abs(z)))
        significant = abs(z) > norm.ppf(1 - self.alpha / 2)
        return {'z': z, 'p': p, 's': s, 'var_s': var_s, 'significant': significant}

    def modified_mk(self):
        """คำนวณ Modified Mann-Kendall (Hamed & Rao, 1998)"""
        base = self.standard_mk()
        s, var_s = base['s'], base['var_s']
        n = self.n
        
        # คำนวณ Autocorrelation ของ Ranks
        ranks = rankdata(self.data)
        rho_sum = 0
        # พิจารณา Lag สูงสุดที่ n-1 หรือจำกัดที่ 10 ตามความเหมาะสมของข้อมูลน้ำฝน
        max_lag = min(n - 1, 10) 
        
        for k in range(1, max_lag + 1):
            r_k = pd.Series(ranks).autocorr(lag=k)
            # ใช้เกณฑ์ความเชื่อมั่น 95% สำหรับค่า Autocorrelation
            if abs(r_k) > (1.96 / np.sqrt(n)):
                rho_sum += (n - k) * r_k
                
        # ปรับค่า Variance Correction Factor
        v_factor = 1 + (2 / n) * rho_sum
        var_s_adj = var_s * v_factor
        
        # คำนวณ Z ใหม่
        if s > 0:
            z_adj = (s - 1) / np.sqrt(var_s_adj)
        elif s < 0:
            z_adj = (s + 1) / np.sqrt(var_s_adj)
        else:
            z_adj = 0
            
        p_adj = 2 * (1 - norm.cdf(abs(z_adj)))
        significant_adj = abs(z_adj) > norm.ppf(1 - self.alpha / 2)
        
        return {'z_adj': z_adj, 'p_adj': p_adj, 'v_factor': v_factor, 'significant': significant_adj}

    def sens_slope(self):
        """คำนวณค่าความชันของ Sen (Sen's Slope)"""
        n = self.n
        x = self.data
        slopes = []
        for i in range(n - 1):
            for j in range(i + 1, n):
                slopes.append((x[j] - x[i]) / (j - i))
        return np.median(slopes)

def process_all_csv(input_dir, output_filename="trend_analysis_summary.csv"):
    """
    ฟังก์ชันสำหรับอ่านและวิเคราะห์ทุกไฟล์ CSV ในโฟลเดอร์
    """
    # ค้นหาไฟล์ .csv ทั้งหมด
    files = glob.glob(os.path.join(input_dir, "*.csv"))
    
    if not files:
        print(f"ไม่พบไฟล์ CSV ในโฟลเดอร์: {input_dir}")
        return

    results_list = []
    print(f"เริ่มการประมวลผลไฟล์จำนวน {len(files)} ไฟล์...")

    for file_path in files:
        file_name = os.path.basename(file_path)
        try:
            # อ่านไฟล์ CSV (ข้ามแถวแรกถ้ามี Header)
            # สามารถปรับเปลี่ยนเป็น pd.read_csv(file_path, names=['rainfall']) หากไม่มี Header
            df = pd.read_csv(file_path) 
            
            # สมมติว่าข้อมูลน้ำฝนอยู่ในคอลัมน์แรกสุด
            # หากต้องการระบุชื่อคอลัมน์ ให้เปลี่ยนเป็น df['ชื่อคอลัมน์']
            rainfall_series = df.iloc[:, 0].values 
            
            # เริ่มการวิเคราะห์
            analyzer = RainfallTrendAnalyzer(rainfall_series)
            mk = analyzer.standard_mk()
            mmk = analyzer.modified_mk()
            slope = analyzer.sens_slope()
            
            # บันทึกผลลัพธ์ของไฟล์นี้
            results_list.append({
                "Station/File": file_name,
                "Sample_Size": analyzer.n,
                "MK_Z-Stat": round(mk['z'], 4),
                "MK_p-Value": round(mk['p'], 4),
                "MK_Significant": mk['significant'],
                "MMK_Z-Stat": round(mmk['z_adj'], 4),
                "MMK_p-Value": round(mmk['p_adj'], 4),
                "MMK_Significant": mmk['significant'],
                "Sen_Slope": round(slope, 4),
                "Trend": "Increasing" if slope > 0 else "Decreasing" if slope < 0 else "No Trend"
            })
            print(f"[OK] วิเคราะห์ไฟล์ {file_name} สำเร็จ")
            
        except Exception as e:
            print(f"[Error] ไม่สามารถวิเคราะห์ไฟล์ {file_name} ได้: {e}")

    # สร้าง DataFrame สรุปผลและบันทึก
    summary_df = pd.DataFrame(results_list)
    summary_df.to_csv(output_filename, index=False, encoding='utf-8-sig')
    print("-" * 50)
    print(f"การประมวลผลเสร็จสมบูรณ์! ผลลัพธ์ถูกบันทึกไว้ใน: {output_filename}")

# --- ส่วนของการรันโปรแกรม ---
if __name__ == "__main__":
    # ใส่ที่อยู่โฟลเดอร์ที่เก็บไฟล์ CSV ของคุณ (เช่น "data/" หรือ "." สำหรับโฟลเดอร์ปัจจุบัน)
    folder_path = "." 
    process_all_csv(folder_path)