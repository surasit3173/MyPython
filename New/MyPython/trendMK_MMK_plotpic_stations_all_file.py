import pandas as pd
import numpy as np
import glob
import os
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import norm, rankdata

# --- [1] Engine การวิเคราะห์สถิติ ---
class RainfallTrendAnalyzer:
    def __init__(self, data, alpha=0.05):
        self.data = np.array(data, dtype=float)
        self.data = self.data[~np.isnan(self.data)]
        self.n = len(self.data)
        self.alpha = alpha

    def standard_mk(self):
        n, x = self.n, self.data
        s = 0
        for i in range(n - 1):
            s += np.sum(np.sign(x[i+1:] - x[i]))
        unique_x, counts = np.unique(x, return_counts=True)
        tie_sum = np.sum(counts * (counts - 1) * (2 * counts + 5))
        var_s = (n * (n - 1) * (2 * n + 5) - tie_sum) / 18.0
        z = (s - np.sign(s)) / np.sqrt(var_s) if s != 0 else 0
        p = 2 * (1 - norm.cdf(abs(z)))
        return {'z': z, 'p': p, 'significant': abs(z) > norm.ppf(1 - self.alpha/2)}

    def modified_mk(self):
        base = self.standard_mk()
        n, x, s, var_s = self.n, self.data, 0, (self.n*(self.n-1)*(2*self.n+5))/18.0
        for i in range(n-1): s += np.sum(np.sign(x[i+1:] - x[i]))
        
        ranks = rankdata(x)
        rho_sum = 0
        for k in range(1, min(n - 1, 10)):
            r_k = pd.Series(ranks).autocorr(lag=k)
            if abs(r_k) > (1.96 / np.sqrt(n)):
                rho_sum += (n - k) * r_k
        
        v_factor = 1 + (2 / n) * rho_sum
        var_s_adj = var_s * v_factor
        z_adj = (s - np.sign(s)) / np.sqrt(var_s_adj) if s != 0 else 0
        p_adj = 2 * (1 - norm.cdf(abs(z_adj)))
        return {'z_adj': z_adj, 'p_adj': p_adj, 'significant': abs(z_adj) > norm.ppf(1 - self.alpha/2)}

    def sens_slope(self):
        n, x = self.n, self.data
        slopes = [ (x[j] - x[i]) / (j - i) for i in range(n) for j in range(i+1, n) ]
        return np.median(slopes)

# --- [2] ฟังก์ชันสำหรับการสร้างกราฟ ---
def generate_summary_plots(df):
    """สร้างกราฟสรุปผลการวิเคราะห์จากตารางรวม"""
    plt.style.use('seaborn-v0_8-muted')
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    plt.subplots_adjust(hspace=0.4, wspace=0.3)

    # กราฟ 1: เปรียบเทียบ Z-Statistic (MK vs MMK)
    df_melted = df.melt(id_vars='Station', value_vars=['MK_Z', 'MMK_Z'], var_name='Method', value_name='Z-Stat')
    sns.barplot(data=df_melted, x='Station', y='Z-Stat', hue='Method', ax=axes[0,0])
    axes[0,0].axhline(1.96, color='red', linestyle='--', alpha=0.5, label='Significant (95%)')
    axes[0,0].axhline(-1.96, color='red', linestyle='--', alpha=0.5)
    axes[0,0].set_title("Comparison of Z-Statistics (MK vs MMK)")
    axes[0,0].tick_params(axis='x', rotation=45)

    # กราฟ 2: การกระจายของสถานะแนวโน้ม (Pie Chart)
    trend_counts = df['Trend_Status'].value_counts()
    axes[0,1].pie(trend_counts, labels=trend_counts.index, autopct='%1.1f%%', startangle=140, colors=['#66b3ff','#99ff99','#ff9999'])
    axes[0,1].set_title("Distribution of Rainfall Trends (Based on MMK)")

    # กราฟ 3: Sen's Slope Value (Magnitude of Change)
    sns.barplot(data=df, x='Station', y='Sen_Slope', palette='viridis', ax=axes[1,0])
    axes[1,0].set_title("Sen's Slope Magnitude (Change per Unit Time)")
    axes[1,0].tick_params(axis='x', rotation=45)
    axes[1,0].set_ylabel("Slope Value (mm/unit)")

    # กราฟ 4: ตารางสรุปจำนวน Significant
    axes[1,1].axis('off')
    summary_text = f"Total Stations: {len(df)}\n" \
                   f"Significant MK: {df['MK_Sig'].sum()}\n" \
                   f"Significant MMK: {df['MMK_Sig'].sum()}"
    axes[1,1].text(0.5, 0.5, summary_text, fontsize=15, ha='center', va='center', 
                   bbox=dict(facecolor='white', alpha=0.5))
    axes[1,1].set_title("Analysis Summary Statistics")

    plt.savefig("trend_analysis_visuals.png", dpi=300, bbox_inches='tight')
    plt.show()

# --- [3] ส่วนประมวลผลหลัก (Batch Process) ---
def run_full_pipeline(folder_path="."):
    files = glob.glob(os.path.join(folder_path, "*.csv"))
    if not files: return print("ไม่พบไฟล์ CSV")

    all_data = []
    for f in files:
        station_name = os.path.basename(f).replace('.csv', '')
        # อ่านข้อมูล (สมมติว่าคอลัมน์แรกคือปริมาณน้ำฝน)
        df_raw = pd.read_csv(f)
        data = df_raw.iloc[:, 0].values
        
        analyzer = RainfallTrendAnalyzer(data)
        mk, mmk, slope = analyzer.standard_mk(), analyzer.modified_mk(), analyzer.sens_slope()
        
        # ตัดสินใจสถานะแนวโน้ม (ใช้ MMK เป็นหลัก)
        status = "Increasing" if mmk['significant'] and slope > 0 else \
                 "Decreasing" if mmk['significant'] and slope < 0 else "No Trend"

        all_data.append({
            'Station': station_name, 'MK_Z': mk['z'], 'MMK_Z': mmk['z_adj'],
            'MK_Sig': mk['significant'], 'MMK_Sig': mmk['significant'],
            'Sen_Slope': slope, 'Trend_Status': status
        })
        print(f"วิเคราะห์สำเร็จ: {station_name}")

    summary_df = pd.DataFrame(all_data)
    summary_df.to_csv("analysis_summary.csv", index=False)
    generate_summary_plots(summary_df)

if __name__ == "__main__":
    run_full_pipeline(".") # ใส่โฟลเดอร์ที่เก็บ CSV