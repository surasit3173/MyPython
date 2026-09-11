from pathlib import Path

import pandas as pd


workbook = Path(r"C:\Users\PC\Downloads\evaluation_results.xlsx")
for sheet in ["E02_primary_station_metrics", "E03_MME_monthly", "E06_station_tiers"]:
    df = pd.read_excel(workbook, sheet)
    print(sheet)
    print(list(df.columns))
    print(df.head(3).to_string(index=False))
    print()
