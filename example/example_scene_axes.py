from random import choice, randint
import sys
from pathlib import Path

import numpy as np

import porescene
import porescene.config
from porescene.color.gradient import SegmentedGradient
from porescene.color.palette import fefa
from porescene.color.palette.fefa import FeFaPalette
from porescene.model import PoreNetwork
from porescene.scene import Scene
from porescene.utility import CompassDirection, Orientation
from porescene.worker import (
    build_structure,
    make_clusters,
    make_coordination_number,
    make_radius,
    make_random,
    make_state,
)

# ============================================================================
# Import Parameters

# absolute data path
pth_abs_data = Path("/Data/")

# network id
# id_nwk = "R_100x100x100_r@1.66_36cae45e-eaab-4ecd-bdf2-ec1be02dbcd3"
# id_nwk = "A_13x13x13_r@1.66_88dc59ee-c3c1-467d-9201-60b56a3d45c3"
# id_nwk = "R_250x50x500_r@14.56_c8228342-5c71-4307-93b1-749e072b4803"
# id_nwk = "A_5x5x100_r@5.00_d3f96ff4-e877-4db9-ab65-7e0258c0c65d"
id_nwk = "R_600x60x600_r@11.85_243e0ab5-39a3-461e-a6ea-08238ae8507a"
id_sim = "403e851f-6543-4c00-ae6d-a37de6c2eb2a"


# ============================================================================
# Data Import

# relative network path
pth_rel_nwk = Path("PNM/Network/", id_nwk)

# relative network path
pth_rel_sim = Path("PNM/FreezeDrying/", id_sim)

# relative CT scan path
pth_rel_scan = Path(
    "Scan",
    "Maltodextrin_DE12_w15",
    "MD_DE12_w15_IV",
    "section_ori@800x1000x1_res@600x60x600",
)

# state variable mapping
state_vars = {
    # "temperature": ("T_p_stp", "T_t_stp"),
    # "saturation": ("S_p_stp", "S_t_stp"),
    "pressure": ("P_v_p_stp", "P_v_t_stp"),
}

states = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000]  #

# pore network instance
pn = PoreNetwork.from_mat(
    pth_abs_data / pth_rel_sim / "Data/DataSelectionStates.mat", states, state_vars
)
# pn = PoreNetwork.from_mat(
#     pth_abs_data / pth_rel_nwk / "nwk.mat"
# )


# ============================================================================
# Configuration

sc = Scene()
sc.config_scene.add_property(
    porescene.config.PropertyConfiguration(
        "radius",
        FeFaPalette().all(),
        heading="Diameter [μm]",
        orientation=Orientation.HORIZONTAL,
        align=CompassDirection.NORTH,
        factor=2e6,
        precision=0,
    )
)
sc.config_scene.add_property(
    porescene.config.PropertyConfiguration(
        "coordination_number",
        FeFaPalette().all(),
        heading="Coordination Number [−]",
        orientation=Orientation.HORIZONTAL,
        align=CompassDirection.NORTH,
        # gradient_class=SegmentedGradient,
    )
)
sc.config_scene.add_property(
    porescene.config.PropertyConfiguration(
        "saturation",
        [fefa.yellow, fefa.pink, fefa.darkblue],
        heading="Saturation [−]",
        orientation=Orientation.HORIZONTAL,
        align=CompassDirection.NORTH,
        precision=2,
        min=0.0,
        max=1.0,
        use_global_boundaries=True,
    )
)

sc.config_scene.add_property(
    porescene.config.PropertyConfiguration(
        "pressure",
        [fefa.lightgreen, fefa.orange, fefa.red],
        heading="Pressure [Pa]",
        orientation=Orientation.HORIZONTAL,
        align=CompassDirection.NORTH,
        precision=-1,
        min=10,
        max=125,
        use_global_boundaries=True,
        color_nan=fefa.gray,
    )
)

sc.config_scene.add_property(
    porescene.config.PropertyConfiguration(
        "temperature",
        [fefa.yellow, fefa.orange, fefa.red, fefa.pink],
        heading="Temperature [°C]",
        orientation=Orientation.HORIZONTAL,
        align=CompassDirection.NORTH,
        precision=1,
        # min=-42,
        # max=-18,
        func_transform=lambda v: v-273.15,
        # use_global_boundaries=True,
        color_nan=fefa.gray,
    )
)


sc.config_axes.font_family = Path.cwd() / "asset/Inter-Regular.ttf"
sc.config_axes.font_size_labels = 0.75 * 1
sc.config_axes.line_width = 0.05 * 1
sc.config_axes.set_labels(pn.length_x, pn.length_y, pn.length_z)
sc.config_axes.ticks_x = [0, 50, 100]
sc.config_axes.ticks_y = [0, 50, 100]
sc.config_axes.ticks_z = [0, 50, 100]
sc.config_axes.enable_ticks = False
sc.scale = sc.size_bounding_box / max(pn.extent)
sc.shift = (sc.size_bounding_box - pn.extent * sc.scale) / 2
sc.aspect = pn.extent / max(pn.extent)
sc.config_image.width = 4096
sc.config_image.height = 4096
sc.config_scene.enable_spheres = False
sc.config_scene.enable_cylinders = False
sc.config_scene.enable_clusters = True


# ============================================================================
# Rendering

sc.remove_defaults()
sc.create_camera("2D")
sc.create_lights()
sc.create_axes()

# build scene structures (spheres, cylinders, solid, ...)
sc = build_structure(sc, pn)

# sc.create_solid(pth_abs_data / pth_rel_scan / "Solid.obj")
# sc.create_void(pth_abs_data / pth_rel_scan / "Void.obj")
sc.create_clusters(pth_abs_data / pth_rel_scan / "SegmentationVoid.obj")
# sc.apply_colors("Clusters", sc.config_scene.palette.random(pn.pore_count))

# sc, pth_img = make_radius(pth_abs_data / pth_rel_nwk / "Image", pn, sc)
# sc, pth_img = make_coordination_number(pth_abs_data / pth_rel_sim / "Image", pn, sc)
sc, pth_img = make_state(pth_abs_data / pth_rel_sim / "Image", pn, sc)
# pnp_i = pn.pnp[:, randint(1, pn.pore_count)]  # pnp_i[np.where(pnp_i != 0)]


# save the scene
# sc.save(Path.cwd() / "data/Scene.blend")
