# Map Data Provenance & GIS Source Documentation: Uttaradit

## 1. Study Area Boundary
- **Source**: Natural Earth Vector Data / Administrative Level 1 (Provinces of Thailand).
- **Format**: GeoJSON (`thailand_regional_adm1.geojson`).
- **Feature Filter**: `NAME_1 == 'Uttaradit'` / `adm1_code == 'THA-1845'`.
- **Coordinate Reference System (CRS)**: WGS 84 (EPSG:4326).
- **Polygon Bounds**: Longitude 99.897°E to 101.165°E, Latitude 17.164°N to 18.372°N.
- **License**: Public Domain (Creative Commons Zero / Natural Earth free vector map data).

## 2. Elevation & Topographic Shading
- **Source**: Natural Earth physical relief & provincial bounds.
- **Station Elevations**: Authoritative station metadata reported by Thai Meteorological Department (TMD), ranging from 54.57 m MSL (lowland river plains) to 427.85 m MSL (mountainous highlands).

## 3. Station Coordinates & Attribution
- **Authority**: Thai Meteorological Department (TMD).
- **Stations**: 13 rainfall stations (`351001` to `351012`, `351201`).
- **Temporal Period**: Authoritative baseline 1995–2014 (20 complete calendar years).
- **Quality Control**: Primary observational records audited with 0% missing data and no artificial synthetic fill.

## 4. Interpolation Surface
- **Method**: 2D Inverse Distance Weighting (IDW) interpolation.
- **Power Parameter ($p$)**: 2.0.
- **Grid Resolution**: 0.005° (~500 m).
- **Masking**: Strictly clipped to the authoritative Uttaradit provincial boundary polygon.
- **Validation**: Leave-One-Out Cross-Validation (LOOCV) documented in `IDW_parameters.txt`.
