from pathlib import Path

import numpy as np

from porescene import io, utility
from porescene.scene import Scene

# =============================================================================
# Parameters

# data subdirectory
pth_data = Path.cwd() / "data"

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
io.mesh2ply(pth_data / "solid.ply", mesh)


# =============================================================================
# Scene configuration and rendering

# initialize a new scene
sc = Scene(extent)

# add axes to the scene
sc.create_axes()

# add a solid object to the scene
sc.create_solid(pth_data / "solid.ply")

# render the scene
pth_img = sc.render(pth_data / "solid+axes.png")
