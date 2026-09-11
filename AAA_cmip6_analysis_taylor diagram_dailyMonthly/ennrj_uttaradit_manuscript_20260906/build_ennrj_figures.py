"""Build the three EnNRJ submission figures for the Uttaradit manuscript.

All quantitative graphics use the validated ``full_with_figures`` output from
the audited ETCCDI workflow.  The main text is projection-led: Figure 1 gives
geographic context, Figure 2 presents model-first future changes, and Figure 3
shows the station-referenced PRCPTOT IDW fields.  Titles are kept in captions,
not duplicated inside the artwork.
"""
from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.lines import Line2D
from matplotlib.path import Path as MplPath
from matplotlib.ticker import MaxNLocator, FuncFormatter
import numpy as np
import pandas as pd
import shapefile


HERE = Path(__file__).resolve().parent
RESULTS = (
    HERE.parent
    / "utt_etccdi_easr_20260905"
    / "outputs"
    / "full_with_figures"
    / "results"
)
BOUNDARY = Path(r"C:\MyPython\CMIP6Uttaradit\Data_Uttaradit\75 pbound.shp")
OUT = HERE / "figures_submission"
OUT.mkdir(parents=True, exist_ok=True)

INDICES = [
    "PRCPTOT", "SDII", "Rx1day", "Rx5day", "CDD", "CWD",
    "R10mm", "R20mm", "R50mm", "R95p", "R99p",
]
SCENARIOS = ["SSP2-4.5", "SSP5-8.5"]
MODELS = [
    "ACCESS-ESM1-5", "CanESM5", "CESM2", "EC-Earth3",
    "FGOALS-g3", "MIROC6", "MRI-ESM2-0",
]
MODEL_COLORS = [
    "#0072B2", "#E69F00", "#D55E00", "#CC79A7",
    "#8C564B", "#7F7F7F", "#B2A800",
]


def setup_style() -> None:
    """Apply the EnNRJ graph typography contract."""
    plt.rcParams.update(
        {
            "font.family": "Times New Roman",
            "font.size": 9.0,
            "axes.labelsize": 10.0,
            "axes.titlesize": 10.0,
            "xtick.labelsize": 9.0,
            "ytick.labelsize": 9.0,
            "legend.fontsize": 8.3,
            "axes.linewidth": 0.75,
            "xtick.major.width": 0.75,
            "ytick.major.width": 0.75,
            "lines.linewidth": 0.75,
            "axes.unicode_minus": False,
            "savefig.facecolor": "white",
        }
    )


def save_figure(fig: plt.Figure, stem: str, dpi: int) -> None:
    png = OUT / f"{stem}.png"
    tif = OUT / f"{stem}.tif"
    fig.savefig(png, dpi=dpi, bbox_inches="tight", pad_inches=0.04, facecolor="white")
    fig.savefig(
        tif,
        dpi=dpi,
        bbox_inches="tight",
        pad_inches=0.04,
        facecolor="white",
        pil_kwargs={"compression": "tiff_lzw"},
    )
    plt.close(fig)


def read_province_rings(path: Path) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Return Uttaradit rings and all provincial rings for the location inset."""
    reader = shapefile.Reader(str(path), encoding="cp874")
    target: list[np.ndarray] = []
    all_rings: list[np.ndarray] = []
    for sr in reader.iterShapeRecords():
        rec = sr.record.as_dict()
        is_target = (
            str(rec.get("PROV_CODE", "")).strip() == "53"
            or str(rec.get("PROV_NAME", "")).strip().upper() == "UTTARADIT"
        )
        pts = np.asarray(sr.shape.points, dtype=float)
        starts = list(sr.shape.parts) + [len(pts)]
        for a, b in zip(starts[:-1], starts[1:]):
            ring = pts[a:b, :2]
            if len(ring) >= 3 and np.isfinite(ring).all():
                all_rings.append(ring)
                if is_target:
                    target.append(ring)
    if not target:
        raise ValueError("Uttaradit polygon (province code 53) was not found")
    return target, all_rings


def _degree_lon(x: float, _: int) -> str:
    return f"{x:.1f}\N{DEGREE SIGN}E"


def _degree_lat(y: float, _: int) -> str:
    return f"{y:.1f}\N{DEGREE SIGN}N"


def _add_scale_bar(ax: plt.Axes, bounds: tuple[float, float, float, float], km: int = 25) -> None:
    xmin, xmax, ymin, ymax = bounds
    lat = 0.5 * (ymin + ymax)
    length = km / (111.320 * math.cos(math.radians(lat)))
    x1 = xmax - 0.06 * (xmax - xmin)
    x0 = x1 - length
    y = ymin + 0.055 * (ymax - ymin)
    ax.plot([x0, x1], [y, y], color="black", lw=1.5, solid_capstyle="butt", zorder=9)
    cap = 0.009 * (ymax - ymin)
    ax.plot([x0, x0], [y - cap, y + cap], color="black", lw=1.0, zorder=9)
    ax.plot([x1, x1], [y - cap, y + cap], color="black", lw=1.0, zorder=9)
    ax.text((x0 + x1) / 2, y + 0.015 * (ymax - ymin), f"{km} km", ha="center", va="bottom", fontsize=8.5)


def _add_north_arrow(ax: plt.Axes) -> None:
    ax.annotate(
        "",
        xy=(0.94, 0.925),
        xytext=(0.94, 0.845),
        xycoords="axes fraction",
        textcoords="axes fraction",
        ha="center",
        va="center",
        arrowprops={"arrowstyle": "-|>", "lw": 1.0, "color": "black"},
        zorder=10,
    )
    ax.text(0.94, 0.945, "N", transform=ax.transAxes, ha="center", va="bottom", fontsize=10, zorder=10)


def figure1_study_area(coords: pd.DataFrame, target: list[np.ndarray], all_rings: list[np.ndarray]) -> None:
    """Create a clean station-location map without the clipped source-map symbol."""
    pts = np.vstack(target)
    xmin, ymin = pts.min(axis=0)
    xmax, ymax = pts.max(axis=0)
    dx, dy = xmax - xmin, ymax - ymin
    bounds = (xmin - 0.055 * dx, xmax + 0.055 * dx, ymin - 0.055 * dy, ymax + 0.055 * dy)

    fig, ax = plt.subplots(figsize=(7.0, 6.1))
    # Neighbor boundaries provide restrained geographic context.
    for ring in all_rings:
        rx0, ry0 = ring.min(axis=0)
        rx1, ry1 = ring.max(axis=0)
        if rx1 >= bounds[0] and rx0 <= bounds[1] and ry1 >= bounds[2] and ry0 <= bounds[3]:
            ax.plot(ring[:, 0], ring[:, 1], color="#A8AFB5", lw=0.45, zorder=1)
    for ring in target:
        ax.fill(ring[:, 0], ring[:, 1], color="#E8F1F7", zorder=2)
        ax.plot(ring[:, 0], ring[:, 1], color="#222222", lw=0.75, zorder=3)

    ax.scatter(
        coords["longitude"], coords["latitude"],
        s=29, c="#0072B2", edgecolors="black", linewidths=0.55, zorder=6,
    )
    offsets = {
        "351001": (5, 7, "left"), "351002": (5, 7, "left"),
        "351003": (5, 7, "left"), "351004": (5, 7, "left"),
        "351005": (-5, -11, "right"), "351006": (5, 7, "left"),
        "351007": (0, 8, "center"), "351008": (5, 7, "left"),
        "351009": (5, 7, "left"), "351010": (-5, 7, "right"),
        "351011": (7, -11, "left"), "351012": (5, 7, "left"),
        "351201": (-7, 7, "right"),
    }
    for row in coords.itertuples(index=False):
        station = str(row.station)
        ox, oy, ha = offsets.get(station, (5, 7, "left"))
        ax.annotate(
            station,
            (float(row.longitude), float(row.latitude)),
            xytext=(ox, oy), textcoords="offset points", ha=ha, va="center",
            fontsize=7.8, zorder=7,
            bbox={"boxstyle": "round,pad=0.10", "fc": "white", "ec": "none", "alpha": 0.82},
        )

    ax.set_xlim(bounds[0], bounds[1])
    ax.set_ylim(bounds[2], bounds[3])
    ax.set_aspect("equal", adjustable="box")
    ax.xaxis.set_major_locator(MaxNLocator(5))
    ax.yaxis.set_major_locator(MaxNLocator(5))
    ax.xaxis.set_major_formatter(FuncFormatter(_degree_lon))
    ax.yaxis.set_major_formatter(FuncFormatter(_degree_lat))
    ax.grid(color="#D4D7DA", lw=0.4, ls=":", zorder=0)
    ax.tick_params(direction="out", length=3)
    _add_north_arrow(ax)
    _add_scale_bar(ax, bounds, 25)

    # Thailand provincial inset; Uttaradit is highlighted without adding a map title.
    inset = fig.add_axes([0.16, 0.655, 0.215, 0.235], zorder=20)
    for ring in all_rings:
        inset.plot(ring[:, 0], ring[:, 1], color="#8F979E", lw=0.25)
    for ring in target:
        inset.fill(ring[:, 0], ring[:, 1], color="#E69F00", alpha=0.85)
        inset.plot(ring[:, 0], ring[:, 1], color="#8A4B00", lw=0.45)
    all_pts = np.vstack(all_rings)
    inset.set_xlim(float(all_pts[:, 0].min()) - 0.3, float(all_pts[:, 0].max()) + 0.3)
    inset.set_ylim(float(all_pts[:, 1].min()) - 0.3, float(all_pts[:, 1].max()) + 0.3)
    inset.set_aspect("equal", adjustable="box")
    inset.set_xticks([])
    inset.set_yticks([])
    for spine in inset.spines.values():
        spine.set_linewidth(0.75)
    inset.text(0.5, 1.02, "Provincial setting", transform=inset.transAxes, ha="center", va="bottom", fontsize=8.0)

    fig.subplots_adjust(left=0.105, right=0.985, bottom=0.075, top=0.985)
    save_figure(fig, "Figure1_Uttaradit_study_area", 600)


def model_first_changes(changes: pd.DataFrame) -> pd.DataFrame:
    """Return one station-median relative change per model, scenario and index."""
    tmp = changes.copy()
    tmp["Station"] = tmp["Station"].astype(str)
    return (
        tmp.groupby(["Scenario", "Model", "Index"], as_index=False, observed=True)["Relative_change_pct"]
        .median()
    )


def figure2_model_changes(changes: pd.DataFrame) -> None:
    ms = model_first_changes(changes)
    models = [model for model in MODELS if model in set(ms["Model"])]
    finite = ms["Relative_change_pct"].to_numpy(float)
    finite = finite[np.isfinite(finite)]
    lo = 5 * math.floor((float(finite.min()) - 2) / 5)
    hi = 5 * math.ceil((float(finite.max()) + 2) / 5)

    fig, axes = plt.subplots(1, 2, figsize=(7.1, 5.0), sharex=True, sharey=True)
    jitter = np.linspace(-0.15, 0.15, len(models))
    for ax, scenario, panel in zip(axes, SCENARIOS, ["(a)", "(b)"]):
        for y, index in enumerate(INDICES):
            vals = (
                ms[(ms["Scenario"] == scenario) & (ms["Index"] == index)]
                .set_index("Model")
                .reindex(models)["Relative_change_pct"]
                .to_numpy(float)
            )
            q1, med, q3 = np.nanquantile(vals, [0.25, 0.50, 0.75])
            ax.plot([q1, q3], [y, y], color="#222222", lw=3.0, solid_capstyle="butt", zorder=3)
            ax.scatter(med, y, s=29, c="black", zorder=4)
            for value, color, dy in zip(vals, MODEL_COLORS, jitter):
                ax.scatter(value, y + dy, s=24, facecolors="white", edgecolors=color, linewidths=0.85, zorder=5)
        ax.axvline(0, color="#444444", lw=0.75, zorder=1)
        ax.grid(axis="x", color="#D2D2D2", lw=0.4, ls=":", zorder=0)
        ax.set_xlim(lo, hi)
        ax.set_xlabel("Relative change (%)")
        ax.set_yticks(range(len(INDICES)), INDICES)
        ax.text(0.0, 1.015, f"{panel} {scenario}", transform=ax.transAxes, ha="left", va="bottom", fontsize=10)
        for spine in ax.spines.values():
            spine.set_linewidth(0.75)
    axes[0].set_ylabel("Precipitation index")
    # The axes share y.  Inverting each panel would toggle the shared axis
    # twice and place R99p at the top.  Set the shared limits once so the
    # declared index order is retained from PRCPTOT (top) to R99p (bottom).
    axes[0].set_ylim(len(INDICES) - 0.5, -0.5)

    handles = [
        Line2D([], [], marker="o", linestyle="", markerfacecolor="white", markeredgecolor=color, markersize=5.0, label=model)
        for model, color in zip(models, MODEL_COLORS)
    ]
    handles.extend(
        [
            Line2D([], [], marker="o", linestyle="", color="black", markersize=5.0, label="Seven-model median"),
            Line2D([], [], color="#222222", lw=3.0, label="Interquartile range"),
        ]
    )
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 0.005), ncol=3, frameon=False)
    fig.subplots_adjust(left=0.105, right=0.99, bottom=0.205, top=0.965, wspace=0.08)
    save_figure(fig, "Figure2_future_model_changes", 1000)


def _closed_path(ring: np.ndarray) -> MplPath:
    v = np.asarray(ring, dtype=float)
    if not np.array_equal(v[0], v[-1]):
        v = np.vstack([v, v[0]])
    return MplPath(v, closed=True)


def _inside_union(points: np.ndarray, rings: list[np.ndarray]) -> np.ndarray:
    inside = np.zeros(len(points), dtype=bool)
    for ring in rings:
        inside |= _closed_path(ring).contains_points(points, radius=1e-10)
    return inside


def _haversine(lat1: np.ndarray, lon1: np.ndarray, lat2: float, lon2: float) -> np.ndarray:
    radius = 6371.0088
    p1 = np.radians(lat1)
    p2 = math.radians(lat2)
    dlat = p2 - p1
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(p1) * math.cos(p2) * np.sin(dlon / 2) ** 2
    return 2 * radius * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def _idw(coords: pd.DataFrame, values: pd.Series, bounds: tuple[float, float, float, float], n: int = 360) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xmin, xmax, ymin, ymax = bounds
    gx, gy = np.meshgrid(np.linspace(xmin, xmax, n), np.linspace(ymin, ymax, n))
    slat = coords["latitude"].to_numpy(float)
    slon = coords["longitude"].to_numpy(float)
    sval = coords["station"].astype(str).map(values).to_numpy(float)
    out = np.empty(gx.size, dtype=float)
    for k, (x, y) in enumerate(zip(gx.ravel(), gy.ravel())):
        d = _haversine(slat, slon, y, x)
        if np.any(d < 1e-12):
            out[k] = sval[int(np.argmin(d))]
        else:
            weights = d ** -2
            out[k] = np.sum(weights * sval) / np.sum(weights)
    return gx, gy, out.reshape(gx.shape)


def figure3_prcptot_idw(coords: pd.DataFrame, target: list[np.ndarray], changes: pd.DataFrame) -> None:
    pts = np.vstack(target)
    bounds = (float(pts[:, 0].min()), float(pts[:, 0].max()), float(pts[:, 1].min()), float(pts[:, 1].max()))
    station_values: dict[str, pd.Series] = {}
    fields = []
    for scenario in SCENARIOS:
        sub = changes[(changes["Scenario"] == scenario) & (changes["Index"] == "PRCPTOT")].copy()
        sub["Station"] = sub["Station"].astype(str)
        values = sub.groupby("Station", observed=True)["Relative_change_pct"].median()
        station_values[scenario] = values
        gx, gy, z = _idw(coords, values, bounds)
        mask = _inside_union(np.column_stack([gx.ravel(), gy.ravel()]), target).reshape(gx.shape)
        z[~mask] = np.nan
        fields.append((gx, gy, z))

    max_abs = max(float(np.nanmax(np.abs(s.to_numpy(float)))) for s in station_values.values())
    clim = 0.5 * math.ceil(max_abs / 0.5)
    levels = np.linspace(-clim, clim, 21)
    norm = TwoSlopeNorm(vmin=-clim, vcenter=0.0, vmax=clim)

    fig, axes = plt.subplots(1, 2, figsize=(7.1, 3.45), sharex=True, sharey=True)
    image = None
    for ax, scenario, panel, field in zip(axes, SCENARIOS, ["(a)", "(b)"], fields):
        gx, gy, z = field
        image = ax.contourf(gx, gy, z, levels=levels, cmap="RdBu_r", norm=norm)
        for ring in target:
            ax.plot(ring[:, 0], ring[:, 1], color="#222222", lw=0.75, zorder=3)
        ax.scatter(
            coords["longitude"], coords["latitude"], s=16,
            c="white", edgecolors="black", linewidths=0.50, zorder=5,
        )
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("Longitude (\N{DEGREE SIGN}E)")
        ax.xaxis.set_major_locator(MaxNLocator(5))
        ax.yaxis.set_major_locator(MaxNLocator(5))
        ax.grid(color="#D4D4D4", lw=0.35, alpha=0.45, zorder=0)
        ax.text(0.0, 1.015, f"{panel} {scenario}", transform=ax.transAxes, ha="left", va="bottom", fontsize=10)
        for spine in ax.spines.values():
            spine.set_linewidth(0.75)
    axes[0].set_ylabel("Latitude (\N{DEGREE SIGN}N)")
    color_ax = fig.add_axes([0.895, 0.18, 0.020, 0.68])
    colorbar = fig.colorbar(image, cax=color_ax, ticks=np.linspace(-clim, clim, 5))
    colorbar.set_label("IDW-estimated PRCPTOT change (%)", fontsize=9.5)
    colorbar.ax.tick_params(labelsize=8.5, width=0.75)
    fig.subplots_adjust(left=0.075, right=0.865, bottom=0.13, top=0.96, wspace=0.08)
    save_figure(fig, "Figure3_prcptot_idw_fields", 600)


def main() -> None:
    setup_style()
    coords = pd.read_csv(RESULTS / "station_coordinates_used.csv", dtype={"station": str})
    changes = pd.read_csv(RESULTS / "future_change_2021_2050.csv", dtype={"Station": str})
    target, all_rings = read_province_rings(BOUNDARY)
    figure1_study_area(coords, target, all_rings)
    figure2_model_changes(changes)
    figure3_prcptot_idw(coords, target, changes)
    print("ENNRJ_FIGURES_OK")
    for path in sorted(OUT.glob("Figure*")):
        print(path.name)


if __name__ == "__main__":
    main()
