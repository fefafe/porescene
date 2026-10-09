from pathlib import Path

import numpy as np

from porescene import io, utility
from porescene.scene import Scene

# =============================================================================
# Parameters

# repository root, so the example runs from any working directory
pth_root = Path(__file__).resolve().parents[1]

# input data directory
pth_data = pth_root / "data"

# output directory, named after this example
pth_out = pth_root / "tmp" / "example" / Path(__file__).stem
pth_out.mkdir(parents=True, exist_ok=True)

# [m] edge length of a single voxel
L_vxl = 1e-6

# [vxl] image resolution
res_img = np.array((100, 100, 100))

# [m] domain dimensions
extent = res_img * L_vxl


# =============================================================================
# Meshing

# load and reshape binarized volume image
img_bin = np.fromfile(pth_data / "img_bin.raw", dtype=np.uint8)
img_bin = img_bin.reshape(res_img)

# mesh representation of the volume image
mesh = utility.volume2mesh(img_bin, L_vxl, name="solid")

# export the mesh in binary PLY format
io.mesh2ply(pth_out / "solid.ply", mesh)


# =============================================================================
# Scene configuration and rendering

# initialize a new scene
sc = Scene(extent)

# add axes to the scene
sc.create_axes()

# add a solid object to the scene
sc.create_solid(pth_out / "solid.ply")

# render the scene
pth_img = sc.render(pth_out / "solid+axes.png")
