"""Finalize pipeline state JSON after partial run."""
import sys
import json
import pathlib
import pandas as pd

sys.path.insert(0, 'src')

df_etccdi  = pd.read_csv('output/data/annual_ETCCDI_1961_2019.csv')
df_trend   = pd.read_excel('output/statistics/trend_analysis.xlsx')
df_baseline = pd.read_excel('output/tables/TABLE_02_PERCENTILE_BASELINE.xlsx')

baseline = {
    'p95': float(df_baseline['P95_threshold_mm'].iloc[0]),
    'p99': float(df_baseline['P99_threshold_mm'].iloc[0]),
    'wet_days': int(df_baseline['Wet_days'].iloc[0]),
}

state = {
    'n_years_etccdi': len(df_etccdi),
    'valid_years': 59,
    'indices': list(df_etccdi.columns[1:]),
    'baseline_p95': baseline['p95'],
    'baseline_p99': baseline['p99'],
    'baseline_wet_days': baseline['wet_days'],
    'trend_summary': df_trend[['Index','Sen_slope','p_raw','p_FDR','Trend']].to_dict('records'),
    'n_significant_raw': int((df_trend['p_raw'] < 0.05).sum()),
    'n_significant_fdr': int((df_trend['p_FDR'] < 0.05).sum()),
}

pathlib.Path('output').mkdir(exist_ok=True)
with open('output/pipeline_state.json', 'w') as f:
    json.dump(state, f, indent=2)

print("Pipeline state saved.")
print(f"Significant trends (raw p<0.05): {state['n_significant_raw']}")
print(f"Significant trends (FDR p<0.05): {state['n_significant_fdr']}")
print()
print("TREND RESULTS:")
for rec in state['trend_summary']:
    print(f"  {rec['Index']:8s}: slope={rec['Sen_slope']:+.4f}  p_raw={rec['p_raw']:.4f}  p_FDR={rec['p_FDR']:.4f}  [{rec['Trend']}]")
