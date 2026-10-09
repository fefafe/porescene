import json
from pathlib import Path

from porescene import image, worker
from porescene.color.gradient import SegmentedGradient
from porescene.color.palette import Colormap, Palette
from porescene.config import QuantityConfiguration
from porescene.model import PoreNetwork
from porescene.scene import Scene
from porescene.utility import CompassDirection, Orientation

# =============================================================================
# Import Parameters

# data directory
pth_data = Path.cwd() / "data"


# =============================================================================
# Scene configuration

# load variable mapping for variable import from .mat file
with open(pth_data / "map_vars.json") as f:
    map_vars = json.load(f)

# load pore network data from MAT file
pn = PoreNetwork.from_mat(pth_data / "pnm.mat", map_vars["data_network"])

# initialize a new scene
sc = Scene(pn.extent)

# disable the throat cylinders so only the pore spheres remain
sc.config_scene.enable_cylinders = False

# initialize PNM quantity "coordination_number"
sc.config_scene.add_quantity(
    QuantityConfiguration(
        "coordination_number",
        Palette.load(Colormap.TAB10).subset(10),
        gradient_class=SegmentedGradient,
        heading="Pore coordination number [–]",
        orientation=Orientation.VERTICAL,
        align=CompassDirection.EAST,
    )
)

# add cylinders and spheres to the scene
worker.build_structure(sc, pn)

# add axes around the scene
sc.create_axes()


# =============================================================================
# Render pores colored by coordination number

# render the scene and color the pores according to their coordination number
pth_vis = worker.make_coordination_number(pth_data, pn, sc)

# render a colorbar on the same scale, and compose the two
conf = sc.config_scene["coordination_number"]
pth_cb = worker.make_colorbar(pth_data, pn, sc, "coordination_number")
pth_img = image.compose_colorbar(pth_vis, pth_cb, conf.align, conf.orientation)
