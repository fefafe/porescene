import json
from pathlib import Path

from porescene import worker
from porescene.color.palette import Colormap, Palette
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

# initialize a new scene
sc = Scene(pn.extent)

# add cylinders and spheres to the scene
worker.build_structure(sc, pn)

# add axes around the scene
sc.create_axes()


# =============================================================================
# Render with a continuous palette

# draw random colors from a continuous colormap (neighbours get similar hues)
sc.config_scene.palette = Palette.load(Colormap.ROMAO)

# render the network with one random color per pore and throat
pth_img = worker.make_random(pth_data, pn, sc)

# rename the render after the palette used, so the next one does not overwrite it
pth_img.replace(pth_img.with_stem("random-continuous"))


# =============================================================================
# Render with a qualitative palette

# draw random colors from a qualitative colormap (colors meant to be told apart)
sc.config_scene.palette = Palette.load(Colormap.SET1)

# render the network again with one random color per pore and throat
pth_img = worker.make_random(pth_data, pn, sc)

# rename the render after the palette used
pth_img.replace(pth_img.with_stem("random-qualitative"))
