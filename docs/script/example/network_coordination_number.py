import runpy
from pathlib import Path

# =============================================================================
# Import Parameters

# tutorial example rendered for the docs
pth_example = Path.cwd() / "example" / "network_coordination_number.py"

# data directory the example renders into
pth_data = Path.cwd() / "data"

# docs image directory
pth_img = Path.cwd() / "docs/source/_static/image/example"


# =============================================================================
# Render and relocate

pth_img.mkdir(parents=True, exist_ok=True)

# remember the colorbar composites already present, then run the example as-is
seen = {p: p.stat().st_mtime for p in pth_data.glob("*+colorbar-*.png")}
runpy.run_path(str(pth_example))

# move each freshly rendered composite into the docs static path, dropping the
# "+colorbar-<align>-<orientation>" suffix from its auto-generated file name
for p in pth_data.glob("*+colorbar-*.png"):
    if seen.get(p) != p.stat().st_mtime:
        p.replace(pth_img / (p.name.split("+colorbar-")[0] + ".png"))
