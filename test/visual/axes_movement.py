from pathlib import Path

import numpy as np

from porescene.scene import Scene

# =============================================================================
# Import Parameters

# repository root, so the script runs from any working directory
pth_root = Path(__file__).resolve().parents[2]

# data directory
pth_data = pth_root / "data"

# output directory for rendered images
pth_out = pth_root / "tmp" / "visual" / Path(__file__).stem
pth_out.mkdir(parents=True, exist_ok=True)

# [m] domain dimensions
dims = np.array((200e-06, 400e-06, 500e-06))

# [°] azimuth step between two renders
ang_step = 15


# =============================================================================
# Scene configuration and rendering

# create a new scene from PoreScene JSON configuration
sc = Scene.from_json(dims, pth_data / "porescene.json")
sc.config_image.width = 1024
sc.config_image.height = 1024

# add axes around the scene
sc.create_axes()

# orbit the camera once around the scene in steps; the rotation is relative, so the
# rulers' flipping and corner snapping accumulate along the way, and the final render
# at 360° has to match the first one at 0°
for ang in range(0, 360 + ang_step, ang_step):
    if ang:
        sc.rotate_azimuth(ang_step)

    # render the scene
    pth_img = sc.render(pth_out / f"axes_{ang:03d}.png")
