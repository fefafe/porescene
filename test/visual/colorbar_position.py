import shutil
from pathlib import Path

import numpy as np

from porescene import image, worker
from porescene.color.palette import Colormap, Palette
from porescene.config import QuantityConfiguration
from porescene.model import PoreNetwork
from porescene.scene import Scene
from porescene.utility import CompassDirection, Orientation

# repository root, so the script runs from any working directory
dir_root = Path(__file__).resolve().parents[2]

# output directory for rendered images
dir_out = dir_root / "tmp" / "visual" / Path(__file__).stem
dir_out.mkdir(parents=True, exist_ok=True)

# the composites are written next to the render, so it is copied into the output first
pth_vis = dir_out / "sticks-radius_spheres-radius_axes.png"
shutil.copy2(dir_root / "tmp" / pth_vis.name, pth_vis)

# both limits are pinned, so no pore network data is read and an empty one will do
conf = QuantityConfiguration(
    "radius",
    Palette.load(Colormap.LIPARI).all(),
    heading="Diameter [µm]",
    precision=0,
    factor=2e6,
    limit_lower=1,
    limit_upper=19,
)

pn = PoreNetwork()
sc = Scene(np.array((1e-3, 1e-3, 1e-3)))
sc.config_scene.add_quantity(conf)

for orientation in Orientation:
    for align in CompassDirection:
        conf.orientation = orientation
        conf.align = align

        # render the colorbar image
        pth_cb = worker.make_colorbar(dir_out, pn, sc, "radius")

        # compose rendered scene and colorbar
        image.compose_colorbar(pth_vis, pth_cb, align, orientation)
