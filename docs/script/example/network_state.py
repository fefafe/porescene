import runpy
from pathlib import Path

# =============================================================================
# Import Parameters

# tutorial example rendered for the docs
pth_example = Path.cwd() / "example" / "network_state.py"

# frames directory the example renders its states into
pth_frames = Path.cwd() / "data" / "frames"

# docs image directory -- the states are shown as a carousel, not as single figures
pth_img = Path.cwd() / "docs/source/_static/image/carousel/example"


# =============================================================================
# Render and relocate

pth_img.mkdir(parents=True, exist_ok=True)

# remember the colorbar composites already present, then run the example as-is
seen = {p: p.stat().st_mtime for p in pth_frames.glob("*+colorbar-*.png")}
runpy.run_path(str(pth_example))

# move each freshly rendered composite -- one per state and property -- into the docs
# static path, dropping the "+colorbar-<align>-<orientation>" suffix from its file name
for p in pth_frames.glob("*+colorbar-*.png"):
    if seen.get(p) != p.stat().st_mtime:
        p.replace(pth_img / (p.name.split("+colorbar-")[0] + ".png"))
