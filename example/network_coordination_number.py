import json
from pathlib import Path

import numpy as np

from porescene import image, worker
from porescene.color.gradient import SegmentedGradient
from porescene.color.palette import Colormap, Palette
from porescene.config import PropertyConfiguration
from porescene.model import PoreNetwork
from porescene.scene import Scene
from porescene.utility import CompassDirection, Orientation


# =============================================================================
# Import Parameters

# data directory
pth_data = Path.cwd() / "data"

# temporary directory for rendered images
pth_tmp = Path.cwd() / "tmp"


# =============================================================================
# Scene configuration and rendering

# load variable mapping for variable import from .mat file
with open(pth_data / "map_vars.json") as f:
    map_vars = json.load(f)

# load pore network data from MAT file
pn = PoreNetwork.from_mat(pth_data / "pnm.mat", map_vars["data_network"])

# load PoreScene config from JSON file
sc = Scene.from_json(pn.extent, pth_data / "porescene.json")

# disable cylinders entirely in the scene
sc.config_scene.enable_cylinders = False

# initialized PNM property "radius"
sc.config_scene.add_property(
    PropertyConfiguration(
        "coordination_number",
        Palette.load(Colormap.TAB10).subset(10),
        heading="Pore coordination number [–]",
        orientation=Orientation.VERTICAL,
        align=CompassDirection.WEST,
        gradient_class=SegmentedGradient,
    )
)

# add cylinders and spheres to the scene
worker.build_structure(sc, pn)

# add axes around the scene
sc.create_axes()

# render the scene and color pores and throat according to their radius
sc, pth_img = worker.make_coordination_number(pth_tmp, pn, sc)

# add padding of 10 %
image.img_pad(pth_img, 0.1, trim=False)
