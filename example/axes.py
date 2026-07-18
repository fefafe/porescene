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

# custom axis labels
sc.config_axes.label_x = "← x axis"
sc.config_axes.label_y = "y axis →"
sc.config_axes.label_z = "← z axis"
sc.config_axes.enable_ticks = False
sc.config_axes.font_size_labels = 1.25
sc.config_axes.line_width = 0.06

# add axes around the scene
sc.create_axes()

# render the scene
pth_img = sc.render(pth_tmp / "axes.png")

# add padding of 10 %
image.img_pad(pth_img, 0.1)
