# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Felix Faber /
# Otto von Guericke University Magdeburg, Thermal Process Engineering

import json
import math
import warnings
from collections.abc import Sequence
from pathlib import Path
from typing import NamedTuple, Self, cast

import bpy

import bmesh  # type: ignore # isort:skip
from mathutils import Matrix, Vector  # type: ignore # isort:skip
from mathutils.geometry import intersect_point_line  # type: ignore # isort:skip
import numpy as np
from rich import progress

from porescene import image
from porescene.color import Color, ColorArray
from porescene.config import (
    AxesConfiguration,
    ImageConfiguration,
    RenderConfiguration,
    SceneConfiguration,
)
from porescene.material import MaterialSpec, color_inputs, lookup
from porescene.utility import RenderDevice, _get_spinner, suppress_stdout


def _radians(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Converts an Euler rotation given in degrees to radians."""
    return (math.radians(x), math.radians(y), math.radians(z))


class _AxisSpec(NamedTuple):
    """Per-axis parameters for drawing major ticks, minor ticks and labels."""

    prefix: str
    ticks: object
    positions: object
    precision: int
    aspect: float
    enable_minor: bool
    enable_labels: bool
    base: list[float]
    dim: int
    tick_rotation: tuple[float, float, float]
    label_rotation: tuple[float, float, float]
    label_dim: int
    align_first: str
    align_last: str
    first_gated: bool
    minor_special: bool
    hide_first_label: bool = False


class Scene:
    # Three-point lighting rig as ``(name, energy, softness angle, azimuth
    # offset from the camera, elevation)``, angles in degrees. The offsets are
    # relative to the camera, which keeps the rig valid at any azimuth.
    #
    # The key sits far enough to one side (+70 degrees) that it only ever
    # reaches the bounding box face on the camera's right, while the weaker
    # fill only reaches the face on its left. That split is what makes the
    # near vertical edge readable: the two faces meeting at it stay a factor
    # 0.53-0.82 apart in irradiance at every camera azimuth, instead of coming
    # out equally lit and merging into one flat silhouette. The rim
    # works from behind and above and only grazes the silhouette edges.
    #
    # The energies are calibrated for the "Standard" view transform (see
    # RenderConfiguration.view_transform): together with the world light of
    # _WORLD_STRENGTH, the most brightly lit surface receives an irradiance of 0.98,
    # so it shows its base color almost exactly and no diffuse surface clips.
    _LIGHT_RIG = (
        ("Key_Light", 2.0, 12, 70, 40),
        ("Fill_Light", 1.0, 35, -40, 30),
        ("Rim_Light", 1.0, 10, -150, 50),
    )

    # Strength of the uniform white world light, which brightens the shadows.
    _WORLD_STRENGTH = 0.12

    # Camera azimuth in degrees that :meth:`create_axes` lays the axes out for. Any
    # azimuth in [45, 90) gives the same layout, so this one sits safely inside.
    _AZIMUTH_AXES = 67.5

    # GPU backends in the order RenderDevice.AUTO tries them: OptiX before CUDA, as
    # it is faster on the NVIDIA cards that support both
    _BACKENDS_GPU = ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL")

    def __init__(self, extent: np.ndarray) -> None:
        """
        Creates an empty :class:`Scene`, wiping Blender's default scene contents and
        setting up a camera, lights and Cycles render settings. Use :meth:`from_json`
        to create a scene sized and configured from a PoreScene JSON file instead.
        """
        self.config_axes = AxesConfiguration(extent)
        self.config_image = ImageConfiguration()
        self.config_render = RenderConfiguration()
        self.config_scene = SceneConfiguration()
        self.size_bounding_box = 10
        self.n_segments = 48
        self.size = (10, 10, 10)
        self.shift = (0, 0, 0)
        self.scale = 1e5
        self._ang_azimuth = 0.0
        self._boundary_cylinder = {
            "left": False,
            "right": False,
            "front": False,
            "back": False,
            "bottom": False,
            "top": False,
        }

        self.has_axes = False
        self.has_cells = False
        self.has_clusters = False
        self.has_cylinders = False
        self.has_lights = False
        self.has_solid = False
        self.has_spheres = False
        self.has_void = False

        # remove default objects from scene
        self.remove_defaults()

        # add camera and lights
        self.create_camera("3D")
        self.create_lights()

        # create collection for scene layers and add it to the scene
        self._layers = bpy.data.collections.new("Layers")
        bpy.context.scene.collection.children.link(self._layers)

        # cycles configuration. Settings a user may want to change live in
        # config_render and are applied by render(); the ones below are what the rest
        # of the pipeline relies on, such as the alpha channel that img_trim crops by.
        bpy.context.scene.render.engine = "CYCLES"

        bpy.context.scene.render.resolution_percentage = 100
        bpy.context.scene.render.film_transparent = True
        bpy.context.scene.render.use_persistent_data = True
        bpy.context.scene.render.image_settings.color_mode = "RGBA"
        bpy.context.scene.render.image_settings.color_depth = "16"

        # the albedo and normal passes guide the denoiser along the edges of surfaces
        # and color boundaries, so it doesn't blend the colors of neighboring pores
        bpy.context.scene.cycles.denoiser = "OPENIMAGEDENOISE"
        bpy.context.scene.cycles.denoising_input_passes = "RGB_ALBEDO_NORMAL"
        bpy.context.scene.cycles.denoising_prefilter = "ACCURATE"
        bpy.context.scene.cycles.use_animated_seed = False

        # the render device applied last, as (requested device, backend used)
        self._device: tuple[RenderDevice, str] | None = None

        self.scale = self.size_bounding_box / max(extent)
        self.shift = (self.size_bounding_box - extent * self.scale) / 2
        self.aspect = extent / max(extent)

    @classmethod
    def from_json(cls, extent: np.ndarray, pth_config: Path) -> Self:
        """
        Creates a :class:`Scene` instance sized to the given physical domain
        dimensions, configured from a PoreScene JSON configuration file.

        Parameters
        ----------
        extent : np.ndarray
            Physical extent of the domain along x, y and z, used to derive the
            scene's :attr:`scale`, :attr:`shift` and :attr:`aspect`.
        pth_config : Path
            Path to the PoreScene JSON configuration file. Its optional ``"axes"``,
            ``"image"`` and ``"render"`` sections populate :attr:`config_axes`,
            :attr:`config_image` and :attr:`config_render`, respectively.

        Returns
        -------
        Self
            :class:`Scene` instance created from the given dimensions and
            configuration file.
        """
        ins = cls(extent)

        with pth_config.open(mode="r", encoding="UTF-8") as json_data:
            config = json.load(json_data)

        if "axes" in config:
            ins.config_axes = AxesConfiguration.from_dict(extent, config["axes"])
        if "image" in config:
            ins.config_image = ImageConfiguration.from_dict(config["image"])
        if "render" in config:
            ins.config_render = RenderConfiguration.from_dict(config["render"])

        return ins

    def apply_colors(
        self,
        name_mesh: str,
        colors: ColorArray | Sequence[Color],
        frame: int = 0,
    ) -> Self:
        """
        Sets the colors for all items in a collection for given frame.

        ``"Spheres"`` and ``"Cylinders"`` take one color per pore and per throat,
        ``"Clusters"`` one per cluster and ``"Cells"`` one per cell of the tessellation,
        in the order :meth:`create_cells` was given the cells in.

        Raises
        ------
        ValueError
            If the cells are given a different number of colors than the tessellation
            has cells.
        """
        if not isinstance(colors, ColorArray):
            colors = ColorArray(colors)
        color_array = colors.lnrgba.astype(np.float32)

        # Single meshes
        mesh = bpy.data.meshes.get(name_mesh)
        if mesh is not None and "cell" in mesh.attributes:
            # the cells share one mesh, whose faces take the color of their cell
            if len(color_array) != mesh["cell_count"]:
                raise ValueError(
                    f"Expected a color for each of the {mesh['cell_count']} cells of "
                    f"the tessellation, got {len(color_array)}"
                )
            cell_attr = mesh.attributes["cell"]
            cells = np.empty(len(cell_attr.data), dtype=np.int32)
            cell_attr.data.foreach_get("value", cells)
            color_attr = mesh.attributes["cell_color"]
            color_attr.data.foreach_set("color", color_array[cells].ravel())
            return self
        if mesh is not None:
            color_attr = mesh.attributes.get("color")
            color_attr.data.foreach_set("color", color_array.ravel())
            return self

        # Collection of individual objects
        col = bpy.data.collections.get(name_mesh)
        if col is not None:

            def label_no(name: str) -> int:
                parts = name.split("_")
                return int(parts[1]) if parts[0] == "label" and parts[1].isdigit() else 0

            for idx, obj in enumerate(
                sorted(col.objects, key=lambda o: label_no(o.name))
            ):
                if idx >= len(color_array):
                    break
                obj_mesh = cast(bpy.types.Mesh, obj.data)
                color_attr = obj_mesh.attributes.get("cluster_color")
                if color_attr is None:
                    continue
                color_attr.data.foreach_set(
                    "color", np.tile(color_array[idx], len(obj_mesh.vertices))
                )
            return self

        raise Exception(f"There is no mesh or collection named '{name_mesh}'")

    def create_axes(self) -> Self:
        """
        Adds axes with ticks and labels to the scene.
        """
        cfg = self.config_axes
        lw = cfg.line_width
        d = cfg.spacing
        sbb = self.size_bounding_box
        sx, sy, sz = self.shift
        ax, ay, az = self.aspect

        mat_axis = self.get_material("AXES")
        font = bpy.data.fonts.load(str(cfg.font_family), check_existing=True)
        col = bpy.data.collections.new("Axes")

        # axis lines. The outermost ticks are centered on the ends of an axis and so
        # stick out by half a line width; the axes are stretched by that same amount
        # at either end to meet them flush.
        mesh_axis = self._add_line("axis", lw, sbb)
        axis_lines = [
            ("axis_x", (sx - 0.5 * lw, sbb - sy + d + lw, sz), _radians(0, 0, -90), ax),
            ("axis_y", (sbb - sx + d, sy - 0.5 * lw, sz), _radians(0, 0, 0), ay),
            ("axis_z", (sbb - sx + d, sy, sz - 0.5 * lw), _radians(90, 0, 0), az),
        ]
        for name, location, rotation, aspect in axis_lines:
            axis = bpy.data.objects.new(name, mesh_axis)
            col.objects.link(axis)
            axis.location = location
            axis.rotation_euler = rotation
            axis.scale = (1, (sbb * aspect + lw) / sbb, 1)

        # axis labels
        axis_labels = [
            (
                cfg.label_x,
                [sbb / 2, sbb - sy + 2 * d + lw, sz],
                1,
                self._clearance_ticks(0),
                _radians(0, 0, 180),
                "scale x",
                "axis label x",
            ),
            (
                cfg.label_y,
                [sbb - sx + 2 * d + lw, sbb / 2, sz],
                0,
                self._clearance_ticks(1),
                _radians(0, 0, 90),
                "scale y",
                "axis label y",
            ),
            (
                cfg.label_z,
                [sbb - sx + 2 * d + lw, sy, sbb / 2],
                0,
                self._clearance_ticks(2),
                _radians(0, 90, 90),
                "scale z",
                "axis label z",
            ),
        ]
        for body, loc, bump, clearance, rotation, curve, name in axis_labels:
            if not body:
                continue
            loc[bump] += clearance
            self._add_text(
                col,
                font,
                name,
                body,
                cfg.font_size_labels,
                "CENTER",
                tuple(loc),
                rotation,
                curve_name=curve,
            )

        # ticks with labels
        if any(cfg.enable_ticks):
            mesh_tick = self._add_line("tick", lw, cfg.tick_length)
            specs = [
                _AxisSpec(
                    prefix="x",
                    ticks=cfg.ticks_x,
                    positions=getattr(cfg, "position_tick_x", None),
                    precision=cfg.precision[0],
                    aspect=ax,
                    enable_minor=cfg.enable_ticks_minor[0],
                    enable_labels=cfg.enable_labels_ticks[0],
                    base=[sx - 0.5 * lw, sbb - sy + d + lw, sz],
                    dim=0,
                    tick_rotation=_radians(0, 0, 0),
                    label_rotation=_radians(0, 0, 180),
                    label_dim=1,
                    align_first="RIGHT",
                    align_last="LEFT",
                    first_gated=True,
                    minor_special=False,
                ),
                _AxisSpec(
                    prefix="y",
                    ticks=cfg.ticks_y,
                    positions=getattr(cfg, "position_tick_y", None),
                    precision=cfg.precision[1],
                    aspect=ay,
                    enable_minor=cfg.enable_ticks_minor[1],
                    enable_labels=cfg.enable_labels_ticks[1],
                    base=[sbb - sx + d + lw, sy + 0.5 * lw, sz],
                    dim=1,
                    tick_rotation=_radians(0, 0, -90),
                    label_rotation=_radians(0, 0, 90),
                    label_dim=0,
                    align_first="LEFT",
                    align_last="RIGHT",
                    first_gated=False,
                    minor_special=True,
                ),
                _AxisSpec(
                    prefix="z",
                    ticks=cfg.ticks_z,
                    positions=getattr(cfg, "position_tick_z", None),
                    precision=cfg.precision[2],
                    aspect=az,
                    enable_minor=cfg.enable_ticks_minor[2],
                    enable_labels=cfg.enable_labels_ticks[2],
                    base=[sbb - sx + d + lw, sy, sz + 0.5 * lw],
                    dim=2,
                    tick_rotation=_radians(90, 90, 0),
                    label_rotation=_radians(0, 90, 90),
                    label_dim=0,
                    align_first="RIGHT",
                    align_last="LEFT",
                    first_gated=False,
                    minor_special=False,
                    hide_first_label=True,
                ),
            ]
            for enabled, spec in zip(cfg.enable_ticks, specs, strict=False):
                if enabled:
                    self._draw_axis_ticks_major(col, font, mesh_tick, spec)

        # apply axis material
        for obj in col.objects:
            obj.data.materials.clear()
            obj.data.materials.append(mat_axis)
            obj.visible_shadow = False

        # add collection into context
        bpy.context.scene.collection.children.link(col)
        self.has_axes = True

        # the axes are built for a fixed camera azimuth, so they are moved to where the
        # camera actually is
        self._move_axes(self._AZIMUTH_AXES, self._ang_azimuth)
        return self

    def _clearance_ticks(self, dim: int) -> float:
        """
        Returns the distance the label of the axis ``dim`` (0 = x, 1 = y, 2 = z) is
        pushed outwards, so that it clears the ticks drawn on that axis. Ticks without
        labels only need room for the tick marks themselves.
        """
        cfg = self.config_axes
        ticks = (cfg.ticks_x, cfg.ticks_y, cfg.ticks_z)[dim]

        if not cfg.enable_ticks[dim] or len(ticks) == 0:
            return 0

        if not cfg.enable_labels_ticks[dim]:
            return cfg.tick_length

        return cfg.tick_length + cfg.font_size_ticks

    def _add_line(self, name: str, width: float, height: float) -> bpy.types.Mesh:
        """Creates a single rectangular face in the xy-plane."""
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(
            [(0, 0, 0), (width, 0, 0), (width, height, 0), (0, height, 0)],
            [],
            [(0, 1, 2, 3)],
        )
        mesh.update()
        return mesh

    def _add_text(
        self,
        col: bpy.types.Collection,
        font: bpy.types.VectorFont,
        name: str,
        body: str,
        size: float,
        align_x: str,
        location: tuple[float, float, float],
        rotation: tuple[float, float, float],
        curve_name: str | None = None,
    ) -> bpy.types.Object:
        """Creates a text object from a font curve and links it to ``col``."""
        curve = bpy.data.curves.new(type="FONT", name=curve_name or name)
        curve.body = body
        curve.size = size
        curve.align_x = align_x
        curve.align_y = "TOP"
        obj = bpy.data.objects.new(name=name, object_data=curve)
        col.objects.link(obj)
        obj.data.font = font
        obj.location = location
        obj.rotation_euler = rotation
        return obj

    def _draw_axis_ticks_major(
        self,
        col: bpy.types.Collection,
        font: bpy.types.VectorFont,
        mesh_tick: bpy.types.Mesh,
        spec: _AxisSpec,
    ) -> None:
        """Draws major ticks, minor ticks and tick labels for a single axis."""
        cfg = self.config_axes
        lw = cfg.line_width
        sbb = self.size_bounding_box
        n = len(spec.ticks)

        for idx, value in enumerate(spec.ticks):
            loc = list(spec.base)
            loc[spec.dim] += sbb * spec.aspect * spec.positions[idx]
            align = "CENTER"
            if idx == 0 and (cfg.indent_ticks or not spec.first_gated):
                loc[spec.dim] += 0.5 * lw
                align = spec.align_first
            if idx == n - 1 and cfg.indent_ticks:
                loc[spec.dim] -= 0.5 * lw
                align = spec.align_last

            tick = bpy.data.objects.new(f"{spec.prefix} tick {idx}", mesh_tick)
            col.objects.link(tick)
            tick.location = tuple(loc)
            tick.rotation_euler = spec.tick_rotation

            if spec.enable_minor:
                self._draw_axis_ticks_minor(col, mesh_tick, spec, idx)

            if not spec.enable_labels:
                continue

            if idx == 0 and spec.hide_first_label:
                continue

            # the value is coerced to float so that an integer tick keeps its trailing
            # zeros, which the stripping below would otherwise eat along with the dot
            label = str(round(float(value), spec.precision)).rstrip("0").rstrip(".")
            label_loc = list(loc)
            label_loc[spec.label_dim] += cfg.spacing + cfg.tick_length
            self._add_text(
                col,
                font,
                f"{spec.prefix} tick label {idx}",
                label,
                cfg.font_size_ticks,
                align,
                tuple(label_loc),
                spec.label_rotation,
            )

    def _draw_axis_ticks_minor(
        self,
        col: bpy.types.Collection,
        mesh_tick: bpy.types.Mesh,
        spec: _AxisSpec,
        idx: int,
    ) -> None:
        """Draws the minor ticks that follow the major tick at ``idx``."""
        cfg = self.config_axes
        sbb = self.size_bounding_box
        pos = spec.positions

        if len(pos) < 2:
            # a single major tick has no adjacent tick to derive a spacing from
            return

        if spec.minor_special and cfg.num_ticks_minor == 1:
            spacing = pos[1] - pos[0] / 2
        else:
            spacing = (pos[1] - pos[0]) / (cfg.num_ticks_minor + 1)

        if idx + 1 == len(spec.ticks):
            n_minor = math.floor((1 - pos[-1]) / spacing)
        else:
            n_minor = cfg.num_ticks_minor

        for j in range(n_minor):
            loc = list(spec.base)
            loc[spec.dim] += sbb * spec.aspect * (pos[idx] + spacing * (j + 1))
            tick = bpy.data.objects.new(f"{spec.prefix} tick minor {idx}", mesh_tick)
            col.objects.link(tick)
            tick.location = tuple(loc)
            tick.rotation_euler = spec.tick_rotation
            tick.scale = (1, 0.5, 1)

    def create_camera(self, view: str = "3D") -> Self:
        """
        Brings camera in position.
        """

        if view == "3D":
            bpy.data.objects["Camera"].location = (25, 40, 20)
            bpy.data.objects["Camera"].rotation_euler = (
                math.radians(90),
                0,
                math.radians(150),
            )
        elif view == "2D":
            bpy.data.objects["Camera"].location = (5, 40, 15)
            bpy.data.objects["Camera"].rotation_euler = (
                math.radians(90),
                0,
                math.radians(180),
            )
        bpy.data.cameras["Camera"].shift_y = -0.55
        bpy.data.cameras["Camera"].lens = 50

        # track the camera's true azimuth around the bounding box's pivot, so
        # that rotate_azimuth's corner-snapping starts from where the camera
        # actually is instead of assuming it starts centered on a corner
        center = self.size_bounding_box / 2
        x, y, _ = bpy.data.objects["Camera"].location
        ang_before = self._ang_azimuth
        self._ang_azimuth = math.degrees(math.atan2(y - center, x - center))

        # the lightning rig and the axes are aligned with the camera, so a later view
        # change has to bring them along
        if self.has_lights:
            self._aim_lights()
        if self.has_axes:
            self._move_axes(ang_before, self._ang_azimuth)
        return self

    def create_cells(
        self,
        pos: np.ndarray,
        corners: Sequence[np.ndarray],
        selection: np.ndarray | None = None,
        bevel: float = 0.05,
        material: str | MaterialSpec | None = None,
    ) -> Self:
        """
        Adds the cells of a tessellation of the domain to the scene, such as the Voronoi
        cells around the pores of a network.

        Every cell is built as the convex hull of its corners, which suits tessellations
        into convex cells -- Voronoi and Laguerre tessellations, also when clipped to the
        domain -- but not concave cells. Triangles of the hull that lie in one plane are
        merged back into the facets of the cell.

        The edges of every cell are rounded off over the width ``bevel`` and darkened
        slightly towards the edge, so that neighboring cells meet in a narrow groove that
        sets them apart even where their colors are alike. Both are done in the
        shading, while the cells keep their exact shape: a bevel of the geometry would
        have to narrow to fit the shortest edge of a cell, and Voronoi cells have many
        short edges, so its width would vary from one cell to the next.

        All cells form a single mesh named ``"Cells"``. Color them with
        :meth:`apply_colors`, passing one color per cell of the tessellation, in the
        order of ``corners``.

        They are rendered with ``material``, a material or the name of a registered one
        (see :mod:`porescene.material`), by default
        :attr:`SceneConfiguration.material_cells
        <porescene.config.SceneConfiguration.material_cells>`.

        Parameters
        ----------
        pos : np.ndarray
            Positions of the cell corners, of shape ``(N, 3)``, in meters.
        corners : Sequence[np.ndarray]
            Indices into ``pos`` of the corners of each cell, zero-based.
        selection : np.ndarray | None, optional
            Indices of the cells to build, by default all of them. Of opaque cells only
            the ones touching the domain boundary can be seen, so building just these
            gives the same image in a fraction of the time.
        bevel : float, optional
            Width of the rounded edges, as a fraction of the mean cell size, by default
            0.05. The mean cell size is the edge length of a cube with the mean volume of
            a cell, assuming the cells fill the bounding box of their corners. ``0``
            keeps the edges sharp.
        material : str | MaterialSpec | None, optional
            Material of the cells, by default the one of the scene configuration. The
            rounded edges need it to have a Principled BSDF.

        Returns
        -------
        Self
            The scene, holding the cells.

        Raises
        ------
        ValueError
            If the corners of a cell span no volume.
        """
        if material is None:
            material = self.config_scene.material_cells
        if selection is None:
            selection = np.arange(len(corners))

        pos = np.asarray(pos) * self.scale + self.shift
        size = (np.prod(np.ptp(pos, axis=0)) / len(corners)) ** (1 / 3)

        # each cell is built in a mesh of its own, since the bmesh operators slow down
        # with the size of the mesh they work in, and the cells are joined afterwards
        coords, faces, dist_edge, cells = [], [], [], []
        n_verts = 0
        for idx in progress.track(selection, description="Creating cells"):
            bm = _convex_cell(pos[corners[idx]])
            if bm.calc_volume() <= 1e-9 * size**3:
                bm.free()
                raise ValueError(f"The corners of cell {idx} span no volume")
            layer = bm.loops.layers.float["cell_edge"]
            bm.verts.index_update()
            coords.append([v.co[:] for v in bm.verts])
            for f in bm.faces:
                faces.append([v.index + n_verts for v in f.verts])
                dist_edge.extend(loop[layer] for loop in f.loops)
            cells.extend([idx] * len(bm.faces))
            n_verts += len(bm.verts)
            bm.free()

        mesh = bpy.data.meshes.new("Cells")
        mesh.from_pydata(np.concatenate(coords), [], faces)

        # every face carries the index of its cell, by which apply_colors spreads the
        # colors of the cells onto their faces. The color attribute must not be named
        # "color", which Cycles doesn't read off a face.
        cell_attr = mesh.attributes.new(name="cell", type="INT", domain="FACE")
        cell_attr.data.foreach_set("value", np.asarray(cells, dtype=np.int32))
        mesh["cell_count"] = len(corners)
        default_color = np.array(Color("#58646E").lnrgba, dtype=np.float32)
        color_attr = mesh.attributes.new(
            name="cell_color", type="FLOAT_COLOR", domain="FACE"
        )
        color_attr.data.foreach_set("color", np.tile(default_color, len(faces)))
        edge_attr = mesh.attributes.new(name="cell_edge", type="FLOAT", domain="CORNER")
        edge_attr.data.foreach_set("value", np.asarray(dist_edge, dtype=np.float32))
        mesh.update()

        mat = self.get_material(material).copy()
        self._apply_attribute_color(mat, "GEOMETRY", "cell_color")
        if bevel > 0:
            _round_cell_edges(mat, bevel * size)
        mesh.materials.append(mat)

        obj = bpy.data.objects.new("Cells", mesh)
        self._layers.objects.link(obj)

        self.has_cells = True
        return self

    def create_clusters(
        self, pth: Path, material: str | MaterialSpec | None = None
    ) -> Self:
        """
        Adds pore clusters to the scene.

        They are rendered with ``material``, a material or the name of a registered one
        (see :mod:`porescene.material`), by default
        :attr:`SceneConfiguration.material_clusters
        <porescene.config.SceneConfiguration.material_clusters>`.
        """

        def handler(n: str):
            parts = n.split("_")
            if parts[0] == "label" and parts[1].isdigit():
                return int(parts[1])
            else:
                return 0

        with _get_spinner(f"[cyan]Loading object: {pth.name}") as p:
            p.add_task("load", total=None)
            _import_object(pth)

        if material is None:
            material = self.config_scene.material_clusters
        mat = self.get_material(material).copy()
        self._apply_attribute_color(mat, "GEOMETRY", "cluster_color")

        col = bpy.data.collections.new("Clusters")
        col_default = bpy.data.collections.get("Collection")
        for obj in progress.track(
            sorted(bpy.data.objects, key=lambda c: handler(c.name)),
            description="Creating cluster geometries",
        ):
            if "label_" in obj.name and obj.name != "label_0":
                obj.rotation_euler = (0, 0, 0)
                obj.scale = (self.scale, self.scale, self.scale)
                obj.location = self.shift
                col_default.objects.unlink(obj)
                col.objects.link(obj)

        default_color = np.array(Color("#58646E").lnrgba, dtype=np.float32)
        for obj in progress.track(col.objects, description="Creating cluster materials"):
            mesh = cast(bpy.types.Mesh, obj.data)
            color_attr = mesh.attributes.new(
                name="cluster_color", type="FLOAT_COLOR", domain="POINT"
            )
            color_attr.data.foreach_set(
                "color", np.tile(default_color, len(mesh.vertices))
            )
            mesh.materials.append(mat)
        bpy.context.scene.collection.children.link(col)
        self.has_clusters = True
        return self

    def create_cylinders(
        self,
        pos: np.ndarray,
        r: np.ndarray,
        name: str = "Cylinders",
        material: str | MaterialSpec | None = None,
    ) -> Self:
        """
        Places a cylinder for each throat in the scene.

        They are rendered with ``material``, a material or the name of a registered one
        (see :mod:`porescene.material`), by default
        :attr:`SceneConfiguration.material_cylinders
        <porescene.config.SceneConfiguration.material_cylinders>`.
        """
        pos1 = pos[:, 0:3] * self.scale
        pos2 = pos[:, 3:6] * self.scale
        d = pos2 - pos1
        r = r * self.scale
        dist = np.linalg.norm(d, axis=1)
        theta = np.arccos(d[:, 2] / dist)
        phi = np.arctan2(d[:, 1], d[:, 0])
        loc = d / 2 + pos1 + self.shift

        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(loc.tolist(), [], [])
        mesh.update()

        rotation = np.zeros((len(r), 3), dtype=np.float32)
        rotation[:, 1] = theta
        rotation[:, 2] = phi
        rot_attr = mesh.attributes.new(
            name="rotation", type="FLOAT_VECTOR", domain="POINT"
        )
        rot_attr.data.foreach_set("vector", rotation.ravel())

        iscale = np.column_stack([r, r, dist]).astype(np.float32)
        scale_attr = mesh.attributes.new(
            name="iscale", type="FLOAT_VECTOR", domain="POINT"
        )
        scale_attr.data.foreach_set("vector", iscale.ravel())

        mesh.attributes.new(name="color", type="FLOAT_COLOR", domain="POINT")

        obj = bpy.data.objects.new(name, mesh)

        self._layers.objects.link(obj)

        if material is None:
            material = self.config_scene.material_cylinders
        obj_template = self._get_cylinder_template(material)
        mod = obj.modifiers.new("CylinderInstances", type="NODES")
        mod.node_group = self._get_node_group(obj_template)

        self.has_cylinders = True
        return self

    def _get_cylinder_template(self, material: str | MaterialSpec) -> bpy.types.Object:
        """
        Returns a unit cylinder (radius=1, depth=1).
        """
        spec = lookup(material)
        name = f"Cylinder_{spec.name}"
        obj_tmpl = bpy.data.objects.get(name)
        if obj_tmpl is not None:
            return obj_tmpl

        bpy.ops.mesh.primitive_cylinder_add(vertices=self.n_segments, radius=1, depth=1)
        obj_tmpl = bpy.context.view_layer.objects.active
        obj_tmpl.name = name
        obj_tmpl.location = (0, 0, 0)
        obj_tmpl.rotation_euler = (0, 0, 0)
        obj_tmpl.scale = (1, 1, 1)
        obj_tmpl.data.polygons.foreach_set(
            "use_smooth", [True] * len(obj_tmpl.data.polygons)
        )

        mat = self.get_material(spec).copy()
        obj_tmpl.data.materials.append(mat)
        self._apply_attribute_color(mat, "INSTANCER", "color")

        templates_col = bpy.data.collections.get("Templates")
        if not templates_col:
            templates_col = bpy.data.collections.new("Templates")
            bpy.context.scene.collection.children.link(templates_col)
            templates_col.hide_render = True
            templates_col.hide_viewport = True
        for c in list(obj_tmpl.users_collection):
            c.objects.unlink(obj_tmpl)
        templates_col.objects.link(obj_tmpl)

        return obj_tmpl

    def _apply_attribute_color(
        self, mat: bpy.types.Material, attribute_type: str, attribute_name: str
    ) -> None:
        """
        Colors ``mat`` per item, by the color attribute ``attribute_name``.

        Instanced spheres and cylinders read the attribute from the point they are
        instanced on (``attribute_type="INSTANCER"``), whereas clusters, which are real
        objects, carry it on their own mesh (``"GEOMETRY"``). Where the color enters
        the material is decided by :func:`~porescene.material.color_inputs`.
        """
        tree = mat.node_tree
        sockets = color_inputs(mat)
        attr_node = tree.nodes.new("ShaderNodeAttribute")
        attr_node.attribute_type = attribute_type
        attr_node.attribute_name = attribute_name
        for socket in sockets:
            tree.links.new(attr_node.outputs["Color"], socket)

    def _get_node_group(self, template: bpy.types.Object) -> bpy.types.NodeTree:
        """
        Builds geometry nodes tree that instances :arg:``template`` onto the points of
        the modified object using the per-point "rotation", "iscale", and "color"
        attributes.
        """
        name = f"Instancer_{template.name}"
        group = bpy.data.node_groups.get(name)
        if group is not None:
            return group

        group = bpy.data.node_groups.new(name, "GeometryNodeTree")
        group.interface.new_socket(
            "Geometry", in_out="INPUT", socket_type="NodeSocketGeometry"
        )
        group.interface.new_socket(
            "Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry"
        )

        n_in = group.nodes.new("NodeGroupInput")
        n_out = group.nodes.new("NodeGroupOutput")

        n_color_attr = group.nodes.new("GeometryNodeInputNamedAttribute")
        n_color_attr.data_type = "FLOAT_COLOR"
        n_color_attr.inputs["Name"].default_value = "color"

        n_capture = group.nodes.new("GeometryNodeCaptureAttribute")
        n_capture.domain = "POINT"
        n_capture.capture_items.new(socket_type="RGBA", name="color")

        n_to_points = group.nodes.new("GeometryNodeMeshToPoints")

        n_rot = group.nodes.new("GeometryNodeInputNamedAttribute")
        n_rot.data_type = "FLOAT_VECTOR"
        n_rot.inputs["Name"].default_value = "rotation"

        n_scale = group.nodes.new("GeometryNodeInputNamedAttribute")
        n_scale.data_type = "FLOAT_VECTOR"
        n_scale.inputs["Name"].default_value = "iscale"

        n_obj_info = group.nodes.new("GeometryNodeObjectInfo")
        n_obj_info.inputs["Object"].default_value = template
        n_obj_info.inputs["As Instance"].default_value = True

        n_instance = group.nodes.new("GeometryNodeInstanceOnPoints")

        n_store_color = group.nodes.new("GeometryNodeStoreNamedAttribute")
        n_store_color.domain = "INSTANCE"
        n_store_color.data_type = "FLOAT_COLOR"
        n_store_color.inputs["Name"].default_value = "color"

        group.links.new(n_in.outputs["Geometry"], n_capture.inputs["Geometry"])
        group.links.new(n_color_attr.outputs["Attribute"], n_capture.inputs["color"])
        group.links.new(n_capture.outputs["Geometry"], n_to_points.inputs["Mesh"])
        group.links.new(n_to_points.outputs["Points"], n_instance.inputs["Points"])
        group.links.new(n_obj_info.outputs["Geometry"], n_instance.inputs["Instance"])
        group.links.new(n_rot.outputs["Attribute"], n_instance.inputs["Rotation"])
        group.links.new(n_scale.outputs["Attribute"], n_instance.inputs["Scale"])
        group.links.new(n_instance.outputs["Instances"], n_store_color.inputs["Geometry"])
        group.links.new(n_capture.outputs["color"], n_store_color.inputs["Value"])
        group.links.new(n_store_color.outputs["Geometry"], n_out.inputs["Geometry"])

        return group

    @staticmethod
    def _sun_euler(azimuth: float, elevation: float) -> tuple[float, float, float]:
        """
        Converts the direction a sun lamp shines *from* into its rotation.

        ``azimuth`` is measured in the xy plane counter-clockwise from the +x
        axis, ``elevation`` above the horizon, both in degrees, so a positive
        elevation always puts the lamp above the scene. A sun lamp emits along
        its local -Z, so an XYZ euler ``(rx, 0, rz)`` lights the scene from
        ``(sin(rz)sin(rx), -cos(rz)sin(rx), cos(rx))``; matching that against
        ``(cos(el)cos(az), cos(el)sin(az), sin(el))`` gives the rotation below.
        """
        return (math.radians(90 - elevation), 0.0, math.radians(azimuth + 90))

    def _aim_lights(self) -> None:
        """
        Aims every lamp of the rig at the stage, using its azimuth offset
        relative to the camera's current azimuth.
        """
        for name, _, _, d_azimuth, elevation in self._LIGHT_RIG:
            obj = bpy.data.objects.get(name)
            if obj is not None:
                obj.rotation_euler = self._sun_euler(
                    self._ang_azimuth + d_azimuth, elevation
                )

    def create_lights(self) -> Self:
        """
        Adds all nessecary lightnings to the scene.

        The lamps form a three-point rig anchored to the camera's azimuth (see
        :attr:`_LIGHT_RIG`), so key and fill land on the side of the stage the
        camera actually looks at instead of on fixed world directions that may
        end up behind or underneath it. :meth:`rotate_azimuth` turns the lamps
        with the camera, which keeps that anchoring intact.
        """
        col = bpy.data.collections.get("Lights")
        if not col:
            col = bpy.data.collections.new("Lights")
            bpy.context.scene.collection.children.link(col)

        for name, energy, angle_deg, _, _ in self._LIGHT_RIG:
            light_data = bpy.data.lights.new(name=name, type="SUN")
            light_data.energy = energy
            light_data.angle = math.radians(angle_deg)
            col.objects.link(bpy.data.objects.new(name, light_data))

        self._aim_lights()

        world = bpy.context.scene.world
        if world is None:
            world = bpy.data.worlds.new("World")
            bpy.context.scene.world = world
        world.use_nodes = True
        bg = world.node_tree.nodes.get("Background")
        if bg:
            bg.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
            bg.inputs["Strength"].default_value = self._WORLD_STRENGTH

        self.has_lights = True
        return self

    def _orbit(self, obj, angle: float, pivot: Vector | None = None) -> None:
        """
        Rotates an object's location and yaw around a vertical (Z) axis by ``angle``
        radians. The axis passes through ``pivot``, by default the scene's center.
        """
        center = self.size_bounding_box / 2
        cx, cy = (center, center) if pivot is None else (pivot.x, pivot.y)
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        x, y, z = obj.location
        x, y = x - cx, y - cy
        obj.location = (
            x * cos_a - y * sin_a + cx,
            x * sin_a + y * cos_a + cy,
            z,
        )
        rx, ry, rz = obj.rotation_euler
        obj.rotation_euler = (rx, ry, rz + angle)

    def _pose_axis_z(self, ang: float) -> tuple[Vector, float]:
        """
        Returns the pivot and the yaw (in radians) of the z ruler for a camera at the
        azimuth ``ang`` (in degrees).

        The z ruler stands on the box corner that bounds the camera's view on the left,
        which changes every 90 degrees, at the end of the x or y ruler running along the
        near edge there; the pivot is that end, on the ruler's center line. Its ticks and
        labels point along the horizontal axis closest to the camera's left, which changes
        halfway in between, so the labels never face the camera at more than 45 degrees.
        The yaw is relative to the ruler as built by :meth:`create_axes`, with ticks along
        +x from the start of the y ruler at the (+x, -y) corner.
        """
        cfg = self.config_axes
        center = self.size_bounding_box / 2
        sx, sy, _ = self.shift

        # the corner, as signs about the box center, and the outward normal of the near
        # edge ending there
        (cx, cy), (nx, ny) = (
            ((1, -1), (1, 0)),
            ((1, 1), (0, 1)),
            ((-1, 1), (-1, 0)),
            ((-1, -1), (0, -1)),
        )[self._quadrant(ang)]

        offset = cfg.spacing + 0.5 * cfg.line_width
        pivot = Vector(
            (
                center + cx * (center - sx) + nx * offset,
                center + cy * (center - sy) + ny * offset,
                0,
            )
        )
        yaw = math.radians(math.floor((ang - 90) / 90 + 0.5) * 90)
        return pivot, yaw

    @staticmethod
    def _quadrant(ang: float) -> int:
        """
        Returns the quadrant (0 to 3) that the azimuth ``ang`` (in degrees) falls in,
        counted counter-clockwise from the +x axis.
        """
        return math.floor(ang / 90) % 4

    def _move_axes(self, ang_from: float, ang_to: float) -> None:
        """
        Moves the axes from their layout for a camera at the azimuth ``ang_from`` to the
        one for ``ang_to`` (both in degrees).

        The x and y rulers each lie on whichever of their two parallel edges faces the
        camera, the x ruler on the +y edge in quadrants 0 and 1 and the y ruler on the +x
        edge in quadrants 0 and 3. The z ruler is posed as given by :meth:`_pose_axis_z`.
        All three are derived from the same quadrant, so the z ruler always stands at the
        end of the ruler it belongs to.
        """
        q_from, q_to = self._quadrant(ang_from), self._quadrant(ang_to)
        flips = {
            "x": (q_from in (0, 1)) != (q_to in (0, 1)),
            "y": (q_from in (0, 3)) != (q_to in (0, 3)),
        }
        pivot_from, yaw_from = self._pose_axis_z(ang_from)
        pivot_to, yaw_to = self._pose_axis_z(ang_to)
        moves_z = pivot_from != pivot_to or yaw_from != yaw_to

        if not (moves_z or any(flips.values())):
            return

        def _axis_of(name: str) -> str | None:
            for axis in ("x", "y", "z"):
                if name == f"axis_{axis}" or name == f"axis label {axis}":
                    return axis
                if name.startswith(f"{axis} "):
                    return axis
            return None

        sbb = self.size_bounding_box

        for obj in bpy.data.collections["Axes"].objects:
            axis = _axis_of(obj.name)
            if axis is None:
                continue

            if axis == "z":
                if moves_z:
                    # turn the ruler around its pivot, then carry it over to the new one
                    self._orbit(obj, yaw_to - yaw_from, pivot_from)
                    obj.location = Vector(obj.location) + (pivot_to - pivot_from)
                continue

            if not flips[axis]:
                continue

            # record the object's own bounding-box center in world space before
            # anything changes, to correct its position afterwards (see below)
            mat_before = Matrix.LocRotScale(
                obj.location, obj.rotation_euler.to_quaternion(), obj.scale
            )
            local_center = sum((Vector(c) for c in obj.bound_box), Vector()) / 8
            center_before = mat_before @ local_center

            x, y, z = obj.location
            if axis == "y":
                x = sbb - x
            else:
                y = sbb - y
            obj.location = (x, y, z)

            if obj.name == f"axis_{axis}":
                sx, sy, sz = obj.scale
                obj.scale = (-sx, sy, sz)
            else:
                obj.rotation_euler.z += math.radians(180)

                mat_after = Matrix.LocRotScale(
                    obj.location, obj.rotation_euler.to_quaternion(), obj.scale
                )
                center_after = mat_after @ local_center
                desired = Vector(center_before)
                if axis == "y":
                    desired.x = sbb - desired.x
                else:
                    desired.y = sbb - desired.y
                obj.location = Vector(obj.location) + (desired - center_after)

    def create_solid(
        self,
        pth: Path,
        material: str | MaterialSpec | None = None,
        name: str = "solid",
    ):
        """
        Adds the solid into the scene.

        It is rendered with ``material``, a material or the name of a registered one
        (see :mod:`porescene.material`), by default
        :attr:`SceneConfiguration.material_solid
        <porescene.config.SceneConfiguration.material_solid>`.
        """
        with _get_spinner(f"[cyan]Loading object: {pth.name}") as p:
            p.add_task("load", total=None)
            _import_object(pth)
            selected = bpy.context.selected_objects
            assert selected
            obj = selected[0]
        mesh = cast(bpy.types.Mesh, obj.data)
        obj.name = name
        mesh.name = name
        obj.rotation_euler = (math.radians(0), 0, math.radians(0))
        obj.scale = (self.scale, self.scale, self.scale)
        obj.location = self.shift
        if material is None:
            material = self.config_scene.material_solid
        mesh.materials.clear()
        mesh.materials.append(self.get_material(material))
        self.has_solid = True

        return self

    def create_spheres(
        self,
        pos: np.ndarray,
        r: np.ndarray,
        name: str = "Spheres",
        material: str | MaterialSpec | None = None,
    ) -> Self:
        """
        Places a sphere for each pore in the scene.

        They are rendered with ``material``, a material or the name of a registered one
        (see :mod:`porescene.material`), by default
        :attr:`SceneConfiguration.material_spheres
        <porescene.config.SceneConfiguration.material_spheres>`.
        """
        loc = pos * self.scale + self.shift
        r = r * self.scale

        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(loc.tolist(), [], [])
        mesh.update()

        iscale = np.column_stack([r, r, r]).astype(np.float32)
        scale_attr = mesh.attributes.new(
            name="iscale", type="FLOAT_VECTOR", domain="POINT"
        )
        scale_attr.data.foreach_set("vector", iscale.ravel())

        mesh.attributes.new(name="color", type="FLOAT_COLOR", domain="POINT")

        obj = bpy.data.objects.new(name, mesh)

        self._layers.objects.link(obj)

        if material is None:
            material = self.config_scene.material_spheres
        template = self._get_sphere_template(material)

        mod = obj.modifiers.new("SphereInstances", type="NODES")
        mod.node_group = self._get_node_group(template)

        self.has_spheres = True
        return self

    def _get_sphere_template(self, material: str | MaterialSpec) -> bpy.types.Object:
        """
        Returns a unit sphere (radius=1)
        """
        spec = lookup(material)
        name = f"Sphere_{spec.name}"
        obj_tmpl = bpy.data.objects.get(name)
        if obj_tmpl is not None:
            return obj_tmpl

        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=self.n_segments, ring_count=self.n_segments, radius=1
        )
        obj_tmpl = bpy.context.view_layer.objects.active
        obj_tmpl.name = name
        obj_tmpl.location = (0, 0, 0)
        obj_tmpl.rotation_euler = (0, 0, 0)
        obj_tmpl.scale = (1, 1, 1)
        obj_tmpl.data.polygons.foreach_set(
            "use_smooth", [True] * len(obj_tmpl.data.polygons)
        )

        mat = self.get_material(spec).copy()
        obj_tmpl.data.materials.append(mat)
        self._apply_attribute_color(mat, "INSTANCER", "color")

        templates_col = bpy.data.collections.get("Templates")
        if not templates_col:
            templates_col = bpy.data.collections.new("Templates")
            bpy.context.scene.collection.children.link(templates_col)
            templates_col.hide_render = True
            templates_col.hide_viewport = True
        for c in list(obj_tmpl.users_collection):
            c.objects.unlink(obj_tmpl)
        templates_col.objects.link(obj_tmpl)

        return obj_tmpl

    def create_void(
        self,
        pth: Path,
        material: str | MaterialSpec | None = None,
        name: str = "void",
    ) -> Self:
        """
        Adds a 3D object of the void space to the scene.

        It is rendered with ``material``, a material or the name of a registered one
        (see :mod:`porescene.material`), by default
        :attr:`SceneConfiguration.material_void
        <porescene.config.SceneConfiguration.material_void>`.
        """
        with _get_spinner(f"[cyan]Loading object: {pth.name}") as p:
            p.add_task("load", total=None)
            _import_object(pth)
            selected = bpy.context.selected_objects
            assert selected
            obj = selected[0]
        mesh = cast(bpy.types.Mesh, obj.data)
        obj.name = name
        mesh.name = name
        obj.rotation_euler = (0, 0, 0)
        obj.scale = (self.scale, self.scale, self.scale)
        obj.location = self.shift
        if material is None:
            material = self.config_scene.material_void
        mesh.materials.clear()
        mesh.materials.append(self.get_material(material))
        self.has_void = True
        return self

    def get_material(self, material: str | MaterialSpec) -> bpy.types.Material:
        """
        Returns the Blender material for ``material``, a material or the name of a
        registered one (see :mod:`porescene.material`).

        The material is built the first time its name is asked for; later calls
        return that same material.
        """
        spec = lookup(material)
        mat = bpy.data.materials.get(spec.name)
        if mat is None:
            mat = spec.build()
        return mat

    def hide_axes(self) -> Self:
        """
        Hides axes from render scene."""
        col = bpy.data.collections.get("Axes")
        if col:
            col.hide_render = True
        return self

    def hide_cells(self) -> Self:
        """Hides the tessellation cells from render scene."""
        obj = bpy.data.objects.get("Cells")
        if obj:
            obj.hide_render = True
        return self

    def hide_clusters(self) -> Self:
        """
        Hides all spheres from render scene."""
        col = bpy.data.collections.get("Clusters")
        if col:
            col.hide_render = True
        return self

    def hide_cylinders(self) -> Self:
        """Hides all cylinders from render scene."""
        obj = bpy.data.objects.get("Cylinders")
        if obj:
            obj.hide_render = True
        return self

    def hide_solid(self) -> Self:
        """
        Hides the solid from render scene."""
        obj = bpy.data.objects.get("solid")
        if obj:
            obj.hide_render = True
        return self

    def hide_spheres(self) -> Self:
        """Hides all spheres from render scene."""
        obj = bpy.data.objects.get("Spheres")
        if obj:
            obj.hide_render = True
        return self

    def hide_void(self) -> Self:
        """
        Hides the void from render scene."""
        obj = bpy.data.objects.get("void")
        if obj:
            obj.hide_render = True
        return self

    def remove_axes(self) -> Self:
        """
        Removes the axes from the scene.
        """
        col = bpy.data.collections.get("Axes")
        if col:
            obs = [o for o in col.objects if o.users == 1]
            while obs:
                bpy.data.objects.remove(obs.pop())
            bpy.data.collections.remove(col)
        self.has_axes = False
        return self

    def remove_defaults(self) -> Self:
        """Deletes the default cube and light of the blender scene."""
        names = ["Cube", "Light"]
        for name in names:
            obj = bpy.data.objects.get(name)
            if obj:
                bpy.data.objects.remove(obj)
        return self

    def remove_void(self, names: tuple[str, ...] = ("void")) -> Self:
        """
        Removes any void from the scene.
        """
        for name in names:
            obj = bpy.data.objects.get(name)
            if obj:
                bpy.data.objects.remove(obj)
            obj = bpy.data.meshes.get(name)
            if obj:
                bpy.data.meshes.remove(obj)
        return self

    def remove_solid(self) -> Self:
        """
        Removes any solid from the scene.
        """
        obj = bpy.data.objects.get("solid")
        if obj:
            bpy.data.objects.remove(obj)
        obj = bpy.data.meshes.get("solid")
        if obj:
            bpy.data.meshes.remove(obj)
        return self

    def render(self, pth_render: Path, trim: bool = True) -> Path:
        """
        Renders the current scene to an image file.

        The render uses Blender's *Cycles* engine at the width and height taken from
        :attr:`config_image`, with the device, quality and color settings taken from
        :attr:`config_render`, and writes the result to ``pth_render``.

        Parameters
        ----------
        pth_render : Path
            Output path for the rendered image. Blender appends the file-format
            extension when the path has none.
        trim : bool, optional
            If true, the saved image is cropped to its content, removing the surrounding
            empty margins, by default True.

        Returns
        -------
        Path
            The output path the render was written to (``pth_render``).
        """
        bpy.context.scene.render.resolution_x = self.config_image.width
        bpy.context.scene.render.resolution_y = self.config_image.height
        bpy.context.scene.render.filepath = str(pth_render)
        self._apply_config_render()

        with _get_spinner(f"[green]Rendering: {pth_render.name}") as p:
            p.add_task("render", total=None)
            with suppress_stdout():
                bpy.ops.render.render(write_still=True)
        if trim:
            image.img_trim(pth_render)

        return pth_render

    def _apply_config_render(self) -> None:
        """
        Hands the settings of :attr:`config_render` to Cycles.

        The device is only set up again when the requested one changes, as looking
        for devices takes a moment and every render of an animation passes through
        here.
        """
        cfg = self.config_render
        cycles = bpy.context.scene.cycles

        if self._device is None or self._device[0] is not cfg.device:
            self._device = (cfg.device, self._setup_device(cfg.device))

        cycles.samples = cfg.samples
        cycles.use_adaptive_sampling = cfg.noise_threshold is not None
        if cfg.noise_threshold is not None:
            cycles.adaptive_threshold = cfg.noise_threshold
        cycles.adaptive_min_samples = cfg.samples_min
        cycles.use_denoising = cfg.enable_denoising
        cycles.denoising_use_gpu = self._device[1] != "CPU"
        cycles.seed = cfg.seed
        cycles.transmission_bounces = cfg.bounces_transmission
        cycles.transparent_max_bounces = cfg.bounces_transparent

        view = bpy.context.scene.view_settings
        view.view_transform = cfg.view_transform
        view.look = "None"
        view.exposure = cfg.exposure
        view.gamma = 1.0

    def _setup_device(self, device: RenderDevice) -> str:
        """
        Points Cycles at ``device`` and enables every GPU of the chosen backend.

        Returns the backend that is used, or ``"CPU"``. See
        :class:`~porescene.utility.RenderDevice` for how ``AUTO`` picks one.

        Raises
        ------
        RuntimeError
            If ``device`` names a GPU backend that has no device on this machine.
        """
        scene = bpy.context.scene
        if device is RenderDevice.CPU:
            scene.cycles.device = "CPU"
            return "CPU"

        prefs = bpy.context.preferences.addons["cycles"].preferences
        if device is RenderDevice.AUTO:
            backends = self._BACKENDS_GPU
        else:
            backends = (device.value,)

        for backend in backends:
            # a backend missing from this build of Blender, such as Metal on Windows,
            # has no devices, while one Cycles doesn't know at all raises
            try:
                with suppress_stdout():
                    devices = prefs.get_devices_for_type(backend)
            except ValueError:
                continue
            if not any(d.type == backend for d in devices):
                continue

            prefs.compute_device_type = backend
            for d in prefs.devices:
                d.use = d.type == backend
            scene.cycles.device = "GPU"
            return backend

        if device is not RenderDevice.AUTO:
            raise RuntimeError(
                f"Cycles found no {device.value} device on this machine. Set "
                f"config_render.device to AUTO to use whatever is available."
            )

        warnings.warn(
            "Cycles found no GPU on this machine, so the scene is rendered on the "
            "CPU, which is considerably slower. Lower config_render.samples or the "
            "image size for quick renders.",
            stacklevel=4,
        )
        scene.cycles.device = "CPU"
        return "CPU"

    def rotate_azimuth(self, ang_rot: float) -> Self:
        """
        Rotates the camera and all lights around the scene's vertical (Z)
        axis by the given azimuth angle ``ang_rot`` (in degrees), orbiting
        them around the scene's center while keeping the camera aimed there.

        The axes are literal rulers built along fixed edges of the
        (stationary) bounding box, so they can't simply follow the camera's
        continuous rotation without drifting off the box they are meant to
        measure. The x and y rulers each stay on whichever of their two
        parallel edges currently faces the camera -- the x ruler flips
        between the front/back edge, the y ruler between the left/right
        edge -- by mirroring to that edge and turning their ticks and
        labels 180 degrees, so ticks keep pointing outward and label text
        stays legible, rather than rotating the whole ruler (which would
        swap their x/y labeling, see the fixed bug this replaced). The
        main ruler bar itself is left unrotated since it's symmetric along
        its own length. The z ruler stands on the box corner bounding the
        view on the left, at the end of the x or y ruler there, and turns
        its ticks and labels in 90-degree steps so they face the camera.
        It is placed from the box's actual corners rather than orbited
        around the scene's center, which would carry it off a box that
        isn't square in the xy plane.
        """
        self._orbit(bpy.data.objects["Camera"], math.radians(ang_rot))

        for obj in bpy.data.collections["Lights"].objects:
            rx, ry, rz = obj.rotation_euler
            obj.rotation_euler = (rx, ry, rz + math.radians(ang_rot))

        ang_before = self._ang_azimuth
        self._ang_azimuth += ang_rot
        if self.has_axes:
            self._move_axes(ang_before, self._ang_azimuth)

        return self

    def save(self, pth: Path) -> Self:
        """
        Saves the current scene as BLEND file.
        """
        with _get_spinner(f"Saving scene: {str(pth.name)}") as p:
            p.add_task("save", total=None)
            bpy.ops.wm.save_as_mainfile(filepath=str(pth))
        return self

    def load(self, pth: Path) -> Self:
        """
        Loads the current scene from BLEND file.
        """
        with _get_spinner(f"Loading scene: {str(pth.name)}") as p:
            p.add_task("load", total=None)
            bpy.ops.wm.open_mainfile(filepath=str(pth))
        return self

    def show_axes(self) -> Self:
        """
        Hides axes from render scene."""
        col = bpy.data.collections.get("Axes")
        if col:
            col.hide_render = False
        return self

    def show_cells(self) -> Self:
        """Shows the tessellation cells in the render scene."""
        obj = bpy.data.objects.get("Cells")
        if obj:
            obj.hide_render = False
        return self

    def show_clusters(self) -> Self:
        """
        Hides all spheres from render scene."""
        col = bpy.data.collections.get("Clusters")
        if col:
            col.hide_render = False
        return self

    def show_cylinders(self) -> Self:
        """Shows all cylinders in the render scene."""
        obj = bpy.data.objects.get("Cylinders")
        if obj:
            obj.hide_render = False
        return self

    def show_solid(self) -> Self:
        """
        Hides the solid from render scene."""
        obj = bpy.data.objects.get("solid")
        if obj:
            obj.hide_render = False
        return self

    def show_spheres(self) -> Self:
        """Shows all spheres in the render scene."""
        obj = bpy.data.objects.get("Spheres")
        if obj:
            obj.hide_render = False
        return self

    def show_void(self) -> Self:
        """
        Hides the void from render scene."""
        obj = bpy.data.objects.get("void")
        if obj:
            obj.hide_render = False
        return self

    @property
    def aspect(self) -> tuple[float, float, float]:
        """
        Relative proportions of the domain along x, y and z, each normalized by the
        largest of the three so the longest axis is ``1``. Set by :meth:`from_json`
        from the given physical ``dims``.
        """
        return self._aspect

    @aspect.setter
    def aspect(self, arg: tuple[float, float, float]):
        self._aspect = arg

    @property
    def config_axes(self) -> AxesConfiguration:
        """
        Configuration controlling how :meth:`create_axes` draws axis lines, ticks and
        labels.
        """
        return self._config_axes

    @config_axes.setter
    def config_axes(self, arg: AxesConfiguration):
        self._config_axes = arg

    @property
    def config_image(self) -> ImageConfiguration:
        """
        Configuration controlling how rendered images are post-processed.
        """
        return self._config_image

    @config_image.setter
    def config_image(self, arg: ImageConfiguration):
        self._config_image = arg

    @property
    def config_render(self) -> RenderConfiguration:
        """
        Configuration controlling how Cycles renders the scene: the device, the number
        of samples, denoising and the color management. Read on every :meth:`render`,
        so changes take effect with the next image.
        """
        return self._config_render

    @config_render.setter
    def config_render(self, arg: RenderConfiguration):
        self._config_render = arg

    @property
    def config_scene(self) -> SceneConfiguration:
        """
        Configuration controlling general scene appearance, such as which items are
        rendered and their styling.
        """
        return self._config_scene

    @config_scene.setter
    def config_scene(self, arg: SceneConfiguration):
        self._config_scene = arg

    @property
    def has_axes(self) -> bool:
        """
        Whether axes with ticks and labels have been added to the scene, via
        :meth:`create_axes`.
        """
        return self._has_axes

    @has_axes.setter
    def has_axes(self, arg: bool):
        self._has_axes = arg

    @property
    def has_cells(self) -> bool:
        """
        Whether the cells of a tessellation have been added to the scene, via
        :meth:`create_cells`.
        """
        return self._has_cells

    @has_cells.setter
    def has_cells(self, arg: bool):
        self._has_cells = arg

    @property
    def has_clusters(self) -> bool:
        """
        Whether pore clusters have been added to the scene, via
        :meth:`create_clusters`.
        """
        return self._has_clusters

    @has_clusters.setter
    def has_clusters(self, arg: bool):
        self._has_clusters = arg

    @property
    def has_cylinders(self) -> bool:
        """
        Whether throat cylinders have been added to the scene, via
        :meth:`create_cylinders`.
        """
        return self._has_cylinders

    @has_cylinders.setter
    def has_cylinders(self, arg: bool):
        self._has_cylinders = arg

    @property
    def has_lights(self) -> bool:
        """
        Whether lights have been added to the scene, via :meth:`create_lights`.
        """
        return self._has_lights

    @has_lights.setter
    def has_lights(self, arg: bool):
        self._has_lights = arg

    @property
    def has_solid(self) -> bool:
        """
        Whether the solid object has been added to the scene, via
        :meth:`create_solid`.
        """
        return self._has_solid

    @has_solid.setter
    def has_solid(self, arg: bool):
        self._has_solid = arg

    @property
    def has_spheres(self) -> bool:
        """
        Whether pore spheres have been added to the scene, via
        :meth:`create_spheres`.
        """
        return self._has_spheres

    @has_spheres.setter
    def has_spheres(self, arg: bool):
        self._has_spheres = arg

    @property
    def has_void(self) -> bool:
        """
        Whether the void-space object has been added to the scene, via
        :meth:`create_void`.
        """
        return self._has_void

    @has_void.setter
    def has_void(self, arg: bool):
        self._has_void = arg


# maps file suffixes to their Blender import operator
_IMPORTERS: dict[str, tuple[str, str]] = {
    ".obj": ("wm", "obj_import"),
    ".ply": ("wm", "ply_import"),
    ".stl": ("wm", "stl_import"),
    ".abc": ("wm", "alembic_import"),
    ".usd": ("wm", "usd_import"),
    ".usda": ("wm", "usd_import"),
    ".usdc": ("wm", "usd_import"),
    ".fbx": ("import_scene", "fbx"),
    ".glb": ("import_scene", "gltf"),
    ".gltf": ("import_scene", "gltf"),
}


def _import_object(pth: Path) -> None:
    """
    Imports a 3D object file using the Blender importer matching its file extension.
    """
    suffix = pth.suffix.lower()
    try:
        namespace, operator = _IMPORTERS[suffix]
    except KeyError:
        raise ValueError(
            f"Unsupported file format {suffix!r} for {pth.name}. "
            f"Supported formats: {', '.join(sorted(_IMPORTERS))}"
        ) from None

    import_op = getattr(getattr(bpy.ops, namespace), operator)
    with suppress_stdout():
        import_op(filepath=str(pth))


# [rad] facets of a cell's hull that meet at a smaller angle are merged into one
_ANGLE_COPLANAR = math.radians(1)

# share of its color a cell keeps right at its edges, see _round_cell_edges
_SHADE_CELL_EDGE = 0.6


def _convex_cell(pos: np.ndarray) -> bmesh.types.BMesh:
    """
    Builds the convex cell around the corners at ``pos``.

    Each facet is split into a fan of triangles around its center, and each corner of a
    triangle carries its distance to the edge of the facet the triangle lies on, as the
    float layer ``"cell_edge"``. Interpolated across the triangle, it gives every point
    of the triangle its distance to that edge, which :func:`_round_cell_edges` rounds
    off the edges by.
    """
    bm = bmesh.new()
    for p in pos:
        bm.verts.new(p)
    res = bmesh.ops.convex_hull(bm, input=bm.verts[:])

    # corners that lie on a facet or an edge of the hull rather than at one of its
    # corners are left over as loose vertices
    loose = {
        g
        for g in res["geom_interior"] + res["geom_unused"]
        if isinstance(g, bmesh.types.BMVert)
    }
    bmesh.ops.delete(bm, geom=list(loose), context="VERTS")

    # the hull comes in triangles; those in one plane are merged back into the facet
    # they split, as the edges between them would be rounded off as well
    bmesh.ops.dissolve_limit(
        bm, angle_limit=_ANGLE_COPLANAR, verts=bm.verts[:], edges=bm.edges[:]
    )

    # the distance to a straight line changes linearly along a triangle, so its values
    # at the corners describe it exactly: zero on the edge, and the distance of the
    # center to the edge at the center
    centers = set(bmesh.ops.poke(bm, faces=bm.faces[:])["verts"])
    layer = bm.loops.layers.float.new("cell_edge")
    for f in bm.faces:
        center, a, b = sorted(f.verts, key=lambda v: v not in centers)
        point, _ = intersect_point_line(center.co, a.co, b.co)
        for loop in f.loops:
            loop[layer] = (center.co - point).length if loop.vert is center else 0

    return bm


def _round_cell_edges(mat: bpy.types.Material, width: float) -> None:
    """
    Rounds off the edges of the cells over ``width`` in the shading of ``mat``, and
    darkens them towards the edge.

    Both follow the profile of a parabola across the rounded strip, read off the
    ``"cell_edge"`` attribute that :func:`_convex_cell` puts on the corners: its height
    bends the normal like a rounded edge would, and it scales the color of the cells
    down to :data:`_SHADE_CELL_EDGE` at the very edge. A material without a Principled
    BSDF is left as it is.
    """
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    n_pr = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)
    if n_pr is None:
        return

    n_dist = nodes.new("ShaderNodeAttribute")
    n_dist.attribute_type = "GEOMETRY"
    n_dist.attribute_name = "cell_edge"

    # 1 - (1 - x)^2 for the distance x from the edge, relative to the width: rises from
    # 0 at the edge and levels off at 1 where the facet turns flat
    n_rel = nodes.new("ShaderNodeMapRange")
    n_rel.clamp = True
    n_rel.inputs["From Max"].default_value = width
    n_rel.inputs["To Min"].default_value = 1
    n_rel.inputs["To Max"].default_value = 0
    n_sq = nodes.new("ShaderNodeMath")
    n_sq.operation = "POWER"
    n_sq.inputs[1].default_value = 2
    n_profile = nodes.new("ShaderNodeMath")
    n_profile.operation = "SUBTRACT"
    n_profile.inputs[0].default_value = 1
    links.new(n_dist.outputs["Fac"], n_rel.inputs["Value"])
    links.new(n_rel.outputs["Result"], n_sq.inputs[0])
    links.new(n_sq.outputs["Value"], n_profile.inputs[1])

    n_height = nodes.new("ShaderNodeMath")
    n_height.operation = "MULTIPLY"
    n_height.inputs[1].default_value = width
    n_bump = nodes.new("ShaderNodeBump")
    # the height is given in scene units already, which the default distance would
    # scale down to next to nothing
    n_bump.inputs["Distance"].default_value = 1
    links.new(n_profile.outputs["Value"], n_height.inputs[0])
    links.new(n_height.outputs["Value"], n_bump.inputs["Height"])

    # a normal the material bends already, e.g. by a bevel, is bent further
    for link in list(n_pr.inputs["Normal"].links):
        links.new(link.from_socket, n_bump.inputs["Normal"])
    links.new(n_bump.outputs["Normal"], n_pr.inputs["Normal"])

    n_shade = nodes.new("ShaderNodeMapRange")
    n_shade.inputs["To Min"].default_value = _SHADE_CELL_EDGE
    links.new(n_profile.outputs["Value"], n_shade.inputs["Value"])

    # the colors of the cells pass through the shading on their way into the material
    for n_attr in [n for n in nodes if n.type == "ATTRIBUTE"]:
        if n_attr.attribute_name != "cell_color":
            continue
        for link in list(n_attr.outputs["Color"].links):
            n_mix = nodes.new("ShaderNodeMixRGB")
            n_mix.blend_type = "MULTIPLY"
            n_mix.inputs["Factor"].default_value = 1
            links.new(n_attr.outputs["Color"], n_mix.inputs["Color1"])
            links.new(n_shade.outputs["Result"], n_mix.inputs["Color2"])
            links.new(n_mix.outputs["Color"], link.to_socket)
