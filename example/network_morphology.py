from pathlib import Path

from porescene import worker
from porescene import image
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

# load PoreScene config from JSON file
sc = Scene.from_json(dims, pth_data / "porescene.json")

# initialized PNM property "radius"
sc.config_scene.add_property(
    PropertyConfiguration(
        "radius",
        Palette.load(Colormap.LIPARI).all(),
        heading="Diameter [µm]",
        orientation=Orientation.VERTICAL,
        align=CompassDirection.WEST,
        precision=0,
        factor=2e6,  # converts radius in [m] to diameter in [µm]
    )
)

# add cylinders and spheres to the scene
worker.build_structure(sc, pn, False)

# add axes around the scene
sc.create_axes()

# add a solid object to the scene
sc.create_solid(pth_data / "solid.ply")

# render the scene and color pores and throat according to their radius
sc, pth_img = worker.make_radius(pth_tmp, pn, sc)

# add padding of 10 %
image.img_pad(pth_img, 0.1, trim=False)
