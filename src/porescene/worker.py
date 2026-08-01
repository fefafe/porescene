# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Felix Faber /
# Otto von Guericke University Magdeburg, Thermal Process Engineering


from pathlib import Path

import bpy
import numpy as np

from mathutils import Matrix, Vector  # type: ignore  # isort:skip

from porescene.color import Color
from porescene.color.gradient import DiscreteGradient, SegmentedGradient, SmoothGradient
from porescene.layout import (
    DiscreteGradientAnnotation,
    SegmentedGradientAnnotation,
    SmoothGradientAnnotation,
)
from porescene.model import PoreNetwork, PoreNetworkQuantity
from porescene.scene import Scene
from porescene.utility import colorbar_ticks, svg2png, tick_labels

SEPARATOR_FRAGMENTS = "+"
SEPARATOR_PROPERTY = "-"


def quantity_range(pn: PoreNetwork, sc: Scene, name: str) -> tuple[float, float]:
    """
    The range the quantity ``name`` covers in a pore network, in stored units.

    The range every ``make_*`` function fits its color gradient to, and the one
    :func:`make_colorbar` works its limits out from, so that an image and the colorbar
    composited onto it report one and the same scale.

    For a quantity carried by the states of the network the range spans the whole
    series, so that states rendered one after another stay comparable. For one of the
    geometry quantities -- ``"radius"`` and ``"coordination_number"``, which the network
    holds once rather than per state -- it covers the values the scene actually draws,
    i.e. the radii of the boundary throats only count when those throats were built into
    it.

    Parameters
    ----------
    pn : PoreNetwork
        The pore network holding the data.
    sc : Scene
        The scene the quantity is drawn in.
    name : str
        Name of the quantity.

    Returns
    -------
    tuple[float, float]
        Lowest and highest value, in the unit the data is stored in. Feed both to
        :meth:`~porescene.config.QuantityConfiguration.resolve_limits` to turn them into
        the limits a colorbar spans.

    Raises
    ------
    ValueError
        If the network carries no quantity of that name.
    """
    if pn.has_quantity(name):
        return pn.quantity_min(name), pn.quantity_max(name)

    quant = _quantity_geometry(pn, sc, name)
    return float(quant.min), float(quant.max)


def _quantity_geometry(pn: PoreNetwork, sc: Scene, name: str) -> PoreNetworkQuantity:
    """
    Wraps a quantity of the network geometry -- one the network holds once rather than
    per state -- into a :class:`~porescene.model.PoreNetworkQuantity`.
    """
    quant = PoreNetworkQuantity(name)

    if name == "coordination_number":
        return quant.set_data(pn.pore_coordination_number, pn.throat_coordination_number)

    if name != "radius":
        raise ValueError(
            f"Could not find a quantity named '{name}': the network carries it in "
            "none of its states, and it is not one of the geometry quantities "
            "('radius', 'coordination_number')"
        )

    do_spheres = sc.config_scene.enable_spheres and sc.has_spheres
    do_cylinders = sc.config_scene.enable_cylinders and sc.has_cylinders

    # only the layers the scene draws take part in the range, so a view showing the
    # throats alone is not colored by a scale stretched to fit the pores as well
    r_p = pn.pore_radius if do_spheres else None
    r_t = None
    if do_cylinders and pn.throat_radius is not None:
        r_t = pn.throat_radius
        for b_name, b_value in sc._boundary_cylinder.items():
            if not b_value:
                continue
            if getattr(pn, f"throat_radius_{b_name}") is None:
                raise Exception(
                    "Missing data: make sure that PoreNetwork.throat_radius_"
                    f"{b_name} and PoreNetwork.pore_position_{b_name} are not empty."
                )
            r_t = np.concatenate([r_t, getattr(pn, f"throat_radius_{b_name}")])

    return quant.set_data(r_p, r_t)


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
                        "Missing data: make sure that PoreNetwork.throat_radius_"
                        f"{b_name} and PoreNetwork.pore_position_{b_name} are not "
                        "empty."
                    )

        sc.create_cylinders(pos_t, r_t)
        sc._boundary_cylinder = boundaries

    if (
        pn.pore_position is not None
        and pn.pore_radius is not None
        and sc.config_scene.enable_spheres
    ):
        sc.create_spheres(pn.pore_position, pn.pore_radius)

    sc.hide_cylinders()
    sc.hide_spheres()
    return sc


def make_clusters(pth: Path, sc: Scene, no: list[int] = None):
    if no is None:
        no = [0]
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
    return sc, fname


def make_img(
    dir_img: Path,
    sc: Scene,
    show_spheres: bool = True,
    show_cylinders: bool = True,
    show_clusters: bool = True,
    color_spheres: tuple[Color, ...] = (),
    color_cylinders: tuple[Color, ...] = (),
    color_clusters: tuple[Color, ...] = (),
    name_spheres: str = "",
    name_cylinders: str = "",
    name_clusters: str = "",
    no_state: int | None = None,
    no_frame: int | None = None,
    solid: Path | None = None,
    void: Path | None = None,
    *,
    trim: bool = True,
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
    dir_img : Path
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
        as ``state-<no_state>``, by default None. Ignored when ``no_frame`` is given.
    no_frame : int | None, optional
        Position of the image in a frame sequence; when given, appended to the file name
        as a zero-padded ``frame-<no_frame>`` *instead of* ``state-<no_state>``, by
        default None.

        Frames of one sequence then share a common prefix and differ only in the padded
        counter, so that sorting them by name -- as :func:`porescene.image.frames2mp4`
        and :func:`porescene.image.frames2gif` expect -- yields the playback order. An
        unpadded counter would sort ``frame-10`` before ``frame-2``, and keeping
        ``state-<no_state>`` in the name would break the common prefix as soon as a frame
        falls on a different stored state.
    solid : Path | None, optional
        Path to a solid-structure object to add to the scene; when given, the solid is
        created and ``solid`` is added to the file name, by default None.
    void : Path | None, optional
        Path to a void-space object to add to the scene; when given, the void is created
        and ``void`` is added to the file name, by default None.
    trim : bool, optional
        If true, the rendered image is cropped to its content, removing the surrounding
        empty margins, by default True. Renders of one series are trimmed each to their
        own content, so turn this off where they have to stay on a common canvas -- the
        frames of a video, or images meant to be placed side by side.

    Returns
    -------
    Path
        File path to the rendered image.
    """
    fname_fragments = []
    if show_cylinders and sc.has_cylinders:
        sc.show_cylinders()
        sc.apply_colors("Cylinders", color_cylinders)
        fname_fragments.append("cylinder" + SEPARATOR_PROPERTY + name_cylinders)
    if show_spheres and sc.has_spheres:
        sc.show_spheres()
        sc.apply_colors("Spheres", color_spheres)
        fname_fragments.append("sphere" + SEPARATOR_PROPERTY + name_spheres)
    if show_clusters and sc.has_clusters:
        sc.show_clusters()
        sc.apply_colors("Clusters", color_clusters)
        fname_fragments.append("cluster" + SEPARATOR_PROPERTY + name_clusters)

    if solid is not None:
        sc.create_solid(solid)
    if void is not None:
        sc.create_void(void)
    if sc.has_solid:
        fname_fragments.append("solid")
    if sc.has_void:
        fname_fragments.append("void")

    if sc.config_scene.enable_axes:
        sc.show_axes()
        fname_fragments.append("axes")

    if no_frame is not None:
        fname_fragments.append(f"frame-{no_frame:05d}")
    elif no_state is not None:
        fname_fragments.append(f"state-{no_state}")

    # render image in given config
    fname = SEPARATOR_FRAGMENTS.join(fname_fragments) + ".png"
    pth_render = sc.render(dir_img / fname, trim=trim)

    # reset scene
    sc.hide_cylinders()
    sc.hide_spheres()
    sc.hide_clusters()
    sc.remove_solid()
    sc.remove_void()

    return pth_render


def make_radius(
    dir_save: Path,
    pn: PoreNetwork,
    sc: Scene,
    *,
    trim: bool = True,
) -> Path:
    """
    Renders the pore network with pores and throats colored by their radius.

    A smooth color gradient is fitted to the radius range (across pore and throat radii,
    see :meth:`~porescene.config.QuantityConfiguration.resolve_limits`) and the sphere and
    cylinder layers are colored accordingly via :func:`make_img`. Spheres and cylinders
    are only colored and shown when enabled in the scene configuration *and* the
    corresponding radius data is present.

    No colorbar is drawn onto the image. Render one with :func:`make_colorbar`, which
    works out the same limits by itself, and composite the two with
    :func:`porescene.image.compose_colorbar`.

    Parameters
    ----------
    dir_save : Path
        Directory to save the rendered image at.
    pn : PoreNetwork
        The pore network providing the pore and throat radii.
    sc : Scene
        The scene holding the already-built geometry and the ``radius`` quantity
        configuration.
    trim : bool, optional
        Whether to crop the rendered image to its content, see :func:`make_img`, by
        default True.

    Returns
    -------
    Path
        The file path to the rendered image.

    Raises
    ------
    Exception
        If any boundary throats are included in the scene and matching ``throat_radius_*``
        data is missing on the :class:`PoreNetwork` instance.
    """
    # check scene components
    do_spheres = sc.config_scene.enable_spheres and sc.has_spheres
    do_cylinders = sc.config_scene.enable_cylinders and sc.has_cylinders

    # collect the radii the scene draws, see quantity_range
    conf = sc.config_scene["radius"]
    quant = _quantity_geometry(pn, sc, "radius")

    # setup colorbar
    mn, mx = conf.resolve_limits(quant.min, quant.max)
    grad = SmoothGradient(conf.colors, mn, mx, fit=True)

    # render given configuration
    return make_img(
        dir_save,
        sc,
        do_spheres,
        do_cylinders,
        False,
        grad(conf.value_display(quant.pore_values)) if do_spheres else [],
        grad(conf.value_display(quant.throat_values)) if do_cylinders else [],
        [],
        "radius",
        "radius",
        trim=trim,
    )


def make_coordination_number(
    dir_img: Path,
    pn: PoreNetwork,
    sc: Scene,
    *,
    trim: bool = True,
) -> Path:
    """
    Renders the pore network with pores, throats, and clusters colored by their
    coordination number.

    A color gradient (the gradient class configured for the ``coordination_number``
    quantity) is fitted to the coordination-number range (see
    :meth:`~porescene.config.QuantityConfiguration.resolve_limits`), and the sphere,
    cylinder and cluster layers are colored accordingly via :func:`make_img`. Each layer
    is only colored and shown when it is enabled in the scene configuration and the
    corresponding data is available.

    No colorbar is drawn onto the image. Render one with :func:`make_colorbar`, which
    works out the same limits by itself, and composite the two with
    :func:`porescene.image.compose_colorbar`.

    Parameters
    ----------
    dir_img : Path
        Directory to save the rendered image at.
    pn : PoreNetwork
        The pore network providing the pore and throat coordination numbers.
    sc : Scene
        The scene holding the already-built geometry and the ``coordination_number``
        quantity configuration.
    trim : bool, optional
        Whether to crop the rendered image to its content, see :func:`make_img`, by
        default True.

    Returns
    -------
    Path
        The file path to the rendered image.
    """
    # check scene components
    do_spheres = sc.config_scene.enable_spheres and sc.has_spheres
    do_cylinders = sc.config_scene.enable_cylinders and sc.has_cylinders
    do_clusters = sc.config_scene.enable_clusters and sc.has_clusters

    # collect the coordination numbers, see quantity_range
    conf = sc.config_scene["coordination_number"]
    quant = _quantity_geometry(pn, sc, "coordination_number")

    limit_lower, limit_upper = conf.resolve_limits(quant.min, quant.max)
    grad = conf.gradient_class(conf.colors, limit_lower, limit_upper)

    return make_img(
        dir_img,
        sc,
        do_spheres,
        do_cylinders,
        do_clusters,
        grad(conf.value_display(quant.pore_values)) if do_spheres else [],
        grad(conf.value_display(quant.throat_values)) if do_cylinders else [],
        grad(conf.value_display(quant.pore_values)) if do_clusters else [],
        "coordination-number",
        "coordination-number",
        "coordination-number",
        trim=trim,
    )


def make_random(
    dir_img: Path,
    pn: PoreNetwork,
    sc: Scene,
    *,
    trim: bool = True,
) -> Path:
    """
    Renders the pore network with pores, throats, and clusters assigned random colors.

    Each layer is drawn with colors picked at random from the scene's palette, so that
    individual pores, throats, and clusters can be told apart visually. A layer is only
    colored and shown when it is enabled in the scene configuration *and* has actually
    been built in the scene. Unlike the quantity-based renders, no colorbar is added,
    since the random colors carry no scale.

    Parameters
    ----------
    dir_img : Path
        Directory to save the rendered image at.
    pn : PoreNetwork
        The pore network providing the pore, throat, and cluster counts used to size the
        random color sets.
    sc : Scene
        The scene holding the already-built geometry and the color palette.
    trim : bool, optional
        Whether to crop the rendered image to its content, see :func:`make_img`, by
        default True.

    Returns
    -------
    Path
        The file path to the rendered image.
    """
    # check scene components
    do_spheres = sc.config_scene.enable_spheres and sc.has_spheres
    do_cylinders = sc.config_scene.enable_cylinders and sc.has_cylinders
    do_clusters = sc.config_scene.enable_clusters and sc.has_clusters

    # render scene configuration
    return make_img(
        dir_img,
        sc,
        do_spheres,
        do_cylinders,
        do_clusters,
        sc.config_scene.palette.random(pn.pore_count) if do_spheres else [],
        (
            sc.config_scene.palette.random(pn.throat_count(**sc._boundary_cylinder))
            if do_cylinders
            else []
        ),
        sc.config_scene.palette.random(pn.pore_count) if do_clusters else [],
        "random",
        "random",
        "random",
        trim=trim,
    )


def make_structure(
    dir_img: Path,
    pn: PoreNetwork,
    sc: Scene,
    *,
    trim: bool = True,
) -> Path:
    """
    Renders the pore network with all pores, throats, and clusters in a uniform gray.

    This is the plain structure view: every layer is drawn in a single neutral gray,
    without any quantity-based coloring or colorbar, giving a clean overview of the
    network geometry. A layer is only shown when it is enabled in the scene
    configuration *and* has actually been built in the scene.

    Parameters
    ----------
    dir_img : Path
        Directory to save the rendered image at.
    pn : PoreNetwork
        The pore network providing the pore and throat counts.
    sc : Scene
        The scene holding the already-built geometry.
    trim : bool, optional
        Whether to crop the rendered image to its content, see :func:`make_img`, by
        default True.

    Returns
    -------
    Path
        The file path to the rendered image.
    """
    do_spheres = sc.config_scene.enable_spheres and sc.has_spheres
    do_cylinders = sc.config_scene.enable_cylinders and sc.has_cylinders
    do_clusters = sc.config_scene.enable_clusters and sc.has_clusters

    color_grey = Color("#7A828C")

    N_p = pn.pore_count
    N_t = pn.throat_count(**sc._boundary_cylinder)

    return make_img(
        dir_img,
        sc,
        do_spheres,
        do_cylinders,
        do_clusters,
        [color_grey for _ in range(N_p)] if do_spheres else [],
        [color_grey for _ in range(N_t)] if do_cylinders else [],
        [color_grey for _ in range(N_p)] if do_clusters else [],
        "structure",
        "structure",
        "structure",
        trim=trim,
    )


def make_state_quantity(
    dir_img: Path,
    pn: PoreNetwork,
    sc: Scene,
    name: str,
    *,
    no_state: int | None = None,
    time_point: float | None = None,
    no_frame: int | None = None,
    trim: bool = True,
) -> Path:
    """
    Renders one quantity of one state of a pore network.

    The state is selected either by its number or by a point in time. Selecting by
    number renders a stored state verbatim; selecting by time evaluates the network at
    that instant via :meth:`~porescene.model.PoreNetwork.state_at`, interpolating
    between the stored states where needed. Call this once per quantity to draw a state
    that carries several of them.

    The color scale spans the whole series rather than the state at hand -- the limits
    are resolved by :meth:`~porescene.config.QuantityConfiguration.resolve_limits` from
    the range the quantity covers across every state of the network, so that states
    rendered one after another stay comparable, and a limit pinned on the configuration
    wins over the computed one.

    No colorbar is drawn onto the image. Render one with :func:`make_colorbar`, which
    works out the same limits by itself, and composite it with
    :func:`porescene.image.compose_colorbar`.

    Parameters
    ----------
    dir_img : Path
        Directory to save the rendered image at.
    pn : PoreNetwork
        The pore network to take the state from.
    sc : Scene
        Scene holding the already-built geometry, see :func:`build_structure`.
    name : str
        Name of the quantity to color the network by. The state has to carry it, and
        the scene has to hold a configuration for it.
    no_state : int | None, optional
        Number of the state to render, matched against
        :attr:`~porescene.model.PoreNetworkState.no`, i.e. the index the state was
        loaded from the source data under -- not its position in
        :attr:`~porescene.model.PoreNetwork.states`. Mutually exclusive with
        ``time_point``.
    time_point : float | None, optional
        Point on the network's :attr:`~porescene.model.PoreNetwork.time_axis` to render.
        Times between two stored states are interpolated per quantity, times outside the
        stored range are clamped. Mutually exclusive with ``no_state``.
    no_frame : int | None, optional
        Position in a frame sequence, used to name the image, see :func:`make_img`.
        Set by :func:`make_frames`; there is rarely a reason to pass it directly.
    trim : bool, optional
        Whether to crop the rendered image to its content, see :func:`make_img`, by
        default True. States rendered for a series are trimmed each to their own
        content, so pass ``False`` to keep them on a common canvas.

    Returns
    -------
    Path
        The file path to the rendered image.

    Raises
    ------
    ValueError
        If neither or both of ``no_state`` and ``time_point`` are given, if no stored
        state carries the requested ``no_state``, or if the state carries no quantity
        named ``name``.
    """
    if (no_state is None) == (time_point is None):
        raise ValueError("Give either 'no_state' or 'time_point', not both or neither")

    if no_state is not None:
        state = next((st for st in pn if st.no == no_state), None)
        if state is None:
            known = [st.no for st in pn]
            raise ValueError(
                f"No state numbered {no_state} in the pore network, which holds "
                f"{len(known)} states: {known[:10]}{' ...' if len(known) > 10 else ''}"
            )
    else:
        state = pn.state_at(time_point)

    quant = state.get_quantity(name)
    conf = sc.config_scene[name]

    # check scene layers
    do_spheres = sc.config_scene.enable_spheres and sc.has_spheres
    do_cylinders = sc.config_scene.enable_cylinders and sc.has_cylinders
    do_clusters = sc.config_scene.enable_clusters and sc.has_clusters

    limits = conf.resolve_limits(*quantity_range(pn, sc, name))
    grad = conf.gradient_class(conf.colors, *limits)

    return make_img(
        dir_img,
        sc,
        do_spheres,
        do_cylinders,
        do_clusters,
        grad(conf.value_display(quant.pore_values)) if do_spheres else [],
        grad(conf.value_display(quant.throat_values)) if do_cylinders else [],
        grad(conf.value_display(quant.pore_values)) if do_clusters else [],
        name,
        name,
        name,
        no_state=state.no,
        no_frame=no_frame,
        trim=trim,
    )


def make_frames(
    pth: Path,
    pn: PoreNetwork,
    sc: Scene,
    name: str,
    fps: int = 30,
    *,
    duration: float | None = None,
    speed: float | None = None,
    t_start: float | None = None,
    t_end: float | None = None,
    trim: bool = True,
) -> list[Path]:
    """
    Renders the frames of a video by resampling a pore network onto regular time steps.

    Computed results are commonly written at irregular intervals, while a video needs
    frames at regular ones. This walks the frame times of
    :meth:`~porescene.model.PoreNetwork.frame_times` and renders each of them with
    :func:`make_state_quantity`, so that playback speed follows the physical time of the
    results rather than the spacing of the stored states.

    The frames are named so that sorting by file name yields the playback order. Feed
    them -- either the bare renders or the composites a colorbar was joined onto with
    :func:`porescene.image.compose_colorbar_frames` -- straight to
    :func:`porescene.image.frames2mp4` or :func:`porescene.image.frames2gif`. Call this
    once per quantity to turn several of them into videos.

    Compose the colorbar with :func:`porescene.image.compose_colorbar_frames` rather
    than with :func:`porescene.image.compose_colorbar`: the series version trims the
    frames against one another, which keeps the colorbar the same size and in the same
    place throughout, while the single-image one crops every frame to its own content.

    .. attention::

        Rendering is by far the slowest part: a 12 second video at 30 fps means 360
        renders. Check the schedule with
        :meth:`~porescene.model.PoreNetwork.frame_times` before committing to it.

    Parameters
    ----------
    pth : Path
        Directory to save the rendered frames at.
    pn : PoreNetwork
        The pore network to resample.
    sc : Scene
        Scene holding the already-built geometry, see :func:`build_structure`.
    name : str
        Name of the quantity to color the network by, see
        :func:`make_state_quantity`.
    fps : int, optional
        Playback speed of the video in frames per second, by default 30.
    duration : float | None, optional
        Wall-clock length of the video in seconds. Mutually exclusive with ``speed``.
    speed : float | None, optional
        Simulated seconds per wall-clock second, by default 1.0, i.e. real time.
        Mutually exclusive with ``duration``.
    t_start : float | None, optional
        First frame time, by default the earliest time in the network.
    t_end : float | None, optional
        Time the frames run up to, by default the latest time in the network.
    trim : bool, optional
        Whether to crop each rendered frame to its content, see :func:`make_img`, by
        default True. Since every frame is cropped on its own, the sequence can end up
        with frames of differing size; pass ``False`` where the encoder needs one and
        the same canvas throughout.

    Returns
    -------
    list[Path]
        The rendered frames, in playback order.

    Examples
    --------
    .. code-block:: python
        :caption: Python
        :linenos:

        for svm in vars_state:
            pths = worker.make_frames(pth_frames, pn, sc, svm.name, fps=30, duration=12)
            image.frames2mp4(pths, pth_data / f"{svm.name}.mp4", fps=30)
    """
    times = pn.frame_times(
        fps, duration=duration, speed=speed, t_start=t_start, t_end=t_end
    )

    return [
        make_state_quantity(
            pth, pn, sc, name, time_point=float(t), no_frame=no_frame, trim=trim
        )
        for no_frame, t in enumerate(times)
    ]


def make_colorbar(
    dir_img: Path,
    pn: PoreNetwork,
    sc: Scene,
    name: str,
    /,
    ticks: tuple[str, ...] = (),
    **kwargs,
) -> Path:
    """
    Renders the colorbar of a quantity as SVG and PNG.

    The counterpart to the ``make_*`` functions that render the scene: they leave their
    images bare, and this draws the scale they were colored on, to be joined to one of
    them with :func:`porescene.image.compose_colorbar`.

    The limits are worked out the same way the render worked them out, from
    :func:`quantity_range` and
    :meth:`~porescene.config.QuantityConfiguration.resolve_limits`, so that the two
    agree without the render having to hand anything over. The data is only read where
    the configuration does not pin both limits itself.

    The gradient class configured for the quantity decides the kind of colorbar; its
    colors, heading, subheading, text, alignment and orientation are taken from the
    configuration as well. Unless ``ticks`` are given, they are placed equidistantly
    between the limits -- one per color boundary for a segmented gradient, five
    otherwise -- and labelled at the configured precision. Remaining ``kwargs`` are
    applied to the underlying annotation where it has a matching attribute.

    The file is named after the quantity, as ``cb-<name>``, and its stem is extended by
    an ``id-<fingerprint>`` part identifying the rendered markup (see
    :attr:`~porescene.layout.BackgroundAnnotation.id`), so that colorbars differing in
    palette, limits, ticks or label do not overwrite each other. Read the location off
    the returned path.

    Parameters
    ----------
    dir_img
        Directory to save the rendered colorbar at.
    pn
        The pore network the colorbar reports the scale of.
    sc
        The scene holding the configuration of the quantity.
    name
        Name of the quantity the colorbar belongs to.
    ticks
        Tick labels, by default derived from the limits and the configuration.
    **kwargs
        Overrides applied to the annotation before it is rendered.

    Returns
    -------
    Path
        The file path of the rendered PNG. The SVG it was converted from sits next to
        it under the same stem.

    Raises
    ------
    ValueError
        If the quantity is configured with an unknown gradient class.
    """
    conf = sc.config_scene[name]

    if conf.limit_lower is not None and conf.limit_upper is not None:
        limit_lower, limit_upper = float(conf.limit_lower), float(conf.limit_upper)
    else:
        limit_lower, limit_upper = conf.resolve_limits(*quantity_range(pn, sc, name))

    pth = dir_img / ("cb" + SEPARATOR_PROPERTY + name + ".svg")

    if conf.gradient_class is SmoothGradient:
        ovl = SmoothGradientAnnotation(pth)
    elif conf.gradient_class is SegmentedGradient:
        ovl = SegmentedGradientAnnotation(pth)
    elif conf.gradient_class is DiscreteGradient:
        ovl = DiscreteGradientAnnotation(pth)
    else:
        raise ValueError("Unknown gradient class")
    if len(ticks) == 0:
        if conf.gradient_class is SegmentedGradient:
            n_ticks = len(conf.colors) + 1
        else:
            n_ticks = 5
        # two decimals beyond the configured precision keep a tick that falls between
        # two rounding steps of the limits legible instead of collapsing it onto one
        ticks = tick_labels(
            colorbar_ticks(
                limit_lower, limit_upper, n_ticks, precision=conf.precision + 2
            ),
            decimals=max(conf.precision, 0) + 2,
        )
    for arg in kwargs.items():
        if hasattr(ovl, arg[0]):
            setattr(ovl, arg[0], arg[1])
    ovl.gradient_colors = conf.colors
    # the annotation reverses the ticks in place for a vertical colorbar
    ovl.ticks = list(ticks)
    ovl.heading = conf.heading
    ovl.subheading = conf.subheading
    ovl.text = conf.text
    ovl.align = conf.align
    ovl.orientation = conf.orientation
    ovl.color_nan = conf.color_nan
    ovl.save(stamp_id=True)

    return svg2png(ovl.path)
