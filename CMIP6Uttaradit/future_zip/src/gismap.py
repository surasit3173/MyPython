"""
gismap.py
=========
Publication-quality GIS maps with no geopandas/pyproj dependency. Each map shows
an IDW-interpolated surface of the gauge values clipped to the study-area
boundary (Scientific-Interpretation-First: surface pattern AND observation
points are both shown to avoid over-interpretation), with international-standard
lon/lat graticule labels (degrees-minutes), a north arrow, scale bar, colour bar
and significance legend arranged in the empty margins so nothing overlaps.

Reusable: a StudyArea is built from any boundary .shp + station coordinate table
via config; a new region needs no code change.
"""
from __future__ import annotations
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch
from matplotlib.lines import Line2D
from matplotlib.offsetbox import AnchoredOffsetbox, AuxTransformBox
import matplotlib.patches as mpatches

from . import config as C
from .geo import read_polygon_shapefile, lonlat_to_utm

log = logging.getLogger("gismap")


def _fmt_lon(lon):
    sign = "E" if lon >= 0 else "W"
    a = abs(lon); d = int(a); m = round((a - d) * 60)
    if m == 60:
        d += 1; m = 0
    return f"{d}\u00b0{m:02d}\u2032{sign}"


def _fmt_lat(lat):
    sign = "N" if lat >= 0 else "S"
    a = abs(lat); d = int(a); m = round((a - d) * 60)
    if m == 60:
        d += 1; m = 0
    return f"{d}\u00b0{m:02d}\u2032{sign}"


def _idw(px, py, pv, GX, GY, power=2.0, eps=1e-6):
    Z = np.zeros_like(GX); W = np.zeros_like(GX)
    for x, y, v in zip(px, py, pv):
        d = np.hypot(GX - x, GY - y) + eps
        w = 1.0 / d ** power
        Z += w * v; W += w
    return Z / W


def _sig_markers(ax, d, color_col, sig_col, dir_col, cmap, vmin, vmax,
                 big=105, small=42):
    """Gauges: non-significant = small circles; significant = triangles
    (up = increase, down = decrease, by sign of dir_col). A thin white halo is
    drawn behind significant triangles so neighbouring markers stay visually
    separate without enlarging them (anti-collision, publication-clean)."""
    sig = d[d[sig_col]]; nsig = d[~d[sig_col]]
    ax.scatter(nsig["E"], nsig["N"], c=nsig[color_col], cmap=cmap, vmin=vmin,
               vmax=vmax, s=small, marker="o", edgecolor="#333333",
               linewidths=0.7, zorder=5)
    up = sig[sig[dir_col] >= 0]; dn = sig[sig[dir_col] < 0]
    for sub, mk in ((up, "^"), (dn, "v")):
        if not len(sub):
            continue
        ax.scatter(sub["E"], sub["N"], s=big * 1.55, marker=mk, color="white",
                   edgecolor="none", zorder=5.5)                 # halo
        ax.scatter(sub["E"], sub["N"], c=sub[color_col], cmap=cmap, vmin=vmin,
                   vmax=vmax, s=big, marker=mk, edgecolor="black",
                   linewidths=1.3, zorder=6)


def _sig_legend(ax, loc="upper left", fontsize=7.5):
    h = [Line2D([0], [0], marker="^", color="w", markerfacecolor="#cccccc",
                markeredgecolor="black", markersize=12, markeredgewidth=2.0,
                label="Significant increase (p<0.05)"),
         Line2D([0], [0], marker="v", color="w", markerfacecolor="#cccccc",
                markeredgecolor="black", markersize=12, markeredgewidth=2.0,
                label="Significant decrease (p<0.05)"),
         Line2D([0], [0], marker="o", color="w", markerfacecolor="white",
                markeredgecolor="#333333", markersize=8, label="Non-significant")]
    ax.legend(handles=h, loc=loc, fontsize=fontsize, framealpha=0.92,
              borderpad=0.6)


class StudyArea:
    def __init__(self):
        self.rings, self.bbox = read_polygon_shapefile(str(C.BOUNDARY_SHP))
        co = pd.read_excel(C.GIS_COORD_FILE)
        co.columns = [str(c).strip().lower() for c in co.columns]
        co = co[co[C.COORD_ID_COL].isin(C.STATION_IDS)].copy()
        e, n = lonlat_to_utm(co[C.COORD_LON_COL].values,
                             co[C.COORD_LAT_COL].values, C.UTM_CENTRAL_MERIDIAN)
        co["E"], co["N"] = e, n
        self.coords = co.set_index(C.COORD_ID_COL)
        self.clat = float(co[C.COORD_LAT_COL].mean())
        self.clon = float(co[C.COORD_LON_COL].mean())
        # compound path for clipping / masking
        verts, codes = [], []
        for xs, ys in self.rings:
            pts = list(zip(xs, ys))
            if len(pts) < 3:
                continue
            codes += [MplPath.MOVETO] + [MplPath.LINETO] * (len(pts) - 2) + \
                     [MplPath.CLOSEPOLY]
            verts += pts
        self.path = MplPath(verts, codes)

    # -- composition helpers --------------------------------------------------
    def _frame(self, ax, pad_frac=0.06):
        xmin, ymin, xmax, ymax = self.bbox
        mx = (xmax - xmin) * pad_frac
        my = (ymax - ymin) * 0.03
        ax.set_xlim(xmin - mx, xmax + mx)
        ax.set_ylim(ymin - my, ymax + my)
        ax.set_aspect("equal")

    def _idw_clip(self, ax, d, value_col, cmap, vmax, nx=200, ny=360, levels=15,
                  vmin=None, alpha=1.0):
        xmin, ymin, xmax, ymax = self.bbox
        gx = np.linspace(xmin, xmax, nx); gy = np.linspace(ymin, ymax, ny)
        GX, GY = np.meshgrid(gx, gy)
        Z = _idw(d["E"].values, d["N"].values, d[value_col].values, GX, GY)
        inside = self.path.contains_points(
            np.column_stack([GX.ravel(), GY.ravel()])).reshape(GX.shape)
        Z = np.where(inside, Z, np.nan)
        lo = -vmax if vmin is None else vmin           # diverging vs sequential
        cf = ax.contourf(GX, GY, Z, levels=levels, cmap=cmap,
                         vmin=lo, vmax=vmax, extend="both", zorder=1,
                         alpha=alpha)
        clip = PathPatch(self.path, transform=ax.transData, fc="none", ec="none")
        ax.add_patch(clip)
        try:
            cf.set_clip_path(clip)                 # matplotlib >= 3.8
        except AttributeError:
            for coll in cf.collections:            # older matplotlib
                coll.set_clip_path(clip)
        return cf

    def _outline(self, ax, lw=0.8):
        ax.add_patch(PathPatch(self.path, transform=ax.transData, fc="none",
                               ec="#333333", lw=lw, zorder=4))

    def _graticule(self, ax, label=True, fontsize=8):
        xmin, ymin, xmax, ymax = self.bbox
        lons = np.arange(99.4, 100.05, 0.2)
        lats = np.arange(11.0, 12.65, 0.2)
        latspan = np.linspace(10.85, 12.75, 80)
        lonspan = np.linspace(99.30, 100.10, 80)
        for lo in lons:
            e, n = lonlat_to_utm(np.full_like(latspan, lo), latspan,
                                 C.UTM_CENTRAL_MERIDIAN)
            ax.plot(e, n, color="#cccccc", lw=0.35, ls=":", zorder=0)
        for la in lats:
            e, n = lonlat_to_utm(lonspan, np.full_like(lonspan, la),
                                 C.UTM_CENTRAL_MERIDIAN)
            ax.plot(e, n, color="#cccccc", lw=0.35, ls=":", zorder=0)
        # axis-edge ticks at round lon/lat (international format)
        xt, xl = [], []
        for lo in lons:
            e, _ = lonlat_to_utm(lo, self.clat, C.UTM_CENTRAL_MERIDIAN)
            if xmin <= e <= xmax:
                xt.append(float(e)); xl.append(_fmt_lon(lo))
        yt, yl = [], []
        for la in lats:
            _, n = lonlat_to_utm(self.clon, la, C.UTM_CENTRAL_MERIDIAN)
            if ymin <= n <= ymax:
                yt.append(float(n)); yl.append(_fmt_lat(la))
        ax.set_xticks(xt); ax.set_yticks(yt)
        if label:
            ax.set_xticklabels(xl, fontsize=fontsize)
            ax.set_yticklabels(yl, fontsize=fontsize)
        else:
            ax.set_xticklabels([]); ax.set_yticklabels([])

    def _scalebar(self, ax, km=20, loc_xy=(0.60, 0.045), fontsize=8):
        """Scale bar placed by axes fraction (default bottom-RIGHT, over the
        empty ocean margin so it never overlaps land), on a light box."""
        xmin, xmax = ax.get_xlim()
        Lfrac = (km * 1000.0) / (xmax - xmin)        # true length in axes frac
        x0, y0 = loc_xy
        pad = 0.014
        ax.add_patch(mpatches.FancyBboxPatch(
            (x0 - pad, y0 - pad), Lfrac + 2 * pad, 0.052,
            transform=ax.transAxes, boxstyle="round,pad=0.004",
            fc="white", ec="#bbbbbb", lw=0.6, alpha=0.88, zorder=6))
        yb = y0 + 0.012
        ax.plot([x0, x0 + Lfrac], [yb, yb], transform=ax.transAxes, color="k",
                lw=2.4, solid_capstyle="butt", zorder=7)
        for xx in (x0, x0 + Lfrac / 2, x0 + Lfrac):
            ax.plot([xx, xx], [yb, yb + 0.011], transform=ax.transAxes,
                    color="k", lw=0.9, zorder=7)
        ax.text(x0 + Lfrac / 2, yb + 0.016, f"{km} km", transform=ax.transAxes,
                ha="center", va="bottom", fontsize=fontsize, zorder=7)

    def _north(self, ax, loc_xy=(0.93, 0.90), size=0.07):
        xmin, ymin, xmax, ymax = ax.get_xlim()[0], ax.get_ylim()[0], \
            ax.get_xlim()[1], ax.get_ylim()[1]
        x = xmin + (xmax - xmin) * loc_xy[0]
        y0 = ymin + (ymax - ymin) * loc_xy[1]
        dy = (ymax - ymin) * size
        ax.annotate("", xy=(x, y0 + dy), xytext=(x, y0),
                    arrowprops=dict(arrowstyle="-|>", color="black", lw=1.6),
                    zorder=6)
        ax.text(x, y0 + dy + (ymax - ymin) * 0.008, "N", ha="center",
                va="bottom", fontsize=11, fontweight="bold", zorder=6)


def significance_map(area, values, value_col, sig_col, title, fname, cbar_label,
                     cmap="RdBu_r", out_dir=None, symmetric=True, dir_col=None):
    out_dir = out_dir or C.GIS_OUT
    d = values.merge(area.coords.reset_index()[[C.COORD_ID_COL, "E", "N"]],
                     left_on="station", right_on=C.COORD_ID_COL, how="inner")
    if symmetric:
        vmax = float(np.nanmax(np.abs(d[value_col]))) or 1.0
        vmin = -vmax
    else:
        vmin = float(np.nanmin(d[value_col]))
        vmax = float(np.nanmax(d[value_col])) or 1.0

    fig, ax = plt.subplots(figsize=(6.2, 8.4))
    area._frame(ax)
    cf = area._idw_clip(ax, d, value_col, cmap, vmax, vmin=vmin)
    area._outline(ax)
    area._graticule(ax)

    _sig_markers(ax, d, value_col, sig_col, dir_col or value_col, cmap, vmin, vmax)

    cb = fig.colorbar(cf, ax=ax, fraction=0.043, pad=0.02, extend="both")
    cb.set_label(cbar_label)
    area._scalebar(ax)
    area._north(ax)
    _sig_legend(ax)
    ax.set_title(title, pad=10)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(out_dir / f"{fname}.{ext}", dpi=C.DPI, bbox_inches="tight")
    plt.close(fig)
    log.info("saved GIS map %s.{png,pdf}", fname)


def year_map(area, values, year_col, sig_col, title, fname, cbar_label,
             cmap="viridis", out_dir=None, dir_col=None):
    """Change-point YEAR map using the SAME IDW rendering standard as the other
    maps. Marker shape encodes the direction of the step (up = rainfall
    increased, down = decreased) via dir_col; colour encodes the year."""
    out_dir = out_dir or C.GIS_OUT
    d = values.merge(area.coords.reset_index()[[C.COORD_ID_COL, "E", "N"]],
                     left_on="station", right_on=C.COORD_ID_COL, how="inner")
    if dir_col is None:
        dir_col = "_dir"; d[dir_col] = 1.0           # no direction -> all "up"
    vmin, vmax = float(d[year_col].min()), float(d[year_col].max())
    fig, ax = plt.subplots(figsize=(6.2, 8.4))
    area._frame(ax)
    cf = area._idw_clip(ax, d, year_col, cmap, vmax, vmin=vmin, levels=12)
    area._outline(ax)
    area._graticule(ax)
    _sig_markers(ax, d, year_col, sig_col, dir_col, cmap, vmin, vmax)
    cb = fig.colorbar(cf, ax=ax, fraction=0.043, pad=0.02, extend="both")
    cb.set_label(cbar_label)
    cb.ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v)}"))
    area._scalebar(ax); area._north(ax)
    _sig_legend(ax)
    ax.set_title(title, pad=10)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(out_dir / f"{fname}.{ext}", dpi=C.DPI, bbox_inches="tight")
    plt.close(fig)
    log.info("saved GIS year-map %s.{png,pdf}", fname)


def significance_map_grid(area, panels, fname, suptitle, cmap="RdBu_r",
                          out_dir=None):
    out_dir = out_dir or C.GIS_OUT
    n = len(panels)
    ncol = 4 if n >= 4 else n
    nrow = int(np.ceil(n / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(3.5 * ncol, 5.6 * nrow),
                             squeeze=False)
    for k, p in enumerate(panels):
        ax = axes[k // ncol][k % ncol]
        area._frame(ax)
        d = p["values"].merge(
            area.coords.reset_index()[[C.COORD_ID_COL, "E", "N"]],
            left_on="station", right_on=C.COORD_ID_COL, how="inner")
        vmax = float(np.nanmax(np.abs(d[p["value_col"]]))) or 1.0
        cf = area._idw_clip(ax, d, p["value_col"], cmap, vmax, nx=120, ny=210,
                            levels=13)
        area._outline(ax, lw=0.6)
        area._graticule(ax, label=False)
        _sig_markers(ax, d, p["value_col"], p["sig_col"], p["value_col"],
                     cmap, -vmax, vmax, big=80, small=22)
        cb = fig.colorbar(cf, ax=ax, fraction=0.05, pad=0.02, extend="both")
        cb.ax.tick_params(labelsize=6)
        cb.set_label(p["cbar_label"], fontsize=7)
        area._north(ax, loc_xy=(0.90, 0.88), size=0.06)
        ax.set_title(p["title"], fontsize=10)
    # one scale bar on the first panel only (shared geometry)
    area._scalebar(axes[0][0], fontsize=6)
    for k in range(n, nrow * ncol):
        axes[k // ncol][k % ncol].axis("off")
    fig.suptitle(suptitle, fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    for ext in ("png", "pdf"):
        fig.savefig(out_dir / f"{fname}.{ext}", dpi=C.DPI, bbox_inches="tight")
    plt.close(fig)
    log.info("saved GIS grid %s.{png,pdf}", fname)


def q1_spatial_coherence_map(
    area,
    trend_df,
    fname="Q1_FIGURE_03_tri_panel_spatial_coherence",
    suptitle="Tri-Panel Spatial Coherence of Seasonal Rainfall Trends",
    out_dir=None,
):
    """Q1-ready tri-panel map: IDW |Sen slope| background + gauge Z-score symbols."""
    out_dir = out_dir or C.Q1
    order = ["Annual", "Wet", "Dry"]
    d0 = trend_df.merge(area.coords.reset_index()[[C.COORD_ID_COL, "E", "N"]],
                        left_on="station", right_on=C.COORD_ID_COL, how="inner")
    d0 = d0[d0["timescale"].isin(order)].copy()
    if d0.empty:
        raise ValueError("No station trend rows available for the Q1 spatial map.")

    slope_max = float(d0["abs_sens_slope_mm_yr"].max()) if "abs_sens_slope_mm_yr" in d0 else float(d0["sens_slope_mm_yr"].abs().max())
    slope_max = slope_max if np.isfinite(slope_max) and slope_max > 0 else 1.0
    z_max = float(d0["z"].abs().max())
    z_max = z_max if np.isfinite(z_max) and z_max > 0 else 1.0

    fig, axes = plt.subplots(1, 3, figsize=(15.8, 6.1), squeeze=False)
    axes = axes.ravel()
    cf = sc = None

    for idx, var in enumerate(order):
        ax = axes[idx]
        d = d0[d0["timescale"] == var].copy()
        d["abs_slope"] = d["sens_slope_mm_yr"].abs()
        d["symbol_size"] = 55.0 + 38.0 * d["z"].abs()
        area._frame(ax)
        cf = area._idw_clip(ax, d, "abs_slope", "YlGnBu", slope_max, nx=170,
                            ny=280, levels=14, vmin=0.0, alpha=0.58)
        area._outline(ax, lw=0.75)
        area._graticule(ax, label=(idx == 0), fontsize=7)
        sc = ax.scatter(d["E"], d["N"], c=d["z"], cmap="RdBu_r",
                        vmin=-z_max, vmax=z_max, s=d["symbol_size"],
                        edgecolor="white", linewidths=0.9, zorder=6)
        sig = d[d["significant"]]
        if len(sig):
            ax.scatter(sig["E"], sig["N"], s=sig["symbol_size"] * 1.28, marker="*",
                       facecolors="none", edgecolors="black", linewidths=1.1,
                       zorder=7)
        area._north(ax, loc_xy=(0.90, 0.88), size=0.06)
        if idx == 0:
            area._scalebar(ax, km=20, loc_xy=(0.56, 0.05), fontsize=7)
        ax.set_title(f"{var} rainfall", fontsize=11)

    fig.subplots_adjust(right=0.89, bottom=0.16, top=0.90, wspace=0.08)
    cax1 = fig.add_axes([0.91, 0.24, 0.016, 0.54])
    cb1 = fig.colorbar(cf, cax=cax1)
    cb1.set_label("|Sen slope| (mm yr$^{-1}$)")
    cax2 = fig.add_axes([0.15, 0.08, 0.50, 0.028])
    cb2 = fig.colorbar(sc, cax=cax2, orientation="horizontal")
    cb2.set_label("TFPW-MK Z-score at gauges")

    size_vals = [1, 2, 3]
    size_handles = [plt.scatter([], [], s=55.0 + 38.0 * v, facecolor="#A9A9A9",
                                edgecolor="white", linewidths=0.9)
                    for v in size_vals]
    sig_handle = Line2D([0], [0], marker="*", linestyle="None", color="black",
                        markerfacecolor="none", markersize=11,
                        label="Significant (p<0.05)")
    fig.legend(size_handles + [sig_handle],
               [f"|Z| = {v}" for v in size_vals] + ["Significant (p<0.05)"],
               loc="lower right", bbox_to_anchor=(0.89, 0.06), ncol=4,
               fontsize=8, frameon=False)
    fig.suptitle(suptitle, fontsize=13)
    for ext in ("png", "pdf"):
        fig.savefig(out_dir / f"{fname}.{ext}", dpi=C.DPI, bbox_inches="tight")
    plt.close(fig)
    log.info("saved Q1 GIS map %s.{png,pdf}", fname)
