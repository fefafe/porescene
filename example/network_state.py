import json
from pathlib import Path

from porescene import image, worker
from porescene.color.palette import Colormap, Palette
from porescene.config import QuantityConfiguration
from porescene.model import PoreNetwork, StateVariableMap
from porescene.scene import Scene
from porescene.utility import CompassDirection, Orientation

# =============================================================================
# Import Parameters

# data directory
pth_data = Path.cwd() / "data"

# frames directory
pth_frames = pth_data / "frames"


# =============================================================================
# Data Import

# load variable mapping for variable import from .mat file
with open(pth_data / "map_vars.json") as f:
    map_vars = json.load(f)

# map the concentration state field to its per-pore .mat variable
concentration = StateVariableMap("concentration")
concentration.variable_sphere = "C_p_storage"
concentration.variable_cylinder = "C_t_storage"

vars_state = [concentration]

# distinct simulation steps to visualize
no_states = (0, 500, 600, 700, 800, 930)

# load the pore network together with the selected states from the MAT file
pn = PoreNetwork.from_mat(
    pth_data / "pnm-states.mat",
    map_vars["data_network"],
    vars_state,
    no_states,
)


# =============================================================================
# Scene configuration

# initialize scene
sc = Scene(pn.extent)

# settings for concentration visualizations
sc.config_scene.add_quantity(
    QuantityConfiguration(
        "concentration",  # key that should match with the StateVariableMap
        Palette.load(Colormap.MATTER).all(),  # colormap
        heading="Concentration [mol/l]",  # colorbar label
        orientation=Orientation.VERTICAL,  # colorbar orientation
        align=CompassDirection.WEST,  # colorbar position around the rendering
        precision=3,  # precision of colorbar ticks
        use_global_boundaries=True,  # clamp colorbar imits to series minimum/maximum
        min=0,
        max=50,
    )
)

# add cylinders and spheres to the scene
worker.build_structure(sc, pn)

# add axes around the scene
sc.create_axes()


# =============================================================================
# Render each state

# render every selected state, coloring the pore spheres by concentration
for no_state in no_states:
    renders = worker.make_state(pth_frames, pn, sc, no_state=no_state)

    # a colorbar is rendered and composed onto every image afterwards
    for name, render in renders.items():
        conf = sc.config_scene[name]
        cb = worker.make_colorbar(
            pth_frames / f"cb-{name}.svg", conf, render.lower, render.upper
        )
        image.compose_colorbar(
            render.path, cb.path.with_suffix(".png"), conf.align, conf.orientation
        )
