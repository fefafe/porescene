from pathlib import Path

import numpy as np

from porescene import io, utility
from porescene.color.palette import Colormap, Palette
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

# load and reshape segmented volume image
img_seg = np.fromfile(pth_data / "img_seg.raw", dtype=np.uint32)
img_seg = img_seg.reshape(res_img)

# void clusters carry labels 1..N; label 0 is the surrounding solid phase
labels = np.unique(img_seg)
labels = labels[labels != 0]

# one mesh per void cluster, named "label_1", "label_2", ...
meshes = utility.volume2mesh(img_seg, L_vxl, labels, per_label=True, name="label")

# export all clusters as separate objects in a single OBJ file
io.mesh2obj(pth_data / "segmentation-void.obj", meshes)


# =============================================================================
# Scene configuration and rendering

# initialize a new scene
sc = Scene(extent)

# add axes to the scene
sc.create_axes()

# add the void clusters to the scene
sc.create_clusters(pth_data / "segmentation-void.obj")

# color each cluster with a random color drawn from a colormap
sc.apply_colors("Clusters", Palette.load(Colormap.TURBO).random(len(labels)))

# render the scene
pth_img = sc.render(pth_data / "cluster-random+axes.png")
