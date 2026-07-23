import json
from pathlib import Path

import numpy as np

from porescene import worker
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
pn.pore_radius = np.ones(pn.pore_count) * 0.4e-6
pn.throat_radius = np.ones(pn.throat_count()) * 0.2e-6

# load PoreScene config from JSON file
sc = Scene.from_json(pn.extent, pth_data / "porescene.json")

# add cylinders and spheres to the scene
worker.build_structure(sc, pn)

# add axes around the scene
sc.create_axes()

# render the scene
pth_img = worker.make_structure(pth_data, pn, sc)
