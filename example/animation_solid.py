from pathlib import Path

import numpy as np

from porescene import image
from porescene.scene import Scene

# =============================================================================
# Import Parameters

# repository root, so the example runs from any working directory
pth_root = Path(__file__).resolve().parents[1]

# input data directory
pth_data = pth_root / "data"

# output directory, named after this example
pth_out = pth_root / "tmp" / "example" / Path(__file__).stem

# frames directory
pth_frames = pth_out / "frames"
pth_frames.mkdir(parents=True, exist_ok=True)

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

# add the solid object exported by the solid example to the scene
sc.create_solid(pth_data / "solid.ply")

for no_frame in range(frames_total):
    # move camera and lights further around the stage
    sc.rotate_azimuth(360 / frames_total)

    # render the scene
    sc.render(pth_frames / f"solid+axes_{no_frame:05d}.png", trim=False)

# compose frames into mp4 video
image.frames2mp4(
    sorted(pth_frames.glob("solid+axes_*.png")),
    pth_out / "solid+axes.mp4",
    fps=fps,
    trim=True,
)
