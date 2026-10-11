"""
Stage 2 - Module B (v3 FINAL): Spatial Analysis with GIS boundaries
Nature-level figures - fixed legends, per-season scales, better contrast
"""

# ================================================================
# 0. Imports
# ================================================================
import os
import sys
import glob
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.path import Path
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from matplotlib.ticker import MultipleLocator, FixedLocator
from scipy.spatial import cKDTree
from scipy.spatial.distance import cdist

try:
    import geopandas as gpd
    from shapely.geometry import box
    from shapely.ops import unary_union
    HAS_GIS = True
except ImportError:
    HAS_GIS = False
    print("⚠️  geopandas not found")


# ================================================================
# 1. Global style
# ================================================================
mpl.rcParams.update({
    "font.family":       "serif",
    "font.serif":        ["Times New Roman", "Times", "DejaVu Serif"],
    "mathtext.fontset":  "stix",
    "font.size":         9,
    "axes.labelsize":    9.5,
    "axes.titlesize":    9.5,
    "xtick.labelsize":   8.5,
    "ytick.labelsize":   8.5,
    "legend.fontsize":   7.5,
    "axes.linewidth":    0.8,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "axes.labelpad":     4,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "xtick.major.size":  3.5,
    "ytick.major.size":  3.5,
    "xtick.minor.width": 0.6,
    "ytick.minor.width": 0.6,
    "xtick.minor.size":  2,
    "ytick.minor.size":  2,
    "xtick.direction":   "out",
    "ytick.direction":   "out",
    "figure.dpi":        200,
    "savefig.dpi":       600,
    "savefig.bbox":      "tight",
    "savefig.pad_inches": 0.06,
    "pdf.fonttype":      42,
    "ps.fonttype":       42,
    "legend.frameon":    True,
    "legend.framealpha": 0.95,
    "legend.edgecolor":  "0.6",
    "legend.fancybox":   False,
    "legend.handlelength": 1.5,
    "legend.borderpad":  0.35,
})

MM       = 1 / 25.4
W_SINGLE = 89  * MM
W_DOUBLE = 183 * MM

CLR_SIG_DEC = "#C1440E"
CLR_SIG_INC = "#1F6FB4"
CLR_NS      = "#9E9E9E"
CMAP_TREND  = "RdBu"

# NE Thailand provinces
NE_PROVINCES_ISO = {
    "TH-30", "TH-31", "TH-32", "TH-33", "TH-34", "TH-35", "TH-36",
    "TH-37", "TH-38", "TH-39", "TH-40", "TH-41", "TH-42", "TH-43",
    "TH-44", "TH-45", "TH-46", "TH-47", "TH-48", "TH-49",
}
NE_PROVINCES_NAMES = {
    "nakhon ratchasima", "buriram", "surin", "sisaket", "ubon ratchathani",
    "yasothon", "chaiyaphum", "amnat charoen", "bueng kan",
    "nong bua lamphu", "khon kaen", "udon thani", "loei", "nong khai",
    "maha sarakham", "roi et", "kalasin", "sakon nakhon",
    "nakhon phanom", "mukdahan",
}


# ================================================================
# 2. Paths & constants
# ================================================================
BASE_DIR  = "."
TAB_A_DIR = os.path.join(BASE_DIR, "outputs", "module_a", "tables")
OUT_DIR   = os.path.join(BASE_DIR, "outputs", "module_b")
FIG_DIR   = os.path.join(OUT_DIR, "figures")
TAB_DIR   = os.path.join(OUT_DIR, "tables")
GIS_DIR   = os.path.join(BASE_DIR, "GIS Thailand")
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(TAB_DIR, exist_ok=True)

LON_MIN, LON_MAX = 100.5, 106.0
LAT_MIN, LAT_MAX = 13.2, 18.7
GRID_STEP        = 0.03
MAX_DIST_MASK    = 1.5


def _find_station_csv():
    for p in [os.path.join(BASE_DIR, "data", "station_coords15sta.csv"),
              os.path.join(BASE_DIR, "station_coords15sta.csv")]:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("ไม่พบ station_coords15sta.csv")


STATION_CSV = _find_station_csv()


# ================================================================
# 3. GIS loaders
# ================================================================
def load_gis_layers():
    result = {"adm0": None, "adm1": None, "raw": []}
    if not HAS_GIS or not os.path.isdir(GIS_DIR):
        return result
    shp_files = glob.glob(os.path.join(GIS_DIR, "**", "*.shp"), recursive=True)
    print(f"🗺️  พบ shapefile {len(shp_files)} ไฟล์")
    bbox = box(LON_MIN, LAT_MIN, LON_MAX, LAT_MAX)
    for shp in shp_files:
        try:
            gdf = gpd.read_file(shp)
            gdf_clip = gdf[gdf.intersects(bbox)]
            if len(gdf_clip) == 0:
                continue
            name = os.path.basename(shp)
            print(f"     • {name}: {len(gdf_clip)} features")
            result["raw"].append((name, gdf_clip))
            n = len(gdf_clip)
            if n == 1 and result["adm0"] is None:
                result["adm0"] = gdf_clip
            elif 2 <= n <= 100 and result["adm1"] is None:
                result["adm1"] = gdf_clip
        except Exception as e:
            print(f"     × {os.path.basename(shp)}: {e}")
    return result


def get_ne_thailand_polygon(gis_layers):
    if not HAS_GIS or gis_layers["adm1"] is None:
        return None, None
    adm1 = gis_layers["adm1"]
    iso_col = next((c for c in adm1.columns
                    if c.upper() in ("ISO_3166_2", "ISO", "ADM1_PCODE")), None)
    name_col = next((c for c in adm1.columns
                     if c.upper() in ("ADM1_EN", "PROVINCE", "PROV_NAME",
                                      "NAME_1", "NAME")), None)
    ne_subset = None
    if iso_col is not None:
        ne_subset = adm1[adm1[iso_col].isin(NE_PROVINCES_ISO)]
    if (ne_subset is None or len(ne_subset) == 0) and name_col is not None:
        ne_subset = adm1[adm1[name_col].str.lower().str.strip()
                         .isin(NE_PROVINCES_NAMES)]
    if ne_subset is None or len(ne_subset) == 0:
        if gis_layers["adm0"] is not None:
            return gis_layers["adm0"], None
        return None, None
    print(f"✅ พบจังหวัดภาคอีสาน {len(ne_subset)} จังหวัด")
    return ne_subset, unary_union(ne_subset.geometry.values)


# ================================================================
# 4. Data loading + IDW
# ================================================================
def load_stations():
    df = pd.read_csv(STATION_CSV)
    df["stncode"] = df["stncode"].astype(int)
    return df


def load_trends(season):
    df = pd.read_csv(os.path.join(TAB_A_DIR, f"trends_{season.lower()}.csv"))
    df["stncode"] = df["stncode"].astype(int)
    return df


def idw_interpolation(lon_pts, lat_pts, values,
                      lon_grid, lat_grid, power=2.0, max_dist=None):
    if max_dist is None:
        max_dist = MAX_DIST_MASK
    pts = np.column_stack([lon_pts, lat_pts])
    grid_pts = np.column_stack([lon_grid.ravel(), lat_grid.ravel()])
    d = cdist(grid_pts, pts)
    d = np.where(d < 1e-10, 1e-10, d)
    w = 1.0 / d**power
    w /= w.sum(axis=1, keepdims=True)
    z_flat = w @ values
    tree = cKDTree(pts)
    min_d, _ = tree.query(grid_pts)
    mask = (min_d > max_dist).reshape(lon_grid.shape)
    return np.ma.array(z_flat.reshape(lon_grid.shape), mask=mask)


def build_grid():
    lon = np.arange(LON_MIN, LON_MAX + GRID_STEP, GRID_STEP)
    lat = np.arange(LAT_MIN, LAT_MAX + GRID_STEP, GRID_STEP)
    return np.meshgrid(lon, lat)


def clip_grid_to_geometry(Z, LON, LAT, geometry):
    if geometry is None or not HAS_GIS:
        return Z
    paths = []
    def collect(g):
        if g.geom_type == "Polygon":
            paths.append(Path(np.asarray(g.exterior.coords)))
            for interior in g.interiors:
                paths.append(Path(np.asarray(interior.coords)))
        elif g.geom_type == "MultiPolygon":
            for sub in g.geoms:
                collect(sub)
    collect(geometry)
    if not paths:
        return Z
    pts = np.column_stack([LON.ravel(), LAT.ravel()])
    inside = np.zeros(len(pts), dtype=bool)
    for p in paths:
        inside |= p.contains_points(pts)
    inside = inside.reshape(LON.shape)
    mask = Z.mask | (~inside) if hasattr(Z, "mask") else (~inside)
    return np.ma.array(Z.data, mask=mask)


# ================================================================
# 5. Map helpers
# ================================================================
def draw_gis_background(ax, gis_layers, ne_gdf):
    if not HAS_GIS:
        return
    if gis_layers["adm0"] is not None:
        try:
            gis_layers["adm0"].plot(ax=ax, facecolor="#F7F6F1",
                                    edgecolor="#888888",
                                    linewidth=0.5, zorder=0)
        except Exception:
            pass
    if ne_gdf is not None:
        try:
            ne_gdf.plot(ax=ax, facecolor="white",
                        edgecolor="none", zorder=0.5)
        except Exception:
            pass
    if gis_layers["adm1"] is not None:
        try:
            gis_layers["adm1"].boundary.plot(ax=ax, color="#777777",
                                             linewidth=0.35, zorder=3)
        except Exception:
            pass
    if gis_layers["adm0"] is not None:
        try:
            gis_layers["adm0"].boundary.plot(ax=ax, color="black",
                                             linewidth=0.8, zorder=4)
        except Exception:
            pass


def draw_ne_outline(ax, ne_gdf):
    if ne_gdf is None:
        return
    try:
        ne_gdf.boundary.plot(ax=ax, color="#333333",
                             linewidth=0.7, zorder=4)
    except Exception:
        pass


def setup_map_axes(ax, show_labels=True):
    ax.set_xlim(LON_MIN, LON_MAX)
    ax.set_ylim(LAT_MIN, LAT_MAX)
    ax.set_aspect("equal")
    ax.xaxis.set_major_locator(MultipleLocator(1))
    ax.yaxis.set_major_locator(MultipleLocator(1))
    ax.xaxis.set_minor_locator(MultipleLocator(0.5))
    ax.yaxis.set_minor_locator(MultipleLocator(0.5))
    ax.set_xlabel("Longitude (°E)")
    if show_labels:
        ax.set_ylabel("Latitude (°N)")
    ax.grid(False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(True)
        ax.spines[s].set_linewidth(0.6)
        ax.spines[s].set_color("0.4")


def marker_size(slope, s_min=25, s_max=180):
    a = np.abs(np.asarray(slope, dtype=float))
    if a.max() == 0:
        return np.full_like(a, s_min)
    return s_min + (s_max - s_min) * (a / a.max())


def add_panel_letter(ax, letter, xoff=-0.15, yoff=1.04):
    ax.text(xoff, yoff, letter, transform=ax.transAxes,
            fontsize=13, fontweight="bold", family="serif",
            ha="left", va="bottom", clip_on=False)


def add_scale_bar(ax, length_km=100, lon0=None, lat0=None):
    if lon0 is None:
        lon0 = LON_MAX - 1.3
    if lat0 is None:
        lat0 = LAT_MIN + 0.25
    km_per_deg = 111.32 * np.cos(np.deg2rad((LAT_MIN + LAT_MAX) / 2))
    length_deg = length_km / km_per_deg
    x1, y1 = lon0, lat0
    x2 = lon0 + length_deg
    ax.plot([x1, x2], [y1, y1], color="black", lw=1.6,
            solid_capstyle="butt", zorder=7)
    ax.plot([x1, x1], [y1 - 0.06, y1 + 0.06], color="black", lw=0.9, zorder=7)
    ax.plot([x2, x2], [y1 - 0.06, y1 + 0.06], color="black", lw=0.9, zorder=7)
    ax.text((x1 + x2) / 2, y1 + 0.10, f"{length_km} km",
            ha="center", va="bottom", fontsize=7, zorder=7)


def add_north_arrow(ax, x=None, y=None):
    if x is None:
        x = LON_MAX - 0.35
    if y is None:
        y = LAT_MAX - 0.45
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.32),
                arrowprops=dict(facecolor="black", edgecolor="black",
                                width=1.0, headwidth=5.5, headlength=5),
                ha="center", va="bottom",
                fontsize=8, fontweight="bold", zorder=7)


def draw_stations(ax, df, size_min=30, size_max=200,
                  use_bubbles=True, label_ids=False, id_offset=(0, -11)):
    """
    วาดสถานี — bubble หรือ marker ตาม significance
    """
    colors = np.where(
        df["significant"],
        np.where(df["slope_mm_dec"] < 0, CLR_SIG_DEC, CLR_SIG_INC),
        CLR_NS)

    if use_bubbles:
        sizes = marker_size(df["slope_mm_dec"].values, size_min, size_max)
        ax.scatter(df["lon"], df["lat"], s=sizes, c=colors,
                   edgecolors="black", linewidths=0.6,
                   alpha=0.92, zorder=6)
    else:
        for _, row in df.iterrows():
            if row["significant"]:
                ax.scatter(row["lon"], row["lat"],
                           s=55, c=colors[list(df.index).index(_)],
                           edgecolors="black", linewidths=0.8,
                           zorder=6)
            else:
                ax.scatter(row["lon"], row["lat"], s=40, c="white",
                           edgecolors="black", linewidths=0.8, zorder=6)

    if label_ids:
        for _, row in df.iterrows():
            ax.annotate(str(row["stncode"]),
                        xy=(row["lon"], row["lat"]),
                        xytext=id_offset, textcoords="offset points",
                        ha="center", va="top",
                        fontsize=5.8, color="0.15", zorder=7,
                        bbox=dict(boxstyle="round,pad=0.12",
                                  facecolor="white", edgecolor="none",
                                  alpha=0.75))


# ================================================================
# 6. Figure 4 — Annual spatial (FIXED legend + significance)
# ================================================================
def plot_fig4(df_ann, stn, gis_layers, ne_gdf, ne_geom):
    print("🎨 Figure 4: Annual spatial pattern ...")

    df = df_ann[df_ann["stncode"] != 0].merge(stn, on="stncode")
    df = df.sort_values("slope_mm_dec").reset_index(drop=True)

    LON, LAT = build_grid()
    Z = idw_interpolation(df["lon"].values, df["lat"].values,
                          df["slope_mm_dec"].values, LON, LAT, power=2.0)
    Z = clip_grid_to_geometry(Z, LON, LAT, ne_geom)

    vmax = np.ceil(np.nanmax(np.abs(df["slope_mm_dec"].values)) / 5) * 5
    vmin = -vmax

    fig = plt.figure(figsize=(W_DOUBLE, 108 * MM))
    gs = GridSpec(2, 2, figure=fig,
                  height_ratios=[1, 0.055],
                  hspace=0.32, wspace=0.16,
                  left=0.075, right=0.975,
                  top=0.93, bottom=0.115)

    # ---- Panel a: bubble map ----
    ax1 = fig.add_subplot(gs[0, 0])
    draw_gis_background(ax1, gis_layers, ne_gdf)
    setup_map_axes(ax1, show_labels=True)

    colors = np.where(
        df["significant"],
        np.where(df["slope_mm_dec"] < 0, CLR_SIG_DEC, CLR_SIG_INC),
        CLR_NS)
    sizes = marker_size(df["slope_mm_dec"].values, 40, 240)

    ax1.scatter(df["lon"], df["lat"], s=sizes, c=colors,
                edgecolors="black", linewidths=0.6,
                alpha=0.92, zorder=6)

    # ✅ Station IDs with white halo for readability
    for _, row in df.iterrows():
        ax1.annotate(str(row["stncode"]),
                     xy=(row["lon"], row["lat"]),
                     xytext=(0, -11), textcoords="offset points",
                     ha="center", va="top",
                     fontsize=5.8, color="0.15", zorder=7,
                     bbox=dict(boxstyle="round,pad=0.12",
                               facecolor="white", edgecolor="none",
                               alpha=0.75))

    # ✅ Legend ย้ายไปมุมขวาบน (ว่าง) พร้อม bubble size
    s_ref = [5, 15, 30]
    handles_size = [
        Line2D([], [], marker="o", linestyle="",
               markerfacecolor="none", markeredgecolor="black",
               markeredgewidth=0.7,
               markersize=np.sqrt(marker_size(s, 40, 240)) / 1.35,
               label=f"{s} mm dec$^{{-1}}$")
        for s in s_ref
    ]
    ax1.legend(handles=handles_size,
               loc="upper left", fontsize=7,
               bbox_to_anchor=(0.015, 0.985),
               title="$|$Sen's slope$|$",
               title_fontsize=7.5,
               labelspacing=1.15, handletextpad=0.7,
               borderpad=0.5)

    # ✅ Scale bar ย้ายไปมุมขวา-ล่าง (ห่าง legend)
    add_scale_bar(ax1, lon0=LON_MAX - 1.3, lat0=LAT_MIN + 0.3)
    add_north_arrow(ax1)
    add_panel_letter(ax1, "a", xoff=-0.13, yoff=1.03)
    ax1.set_title("Station-level trends", pad=6, fontsize=9.5)

    # ---- Panel b: IDW clipped ----
    ax2 = fig.add_subplot(gs[0, 1])
    draw_gis_background(ax2, gis_layers, ne_gdf)
    setup_map_axes(ax2, show_labels=True)

    levels = np.linspace(vmin, vmax, 21)
    cf = ax2.contourf(LON, LAT, Z, levels=levels,
                      cmap=CMAP_TREND, extend="both", zorder=2)
    cs = ax2.contour(LON, LAT, Z, levels=levels[::4],
                     colors="black", linewidths=0.4,
                     alpha=0.55, zorder=3)
    ax2.clabel(cs, inline=True, fontsize=6, fmt="%.0f", colors="black")
    draw_ne_outline(ax2, ne_gdf)

    # ✅ Station markers: same as panel a (color-coded by significance)
    marker_colors = np.where(
        df["significant"],
        np.where(df["slope_mm_dec"] < 0, CLR_SIG_DEC, CLR_SIG_INC),
        "black")
    ax2.scatter(df["lon"], df["lat"], s=50, c=marker_colors,
                edgecolors="black", linewidths=0.8, zorder=6)

    add_scale_bar(ax2, lon0=LON_MAX - 1.3, lat0=LAT_MIN + 0.3)
    add_north_arrow(ax2)
    add_panel_letter(ax2, "b", xoff=-0.13, yoff=1.03)
    ax2.set_title("Interpolated surface (IDW, power = 2)",
                  pad=6, fontsize=9.5)

    cax = fig.add_subplot(gs[1, :])
    cb = fig.colorbar(cf, cax=cax, orientation="horizontal")
    cb.set_label("Sen's slope (mm dec$^{-1}$)", fontsize=8.5)
    cb.ax.tick_params(labelsize=7.5)
    cb.outline.set_linewidth(0.6)

    out = os.path.join(FIG_DIR, "fig4_annual_spatial_gis")
    for ext in ("png", "pdf"):
        fig.savefig(f"{out}.{ext}")
    plt.close(fig)


# ================================================================
# 7. Figure 5 — Seasonal comparison (FIXED per-season scales)
# ================================================================
def plot_fig5(df_ann, df_dry, df_wet, stn, gis_layers, ne_gdf, ne_geom):
    print("🎨 Figure 5: Seasonal spatial comparison ...")

    LON, LAT = build_grid()

    seasons = [
        ("Annual",        df_ann, "a"),
        ("Dry (Nov–Apr)", df_dry, "b"),
        ("Wet (May–Oct)", df_wet, "c"),
    ]

    # ✅ Compute per-season color limits for better contrast
    season_data = []
    for label, df_s, letter in seasons:
        d = df_s[df_s["stncode"] != 0].merge(stn, on="stncode")
        Z = idw_interpolation(d["lon"].values, d["lat"].values,
                              d["slope_mm_dec"].values, LON, LAT, power=2.0)
        Z = clip_grid_to_geometry(Z, LON, LAT, ne_geom)
        # Per-season absolute max (rounded up to 5)
        abs_max = np.ceil(np.nanmax(np.abs(Z.compressed())) / 5) * 5
        abs_max = max(abs_max, 5)
        season_data.append((label, d, Z, letter, abs_max))

    reg_path = os.path.join(TAB_A_DIR, "regional_trends.csv")
    reg_df = pd.read_csv(reg_path) if os.path.exists(reg_path) else None

    fig = plt.figure(figsize=(W_DOUBLE, 92 * MM))
    gs = GridSpec(2, 3, figure=fig,
                  height_ratios=[1, 0.055],
                  hspace=0.30, wspace=0.16,
                  left=0.06, right=0.98,
                  top=0.90, bottom=0.135)

    contourfs = []
    for i, (label, d, Z, letter, abs_max) in enumerate(season_data):
        ax = fig.add_subplot(gs[0, i])
        draw_gis_background(ax, gis_layers, ne_gdf)
        setup_map_axes(ax, show_labels=(i == 0))

        vmin, vmax = -abs_max, abs_max
        levels = np.linspace(vmin, vmax, 21)
        cf = ax.contourf(LON, LAT, Z, levels=levels,
                         cmap=CMAP_TREND, extend="both", zorder=2)
        cs = ax.contour(LON, LAT, Z,
                        levels=np.linspace(vmin, vmax, 9)[1:-1],
                        colors="black", linewidths=0.35,
                        alpha=0.5, zorder=3)
        contourfs.append((cf, vmin, vmax))
        draw_ne_outline(ax, ne_gdf)

        colors = np.where(
            d["significant"],
            np.where(d["slope_mm_dec"] < 0, CLR_SIG_DEC, CLR_SIG_INC),
            "black")
        ax.scatter(d["lon"], d["lat"], s=32, c=colors,
                   edgecolors="black", linewidths=0.6, zorder=6)

        # Regional annotation
        if reg_df is not None:
            key = label.split()[0].lower()
            row = reg_df[reg_df["season"].str.lower() == key]
            if len(row) > 0:
                s_val = float(row.iloc[0]["slope_mm_dec"])
                p_val = float(row.iloc[0]["p_value"])
                stars = ("***" if p_val < 0.001 else
                         "**"  if p_val < 0.01  else
                         "*"   if p_val < 0.05  else "n.s.")
                ax.text(0.98, 0.03,
                        f"Regional: {s_val:+.2f} ({stars})",
                        transform=ax.transAxes,
                        ha="right", va="bottom", fontsize=6.8,
                        bbox=dict(boxstyle="round,pad=0.25",
                                  facecolor="white", edgecolor="0.75",
                                  linewidth=0.5, alpha=0.95),
                        zorder=7)

        add_panel_letter(ax, letter, xoff=-0.14, yoff=1.03)
        ax.set_title(label, pad=6, fontsize=9)

        # ✅ Per-panel colorbar (small, below each map)
        #    แสดง scale ของแต่ละฤดูแยกกัน → Wet ไม่ถูก wash out
        cax_i = fig.add_subplot(gs[1, i])
        cb_i = fig.colorbar(cf, cax=cax_i, orientation="horizontal")
        cb_i.set_label(f"Sen's slope (mm dec$^{{-1}}$)", fontsize=7.5)
        cb_i.ax.tick_params(labelsize=6.5)
        cb_i.outline.set_linewidth(0.5)

    out = os.path.join(FIG_DIR, "fig5_seasonal_spatial_gis")
    for ext in ("png", "pdf"):
        fig.savefig(f"{out}.{ext}")
    plt.close(fig)


# ================================================================
# 8. Figure 6 — Significance & uncertainty (FIXED)
# ================================================================
def plot_fig6(df_ann, stn, gis_layers, ne_gdf, ne_geom):
    print("🎨 Figure 6: Significance & uncertainty ...")

    df = df_ann[df_ann["stncode"] != 0].merge(stn, on="stncode")
    df["ci_width"] = (df["slope_hi"] - df["slope_lo"]) * 10

    LON, LAT = build_grid()
    Z_p = idw_interpolation(df["lon"].values, df["lat"].values,
                            df["p_value"].values, LON, LAT, power=2.0)
    Z_ci = idw_interpolation(df["lon"].values, df["lat"].values,
                             df["ci_width"].values, LON, LAT, power=2.0)
    Z_p = clip_grid_to_geometry(Z_p, LON, LAT, ne_geom)
    Z_ci = clip_grid_to_geometry(Z_ci, LON, LAT, ne_geom)

    fig = plt.figure(figsize=(W_DOUBLE, 96 * MM))
    gs = GridSpec(2, 2, figure=fig,
                  height_ratios=[1, 0.055],
                  hspace=0.32, wspace=0.16,
                  left=0.075, right=0.975,
                  top=0.92, bottom=0.125)

    # ---- Panel a: p-value ----
    ax1 = fig.add_subplot(gs[0, 0])
    draw_gis_background(ax1, gis_layers, ne_gdf)
    setup_map_axes(ax1, show_labels=True)

    levels_p = [0, 0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 1.0]
    cf1 = ax1.contourf(LON, LAT, Z_p, levels=levels_p,
                       cmap="viridis_r", extend="max", zorder=2)
    cs1 = ax1.contour(LON, LAT, Z_p, levels=[0.05],
                      colors="red", linewidths=1.5,
                      linestyles="--", zorder=3)
    draw_ne_outline(ax1, ne_gdf)

    for _, row in df.iterrows():
        if row["significant"]:
            ax1.plot(row["lon"], row["lat"], marker="*", markersize=10,
                     markerfacecolor="red", markeredgecolor="black",
                     markeredgewidth=0.6, zorder=7)
        else:
            ax1.plot(row["lon"], row["lat"], marker="o", markersize=4.5,
                     markerfacecolor="white", markeredgecolor="black",
                     markeredgewidth=0.8, zorder=7)

    # ✅ Legend ย้ายไปมุมขวา-บน (ห่างจากสถานี significant ที่อยู่ซ้าย-ล่าง)
    leg_handles = [
        Line2D([], [], marker="*", linestyle="",
               markerfacecolor="red", markeredgecolor="black",
               markeredgewidth=0.6, markersize=10, label="$p$ < 0.05"),
        Line2D([], [], marker="o", linestyle="",
               markerfacecolor="white", markeredgecolor="black",
               markeredgewidth=0.8, markersize=5, label="$p$ ≥ 0.05"),
        Line2D([], [], color="red", lw=1.5, ls="--",
               label="$p$ = 0.05 contour"),
    ]
    ax1.legend(handles=leg_handles, loc="upper right",
               fontsize=7, borderpad=0.5,
               bbox_to_anchor=(0.99, 0.99))

    add_scale_bar(ax1, lon0=LON_MAX - 1.3, lat0=LAT_MIN + 0.3)
    add_panel_letter(ax1, "a", xoff=-0.13, yoff=1.03)
    ax1.set_title("Mann–Kendall $p$-value", pad=6, fontsize=9.5)

    # ✅ Colorbar with explicit tick labels
    cax1 = fig.add_subplot(gs[1, 0])
    cb1 = fig.colorbar(cf1, cax=cax1, orientation="horizontal")
    cb1.set_label("$p$-value", fontsize=8)
    cb1.ax.tick_params(labelsize=7)
    cb1.outline.set_linewidth(0.6)

    # ---- Panel b: CI width (with capped percentile) ----
    ax2 = fig.add_subplot(gs[0, 1])
    draw_gis_background(ax2, gis_layers, ne_gdf)
    setup_map_axes(ax2, show_labels=True)

    # ✅ Cap CI at 90th percentile for better visual contrast
    ci_vals = Z_ci.compressed()
    vmax_ci = np.percentile(ci_vals, 90)
    vmax_ci = np.ceil(vmax_ci / 5) * 5
    levels_ci = np.linspace(0, vmax_ci, 13)

    cf2 = ax2.contourf(LON, LAT, Z_ci, levels=levels_ci,
                       cmap="YlOrRd", extend="max", zorder=2)
    cs2 = ax2.contour(LON, LAT, Z_ci,
                      levels=np.linspace(0, vmax_ci, 5)[1:-1],
                      colors="black", linewidths=0.4,
                      alpha=0.6, zorder=3)
    ax2.clabel(cs2, inline=True, fontsize=6.5, fmt="%.0f", colors="black")
    draw_ne_outline(ax2, ne_gdf)

    ax2.scatter(df["lon"], df["lat"], s=40, c="black",
                edgecolors="white", linewidths=0.7, zorder=6)

    add_scale_bar(ax2, lon0=LON_MAX - 1.3, lat0=LAT_MIN + 0.3)
    add_panel_letter(ax2, "b", xoff=-0.13, yoff=1.03)
    ax2.set_title("95% CI width of Sen's slope", pad=6, fontsize=9.5)

    cax2 = fig.add_subplot(gs[1, 1])
    cb2 = fig.colorbar(cf2, cax=cax2, orientation="horizontal")
    cb2.set_label("CI width (mm dec$^{-1}$)", fontsize=8)
    cb2.ax.tick_params(labelsize=7)
    cb2.outline.set_linewidth(0.6)

    out = os.path.join(FIG_DIR, "fig6_significance_uncertainty_gis")
    for ext in ("png", "pdf"):
        fig.savefig(f"{out}.{ext}")
    plt.close(fig)


# ================================================================
# 9. Export tables
# ================================================================
def export_tables(df_ann, df_dry, df_wet, stn, ne_geom):
    print("💾 Exporting tables ...")
    LON, LAT = build_grid()
    for name, df_s in [("annual", df_ann), ("dry", df_dry), ("wet", df_wet)]:
        d = df_s[df_s["stncode"] != 0].merge(stn, on="stncode")
        Z = idw_interpolation(d["lon"].values, d["lat"].values,
                              d["slope_mm_dec"].values, LON, LAT, power=2.0)
        Z = clip_grid_to_geometry(Z, LON, LAT, ne_geom)
        pd.DataFrame({
            "lon": LON.ravel(), "lat": LAT.ravel(),
            "slope_mm_dec": np.asarray(Z).ravel(),
        }).to_csv(os.path.join(TAB_DIR, f"grid_slope_{name}_gis.csv"),
                  index=False)


# ================================================================
# 10. Main
# ================================================================
def main():
    print("=" * 70)
    print("Stage 2 - Module B (v3 FINAL)")
    print("=" * 70)

    stn = load_stations()
    print(f"   Stations: {len(stn)}")

    gis_layers = load_gis_layers()
    ne_gdf, ne_geom = get_ne_thailand_polygon(gis_layers)
    if ne_geom is None:
        print("⚠️  ไม่มี polygon ภาคอีสาน")

    df_ann = load_trends("annual")
    df_dry = load_trends("dry")
    df_wet = load_trends("wet")

    plot_fig4(df_ann, stn, gis_layers, ne_gdf, ne_geom)
    plot_fig5(df_ann, df_dry, df_wet, stn, gis_layers, ne_gdf, ne_geom)
    plot_fig6(df_ann, stn, gis_layers, ne_gdf, ne_geom)
    export_tables(df_ann, df_dry, df_wet, stn, ne_geom)

    print(f"\n📁 Figures: {os.path.abspath(FIG_DIR)}")


if __name__ == "__main__":
    main()