from pathlib import Path

from porescene import image
from porescene.scene import Scene


# ==============================================================
# Import Parameters

# data directory
pth_data = Path.cwd() / "data"

# temporary directory for rendered images
pth_tmp = Path.cwd() / "tmp"

# [m] domain dimensions
dims = (100e-06, 100e-06, 100e-06)


# ==============================================================
# Scene configuration and rendering

# create a new scene from PoreScene JSON configuration
sc = Scene.from_json(dims, pth_data / "porescene.json")

# add axes around the scene
sc.create_axes()

# add a solid object to the scene
sc.create_solid(pth_data / "solid.ply")

# render the scene
pth_img = sc.render(pth_tmp, "solid")

# trim whitespace from the renderen PNG, add a padding of 50 px
image.img_trim(pth_img, 50)
