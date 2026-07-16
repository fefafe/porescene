from pathlib import Path

import numpy as np

from porescene import worker
from porescene import image
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

# [m] domain dimensions
dims = (100e-06, 100e-06, 100e-06)


# =============================================================================
# Scene configuration and rendering

# load pore network data from MAT file
pn = PoreNetwork.from_mat(pth_data / "pnm.mat")

# unify throat radii to 1 µm
pn.throat_radius = np.ones(pn.throat_count) * 1e-6

# load PoreScene config from JSON file
sc = Scene.from_json(dims, pth_data / "porescene.json")
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
worker.build_structure(sc, pn, False)

# add axes around the scene
sc.create_axes()

# render the scene and color pores and throat according to their radius
sc, pth_img = worker.make_coordination_number(pth_tmp, pn, sc)

# add padding of 10 %
image.img_pad(pth_img, 0.1, trim=False)
