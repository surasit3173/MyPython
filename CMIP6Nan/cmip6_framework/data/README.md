# Input data layout

```
data/
├─ observed/     daily rain-gauge CSV:  YEAR, MONTH, DAY, <station ids...>  in mm/day
├─ cmip6_raw/    raw CMIP6 CSV, same layout, filenames starting with pr_day_
│                and containing the model name and historical / sspXXX.
│                Searched recursively, so any folder structure works.
│                Files named bc_*, *bias*, *qdm* or *corrected* are REFUSED:
│                the framework derives its own bias correction from raw output.
└─ gis/          station_coordinates.xlsx with columns station, latitude, longitude.
                 The administrative boundary is downloaded and verified
                 automatically by the gate_f stage; nothing to prepare here.
```

Only the paths in the YAML matter; the directory names above are a convention.
