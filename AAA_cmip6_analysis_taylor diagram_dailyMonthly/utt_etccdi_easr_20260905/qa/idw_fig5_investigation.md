# Figure 5 IDW investigation

## Symptom

The northern part of the Uttaradit polygon, approximately north of 18.3 degrees N, was white in both Figure 5 panels even though it was inside the drawn province boundary.

## Reproduction

The focused diagnostic used the supplied station coordinates, the supplied Uttaradit boundary shapefile, and the existing `idw_grid` call.

- Station latitude bounds: 17.23 to 18.02 degrees N.
- Province boundary latitude bounds: 17.163948 to 18.381645 degrees N.
- Existing IDW grid latitude bounds with `padding=0.30`: 16.993 to 18.257 degrees N.
- Therefore the polygon area from about 18.257 to 18.382 degrees N had no IDW grid cells before masking.

## Verified cause

`idw_grid` derived its grid extent from station coordinates only. The later polygon mask could remove cells outside the province, but it could not create cells in the northern polygon area that the station-bounded grid never generated. The symptom was a grid-extent omission, not missing station values, zero values, or an incorrect polygon mask.

## Fix and regression coverage

`idw_grid` now accepts an optional finite `(lon_min, lon_max, lat_min, lat_max)` extent. Figure 5 and the production IDW map pass the full boundary extent, with a small outside buffer, before applying the polygon mask. The regression test `test_idw_grid_can_cover_supplied_boundary_extent` verifies that a supplied northern extent is represented in the grid. The manuscript Methods and Figure 5 caption identify the northern area beyond the station convex hull as extrapolation and not station-supported detail.
