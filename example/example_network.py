from random import choice, randint
import sys
from pathlib import Path

import numpy as np

import porescene
import porescene.config
from porescene.color.gradient import SegmentedGradient
from porescene.color.palette import fefa
from porescene.color.palette.fefa import FeFaPalette
from porescene.image import img_trim
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
    make_structure,
)

# ============================================================================
# Import Parameters

# absolute data path
pth_abs_data = Path("/Data/")

# network id
id_nwk = "R_200x200x200_r@2.72_3d901689-88ea-460b-9f73-d587d777d817"


# ============================================================================
# Data Import

# relative network path
pth_rel_nwk = Path("PNM/Network/", id_nwk)

# relative CT scan path
pth_rel_scan = Path(
    "Scan",
    "Titan_Sintered\Ti45_500_850_IEK90\section_ori@1x1x1_res@200x200x200"
)

pn = PoreNetwork.from_mat(
    pth_abs_data / pth_rel_nwk / "nwk.mat"
)

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

extent = np.array((200, 200, 200)) * 1e-6  # 3.87592e-06

sc.config_axes.font_family = Path.cwd() / "asset/Inter-Regular.ttf"
sc.config_axes.font_size_labels = 1.5
sc.config_axes.line_width = 0.1
sc.config_axes.set_labels(pn.length_x, pn.length_y, pn.length_z)
sc.config_axes.enable_ticks = False
sc.scale = sc.size_bounding_box / max(extent)
sc.shift = (sc.size_bounding_box - extent * sc.scale) / 2
sc.aspect = extent / max(extent)
sc.config_image.width = 2048*2
sc.config_image.height = 2048*2
sc.config_scene.enable_spheres = False
sc.config_scene.enable_cylinders = True
sc.config_scene.enable_clusters = False


# ============================================================================
# Rendering

sc.remove_defaults()
sc.create_camera("3D")
sc.create_lights()
sc.create_axes()

# build scene structures (spheres, cylinders, solid, ...)
sc = build_structure(sc, pn, False)

# sc.create_solid(pth_abs_data / pth_rel_scan / "Solid.obj")
# sc.create_void(pth_abs_data / pth_rel_scan / "Void.obj")
# sc.create_clusters(pth_abs_data / pth_rel_scan / "SegmentationVoid.obj")
sc.apply_colors("Cylinders", sc.config_scene.palette.random(pn.throat_count))
make_random(pth_abs_data / pth_rel_scan / "Image", pn, sc)
# make_structure(pth_abs_data / pth_rel_scan / "Image", pn, sc)

# sc, pth_img = make_radius(pth_abs_data / pth_rel_nwk / "Image", pn, sc)
# sc, pth_img = make_coordination_number(pth_abs_data / pth_rel_nwk / "Image", pn, sc)

# for _ in range(10):
#     sc, pth = make_clusters(
#         pth_abs_data / pth_rel_scan / "Image", sc, [choice(range(pn.pore_count))]
#     )
