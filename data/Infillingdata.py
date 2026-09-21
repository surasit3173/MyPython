import os
import numpy as np
import pandas as pd

def complete_daily_rainfall_dataset(
    raw_csv_path: str,
    output_csv_path: str,
    log_csv_path: str,
    start_date: str = "1961-01-01",
    end_date: str = "2020-12-31"
):
    """
    Standardizes and imputes daily precipitation series for TMD stations.
    
    Parameters
    ----------
    raw_csv_path : str
        Path to the source raw dataset.
    output_csv_path : str
        Path to save the completed and imputed dataset.
    log_csv_path : str
        Path to save station-by-station missing and imputed statistics.
    start_date : str
        Beginning date of the complete climatological series (YYYY-MM-DD).
    end_date : str
        Ending date of the complete climatological series (YYYY-MM-DD).
    """
    print(f"Reading source data from: {raw_csv_path}")
    df = pd.read_csv(raw_csv_path)

    # Standardize date column identifier
    date_col = [c for c in df.columns if c.lower() in ["date", "datetime", "time", "day"]]
    if date_col:
        df["Date"] = pd.to_datetime(df[date_col[0]])
        df = df.set_index("Date")
        if date_col[0] != "Date":
            df = df.drop(columns=[date_col[0]])
    else:
        # Fallback: assume first column represents dates
        df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])
        df = df.set_index(df.columns[0])

    station_cols = [c for c in df.columns if df[c].dtype in [np.float64, np.int64, float, int]]
    print(f"Detected {len(station_cols)} rainfall station columns: {station_cols}")

    # Construct the complete target daily index (1961-01-01 to 2020-12-31)
    full_index = pd.date_range(start=start_date, end=end_date, freq="D")
    df_reindexed = df.reindex(full_index)
    df_reindexed.index.name = "Date"

    # Compute missing data summary before imputation
    audit_records = []
    for stn in station_cols:
        raw_count = df[stn].count() if stn in df.columns else 0
        missing_count = df_reindexed[stn].isna().sum()
        pct_missing = (missing_count / len(full_index)) * 100.0
        audit_records.append({
            "Station": stn,
            "Total_Days": len(full_index),
            "Observed_Days": raw_count,
            "Missing_Days": missing_count,
            "Missing_Percentage": round(pct_missing, 2)
        })

    audit_df = pd.DataFrame(audit_records)
    print("\n--- Missing Data Summary (Prior to Imputation) ---")
    print(audit_df.to_string(index=False))

    # Calculate long-term monthly precipitation averages for Normal Ratio scaling
    df_imputed = df_reindexed.copy()
    monthly_means = df_imputed[station_cols].groupby(df_imputed.index.month).mean()

    # Step 1: Normal Ratio Method across concurrent stations
    for target_stn in station_cols:
        target_series = df_imputed[target_stn]
        missing_mask = target_series.isna()

        donor_stns = [s for s in station_cols if s != target_stn]

        for date_val in df_imputed.index[missing_mask]:
            m = date_val.month
            Nx = monthly_means.loc[m, target_stn]
            
            # Find available donor observations on this date
            valid_donors = [d for d in donor_stns if not np.isnan(df_imputed.loc[date_val, d])]
            
            if len(valid_donors) >= 2 and Nx > 0:
                weights = []
                ratios = []
                for d in valid_donors:
                    Ni = monthly_means.loc[m, d]
                    if Ni > 0:
                        Pi = df_imputed.loc[date_val, d]
                        ratios.append((Nx / Ni) * Pi)
                        weights.append(1.0)

                if ratios:
                    estimated_val = np.average(ratios, weights=weights)
                    df_imputed.loc[date_val, target_stn] = max(0.0, round(float(estimated_val), 1))

    # Step 2: Fallback for days with zero gauge donors (e.g., Nov–Dec 2020 tail)
    remaining_missing = df_imputed[station_cols].isna().sum().sum()
    if remaining_missing > 0:
        print(f"\nRemaining unassigned daily records ({remaining_missing} total entries).")
        print("Note: If November–December 2020 data were unrecorded across all stations,")
        print("they should be populated using external TMD station records, CHIRPS v2.0,")
        print("or calibrated ERA5-Land reanalysis.")

    # Write results
    df_imputed.to_csv(output_csv_path)
    audit_df.to_csv(log_csv_path, index=False)

    print(f"\nCompleted series written to: {output_csv_path}")
    print(f"Audit log written to: {log_csv_path}")

if __name__ == "__main__":
    raw_path = "Observed_Rain_daily_196101_202010_TMD10_raw_Markovchaindataset.csv"
    out_path = "Observed_Rain_daily_196101_202012_TMD10_imputed_Markovchaindataset.csv"
    log_path = "Rainfall_Imputation_Audit_1961_2020.csv"

    if os.path.exists(raw_path):
        complete_daily_rainfall_dataset(raw_path, out_path, log_path)
    else:
        print(f"File not found: {raw_path}. Verify current working directory.")