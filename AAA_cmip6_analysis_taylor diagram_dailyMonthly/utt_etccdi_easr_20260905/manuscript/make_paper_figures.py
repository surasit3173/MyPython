"""Create the four manuscript figures only from validated result tables."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap, TwoSlopeNorm
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.path import Path as MplPath
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "outputs" / "full_with_figures" / "results"
FIGURES = ROOT / "manuscript" / "figures"
SOURCE = ROOT / "Uttaradit_ETCCDI_MK_MMK2004_Sen_IDW_Q3_fixed.py"
BOUNDARY = Path(r"C:\MyPython\CMIP6Uttaradit\Data_Uttaradit\75 pbound.shp")
INDICES = ["PRCPTOT", "SDII", "Rx1day", "Rx5day", "CDD", "CWD", "R10mm", "R20mm", "R50mm", "R95p", "R99p"]


def pipeline():
    spec = importlib.util.spec_from_file_location("utt_pipeline_figures", SOURCE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def save(fig: plt.Figure, name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / name, dpi=400, bbox_inches="tight")
    plt.close(fig)


def setup() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "axes.labelsize": 9,
            "axes.titlesize": 10,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "axes.unicode_minus": False,
        }
    )


def figure_1(coords: pd.DataFrame, boundary_parts: list[np.ndarray]) -> None:
    fig, ax = plt.subplots(figsize=(6.1, 5.3))
    for ring in boundary_parts:
        ax.plot(ring[:, 0], ring[:, 1], color="0.25", linewidth=0.55, zorder=1)
    ax.scatter(coords.longitude, coords.latitude, s=26, facecolors="white", edgecolors="black", linewidths=0.75, zorder=3)
    # Label every station so the map is directly traceable to the tabulated
    # station-level results.  A compact white halo preserves readability at
    # journal column width without obscuring the gauge marker.
    offsets = [(5,5),(5,-10),(5,5),(5,5),(5,5),(5,5),(5,5),(5,5),(5,5),(5,5),(5,5),(-31,-9),(5,5)]
    for (_, row), offset in zip(coords.iterrows(), offsets):
        sid = str(row["station"])
        label = f"S{sid[-3:]}"
        if sid.endswith("003"):
            offset = (8, 9)
        elif sid.endswith("012"):
            offset = (17, -5)
        ax.annotate(
            label,
            (float(row["longitude"]), float(row["latitude"])),
            xytext=offset,
            textcoords="offset points",
            fontsize=7.0,
            color="0.10",
            bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.78),
            zorder=4,
        )
    ax.set_xlabel("Longitude (°E)")
    ax.set_ylabel("Latitude (°N)")
    ax.set_title("Uttaradit rain-gauge network (n = 13)")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(alpha=0.18, linewidth=0.45)
    # 50-km scale bar (local longitude approximation) and north arrow.
    lat0 = float(coords.latitude.mean())
    dx = 50.0 / (111.32 * np.cos(np.deg2rad(lat0)))
    x0 = float(coords.longitude.min()) - 0.01
    y0 = float(coords.latitude.min()) - 0.02
    ax.plot([x0, x0 + dx], [y0, y0], color="0.1", lw=1.6, solid_capstyle="butt", zorder=5)
    ax.text(x0 + dx / 2, y0 + 0.018, "50 km", ha="center", va="bottom", fontsize=7)
    ax.annotate("N", xy=(101.17, 18.30), xytext=(101.17, 18.17), ha="center", fontsize=8,
                arrowprops=dict(arrowstyle="-|>", lw=0.8, color="0.1"), zorder=5)
    save(fig, "Figure1_station_network.png")


def figure_2(observed: pd.DataFrame) -> None:
    station_order = sorted(observed.Station.astype(str).unique())
    slopes = observed.assign(Station=observed.Station.astype(str)).pivot(index="Index", columns="Station", values="Sen_slope").reindex(index=INDICES, columns=station_order)
    # Standardize within index solely for an interpretable cross-index pattern;
    # raw units remain in the supplementary table.
    scaled = slopes.apply(lambda r: (r-r.median())/(r.abs().quantile(.75)+1e-12), axis=1).clip(-2,2)
    p = observed.assign(Station=observed.Station.astype(str)).pivot(index="Index", columns="Station", values="p_MK").reindex(index=INDICES, columns=station_order)
    # One BH family of all 143 observed station-index tests, matching Table S5.
    raw = p.to_numpy(float).ravel(); order=np.argsort(raw); ranked=raw[order]*len(raw)/np.arange(1,len(raw)+1)
    adjusted=np.minimum.accumulate(ranked[::-1])[::-1]; q=np.empty_like(adjusted); q[order]=np.minimum(adjusted,1.0)
    fdr = q.reshape(p.shape) < .05
    fig, axes = plt.subplots(1, 2, figsize=(8.2, 4.5), sharey=True, layout="constrained")
    im=axes[0].imshow(scaled.to_numpy(), cmap="RdBu_r", norm=TwoSlopeNorm(vmin=-2,vcenter=0,vmax=2), aspect="auto")
    axes[0].set_title("(a) Standardized Sen slope")
    fig.colorbar(im, ax=axes[0], fraction=.046, pad=.04, label="Within-index robust scale")
    sign=np.sign(slopes.to_numpy()); sig=np.where(fdr, sign, 0)
    axes[1].imshow(sig, cmap=ListedColormap(["#2166ac", "#f5f5f5", "#b2182b"]), norm=BoundaryNorm([-1.5,-.5,.5,1.5],3), aspect="auto")
    axes[1].set_title("(b) Direction significant after BH-FDR")
    for ax in axes:
        ax.set_xticks(np.arange(len(station_order)), [f"S{s[-3:]}" for s in station_order], rotation=45, ha="right")
        ax.set_yticks(np.arange(len(INDICES)), INDICES)
        for y in range(len(INDICES)+1): ax.axhline(y-.5,color="white",lw=.55)
        for x in range(len(station_order)+1): ax.axvline(x-.5,color="white",lw=.55)
    axes[1].legend(handles=[Patch(facecolor="#b2182b",label="Significant increasing"),Patch(facecolor="#2166ac",label="Significant decreasing"),Patch(facecolor="#f5f5f5",edgecolor="0.6",label="Not significant")], loc="upper center", bbox_to_anchor=(.5,-.20), ncol=1, frameon=False, fontsize=7.2)
    fig.suptitle("Observed annual precipitation-index trends, 1981–2014")
    save(fig, "Figure2_observed_mmk_direction.png")


def figure_3(changes: pd.DataFrame) -> None:
    ms=changes.groupby(["Scenario","Model","Station","Index"],as_index=False).Relative_change_pct.median().groupby(["Scenario","Model","Index"],as_index=False).Relative_change_pct.median()
    main_indices=[x for x in INDICES if x != "R99p"]
    models=sorted(ms.Model.unique())
    colors=plt.get_cmap("tab10")(np.linspace(0,.9,len(models)))
    fig, axes=plt.subplots(2,2,figsize=(8.25,6.3),gridspec_kw={"height_ratios":[5,1]},sharey="row")
    fig.subplots_adjust(left=.11,right=.985,top=.87,bottom=.24,hspace=.37,wspace=.035)
    for col,scenario in enumerate(["SSP2-4.5","SSP5-8.5"]):
        ax=axes[0,col]
        for y,idx in enumerate(main_indices):
            v=ms.loc[(ms.Scenario==scenario)&(ms.Index==idx),'Relative_change_pct'].to_numpy()
            jitter=np.linspace(-.13,.13,len(v))
            for value, jitter_y, model, color in zip(v,jitter,models,colors): ax.scatter(value,y+jitter_y,s=22,facecolors="white",edgecolors=color,linewidths=.95,zorder=2)
            q1,med,q3=np.quantile(v,[.25,.5,.75])
            ax.plot([q1,q3],[y,y],color="#343434",lw=3.0,zorder=3)
            ax.scatter([med],[y],s=38,color="black",zorder=4)
        ax.axvline(0,color="0.25",lw=.8)
        ax.set_title(scenario); ax.grid(axis="x",alpha=.18); ax.set_xlabel("Relative change (%)")
        ax.set_yticks(np.arange(len(main_indices)),main_indices)
        ax2=axes[1,col]; v=ms.loc[(ms.Scenario==scenario)&(ms.Index=="R99p"),'Relative_change_pct'].to_numpy()
        for value, jitter_y, color in zip(v,np.linspace(-.10,.10,len(v)),colors): ax2.scatter(value,jitter_y,s=22,facecolors="white",edgecolors=color,linewidths=.95,zorder=2)
        q1,med,q3=np.quantile(v,[.25,.5,.75]); ax2.plot([q1,q3],[0,0],color="#343434",lw=3,zorder=3); ax2.scatter([med],[0],s=38,color="black",zorder=4)
        ax2.axvline(0,color="0.25",lw=.8); ax2.grid(axis="x",alpha=.18); ax2.set_yticks([0],["R99p"]); ax2.set_xlabel("R99p relative change (%)")
    handles=[Line2D([],[],marker='o',ls='',mfc='white',mec=c,ms=5,label=m) for m,c in zip(models,colors)] + [Line2D([],[],marker='o',ls='',color='black',label='Median'),Line2D([],[],color='#343434',lw=3,label='IQR')]
    fig.legend(handles=handles, loc="lower center", bbox_to_anchor=(.5,.02), ncol=5, frameon=False, fontsize=6.4)
    fig.suptitle("Seven model-specific station-median relative changes, 2021–2050 relative to 1995–2014", y=.98)
    save(fig, "Figure3_future_median_relative_change.png")


def figure_4(changes: pd.DataFrame, coords: pd.DataFrame, boundary_parts: list[np.ndarray], module) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 4.6), sharex=True, sharey=True, layout="constrained")
    panels = []
    for scenario in ("SSP2-4.5", "SSP5-8.5"):
        values = changes.loc[(changes.Index == "PRCPTOT") & (changes.Scenario == scenario)].groupby("Station").Absolute_change.median()
        panels.append(values)
    extent = max(float(np.nanmax(np.abs(v))) for v in panels)
    extent = max(extent, 1.0)
    norm = TwoSlopeNorm(vmin=-extent, vcenter=0, vmax=extent)
    im = None
    paths=[MplPath(ring) for ring in boundary_parts]
    boundary_vertices=np.vstack([np.asarray(ring, dtype=float) for ring in boundary_parts])
    grid_bounds=(
        float(boundary_vertices[:, 0].min()),
        float(boundary_vertices[:, 0].max()),
        float(boundary_vertices[:, 1].min()),
        float(boundary_vertices[:, 1].max()),
    )
    for ax, (scenario, values) in zip(axes, zip(("SSP2-4.5", "SSP5-8.5"), panels)):
        for ring in boundary_parts:
            ax.plot(ring[:, 0], ring[:, 1], color="0.20", linewidth=0.6, zorder=1)
        values.index=values.index.astype(str)
        display=coords.copy(); display["value"]=display.station.astype(str).map(values)
        lon,lat,grid=module.idw_grid(
            display[["station","latitude","longitude"]],
            values,
            power=2.0,
            nx=260,
            ny=260,
            padding=.03,
            grid_bounds=grid_bounds,
        )
        points=np.column_stack([lon.ravel(),lat.ravel()]); inside=np.zeros(points.shape[0],dtype=bool)
        for path in paths: inside |= path.contains_points(points)
        field=np.ma.masked_where(~inside.reshape(grid.shape),grid)
        im=ax.contourf(lon,lat,field,levels=np.linspace(-extent,extent,17),cmap="RdBu_r",norm=norm,extend="both",zorder=0)
        ax.contour(lon,lat,field,levels=[0],colors="0.25",linewidths=.55,zorder=1)
        ax.scatter(display.longitude, display.latitude, c=display.value, s=32, cmap="RdBu_r", norm=norm, edgecolors="black", linewidths=.55, zorder=3)
        for _,row in display.iterrows(): ax.annotate(f"S{str(row.station)[-3:]}",(row.longitude,row.latitude),xytext=(3,3),textcoords="offset points",fontsize=5.8,bbox=dict(boxstyle="round,pad=.08",fc="white",ec="none",alpha=.72),zorder=4)
        ax.set_title(scenario)
        ax.text(0.02, 0.97, "(a)" if scenario == "SSP2-4.5" else "(b)", transform=ax.transAxes,
                ha="left", va="top", fontsize=9, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.16", fc="white", ec="none", alpha=0.78), zorder=5)
        ax.set_xlabel("Longitude (°E)")
        ax.set_aspect("equal", adjustable="box")
    axes[0].set_ylabel("Latitude (°N)")
    assert im is not None
    cbar = fig.colorbar(im, ax=axes, shrink=0.88, pad=0.02)
    cbar.set_label("IDW-estimated PRCPTOT absolute change (mm)")
    fig.suptitle("IDW depiction of station-median PRCPTOT change, 2021–2050 minus 1995–2014", fontsize=10)
    save(fig, "Figure4_prcptot_idw_change.png")


def figure_5_mean_change_vs_trend() -> None:
    """Three-layer analytical workflow."""
    fig, ax = plt.subplots(figsize=(7.2, 4.3)); ax.axis("off")
    layers=[("1  Observed variability",.76,"Daily rainfall  →  QC and 11 indices  →  Sen slope and standard MK  →  BH-FDR"), ("2  Future projected mean change",.49,"1995–2014 baseline  →  2021–2050 mean  →  absolute/relative change  →  model median, IQR and sign support"), ("3  Temporal diagnostic",.22,"2021–2050 annual indices  →  within-window standard MK  →  increasing, decreasing or not significant")]
    for title,y,text in layers:
        ax.text(.03,y+.08,title,ha='left',va='center',fontweight='bold',fontsize=8.6,transform=ax.transAxes,color='#17365D')
        ax.text(.52,y-.015,text,ha='center',va='center',fontsize=8.0,transform=ax.transAxes,bbox=dict(boxstyle='round,pad=.56',fc='#F6F8FA',ec='#537895',lw=.8))
    ax.text(.5,.045,"Interpretation: future mean change ≠ within-window trend",ha='center',va='center',fontsize=8.0,transform=ax.transAxes,bbox=dict(boxstyle='round,pad=.38',fc='#FFF4E5',ec='#B45F06',lw=.8))
    ax.set_title("Analytical framework for observed trends, near-term projected change and within-window temporal diagnostics",fontsize=10)
    save(fig, "Figure5_mean_change_vs_trend.png")


def main() -> None:
    setup()
    module = pipeline()
    coords = pd.read_csv(RESULTS / "station_coordinates_used.csv", dtype={"station": str})
    observed = pd.read_csv(RESULTS / "observed_trend_1981_2014.csv", dtype={"Station": str})
    changes = pd.read_csv(RESULTS / "future_change_2021_2050.csv", dtype={"Station": str})
    boundary_parts = module.read_boundary_parts(BOUNDARY)
    figure_1(coords, boundary_parts)
    figure_2(observed)
    figure_3(changes)
    figure_4(changes, coords, boundary_parts, module)
    figure_5_mean_change_vs_trend()
    print("PAPER_FIGURES_OK")


if __name__ == "__main__":
    main()
