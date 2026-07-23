import json
from pathlib import Path

import numpy as np

from porescene import worker
from porescene.color.palette import fefa
from porescene.model import PoreNetwork
from porescene.scene import Scene

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

# unify pore and throat radii
pn.pore_radius = np.ones(pn.pore_count) * 0.6e-6
pn.throat_radius = np.ones(pn.throat_count()) * 0.1e-6

# load PoreScene config from JSON file
sc = Scene(pn.extent)

# add cylinders and spheres to the scene
worker.build_structure(sc, pn)

# add axes around the scene
sc.create_axes()

# color every pore orange and every throat dark green
color_pores = [fefa.orange for _ in range(pn.pore_count)]
color_throats = [fefa.darkgreen for _ in range(pn.throat_count())]

# render the scene with uniform pore and throat colors
worker.make_img(
    pth_data,
    sc,
    color_spheres=color_pores,
    color_cylinders=color_throats,
    name_spheres="orange",
    name_cylinders="green",
)
