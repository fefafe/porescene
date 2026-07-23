import json
from pathlib import Path

from porescene import worker
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

# initialize PNM property "radius"
sc.config_scene.add_property(
    PropertyConfiguration(
        "radius",
        Palette.load(Colormap.EMBER).reversed(),
        heading="Diameter [µm]",
        orientation=Orientation.VERTICAL,
        align=CompassDirection.WEST,
        precision=0,
        factor=2e6,  # converts radius in [m] to diameter in [µm]
    )
)

# add cylinders and spheres to the scene
worker.build_structure(sc, pn)

# add axes around the scene
sc.create_axes()


# =============================================================================
# Render pores and throats colored by radius

# render the scene and color pores and throats according to their radius
pth_img = worker.make_radius(pth_data, pn, sc)


# =============================================================================
# Render the solid with throats only

# add a solid object to the scene
sc.create_solid(pth_data / "solid.ply")

# disable the pore spheres so only the solid and throats remain
sc.config_scene.enable_spheres = False

# change the colormap for radius property
sc.config_scene["radius"].colors = Palette.load(Colormap.SPEED).all()

# render the scene and color the throats according to their radius
pth_img = worker.make_radius(pth_data, pn, sc)
