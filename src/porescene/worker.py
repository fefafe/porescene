# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Felix Faber /
# Otto von Guericke University Magdeburg, Thermal Process Engineering


from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

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


def build_structure(
    sc: Scene,
    pn: PoreNetwork,
    *,
    left: bool = False,
    right: bool = False,
    front: bool = False,
    back: bool = False,
    bottom: bool = False,
    top: bool = False,
) -> Scene:
    """
    Constructs the cylinder and sphere meshes in the Blender scene based on the given
    :class:`PoreNetwork <porescene.model.PoreNetwork>` instance.

    Parameters
    ----------
    sc : Scene
        The scene to add the objects to.
    pn : PoreNetwork
        The pore network that is used to calculate cylinder and sphere positions
        as well as dimensions
    left : bool, optional
        If true, boundary pores (as well as their connections into the central network)
        at the start of the x-dimension are added into the scene, by default False
    right : bool, optional
        If true, boundary pores (as well as their connections into the central network)
        at the end of the x-dimension are added into the scene, by default False
    front : bool, optional
        If true, boundary pores (as well as their connections into the central network)
        at the start of the y-dimension are added into the scene, by default False
    back : bool, optional
        If true, boundary pores (as well as their connections into the central network)
        at the end of the y-dimension are added into the scene, by default False
    bottom : bool, optional
        If true, boundary pores (as well as their connections into the central network)
        at the start of the z-dimension are added into the scene, by default False
    top : bool, optional
        If true, boundary pores (as well as their connections into the central network)
        at the end of the z-dimension are added into the scene, by default False

    Returns
    -------
    Scene
        The scene with added objects.
    """
    if (
        pn.pore_position is not None
        and pn.throat_radius is not None
        and pn.tnp is not None
        and sc.config_scene.enable_cylinders
    ):
        pos_t = np.hstack(
            [
                pn.pore_position[pn.tnp[:, 0], :],
                pn.pore_position[pn.tnp[:, 1], :],
            ]
        )
        r_t = pn.throat_radius

        boundaries = {
            "left": left,
            "right": right,
            "front": front,
            "back": back,
            "bottom": bottom,
            "top": top,
        }

        for b_name, b_value in boundaries.items():
            if b_value:
                if (
                    getattr(pn, f"throat_radius_{b_name}") is not None
                    and getattr(pn, f"pore_position_{b_name}") is not None
                ):
                    pos_t = np.vstack(
                        [
                            pos_t,
                            np.hstack(
                                [
                                    pn.pore_position[getattr(pn, f"pores_{b_name}"), :],
                                    getattr(pn, f"pore_position_{b_name}"),
                                ]
                            ),
                        ]
                    )
                    r_t = np.concatenate([r_t, getattr(pn, f"throat_radius_{b_name}")])
                else:
                    raise Exception(
                        (
                            "Missing data: make sure that PoreNetwork.throat_radius_"
                            f"{b_name} and PoreNetwork.pore_position_{b_name} are not "
                            "empty."
                        )
                    )

        sc.create_cylinders(pos_t, r_t)

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
) -> Path:
    """
    Populates the scene with the specified components, renders it, and resets the
    scene afterwards.

    The pore spheres, throat cylinders, and pore clusters are shown (and colored) only
    when their respective ``show_*`` flag is set; a solid and/or void object are added
    when their paths are given, and axes are shown when enabled in the scene
    configuration. The output file name is assembled from the enabled components (e.g.
    ``sphere-radius+cylinder-radius+axes``), so each rendered combination gets a
    distinct, descriptive name. After rendering, all layers are hidden and the solid and
    void objects are removed, leaving the scene ready for the next render.

    Parameters
    ----------
    pth : Path
        Directory to save the rendered image at.
    sc : Scene
        Scene to populate and render.
    show_spheres : bool, optional
        Whether to show the pore spheres, by default True.
    show_cylinders : bool, optional
        Whether to show the throat cylinders, by default True.
    show_clusters : bool, optional
        Whether to show the pore clusters, by default True.
    color_spheres : list[Color], optional
        Per-pore colors applied to the sphere layer (one :class:`Color` per pore); used
        only when ``show_spheres`` is set, by default [].
    color_cylinders : list[Color], optional
        Per-throat colors applied to the cylinder layer (one :class:`Color` per throat);
        used only when ``show_cylinders`` is set, by default [].
    color_clusters : list[Color], optional
        Per-cluster colors applied to the cluster layer; used only when ``show_clusters``
        is set, by default [].
    name_spheres : str, optional
        Label describing the sphere coloring, embedded in the output file name with
        underscores replaced by hyphens (e.g. ``"radius"``), by default "".
    name_cylinders : str, optional
        Label describing the cylinder coloring, embedded in the output file name with
        underscores replaced by hyphens, by default "".
    name_clusters : str, optional
        Label describing the cluster coloring, embedded in the output file name with
        underscores replaced by hyphens, by default "".
    no_state : int | None, optional
        Index of the network state being rendered; when given, appended to the file name
        as ``state@<no_state>``, by default None.
    solid : Path | None, optional
        Path to a solid-structure object to add to the scene; when given, the solid is
        created and ``solid`` is added to the file name, by default None.
    void : Path | None, optional
        Path to a void-space object to add to the scene; when given, the void is created
        and ``void`` is added to the file name, by default None.

    Returns
    -------
    Path
        File path to the rendered image.
    """
    fname_fragments = []
    sep = "-"
    if show_cylinders:
        sc.show_cylinders()
        sc.apply_colors("Cylinders", color_cylinders)
        fname_fragments.append("cylinder" + sep + name_cylinders)
    if show_spheres:
        sc.show_spheres()
        sc.apply_colors("Spheres", color_spheres)
        fname_fragments.append("sphere" + sep + name_spheres)
    if show_clusters:
        sc.show_clusters()
        sc.apply_colors("Clusters", color_clusters)
        fname_fragments.append("cluster" + sep + name_clusters)
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
        fname_fragments.append(f"state-{no_state}")

    # render image in given config
    fname = "+".join(fname_fragments) + ".png"
    pth_render = sc.render(pth.with_name(fname))

    # reset scene
    sc.hide_cylinders()
    sc.hide_spheres()
    sc.hide_clusters()
    sc.remove_solid()
    sc.remove_void()

    return pth_render


def make_radius(
    pth: Path,
    pn: PoreNetwork,
    sc: Scene,
    *,
    left: bool = False,
    right: bool = False,
    front: bool = False,
    back: bool = False,
    bottom: bool = False,
    top: bool = False,
) -> tuple[Scene, Path]:
    """
    Create images of the model colored depending on radius.
    """
    # check scene components
    do_spheres = sc.config_scene.enable_spheres and pn.pore_radius is not None
    do_cylinders = sc.config_scene.enable_cylinders and pn.throat_radius is not None

    # create property instance
    conf = sc.config_scene["radius"]
    prop = PoreNetworkProperty("radius")

    if pn.throat_radius is not None:
        r_t = pn.throat_radius

    boundaries = {
        "left": left,
        "right": right,
        "front": front,
        "back": back,
        "bottom": bottom,
        "top": top,
    }

    for b_name, b_value in boundaries.items():
        if b_value:
            if (
                getattr(pn, f"throat_radius_{b_name}") is not None
                and getattr(pn, f"pore_position_{b_name}") is not None
            ):
                r_t = np.concatenate([r_t, getattr(pn, f"throat_radius_{b_name}")])
            else:
                raise Exception(
                    (
                        "Missing data: make sure that PoreNetwork.throat_radius_"
                        f"{b_name} and PoreNetwork.pore_position_{b_name} are not "
                        "empty."
                    )
                )

    prop.set_data(pn.pore_radius, r_t)
    mn, mx = _get_bounds(prop.min, prop.max, conf.precision, conf.factor)
    grad = SmoothGradient(conf.colors, mn / conf.factor, mx / conf.factor, fit=True)
    pth_vis = make_img(
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
    pth_vis = make_img(
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
    fname = make_img(
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


def make_structure(
    pth: Path,
    pn: PoreNetwork,
    sc: Scene,
    *,
    left: bool = False,
    right: bool = False,
    front: bool = False,
    back: bool = False,
    bottom: bool = False,
    top: bool = False,
) -> tuple[Scene, Path]:
    """
    Create images of the model colored depending on radius.
    """
    do_spheres = sc.config_scene.enable_spheres and pn.pore_radius is not None
    do_cylinders = sc.config_scene.enable_cylinders and pn.throat_radius is not None
    do_clusters = sc.config_scene.enable_clusters and sc.has_clusters

    color_grey = Color("#7A828C")

    N_p = pn.pore_count
    N_t = pn.throat_count(left, right, front, back, bottom, top)

    fname = make_img(
        pth,
        sc,
        do_spheres,
        do_cylinders,
        do_clusters,
        [color_grey for _ in range(N_p)] if do_spheres else [],
        [color_grey for _ in range(N_t)] if do_cylinders else [],
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
            pth_vis = make_img(
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
