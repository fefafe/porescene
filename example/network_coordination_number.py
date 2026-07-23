import json
from pathlib import Path

from porescene import worker
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

# initialize PNM property "coordination_number"
sc.config_scene.add_property(
    PropertyConfiguration(
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
pth_img = worker.make_coordination_number(pth_data, pn, sc)
