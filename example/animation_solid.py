from pathlib import Path

import numpy as np

from porescene import image
from porescene.scene import Scene

# =============================================================================
# Import Parameters

# data directory
pth_data = Path.cwd() / "data"

# frames directory
pth_frames = pth_data / "frames"

# [m] domain size
extent = np.array((100e-06, 100e-06, 100e-06))

# [s] video duration
duration = 12

# [frame/second] video frame rate
fps = 30

# [-] total number of frames in the video
frames_total = duration * fps

# =============================================================================
# Scene configuration and rendering

# create a new scene
sc = Scene(extent)

# add axes around the scene
sc.create_axes()

# add a solid object to the scene
sc.create_solid(pth_data / "solid.ply")

for no_frame in range(frames_total):
    # move camera and lights further around the stage
    sc.rotate_azimuth(360 / frames_total)

    # render the scene
    sc.render(pth_frames / f"solid+axes_{no_frame:05d}.png", trim=False)

# compose frames into mp4 video
image.frames2mp4(
    sorted(pth_frames.glob("solid+axes_*.png")),
    pth_data / "solid+axes.mp4",
    fps=fps,
    trim=True,
)
