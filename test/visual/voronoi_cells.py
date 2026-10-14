from pathlib import Path

import bpy
import h5py
import numpy as np
from PIL import Image

from porescene.color import ColorArray
from porescene.scene import Scene

# =============================================================================
# Import Parameters

# repository root, so the script runs from any working directory
pth_root = Path(__file__).resolve().parents[2]

# data directory
pth_data = pth_root / "data"

# output directory for rendered images
pth_out = pth_root / "tmp" / "visual" / Path(__file__).stem
pth_out.mkdir(parents=True, exist_ok=True)

# [-] widths of the rounded cell edges to compare, as fractions of the mean cell size
bevels = (0, 0.05, 0.15)

# bevel width of the render that builds every cell rather than the boundary ones only
bevel_all = 0.05


# =============================================================================
# Data Import

# MATLAB stores its arrays transposed and counts from one
with h5py.File(pth_data / "pnm.mat") as f:
    extent = np.array(
        [f[k][()].item() for k in ("L_sample_x", "L_sample_y", "L_sample_z")]
    )
    pos_corners = np.array(f["pos_cv_corner"]).T
    corners = [np.array(f[ref]).ravel().astype(int) - 1 for ref in f["vtx_cv"][0]]
    cells_boundary = np.array(f["cv_boundary"]).ravel().astype(int) - 1

# color every cell by where it sits, its x, y and z coordinate setting its red, green
# and blue: the faces of the domain show smooth two-dimensional gradients, in which a
# cell that took the color of another stands out, as does a missing cell. Neighboring
# cells differ only slightly in color, so the bevel alone has to tell them apart.
centers = np.array([pos_corners[c].mean(axis=0) for c in corners])
colors = ColorArray.from_nrgb(*(centers / extent).T)


# =============================================================================
# Scene configuration and rendering


def render(bevel: float, selection: np.ndarray | None, name: str) -> Path:
    # the cells are built once per scene, so each render starts from an empty one
    bpy.ops.wm.read_factory_settings()
    sc = Scene(extent)
    sc.config_image.width = 1024
    sc.config_image.height = 1024
    sc.create_cells(pos_corners, corners, selection=selection, bevel=bevel)
    sc.apply_colors("Cells", colors)
    return sc.render(pth_out / f"{name}.png")


# the bevel separates neighboring cells: none at 0, a thin groove at the default, a
# broad one at the largest width
for bevel in bevels:
    render(bevel, cells_boundary, f"cells-position+bevel-{bevel}")

# the opaque cells hide the inner ones, so building all cells must give the same image
# as building the boundary cells only
pth_all = render(bevel_all, None, f"cells-position+bevel-{bevel_all}+all")
pth_boundary = pth_out / f"cells-position+bevel-{bevel_all}.png"
img_all, img_boundary = (
    np.asarray(Image.open(p).convert("RGBA"), dtype=int) for p in (pth_all, pth_boundary)
)
if img_all.shape == img_boundary.shape:
    diff = np.abs(img_all - img_boundary).max()
    print(f"Largest difference between all and boundary cells: {diff} of 255")
else:
    print(f"All and boundary cells differ in size: {img_all.shape} {img_boundary.shape}")
