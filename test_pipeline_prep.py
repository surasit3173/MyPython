import pandas as pd
import numpy as np

csv_path = 'data/raw/Observed_Rain_daily_196101_202010_TMD10_raw_Markovchaindataset.csv'
df = pd.read_csv(csv_path)

print("Columns:", df.columns.tolist())
print("Shape:", df.shape)

# Check Date construction
df['DATE'] = pd.to_datetime(df[['YEAR', 'MONTH', 'DAY']])
print("Date min:", df['DATE'].min(), "Date max:", df['DATE'].max())
print("Total days in date range:", (df['DATE'].max() - df['DATE'].min()).days + 1)
print("Is continuous calendar?", len(df) == (df['DATE'].max() - df['DATE'].min()).days + 1)

# Check stations
stations = ['353201', '354201', '356201', '357201', '381201', '403201', '405201', '407501', '431201', '432201']
for st in stations:
    col = df[st]
    print(f"Station {st}: nulls={col.isnull().sum()}, min={col.min()}, max={col.max()}, non-numeric={col.apply(lambda x: not isinstance(x, (int, float, np.number))).sum()}")
