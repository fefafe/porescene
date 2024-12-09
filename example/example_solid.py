from pathlib import Path

import numpy as np

from porescene.image import img_trim
from porescene.scene import Scene

# ============================================================================
# Import Parameters

# absolute data path
pth_abs_data = Path("/Data/")

# relative CT scan path
pth_rel_scan = Path(
    "Scan\Maltodextrin_DE12_w5\MD_DE12_w5_I\section_ori@668x668x1_res@600x600x800"
)

# domain extent
extent = np.array((600, 600, 800)) * 3.87592e-06

do_solid = True
do_void = False
do_clusters = False


# ============================================================================
# Data Import

sc = Scene()
sc.config_axes.font_family = Path.cwd() / "asset/Inter-Regular.ttf"
sc.config_axes.font_size_labels = 1
sc.config_axes.line_width = 0.05 * 1
sc.config_axes.precision = (2, 2, 2)
sc.config_axes.factor = (1e3, 1e3, 1e3)
sc.config_axes.set_labels(*extent)
sc.config_axes.label_z = "[mm]"
sc.config_axes.enable_ticks = True
sc.config_axes.ticks_z = [0, 0.5, 1, 1.5, 2]
sc.scale = sc.size_bounding_box / max(extent)
sc.shift = (sc.size_bounding_box - extent * sc.scale) / 2
sc.aspect = extent / max(extent)
sc.config_image.width = 2048 * 2
sc.config_image.height = 2048 * 2
sc.config_scene.enable_spheres = False
sc.config_scene.enable_cylinders = False
sc.config_scene.enable_clusters = True
sc.config_scene.enable_axes = False


# ============================================================================
# Rendering

sc.remove_defaults()
sc.create_camera("3D")
sc.create_lights()
sc.create_axes()

if do_solid:
    sc.create_solid(pth_abs_data / pth_rel_scan / "Solid.obj")
    fname = sc.render(pth_abs_data / pth_rel_scan / "Image", "solid")
    img_trim(fname)

if do_void:
    sc.create_void(pth_abs_data / pth_rel_scan / "Void.obj")
    fname = sc.render(pth_abs_data / pth_rel_scan / "Image", "void")
    img_trim(fname)

if do_clusters:
    sc.create_clusters(pth_abs_data / pth_rel_scan / "SegmentationVoid.obj")
    sc.create_solid(pth_abs_data / pth_rel_scan / "Solid.obj")
    sc.apply_colors("Clusters", sc.config_scene.palette.random(5000))
    fname = sc.render(pth_abs_data / pth_rel_scan / "Image", "clusters@random_solid")
    img_trim(fname)
