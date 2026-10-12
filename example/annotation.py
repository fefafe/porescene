import json
from pathlib import Path

from porescene import worker
from porescene.color.palette import Colormap, Palette, fefa
from porescene.layout import (
    DiscreteGradientAnnotation,
    LabelsAnnotation,
    SegmentedGradientAnnotation,
    SmoothGradientAnnotation,
    SVGCanvas,
    TextAnnotation,
    TimestampAnnotation,
)
from porescene.model import PoreNetwork, StateVariableMap
from porescene.scene import Scene
from porescene.utility import CompassDirection, Orientation, px2cm, svg2png

# =============================================================================
# Import Parameters

# repository root, so the example runs from any working directory
pth_root = Path(__file__).resolve().parents[1]

# input data directory
pth_data = pth_root / "data"

# output directory, named after this example
pth_out = pth_root / "tmp" / "example" / Path(__file__).stem
pth_out.mkdir(parents=True, exist_ok=True)

# step of the drying simulation shown in the figure
no_state = 4000

# [cm] margin kept around an annotation saved on its own, so its outline is not clipped
margin = 0.1

# colors of the three states a pore passes through while it dries
color_saturated = fefa.darkblue
color_drying = fefa.pink
color_dry = fefa.yellow


# =============================================================================
# Colorbars

# smooth: the colors blend continuously, the ticks are spread evenly along the bar
cb_smooth = SmoothGradientAnnotation(
    [color_dry, color_drying, color_saturated],
    ["0", "0.25", "0.5", "0.75", "1"],
)
cb_smooth.heading = "Saturation [–]"
cb_smooth.text = ["Share of the pore volume filled with liquid"]
cb_smooth.orientation = Orientation.HORIZONTAL

# segmented: the colors stand in bands, ticked on their boundaries -- so there is one
# tick more than there are colors; the exponent is printed at the high end of the axis
cb_segmented = SegmentedGradientAnnotation(
    Palette.load(Colormap.BATLOW).subset(5),
    ["0", "2", "4", "6", "8", "10"],
)
cb_segmented.heading = "Pore diameter [m]"
cb_segmented.exponent = -6
cb_segmented.orientation = Orientation.HORIZONTAL

# discrete: every color stands for a value of its own, ticked in the middle of its band
cb_discrete = DiscreteGradientAnnotation(
    Palette.load(Colormap.TAB10).subset(6),
    ["1", "2", "3", "4", "5", "6"],
)
cb_discrete.heading = "Coordination number [–]"
cb_discrete.orientation = Orientation.HORIZONTAL


# =============================================================================
# Legend

# one colored box per pore state, for states that carry no scale to put ticks on
legend = LabelsAnnotation()
legend.add_label(color_saturated, "saturated")
legend.add_label(color_drying, "drying")
legend.add_label(color_dry, "dry")
legend.heading = "Pore state"
legend.title.font_size_heading = 14


# =============================================================================
# Save every annotation on its own

for name, element, align in (
    ("cb-saturation", cb_smooth, CompassDirection.SOUTH),
    ("cb-pore-diameter", cb_segmented, CompassDirection.SOUTH),
    ("cb-coordination-number", cb_discrete, CompassDirection.SOUTH),
    ("legend-pore-state", legend, CompassDirection.WEST),
):
    canvas = SVGCanvas(padding=(margin,) * 4)
    canvas.add(element, align)

    # shrink the canvas onto the annotation, read only after it knows its edge
    box = element.bbox()
    canvas.size = (px2cm(box.width) + 2 * margin, px2cm(box.height) + 2 * margin)

    svg2png(canvas.save(pth_out / f"{name}.svg"))


# =============================================================================
# Render the pores of a drying pore network

# load variable mapping for variable import from .mat file
with open(pth_data / "map_vars.json") as f:
    map_vars = json.load(f)

# load pore network data from MAT file
pn = PoreNetwork.from_mat(pth_data / "pnm.mat", map_vars["data_network"])

# load the saturation of every pore at the chosen step of the drying simulation
saturation = StateVariableMap("saturation")
saturation.variable_sphere = "S_p_storage"
pn.load_states_from_mat(pth_data / "pnm-states.mat", [saturation], [no_state])

# sort every pore into one of the three states by its saturation
color_pores = [
    color_saturated if s == 1 else color_dry if s == 0 else color_drying
    for s in pn.states[0].get_quantity("saturation").pore_values
]

# initialize a new scene
sc = Scene(pn.extent)

# disable the throat cylinders so only the pore spheres remain
sc.config_scene.enable_cylinders = False

# add spheres to the scene
worker.build_structure(sc, pn)

# add axes around the scene
sc.create_axes()

# render the scene with every pore colored by its state
pth_render = worker.make_img(
    pth_out, sc, color_spheres=color_pores, name_spheres="state", no_state=no_state
)


# =============================================================================
# Compose the figure

# title in the upper left corner, the simulation step in the upper right one
title = TextAnnotation("Drying pore network", "Pores sorted by their saturation")
stamp = TimestampAnnotation(no_state, unit="", precision=0, prefix="Step")

# the render goes into the middle, scaled into the room the annotations leave
canvas = SVGCanvas((20, 16))
canvas.add_image(pth_render)
canvas.add(title, CompassDirection.NORTHWEST)
canvas.add(stamp, CompassDirection.NORTHEAST)
canvas.add(legend, CompassDirection.WEST)

svg2png(canvas.save(pth_out / "figure-drying.svg"))
