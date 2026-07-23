import runpy
from pathlib import Path

# =============================================================================
# Import Parameters

# tutorial example rendered for the docs
pth_example = Path.cwd() / "example" / "segmentation.py"

# data directory the example renders into
pth_data = Path.cwd() / "data"

# docs image directory
pth_img = Path.cwd() / "docs/source/_static/image/example"


# =============================================================================
# Render and relocate

pth_img.mkdir(parents=True, exist_ok=True)

# remember the renders already present, then run the example as-is
seen = {p: p.stat().st_mtime for p in pth_data.glob("*.png")}
runpy.run_path(str(pth_example))

# move every image the run produced into the docs static path
for p in pth_data.glob("*.png"):
    if seen.get(p) != p.stat().st_mtime:
        p.replace(pth_img / p.name)
