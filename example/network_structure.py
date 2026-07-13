from pathlib import Path

from porescene import worker
from porescene import image
from porescene.model import PoreNetwork
from porescene.scene import Scene

# ==============================================================
# Import Parameters

# data directory
pth_data = Path.cwd() / "data"

# temporary directory for rendered images
pth_tmp = Path.cwd() / "tmp"

# [m] domain dimensions
dims = (100e-06, 100e-06, 100e-06)


# ==============================================================
# Scene configuration

# load pore network data from MAT file
pn = PoreNetwork.from_mat(pth_data / "pnm.mat")

# load PoreScene config from JSON file
sc = Scene.from_json(dims, pth_data / "porescene.json")

# add cylinders and spheres to the scene
worker.build_structure(sc, pn, False)

# render the scene
sc, pth_img = worker.make_structure(pth_tmp, pn, sc)

# add padding of 10 %
image.img_pad(pth_img, 0.1)
