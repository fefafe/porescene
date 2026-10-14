from pathlib import Path

import h5py
import numpy as np

from porescene import image
from porescene.color.gradient import SmoothGradient
from porescene.color.palette import Colormap, Palette
from porescene.layout import SmoothGradientAnnotation, SVGCanvas
from porescene.scene import Scene
from porescene.utility import (
    CompassDirection,
    Orientation,
    colorbar_limits,
    colorbar_ticks,
    svg2png,
    tick_labels,
)

# =============================================================================
# Import Parameters

# repository root, so the example runs from any working directory
pth_root = Path(__file__).resolve().parents[1]

# input data directory
pth_data = pth_root / "data"

# output directory, named after this example
pth_out = pth_root / "tmp" / "example" / Path(__file__).stem
pth_out.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Data Import

# MATLAB stores its arrays transposed and counts from one, so every array is turned
# around and every index lowered by one
with h5py.File(pth_data / "pnm.mat") as f:
    # [m] domain dimensions
    extent = np.array(
        [f[k][()].item() for k in ("L_sample_x", "L_sample_y", "L_sample_z")]
    )

    # [m] positions of all cell corners
    pos_corners = np.array(f["pos_cv_corner"]).T

    # indices of the corners of each cell, stored in a MATLAB cell array
    corners = [np.array(f[ref]).ravel().astype(int) - 1 for ref in f["vtx_cv"][0]]

    # indices of the cells touching the domain boundary
    cells_boundary = np.array(f["cv_boundary"]).ravel().astype(int) - 1

    # [-] porosity of each cell
    porosity = np.array(f["epsilon_cv"]).ravel()


# =============================================================================
# Color scale

# widen the porosity range outward to round limits and spread the ticks evenly between
# them, one per tenth
limit_lower, limit_upper = colorbar_limits(porosity.min(), porosity.max(), precision=1)
ticks = tick_labels(colorbar_ticks(limit_lower, limit_upper, num_ticks=7))

# the cells and the colorbar share one palette and one pair of limits
colors = Palette.load(Colormap.BATLOW).all()
gradient = SmoothGradient(colors, limit_lower, limit_upper)


# =============================================================================
# Scene configuration and rendering

# initialize a new scene
sc = Scene(extent)

# add axes around the scene
sc.create_axes()

# add the cells to the scene; the cells are opaque, so only those on the domain boundary
# can be seen and the inner ones are left out
sc.create_cells(pos_corners, corners, selection=cells_boundary)

# color each cell by its porosity
sc.apply_colors("Cells", gradient(porosity))

# render the scene
pth_vis = sc.render(pth_out / "cell-porosity+axes.png")


# =============================================================================
# Colorbar

cb = SmoothGradientAnnotation(colors, ticks)
cb.heading = "Porosity [–]"
cb.orientation = Orientation.VERTICAL

# render the colorbar, and compose it with the scene
canvas = SVGCanvas().add(cb, CompassDirection.WEST)
pth_cb = svg2png(canvas.save(pth_out / "cb-porosity.svg"))
pth_img = image.compose_colorbar(
    pth_vis, pth_cb, CompassDirection.WEST, Orientation.VERTICAL
)
