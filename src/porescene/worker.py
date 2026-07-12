# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Felix Faber /
# Otto von Guericke University Magdeburg, Thermal Process Engineering


import bpy
import numpy as np
from mathutils import Matrix, Vector
from pathlib import Path

from porescene.color import Color
from porescene.color.gradient import DiscreteGradient, SegmentedGradient, SmoothGradient
from porescene.config import PropertyConfiguration
from porescene.image import img_add_colorbar, img_trim
from porescene.layout import (
    DiscreteGradientOverlay,
    Overlay,
    SegmentedGradientOverlay,
    SmoothGradientOverlay,
)
from porescene.model import PoreNetwork, PoreNetworkProperty
from porescene.scene import Scene
from porescene.utility import _get_bounds, svg2png


def build_structure(sc: Scene, pn: PoreNetwork, top: bool = False):
    if (
        pn.pore_position is not None
        and pn.throat_radius is not None
        and pn.tnp is not None
        and sc.config_scene.enable_cylinders
    ):
        sc.create_cylinders(
            np.hstack(
                [
                    pn.pore_position[pn.tnp[:, 0], :],
                    pn.pore_position[pn.tnp[:, 1], :],
                ]
            ),
            pn.throat_radius,
        )
        if top:
            sc.create_cylinders(
                np.hstack(
                    [
                        pn.pore_position[pn.pores_top, :],
                        pn.pore_position_top,
                    ]
                ),
                pn.throat_radius_top,
            )
    if (
        pn.pore_position is not None
        and pn.pore_radius is not None
        and sc.config_scene.enable_spheres
    ):
        sc.create_spheres(pn.pore_position, pn.pore_radius)
    sc.hide_cylinders()
    sc.hide_spheres()
    return sc


def make_clusters(pth: Path, sc: Scene, no: list[int] = [0]):
    col = bpy.data.collections.get("Clusters")
    bb_min = [0, 0, 0]
    bb_max = [0, 0, 0]
    for obj in col.objects:
        obj.hide_render = True
        obj.hide_viewport = True
    for n in no:
        obj = col.objects.get(f"label_{n}")
        obj.hide_render = False
        obj.hide_viewport = False
        for dim in range(3):
            bb_min[dim] = min([obj.dimensions[dim], bb_min[dim]])
            bb_max[dim] = max([obj.dimensions[dim], bb_max[dim]])
    dim = np.array(
        (bb_max[0] - bb_min[0], bb_max[1] - bb_min[1], bb_max[2] - bb_min[2]),
    )
    # sc.config_axes.set_labels(dim[0], dim[1], dim[2])
    # sc.scale = sc.size_bounding_box / max(dim)
    # sc.shift = (sc.size_bounding_box - dim * sc.scale) / 2
    # sc.aspect = dim / max(dim)
    # sc.remove_axes()
    # sc.create_axes()
    for n in no:
        obj = col.objects.get(f"label_{n}")
        scale = sc.size_bounding_box / max(dim)
        scale = (scale, scale, scale)
        mw = obj.matrix_world

        # Thanks to https://blender.stackexchange.com/questions/179028/scale-object-in-place-keeping-its-origin
        bbox = [Vector(b) for b in obj.bound_box]
        go = mw @ Vector(sum(bbox, Vector()) / 8)
        T = Matrix.Translation(go)
        S = Matrix.Diagonal(scale).to_4x4()
        T2 = Matrix.Translation(-go)
        M = T @ S @ T2
        obj.matrix_world = M @ obj.matrix_world
        obj.location += Vector((5, 5, 5))

    #     # scale = (2, 2, 1)
    #     # bbox = [Vector(b) for b in obj.bound_box]
    #     # o = sum(bbox, Vector()) / 8
    #     # T = Matrix.Translation(o)
    #     # S = Matrix.Diagonal(scale).to_4x4()
    #     # T2 = Matrix.Translation(-o)
    #     # M = T @ S @ T2

    #     # ob.data.transform(M)
    #     obj.data.update()

    if len(no) == 1:
        fname = f"label@{no[0]}"
    else:
        fname = "labels"
    fname = sc.render(pth, fname)
    img_trim(fname)
    return sc, fname


def make_img(
    pth: Path,
    sc: Scene,
    show_spheres: bool = True,
    show_cylinders: bool = True,
    show_clusters: bool = True,
    color_spheres: list[Color] = [],
    color_cylinders: list[Color] = [],
    color_clusters: list[Color] = [],
    name_spheres: str = "",
    name_cylinders: str = "",
    name_clusters: str = "",
    no_state: int | None = None,
    solid: Path | None = None,
    void: Path | None = None,
):
    fname_fragments = []
    if show_cylinders:
        sc.show_cylinders()
        sc.apply_colors("Cylinders", color_cylinders)
        fname_fragments.append("sticks@" + name_cylinders.replace("_", "-"))
    if show_spheres:
        sc.show_spheres()
        sc.apply_colors("Spheres", color_spheres)
        fname_fragments.append("spheres@" + name_spheres.replace("_", "-"))
    if show_clusters:
        sc.show_clusters()
        sc.apply_colors("Clusters", color_clusters)
        fname_fragments.append("clusters@" + name_clusters.replace("_", "-"))
    if solid is not None:
        sc.create_solid(solid)
        fname_fragments.append("solid")
    if void is not None:
        sc.create_void(void)
        fname_fragments.append("void")
    if sc.config_scene.enable_axes:
        sc.show_axes()
        fname_fragments.append("axes")
    if no_state is not None:
        fname_fragments.append(f"state@{no_state}")
    fname_fragments.append("solid_bulk")
    fname = "_".join(fname_fragments)
    fname = sc.render(pth, fname)
    sc.hide_cylinders()
    sc.hide_spheres()
    sc.hide_clusters()
    sc.remove_solid()
    sc.remove_void()
    return sc, fname


def make_radius(pth: Path, pn: PoreNetwork, sc: Scene) -> tuple[Scene, Path]:
    """
    Create images of the model colored depending on radius.
    """
    do_spheres = sc.config_scene.enable_spheres and pn.pore_radius is not None
    do_cylinders = sc.config_scene.enable_cylinders and pn.throat_radius is not None
    conf = sc.config_scene["radius"]
    prop = PoreNetworkProperty("radius")
    prop.set_data(pn.pore_radius, np.vstack((pn.throat_radius, pn.throat_radius_top)))
    mn, mx = _get_bounds(prop.min, prop.max, conf.precision, conf.factor)
    grad = SmoothGradient(conf.colors, mn / conf.factor, mx / conf.factor, fit=True)
    sc, pth_vis = make_img(
        pth,
        sc,
        do_spheres,
        do_cylinders,
        False,
        grad(prop.pore_values),
        grad(prop.throat_values),
        [],
        "radius",
        "radius",
    )
    img_trim(pth_vis)
    pth_cb = pth_vis.with_name("colorbar_radius.svg")
    make_gradient_overlay(
        pth_cb,
        sc.config_scene["radius"],
        mn,
        mx,
    )
    img_add_colorbar(pth_vis, pth_cb.with_suffix(".png"))
    return sc, pth_vis


def make_coordination_number(pth: Path, pn: PoreNetwork, sc: Scene) -> tuple[Scene, Path]:
    """
    Create images of the model colored depending on coordination number.
    """
    do_spheres = sc.config_scene.enable_spheres and pn.pore_radius is not None
    do_cylinders = sc.config_scene.enable_cylinders and pn.throat_radius is not None
    do_clusters = sc.config_scene.enable_clusters
    conf = sc.config_scene["coordination_number"]
    prop = PoreNetworkProperty("coordination_number")
    prop.set_data(pn.pore_coordination_number, pn.throat_coordination_number)
    mn, mx = _get_bounds(prop.min, prop.max, conf.precision, conf.factor)
    grad = conf.gradient_class(conf.colors, mn / conf.factor, mx / conf.factor)
    sc, pth_vis = make_img(
        pth,
        sc,
        do_spheres,
        do_cylinders,
        False,
        grad(prop.pore_values) if do_spheres else [],
        grad(prop.throat_values) if do_cylinders else [],
        grad(prop.pore_values) if do_clusters else [],
        "coordination-number",
        "coordination-number",
        "coordination-number",
    )
    img_trim(pth_vis)
    pth_cb = pth_vis.with_name("colorbar_coordination_number.svg")
    make_gradient_overlay(
        pth_cb,
        sc.config_scene["coordination_number"],
        mn,
        mx,
    )
    img_add_colorbar(pth_vis, pth_cb.with_suffix(".png"))
    return sc, pth_vis


def make_random(pth: Path, pn: PoreNetwork, sc: Scene) -> tuple[Scene, Path]:
    """
    Create images of the model colored depending on radius.
    """
    do_spheres = sc.config_scene.enable_spheres and pn.pore_radius is not None
    do_cylinders = sc.config_scene.enable_cylinders and pn.throat_radius is not None
    do_clusters = sc.config_scene.enable_clusters
    sc, fname = make_img(
        pth,
        sc,
        do_spheres,
        do_cylinders,
        do_clusters,
        sc.config_scene.palette.random(pn.pore_count) if do_spheres else [],
        sc.config_scene.palette.random(pn.throat_count) if do_cylinders else [],
        sc.config_scene.palette.random(pn.pore_count) if do_clusters else [],
        "random",
        "random",
        "random",
    )
    img_trim(fname)
    return sc, fname


def make_structure(pth: Path, pn: PoreNetwork, sc: Scene) -> tuple[Scene, Path]:
    """
    Create images of the model colored depending on radius.
    """
    do_spheres = sc.config_scene.enable_spheres and pn.pore_radius is not None
    do_cylinders = sc.config_scene.enable_cylinders and pn.throat_radius is not None
    do_clusters = sc.config_scene.enable_clusters
    sc, fname = make_img(
        pth,
        sc,
        do_spheres,
        do_cylinders,
        do_clusters,
        [fefa.gray for _ in range(pn.pore_count)] if do_spheres else [],
        [fefa.gray for _ in range(pn.throat_count)] if do_cylinders else [],
        sc.config_scene.palette.random(pn.pore_count) if do_clusters else [],
        "structure",
        "structure",
        "structure",
    )
    img_trim(fname)
    return sc, fname


def make_state(pth: Path, pn: PoreNetwork, sc: Scene):
    do_spheres = sc.config_scene.enable_spheres and pn.pore_radius is not None
    do_cylinders = sc.config_scene.enable_cylinders and pn.throat_radius is not None
    do_clusters = sc.config_scene.enable_clusters
    grad_dict = {}
    for conf in sc.config_scene:
        if conf.use_global_boundaries:
            mn, mx = _get_bounds(conf.min, conf.max, conf.precision, conf.factor)
            grad_dict[conf.name] = conf.gradient_class(
                conf.colors, mn / conf.factor, mx / conf.factor
            )

    for state in pn.states:
        for prop in state.properties:
            conf = sc.config_scene[prop.name]

            if not conf.use_global_boundaries:
                if conf.min is None:
                    mn, _ = _get_bounds(
                        prop.min,
                        prop.max,
                        conf.precision,
                        conf.factor,
                        conf.func_transform,
                    )
                else:
                    mn = conf.min
                if conf.max is None:
                    _, mx = _get_bounds(
                        prop.min,
                        prop.max,
                        conf.precision,
                        conf.factor,
                        conf.func_transform,
                    )
                else:
                    mx = conf.max

                grad = conf.gradient_class(
                    conf.colors, mn / conf.factor, mx / conf.factor
                )
            else:
                grad = grad_dict[conf.name]
                mn, mx = _get_bounds(conf.min, conf.max, conf.precision, conf.factor)
            sc, pth_vis = make_img(
                pth,
                sc,
                do_spheres,
                do_cylinders,
                do_clusters,
                grad(conf.func_transform(prop.pore_values)) if do_spheres else [],
                grad(conf.func_transform(prop.throat_values)) if do_cylinders else [],
                grad(conf.func_transform(prop.pore_values)) if do_clusters else [],
                prop.name,
                prop.name,
                prop.name,
                no_state=state.no,
            )
            img_trim(pth_vis)
            pth_cb = pth_vis.with_name("colorbar_" + prop.name + ".svg")
            make_gradient_overlay(
                pth_cb,
                sc.config_scene[prop.name],
                mn,
                mx,
            )
            img_add_colorbar(pth_vis, pth_cb.with_suffix(".png"))
    return sc, pth_vis


# def make_structure(pth: Path, pn: PoreNetwork, sc: Scene):
#     do_spheres = sc.config_scene.enable_spheres and pn.pore_radius is not None
#     do_cylinders = sc.config_scene.enable_cylinders and pn.throat_radius is not None
#     do_clusters = sc.config_scene.enable_clusters
#     sc, fname = make_img(
#         pth,
#         sc,
#         do_spheres,
#         do_cylinders,
#         do_clusters,
#         sc.config_scene.palette.random(pn.pore_count) if do_spheres else [],
#         sc.config_scene.palette.random(pn.throat_count) if do_cylinders else [],
#         sc.config_scene.palette.random(pn.pore_count) if do_clusters else [],
#         "random",
#         "random",
#         "random",
#     )
#     return sc, fname


def make_gradient_overlay(
    pth: Path,
    config: PropertyConfiguration,
    mn: float,
    mx: float,
    /,
    ticks: list[str] = [],
    **kwargs,
) -> Overlay:
    if config.gradient_class is SmoothGradient:
        ovl = SmoothGradientOverlay(pth)
    elif config.gradient_class is SegmentedGradient:
        ovl = SegmentedGradientOverlay(pth)
    elif config.gradient_class is DiscreteGradient:
        ovl = DiscreteGradientOverlay(pth)
    else:
        raise ValueError("Unknown gradient class")
    if len(ticks) == 0:
        if config.gradient_class is SegmentedGradient:
            n_ticks = len(config.colors) + 1
        else:
            n_ticks = 5
        ticks_num: list[float] = list(
            np.round(np.linspace(mn, mx, n_ticks), config.precision + 2)
        )
        if config.precision <= 0:
            ticks = [
                f"{v:.0f}" if v.is_integer() else f"{v:.2f}".rstrip("0")
                for v in ticks_num
            ]
        else:
            ticks = [
                (
                    f"{v:.0f}"
                    if v.is_integer()
                    else f"{v:.{config.precision + 2}f}".rstrip("0")
                )
                for v in ticks_num
            ]
    for arg in kwargs.items():
        if hasattr(ovl, arg[0]):
            setattr(ovl, arg[0], arg[1])
    ovl.gradient_colors = config.colors
    ovl.ticks = ticks
    ovl.heading = config.heading
    ovl.subheading = config.subheading
    ovl.text = config.text
    ovl.align = config.align
    ovl.orientation = config.orientation
    ovl.color_nan = None  # config.color_nan
    ovl.save()
    svg2png(pth)
    return ovl
