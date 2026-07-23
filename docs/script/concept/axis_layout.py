from pathlib import Path

import numpy as np

from porescene.scene import Scene

# =============================================================================
# Import Parameters

# temporary directory for rendered images
pth_img = Path.cwd() / "docs/source/_static/image/concept"

# [m] domain extent
extent = np.array((100e-06, 100e-06, 100e-06))


# =============================================================================
# Scene configuration and rendering

# create a new scene from PoreScene JSON configuration
sc = Scene(extent)

# custom axis labels
sc.config_axes.label_x = "← x axis"
sc.config_axes.label_y = "y axis →"
sc.config_axes.label_z = "← z axis"
sc.config_axes.enable_ticks = False
sc.config_axes.font_size_labels = 1.25
sc.config_axes.line_width = 0.06

# add axes around the scene
sc.create_axes()

# render the scene
pth_img = sc.render(pth_img / "axes.png")
