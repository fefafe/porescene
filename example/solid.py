from pathlib import Path

from porescene import image
from porescene.scene import Scene


# ==============================================================
# Import Parameters

# relative CT scan path
pth_data = Path.cwd() / "./data/"
pth_tmp = Path.cwd() / "./tmp/"

# [m] domain dimensions
dims = (100e-06, 100e-06, 100e-06)


# ==============================================================
# Scene configuration and rendering

sc = Scene.from_json(dims, pth_data / "porescene.json")
sc.create_camera("3D")
sc.create_lights()
sc.create_axes()
sc.create_solid(pth_data / "Solid.obj")
pth_img = sc.render(pth_tmp, "solid")

image.img_trim(pth_img, 50)
