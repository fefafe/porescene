from pathlib import Path

from porescene import image
from porescene.scene import Scene

# =============================================================================
# Import Parameters

# data directory
pth_data = Path.cwd() / "data"

# temporary directory for rendered images
pth_tmp = Path.cwd() / "tmp"

# [m] domain dimensions
dims = (100e-06, 100e-06, 100e-06)


# =============================================================================
# Scene configuration and rendering

# create a new scene from PoreScene JSON configuration
sc = Scene.from_json(dims, pth_data / "porescene.json")

# add axes around the scene
sc.create_axes()

# add a solid object to the scene
sc.create_solid(pth_data / "solid.ply")

# render the scene
pth_img = sc.render(pth_tmp / "solid+axes.png")

# add padding of 10 %
image.img_pad(pth_img, 0.1)
