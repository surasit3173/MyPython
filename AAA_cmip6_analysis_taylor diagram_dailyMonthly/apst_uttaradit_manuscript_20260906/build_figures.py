"""Build APST-ready Uttaradit figures from the validated result tables.

The maps are deliberately labelled as station-referenced IDW depictions. They
are not gridded climate-model output and are masked to the province polygon.
Station markers are shown without connecting lines so that no station is
visually treated as a special case.
"""
from __future__ import annotations

import math
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap, TwoSlopeNorm
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Polygon as MplPolygon
from matplotlib.path import Path as MplPath
import numpy as np
import pandas as pd
import shapefile


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent / "utt_etccdi_easr_20260905"
PRIMARY = PROJECT / "outputs" / "full_with_figures" / "results"
BOUNDARY = Path(r"C:\MyPython\CMIP6Uttaradit\Data_Uttaradit\75 pbound.shp")
ATTACHED_FIG1 = Path(r"C:\MyPython\CMIP6Uttaradit\Uttaradit.png")
FIGDIR = HERE / "figures"
FIGDIR.mkdir(parents=True, exist_ok=True)

INDICES = ["PRCPTOT", "SDII", "Rx1day", "Rx5day", "CDD", "CWD", "R10mm", "R20mm", "R50mm", "R95p", "R99p"]
SCENARIOS = ["SSP2-4.5", "SSP5-8.5"]
MODEL_ORDER = ["ACCESS-ESM1-5", "CanESM5", "CESM2", "EC-Earth3", "FGOALS-g3", "MIROC6", "MRI-ESM2-0"]


def load_boundary(path: Path) -> list[np.ndarray]:
    reader = shapefile.Reader(str(path), encoding="cp874")
    rings: list[np.ndarray] = []
    records = [sr.shape for sr in reader.iterShapeRecords()
               if str(sr.record.as_dict().get("PROV_CODE", "")).strip() == "53"
               or str(sr.record.as_dict().get("PROV_NAME", "")).strip().upper() == "UTTARADIT"]
    if not records:
        raise ValueError("No Uttaradit polygon found in boundary shapefile")
    for shp in records:
        points = np.asarray(shp.points, dtype=float)
        starts = list(shp.parts) + [len(points)]
        for a, b in zip(starts[:-1], starts[1:]):
            ring = points[a:b, :2]
            if len(ring) >= 3 and np.isfinite(ring).all():
                rings.append(ring)
    if not rings:
        raise ValueError("No polygon rings found")
    return rings


def boundary_path(ring: np.ndarray) -> MplPath:
    v = np.asarray(ring, dtype=float)
    if not np.array_equal(v[0], v[-1]):
        v = np.vstack([v, v[0]])
    return MplPath(v, closed=True)


def inside_union(points: np.ndarray, rings: list[np.ndarray]) -> np.ndarray:
    out = np.zeros(len(points), dtype=bool)
    for ring in rings:
        out |= boundary_path(ring).contains_points(points, radius=1e-10)
    return out


def haversine_km(lat1: np.ndarray, lon1: np.ndarray, lat2: float, lon2: float) -> np.ndarray:
    radius = 6371.0088
    p1 = np.radians(lat1)
    p2 = math.radians(lat2)
    dlat = p2 - p1
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(p1) * math.cos(p2) * np.sin(dlon / 2) ** 2
    return 2 * radius * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def idw_grid(coords: pd.DataFrame, values: pd.Series, bounds: tuple[float, float, float, float], nx=320, ny=320, power=2.0):
    lon_min, lon_max, lat_min, lat_max = bounds
    lon = np.linspace(lon_min, lon_max, nx)
    lat = np.linspace(lat_min, lat_max, ny)
    xx, yy = np.meshgrid(lon, lat)
    slat = coords["latitude"].to_numpy(float)
    slon = coords["longitude"].to_numpy(float)
    sval = coords["station"].astype(str).map(values).to_numpy(float)
    out = np.empty(xx.size, dtype=float)
    for i, (x, y) in enumerate(zip(xx.ravel(), yy.ravel())):
        d = haversine_km(slat, slon, y, x)
        if np.any(d == 0):
            out[i] = sval[np.argmin(d)]
        else:
            w = 1.0 / np.power(d, power)
            out[i] = np.sum(w * sval) / np.sum(w)
    return xx, yy, out.reshape(xx.shape)


def save(fig: plt.Figure, stem: str, dpi: int = 600, tiff: bool = True) -> None:
    fig.savefig(FIGDIR / f"{stem}.png", dpi=dpi, bbox_inches="tight", facecolor="white")
    if tiff:
        fig.savefig(FIGDIR / f"{stem}.tif", dpi=dpi, bbox_inches="tight", facecolor="white", pil_kwargs={"compression": "tiff_lzw"})
    plt.close(fig)


def setup() -> None:
    plt.rcParams.update({
        "font.family": "Times New Roman",
        "font.size": 8.0,
        "axes.labelsize": 8.5,
        "axes.titlesize": 9.5,
        "xtick.labelsize": 7.2,
        "ytick.labelsize": 7.2,
        "axes.unicode_minus": False,
        "savefig.facecolor": "white",
    })


def station_labels(coords: pd.DataFrame) -> dict[str, str]:
    return {str(s): f"S{str(s)[-3:]}" for s in coords["station"].astype(str)}


def copy_attached_fig1() -> None:
    """Use the supplied Uttaradit elevation and station map unchanged as Figure 1."""
    if not ATTACHED_FIG1.is_file():
        raise FileNotFoundError(ATTACHED_FIG1)
    shutil.copy2(ATTACHED_FIG1, FIGDIR / "Figure1_Uttaradit.png")


def bh_q(p: np.ndarray) -> np.ndarray:
    out = np.full(p.shape, np.nan, float)
    finite = np.isfinite(p)
    vals = p[finite]
    order = np.argsort(vals)
    ranked = vals[order] * len(vals) / np.arange(1, len(vals) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    q = np.empty_like(ranked); q[order] = np.minimum(ranked, 1)
    out[finite] = q
    return out


def fig2(observed: pd.DataFrame) -> None:
    obs = observed.copy(); obs["Station"] = obs["Station"].astype(str)
    stations = sorted(obs.Station.unique())
    slopes = obs.pivot(index="Index", columns="Station", values="Sen_slope").reindex(index=INDICES, columns=stations)
    # robust, within-index scaling only controls colour; raw Sen slopes remain in Table 1.
    scaled = slopes.apply(lambda r: (r - r.median()) / (r.abs().quantile(.75) + 1e-12), axis=1).clip(-2, 2)
    p = obs.pivot(index="Index", columns="Station", values="p_MK").reindex(index=INDICES, columns=stations)
    q = bh_q(p.to_numpy(float).ravel()).reshape(p.shape)
    # Direction follows the standard MK statistic, not the Sen slope.  This
    # matters for count indices such as R50mm, whose Sen slope can be exactly
    # zero while the MK statistic has a clear positive or negative direction.
    z = obs.pivot(index="Index", columns="Station", values="Z_MK").reindex(index=INDICES, columns=stations)
    sig = np.where(q < .05, np.sign(z.to_numpy(float)), 0)
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 3.95), sharey=True)
    im = axes[0].imshow(scaled.to_numpy(), cmap="RdBu_r", norm=TwoSlopeNorm(vmin=-2, vcenter=0, vmax=2), aspect="auto")
    axes[0].set_title("(a) Standardized Sen slope", loc="left", fontweight="bold")
    fig.colorbar(im, ax=axes[0], fraction=.046, pad=.04, label="Within-index robust scale")
    cmap = ListedColormap(["#2166AC", "#F2F2F2", "#B2182B"])
    axes[1].imshow(sig, cmap=cmap, norm=BoundaryNorm([-1.5, -.5, .5, 1.5], 3), aspect="auto")
    axes[1].set_title("(b) BH-FDR decision", loc="left", fontweight="bold")
    for ax in axes:
        ax.set_xticks(np.arange(len(stations)), [f"S{s[-3:]}" for s in stations], rotation=45, ha="right")
        ax.set_yticks(np.arange(len(INDICES)), INDICES)
        ax.set_xlabel("Station")
        for x in range(len(stations) + 1): ax.axvline(x - .5, color="white", lw=.5)
        for y in range(len(INDICES) + 1): ax.axhline(y - .5, color="white", lw=.5)
    axes[0].set_ylabel("Index")
    axes[1].legend(handles=[Patch(facecolor="#B2182B", label="Increasing (q < 0.05)"), Patch(facecolor="#2166AC", label="Decreasing (q < 0.05)"), Patch(facecolor="#F2F2F2", edgecolor="0.6", label="Not significant")], loc="upper center", bbox_to_anchor=(.5, -.19), frameon=False, fontsize=6.8, ncol=3)
    fig.subplots_adjust(left=.08, right=.98, bottom=.22, top=.95, wspace=.12)
    save(fig, "Figure2_observed_trends", dpi=1000)


def fig3(changes: pd.DataFrame) -> None:
    c = changes.copy(); c["Station"] = c["Station"].astype(str)
    # model-first: station median within each model, then distribution across seven models
    ms = c.groupby(["Scenario", "Model", "Station", "Index"], as_index=False)["Relative_change_pct"].median()
    ms = ms.groupby(["Scenario", "Model", "Index"], as_index=False)["Relative_change_pct"].median()
    models = [m for m in MODEL_ORDER if m in ms.Model.unique()]
    fig, axes = plt.subplots(1, 2, figsize=(8.7, 5.25), sharey=True)
    colours = plt.get_cmap("tab10")(np.linspace(.02, .88, len(models)))
    for ax, scenario in zip(axes, SCENARIOS):
        for y, idx in enumerate(INDICES):
            vals = ms.query("Scenario == @scenario and Index == @idx").set_index("Model").reindex(models)["Relative_change_pct"].to_numpy(float)
            q1, med, q3 = np.nanquantile(vals, [.25, .5, .75])
            ax.plot([q1, q3], [y, y], color="#303030", lw=3.5, zorder=3)
            ax.scatter([med], [y], s=35, c="black", zorder=4)
            for value, model, colour, jit in zip(vals, models, colours, np.linspace(-.14, .14, len(models))):
                ax.scatter([value], [y + jit], s=25, facecolors="white", edgecolors=[colour], lw=.9, zorder=5)
        ax.axvline(0, color="0.25", lw=.8); ax.grid(axis="x", alpha=.17, lw=.5)
        label = "(a) SSP2-4.5" if scenario == "SSP2-4.5" else "(b) SSP5-8.5"
        ax.set_title(label, loc="left", fontweight="bold")
        ax.set_xlabel("Relative change (%)")
        ax.set_yticks(range(len(INDICES)), INDICES)
        ax.invert_yaxis()
    axes[0].set_ylabel("Index")
    handles = [Line2D([], [], marker="o", ls="", mfc="white", mec=c, ms=5, label=m) for m, c in zip(models, colours)] + [Line2D([], [], marker="o", ls="", color="black", label="Median"), Line2D([], [], color="#303030", lw=3, label="Interquartile range")]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(.5, -.02), ncol=3, frameon=False, fontsize=6.6)
    fig.subplots_adjust(left=.08, right=.98, bottom=.18, top=.95, wspace=.08)
    save(fig, "Figure3_future_model_changes", dpi=1000)


def station_change(result_dir: Path, scenario: str, relative: bool) -> pd.Series:
    c = pd.read_csv(result_dir / "future_change_2021_2050.csv", dtype={"Station": str})
    c = c.query("Scenario == @scenario and Index == 'PRCPTOT'")
    col = "Relative_change_pct" if relative else "Absolute_change"
    return c.groupby("Station")[col].median()


def fig4(coords: pd.DataFrame, rings: list[np.ndarray]) -> None:
    # Use the same station-coordinate input as the temporal analysis and Table 1.
    coords_final = coords.copy()
    # common bounds exactly equal to the province polygon extent, so no white
    # pixels are interpreted as missing interpolation outside the study area.
    all_pts = np.vstack(rings)
    bounds = (float(all_pts[:, 0].min()), float(all_pts[:, 0].max()), float(all_pts[:, 1].min()), float(all_pts[:, 1].max()))
    mask_rings = rings
    fields = []
    for scenario in SCENARIOS:
        vals = station_change(PRIMARY, scenario, relative=True)
        xx, yy, z = idw_grid(coords_final, vals, bounds)
        inside = inside_union(np.column_stack([xx.ravel(), yy.ravel()]), mask_rings).reshape(xx.shape)
        z[~inside] = np.nan
        fields.append((xx, yy, z))
    abs_values = np.concatenate([np.abs(z[np.isfinite(z)]) for _, _, z in fields])
    clim = max(1.0, float(np.nanpercentile(abs_values, 98)))
    fig, axes = plt.subplots(1, 2, figsize=(8.9, 4.7), sharex=True, sharey=True)
    for ax, (scenario, (xx, yy, z)) in zip(axes, zip(SCENARIOS, fields)):
        norm = TwoSlopeNorm(vmin=-clim, vcenter=0, vmax=clim)
        im = ax.contourf(xx, yy, z, levels=np.linspace(-clim, clim, 19), cmap="RdBu_r", norm=norm, extend="both")
        for ring in rings: ax.plot(ring[:, 0], ring[:, 1], color="0.18", lw=.5, zorder=3)
        ax.scatter(coords_final.longitude, coords_final.latitude, s=16, c="white", edgecolors="black", lw=.45, zorder=5)
        ax.set_title("(a) SSP2-4.5" if scenario == "SSP2-4.5" else "(b) SSP5-8.5", loc="left", fontsize=9.0, fontweight="bold")
        ax.set_xlabel("Longitude (°E)")
        ax.set_aspect("equal", adjustable="box")
        ax.grid(alpha=.12, lw=.35)
    axes[0].set_ylabel("Latitude (°N)")
    cax = fig.add_axes([.90, .16, .022, .70])
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=TwoSlopeNorm(vmin=-clim, vcenter=0, vmax=clim), cmap="RdBu_r"), cax=cax)
    cb.set_label("IDW-estimated PRCPTOT relative change (%)")
    fig.subplots_adjust(left=.07, right=.87, bottom=.12, top=.95, wspace=.08)
    save(fig, "Figure4_prcptot_idw_fields", dpi=600)


def main() -> None:
    setup()
    coords = pd.read_csv(PRIMARY / "station_coordinates_used.csv", dtype={"station": str})
    observed = pd.read_csv(PRIMARY / "observed_trend_1981_2014.csv", dtype={"Station": str})
    changes = pd.read_csv(PRIMARY / "future_change_2021_2050.csv", dtype={"Station": str})
    rings = load_boundary(BOUNDARY)
    # Remove the previous audit-map outputs so only the user-supplied Figure 1
    # and the focused scientific figure set remain in the package.
    for stale in ["Figure1_station_network.png", "Figure1_station_network.tif", "Figure1_Phetchaburi.png", "Figure1_Phetchaburi.tif", "Figure4_prcptot_idw_coordinate_sensitivity.png", "Figure4_prcptot_idw_coordinate_sensitivity.tif"]:
        (FIGDIR / stale).unlink(missing_ok=True)
    copy_attached_fig1()
    fig2(observed)
    fig3(changes)
    fig4(coords, rings)
    print("APST_FIGURES_OK", sorted(p.name for p in FIGDIR.glob("Figure*.png")))


if __name__ == "__main__":
    main()
