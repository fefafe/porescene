from pathlib import Path

import numpy as np

from porescene.image import img_trim
from porescene.scene import Scene

# ============================================================================
# Import Parameters

# relative CT scan path
pth_data = Path.cwd() / "./data/"
pth_tmp = Path.cwd() / "./tmp/"

# domain extent
extent = np.array((100, 100, 100)) * 1e-06

do_axes = True
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
sc.config_axes.factor = (1e6, 1e6, 1e6)
sc.config_axes.set_labels(*extent)
sc.config_axes.label_z = "[µm]"
sc.config_axes.enable_ticks = True
sc.config_axes.ticks_z = [0, 0.5, 1, 1.5, 2]
sc.scale = sc.size_bounding_box / max(extent)
sc.shift = (sc.size_bounding_box - extent * sc.scale) / 2
sc.aspect = extent / max(extent)
sc.config_image.width = int(2048 * 0.5)
sc.config_image.height = int(2048 * 0.5)
sc.config_scene.enable_spheres = False
sc.config_scene.enable_cylinders = False
sc.config_scene.enable_clusters = True
sc.config_scene.enable_axes = False


# ============================================================================
# Rendering

sc.remove_defaults()
sc.create_camera("3D")
sc.create_lights()
# sc.create_axes()

if do_axes:
    sc.create_axes()
    fname = sc.render(pth_tmp / "Image", "axes")
    sc.hide_axes()

if do_solid:
    sc.create_solid(pth_tmp / "Solid.obj")
    fname = sc.render(pth_tmp / "Image", "solid")
    img_trim(fname)

if do_void:
    sc.create_void(pth_tmp / "Void.obj")
    fname = sc.render(pth_tmp / "Image", "void")
    img_trim(fname)

if do_clusters:
    sc.create_clusters(pth_tmp / "SegmentationVoid.obj")
    sc.create_solid(pth_tmp / "Solid.obj")
    sc.apply_colors("Clusters", sc.config_scene.palette.random(5000))
    fname = sc.render(pth_tmp / "Image", "clusters@random_solid")
    img_trim(fname)
