#!/usr/bin/env python3
"""Figure 1: Study area map for Nan Province using matplotlib only."""

import warnings
warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
from pathlib import Path

plt.rcParams.update({
    'font.family': 'Times New Roman',
    'font.size': 10,
    'axes.linewidth': 0.8,
    'figure.dpi': 150,
    'savefig.dpi': 600,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.05,
})

BASE   = Path(r'C:\MyPython\CMIP6Nan')
STA_F  = BASE / 'Station_latitude_longitude.csv'
OUT_D  = BASE / 'trend_analysis_output' / 'figures'

sta_df = pd.read_csv(STA_F)
print("Stations loaded:", len(sta_df))
print(sta_df.head())

# ── Approximate Nan Province boundary (simplified polygon from geodata) ──────
# Nan Province approximate boundary (hand-digitised bounding box + key vertices)
nan_lon = [100.35, 100.40, 100.50, 100.65, 100.85, 101.00, 101.10, 101.20,
           101.15, 101.10, 101.05, 100.95, 100.80, 100.70, 100.60, 100.55,
           100.45, 100.35, 100.35]
nan_lat = [18.10, 17.97, 17.92, 18.00, 17.95, 18.05, 18.20, 18.40,
           18.70, 18.95, 19.10, 19.35, 19.56, 19.50, 19.40, 19.20,
           18.90, 18.50, 18.10]

# ── Neighbouring provinces (rough centres) ──────────────────────────────────
neighbours = {
    'Phrae':    (100.14, 18.15),
    'Uttaradit':(100.10, 17.62),
    'Phitsanulok': (100.25, 16.83),
    'Phayao':   (100.20, 19.15),
    'Chiang Rai': (99.83, 19.90),
    'Luang Prabang\n(Laos)': (102.13, 19.88),
}

fig, axes = plt.subplots(1, 2, figsize=(7.2, 5.5),
                          gridspec_kw={'width_ratios': [1, 2.8]},
                          constrained_layout=True)

# ── Left panel: Thailand location map ─────────────────────────────────────
ax_loc = axes[0]
# Draw simplified Thailand outline (rough approximation)
th_lon = [97.5, 98.0, 99.0, 100.0, 100.5, 101.5, 102.5, 103.5, 104.5, 105.5,
          105.6, 104.5, 103.5, 102.5, 101.5, 100.5, 99.5, 98.5, 97.5, 97.5]
th_lat = [20.5, 20.5, 20.3, 20.4, 20.5, 20.5, 20.3, 20.0, 19.5, 18.5,
          16.5, 13.5, 12.5, 12.0, 11.0, 7.0, 5.7, 5.7, 6.5, 20.5]

ax_loc.fill(th_lon, th_lat, color='#E8E8E8', zorder=1, linewidth=0)
ax_loc.plot(th_lon, th_lat, color='#888888', lw=0.8, zorder=2)

# Mark Nan Province as red box
nan_box_lon = [100.35, 101.20, 101.20, 100.35, 100.35]
nan_box_lat = [17.92, 17.92, 19.56, 19.56, 17.92]
ax_loc.fill(nan_box_lon, nan_box_lat, color='#d73027', alpha=0.7, zorder=3)
ax_loc.plot(nan_box_lon, nan_box_lat, color='#d73027', lw=1.0, zorder=4)

ax_loc.set_xlim(97.0, 106.0)
ax_loc.set_ylim(5.0, 21.5)
ax_loc.set_xlabel('Longitude (°E)', fontsize=8)
ax_loc.set_ylabel('Latitude (°N)', fontsize=8)
ax_loc.set_title('(a) Location map', loc='left', fontweight='bold', fontsize=9)
ax_loc.text(101.5, 18.7, 'NAN', fontsize=7, fontweight='bold', color='white', zorder=5,
            ha='center', va='center')
ax_loc.text(101.0, 13.5, 'THAILAND', fontsize=7, color='#555555', ha='center')
ax_loc.tick_params(labelsize=7.5)
ax_loc.set_aspect('equal')

# ── Right panel: Nan Province detail ─────────────────────────────────────
ax = axes[1]

# Province fill
ax.fill(nan_lon, nan_lat, color='#f5f5f5', zorder=1, linewidth=0)
ax.plot(nan_lon, nan_lat, color='#333333', lw=1.2, zorder=2)

# River (Nan River - approximate)
river_lon = [100.95, 100.90, 100.85, 100.80, 100.75, 100.78, 100.75, 100.72,
             100.70, 100.65, 100.63, 100.60, 100.55, 100.50, 100.45]
river_lat = [19.20, 19.00, 18.80, 18.60, 18.40, 18.20, 18.10, 18.00,
             17.90, 17.80, 17.75, 17.70, 17.65, 17.60, 17.55]
ax.plot(river_lon, river_lat, color='#5bafd6', lw=1.8, zorder=3,
        solid_capstyle='round', label='Nan River (approx.)')

# Elevation shading (simple gradient background)
from matplotlib.colors import LinearSegmentedColormap
# Add elevation hint with terrain colours
x_grid = np.linspace(100.35, 101.20, 50)
y_grid = np.linspace(17.92, 19.56, 50)
X, Y = np.meshgrid(x_grid, y_grid)
# Higher elevations on edges (rough approximation)
Z = (np.sin((X-100.35)*5) * np.cos((Y-17.92)*3) * 300 + 400)
ax.contourf(X, Y, Z, levels=5, cmap='terrain', alpha=0.25, zorder=1)

# Plot stations
unique_elev_label = True
for _, row in sta_df.iterrows():
    ax.scatter(row['longitude'], row['latitude'],
               c='#d73027', s=55, zorder=6, edgecolors='white',
               linewidths=0.8, marker='^',
               label='Rain gauge station' if unique_elev_label else '')
    unique_elev_label = False
    # Station label (rotated to avoid overlap)
    ax.annotate(str(int(row['Station_ID'])),
                xy=(row['longitude'], row['latitude']),
                xytext=(5, 4), textcoords='offset points',
                fontsize=5.5, color='#333333', zorder=7)

# Province name
ax.text(100.775, 18.74, 'Nan Province', fontsize=10.5, fontweight='bold',
        color='#333333', ha='center', va='center', zorder=8,
        style='italic')

# Scale bar
scale_lon = [100.40, 100.55]
scale_lat = [18.05, 18.05]
ax.plot(scale_lon, scale_lat, 'k-', lw=2.0, zorder=8)
ax.text(np.mean(scale_lon), 18.02, '~15 km', ha='center', fontsize=7,
        color='black', zorder=9)

# North arrow
ax.annotate('', xy=(101.10, 19.45), xytext=(101.10, 19.25),
            arrowprops=dict(arrowstyle='->', color='black', lw=1.5),
            zorder=8)
ax.text(101.10, 19.50, 'N', ha='center', va='bottom', fontsize=9,
        fontweight='bold', zorder=9)

# Grid
ax.grid(True, lw=0.4, ls=':', color='#cccccc', alpha=0.7)
ax.set_xlim(100.30, 101.28)
ax.set_ylim(17.85, 19.65)
ax.set_xlabel('Longitude (°E)', fontsize=9, labelpad=4)
ax.set_ylabel('Latitude (°N)', fontsize=9, labelpad=4)
ax.set_aspect('equal')
ax.set_title('(b) Rain-gauge network, Nan Province', loc='left',
             fontweight='bold', fontsize=9)
ax.tick_params(labelsize=8)

# Coordinate tick labels
ax.xaxis.set_major_locator(plt.MultipleLocator(0.2))
ax.yaxis.set_major_locator(plt.MultipleLocator(0.3))

# Legend
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles, labels, loc='lower left', fontsize=7.5, framealpha=0.9)

fig.suptitle(
    f'Figure 1  Study area: Nan Province, northern Thailand\n'
    f'({len(sta_df)} rain-gauge stations, 1981–2014; triangles = gauge locations)',
    fontsize=9.5, fontweight='bold')
fig.savefig(OUT_D / 'Fig1_Study_Area.png')
plt.close(fig)
print("Fig1_Study_Area.png saved!")
