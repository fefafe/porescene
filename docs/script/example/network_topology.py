import runpy
import shutil
from pathlib import Path

# =============================================================================
# Import Parameters

# tutorial example rendered for the docs
pth_example = Path.cwd() / "example" / "network_topology.py"

# output directory the example renders into, named after it
pth_out = Path.cwd() / "tmp" / "example" / pth_example.stem

# docs image directory
pth_img = Path.cwd() / "docs/source/_static/image/example"


# =============================================================================
# Render and relocate

pth_img.mkdir(parents=True, exist_ok=True)

# start from an empty output directory, so everything in it afterwards is from this run
shutil.rmtree(pth_out, ignore_errors=True)
runpy.run_path(str(pth_example))

# move every image the run produced into the docs static path
for p in pth_out.glob("*.png"):
    p.replace(pth_img / p.name)
