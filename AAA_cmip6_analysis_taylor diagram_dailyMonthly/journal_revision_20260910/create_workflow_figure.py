import os
from pathlib import Path

BASE = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(BASE / ".matplotlib"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


OUT = BASE / "figure2_workflow_revised.png"


def box(ax, y, text, face, edge, height=0.105, fontsize=16):
    x, width = 0.09, 0.82
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.012,rounding_size=0.018",
        linewidth=2.2,
        edgecolor=edge,
        facecolor=face,
    )
    ax.add_patch(patch)
    ax.text(
        0.5,
        y + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        color="#17202a",
        linespacing=1.15,
    )
    return y, height


def arrow(ax, y1, y2):
    ax.add_patch(
        FancyArrowPatch(
            (0.5, y1),
            (0.5, y2),
            arrowstyle="-|>",
            mutation_scale=20,
            linewidth=2.0,
            color="#4d5656",
        )
    )


fig, ax = plt.subplots(figsize=(6.2, 10.5), dpi=300)
fig.patch.set_facecolor("white")
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis("off")

ax.text(
    0.5,
    0.965,
    "MBCn bias-correction workflow",
    ha="center",
    va="center",
    fontsize=20,
    fontweight="bold",
    color="#17202a",
)
ax.text(
    0.5,
    0.925,
    "All mappings are fitted on 1981-2000 data only",
    ha="center",
    va="center",
    fontsize=13,
    color="#566573",
)

box(ax, 0.79, "Observed and model daily precipitation\n12 gauges x calendar month", "#edf2f7", "#7f8c8d")
arrow(ax, 0.79, 0.765)
box(ax, 0.64, "Initial QDM at each gauge [4]\nPreserve the model's relative quantile change", "#fdebd0", "#d68910")
arrow(ax, 0.64, 0.615)

loop = FancyBboxPatch(
    (0.045, 0.245),
    0.91,
    0.35,
    boxstyle="round,pad=0.012,rounding_size=0.018",
    linewidth=2.2,
    edgecolor="#2874a6",
    facecolor="#ebf5fb",
)
ax.add_patch(loop)
ax.text(0.07, 0.565, "Iterative dependence adjustment (25 passes) [8]", ha="left", va="center", fontsize=15, fontweight="bold", color="#1b4f72")

box(ax, 0.455, "1  Rotate the 12-dimensional field\nwith a seeded random orthogonal matrix", "#d6eaf8", "#3498db", height=0.085, fontsize=14)
arrow(ax, 0.455, 0.43)
box(ax, 0.335, "2  Quantile-map each rotated component\nto the equivalently rotated observations", "#d6eaf8", "#3498db", height=0.085, fontsize=14)
arrow(ax, 0.335, 0.31)
box(ax, 0.255, "3  Reverse the rotation and repeat", "#d6eaf8", "#3498db", height=0.06, fontsize=14)

arrow(ax, 0.245, 0.205)
box(ax, 0.09, "Final rank substitution\nRestore QDM values at every gauge", "#d5f5e3", "#239b56")
arrow(ax, 0.09, 0.065)
ax.text(
    0.5,
    0.025,
    "Output: QDM marginal distributions + adjusted inter-station ranks",
    ha="center",
    va="center",
    fontsize=13,
    color="#196f3d",
    fontweight="bold",
)

plt.savefig(OUT, bbox_inches="tight", pad_inches=0.08, facecolor="white")
plt.close(fig)
print(OUT)
