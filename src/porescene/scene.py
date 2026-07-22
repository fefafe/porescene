# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Felix Faber /
# Otto von Guericke University Magdeburg, Thermal Process Engineering

import json
import math
import random
from pathlib import Path
from typing import NamedTuple, Self, cast

import bpy
import numpy as np
from mathutils import Matrix, Vector
from rich import progress

from porescene import image
from porescene.color import Color
from porescene.config import AxesConfiguration, ImageConfiguration, SceneConfiguration
from porescene.utility import _get_spinner, suppress_stdout

import bmesh  # isort:skip


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

    def __init__(self, extent: np.ndarray) -> None:
        """
        Creates an empty :class:`Scene`, wiping Blender's default scene contents and
        setting up a camera, lights and Cycles render settings. Use :meth:`from_json`
        to create a scene sized and configured from a PoreScene JSON file instead.
        """
        self.config_axes = AxesConfiguration(extent)
        self.config_image = ImageConfiguration()
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

        # cycles configuration
        bpy.context.scene.render.engine = "CYCLES"

        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"  # falls back to CUDA if no RTX-capable device
        with suppress_stdout():
            prefs.get_devices()
        for device in prefs.devices:
            device.use = device.type in {"OPTIX", "CUDA"}

        bpy.context.scene.cycles.device = "GPU"

        bpy.context.scene.render.resolution_percentage = 100
        bpy.context.scene.render.film_transparent = True
        bpy.context.scene.render.use_persistent_data = True
        bpy.context.scene.render.image_settings.color_mode = "RGBA"
        bpy.context.scene.render.image_settings.color_depth = "16"

        bpy.context.scene.cycles.samples = 1024
        bpy.context.scene.cycles.use_adaptive_sampling = True
        bpy.context.scene.cycles.adaptive_threshold = 0.01
        bpy.context.scene.cycles.adaptive_min_samples = 32

        bpy.context.scene.cycles.use_denoising = True
        bpy.context.scene.cycles.denoiser = "OPENIMAGEDENOISE"

        bpy.context.scene.cycles.transmission_bounces = 12
        bpy.context.scene.cycles.transparent_max_bounces = 64

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
            Path to the PoreScene JSON configuration file. Its optional ``"axes"``
            and ``"image"`` sections populate :attr:`config_axes` and
            :attr:`config_image`, respectively.

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

        return ins

    def apply_colors(
        self,
        name_mesh: str,
        colors: list[Color],
        frame: int = 0,
    ) -> Self:
        """
        Sets the colors for all items in a collection for given frame.
        """
        color_array = np.array([c.lnrgba for c in colors], dtype=np.float32)

        # Single meshes
        mesh = bpy.data.meshes.get(name_mesh)
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
        d = cfg.distance
        sbb = self.size_bounding_box
        sx, sy, sz = self.shift
        ax, ay, az = self.aspect

        mat_axis = self.get_material("AXES", "axes")
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
            for enabled, spec in zip(cfg.enable_ticks, specs):
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

            label = str(round(value, spec.precision)).rstrip("0").rstrip(".")
            label_loc = list(loc)
            label_loc[spec.label_dim] += cfg.distance + cfg.tick_length
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
        self._ang_azimuth = math.degrees(math.atan2(y - center, x - center))
        return self

    def create_cells(
        self,
        pos: np.ndarray,
        vtx_cv: list[np.ndarray],
        p_selection: np.ndarray | None = None,
        merge_dist: float = 0,
        style="CELL_DEFAULT",
    ) -> Self:
        col = bpy.data.collections.get("Cells")
        mat = self.get_material(style, "default")
        if p_selection is None:
            p_selection = np.array(range(len(vtx_cv)))
        if not col:
            col = bpy.data.collections.new("Cells")
            bpy.context.scene.collection.children.link(col)
        for p in progress.track(p_selection, description="Creating cells"):
            # select current cell vertex list
            verts = pos[vtx_cv[p], :] * self.scale + self.shift
            # create point cloud mesh and object of cell vertices
            mesh = bpy.data.meshes.new(f"cell {p}")
            mesh.from_pydata(verts, [], [])
            obj = bpy.data.objects.new(f"cell {p}", mesh)
            # compute convex hull from point cloud
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bmesh.ops.convex_hull(bm, input=bm.verts)
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge_dist)
            bm.to_mesh(mesh)
            bm.free()
            #
            # vtx_boundary = []
            # for ind, vtx in enumerate(obj.data.vertices):
            #     if abs(vtx.co.x - (10 - self.shift[0])) < 1e-2:
            #         vtx_boundary.append(ind)
            #     if abs(vtx.co.y - (10 - self.shift[1])) < 1e-2:
            #         vtx_boundary.append(ind)
            #     if abs(vtx.co.z - (10 - self.shift[2])) < 1e-2:
            #         vtx_boundary.append(ind)
            # grp = obj.vertex_groups.new(name="Boundary")
            # grp.add(vtx_boundary, 1.0, 'REPLACE')
            # mod = obj.modifiers.new(name=f"Decimate {p}", type='DECIMATE')
            # mod.decimate_type = 'UNSUBDIV'
            # mod.use_dissolve_boundaries = True
            # mod = obj.modifiers.new(name=f"Bevel {p}", type='BEVEL')
            # mod.offset_type = 'WIDTH'
            # mod.width = 0.006
            # mod.segments = 16
            # mod.use_clamp_overlap = False
            # mod.vmesh_method = 'CUTOFF'
            # mod.limit_method = 'ANGLE'
            # mod.angle_limit = math.radians(50)
            # mod.vertex_group = "Boundary"
            # append object to collection
            col.objects.link(obj)
            # apply material
            obj.data.materials.append(mat.copy())
            obj.data.materials[0].name = obj.name
        return self

    def create_clusters(self, pth: Path, style: str = "CLUSTER_DEFAULT") -> Self:
        """
        Adds pore clusters to the scene.
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

        mat = self.get_material(style, "clusters")
        if not any(n.type == "ATTRIBUTE" for n in mat.node_tree.nodes):
            self._apply_object_color(mat)

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
        style: str = "STRUCTURE_DEFAULT",
    ) -> Self:
        """
        Places a cylinder for each throat in the scene.
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

        obj_template = self._get_cylinder_template(style)
        mod = obj.modifiers.new("CylinderInstances", type="NODES")
        mod.node_group = self._get_node_group(obj_template)

        self.has_cylinders = True
        return self

    def _get_cylinder_template(self, style: str) -> bpy.types.Object:
        """
        Returns a unit cylinder (radius=1, depth=1).
        """
        name = f"Cylinder_{style}"
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

        mat = self.get_material(style, "default").copy()
        obj_tmpl.data.materials.append(mat)
        self._apply_instance_color(mat)

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

    def _apply_instance_color(self, mat: bpy.types.Material) -> None:
        """
        Connects material base color to instance attribute.
        """
        tree = mat.node_tree
        principled = next(n for n in tree.nodes if n.type == "BSDF_PRINCIPLED")
        attr_node = tree.nodes.new("ShaderNodeAttribute")
        attr_node.attribute_type = "INSTANCER"
        attr_node.attribute_name = "color"
        tree.links.new(attr_node.outputs["Color"], principled.inputs["Base Color"])

    def _apply_object_color(self, mat: bpy.types.Material) -> None:
        """
        Connects material base color to the per-object "color" mesh attribute.

        Object counterpart of :meth:`_apply_instance_color`: used for real
        objects (e.g. clusters) that carry their own "color" attribute rather
        than being instanced through geometry nodes.
        """
        tree = mat.node_tree
        principled = next(n for n in tree.nodes if n.type == "BSDF_PRINCIPLED")
        attr_node = tree.nodes.new("ShaderNodeAttribute")
        attr_node.attribute_type = "GEOMETRY"
        attr_node.attribute_name = "cluster_color"
        tree.links.new(attr_node.outputs["Color"], principled.inputs["Base Color"])

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

    def create_lights(self) -> Self:
        """
        Adds all nessecary lightnings to the scene.
        """
        col = bpy.data.collections.get("Lights")
        if not col:
            col = bpy.data.collections.new("Lights")
            bpy.context.scene.collection.children.link(col)

        def add_sun(name, energy, angle_deg, rot_deg):
            light_data = bpy.data.lights.new(name=name, type="SUN")
            light_data.energy = energy
            light_data.angle = math.radians(angle_deg)
            obj = bpy.data.objects.new(name, light_data)
            obj.rotation_euler = tuple(math.radians(a) for a in rot_deg)
            col.objects.link(obj)
            return obj

        add_sun("Key_Light", energy=4.0, angle_deg=15, rot_deg=(-55, 0, -70))
        add_sun("Fill_Light", energy=2.5, angle_deg=30, rot_deg=(-50, 0, 110))
        add_sun("Rim_Light", energy=2.0, angle_deg=10, rot_deg=(140, 0, 20))

        world = bpy.context.scene.world
        if world is None:
            world = bpy.data.worlds.new("World")
            bpy.context.scene.world = world
        world.use_nodes = True
        bg = world.node_tree.nodes.get("Background")
        if bg:
            bg.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
            bg.inputs["Strength"].default_value = 0.15

        self.has_lights = True
        return self

    def _orbit(self, obj, angle: float) -> None:
        """
        Rotates an object's location and yaw around the scene's vertical
        (Z) axis, through the scene's center, by ``angle`` radians.
        """
        center = self.size_bounding_box / 2
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        x, y, z = obj.location
        x, y = x - center, y - center
        obj.location = (
            x * cos_a - y * sin_a + center,
            x * sin_a + y * cos_a + center,
            z,
        )
        rx, ry, rz = obj.rotation_euler
        obj.rotation_euler = (rx, ry, rz + angle)

    def create_solid(self, pth: Path, style: str = "SOLID_DEFAULT", name: str = "solid"):
        """
        Adds the solid into the scene.
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
        mesh.materials.clear()
        mesh.materials.append(self.get_material(style, "solid"))
        self.has_solid = True

        return self

    def create_spheres(
        self,
        pos: np.ndarray,
        r: np.ndarray,
        name: str = "Spheres",
        style: str = "STRUCTURE_DEFAULT",
    ) -> Self:
        """
        Places a sphere for each pore in the scene.
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

        template = self._get_sphere_template(style)

        mod = obj.modifiers.new("SphereInstances", type="NODES")
        mod.node_group = self._get_node_group(template)

        self.has_spheres = True
        return self

    def _get_sphere_template(self, style: str) -> bpy.types.Object:
        """
        Returns a unit sphere (radius=1)
        """
        name = f"Sphere_{style}"
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

        mat = self.get_material(style, "default").copy()
        obj_tmpl.data.materials.append(mat)
        self._apply_instance_color(mat)

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

    def create_void(self, pth: Path, style: str = "ICE", name: str = "void") -> Self:
        """
        Adds a 3D object of the void space to the scene.
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
        mesh.materials.clear()
        mesh.materials.append(self.get_material(style, name))
        self.has_void = True
        return self

    def get_material(self, style: str, name: str):
        """
        Creates a new material instance for the given style.
        """
        mat = bpy.data.materials.get(name)
        if mat:
            return mat
        else:
            mat = bpy.data.materials.new(name)
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            output = nodes.get("Material Output")
            links = mat.node_tree.links
            n_pr = nodes.get("Principled BSDF")
            n_pr.subsurface_method = "BURLEY"
            links.new(n_pr.outputs["BSDF"], output.inputs["Surface"])

            if style in ["STRUCTURE_DEFAULT", "CLUSTER_DEFAULT"]:
                n_pr.inputs["Base Color"].default_value = Color("#58646E").lnrgba
                n_pr.inputs["Metallic"].default_value = 0.4
                n_pr.inputs["Roughness"].default_value = 0.5
                n_pr.inputs["Subsurface Weight"].default_value = 0.1
                n_pr.inputs["Specular IOR Level"].default_value = 0.1
                n_pr.inputs["Sheen Weight"].default_value = 0.1
                n_pr.inputs["Sheen Roughness"].default_value = 0
            elif style == "VOID_FROZEN":
                # links.clear()
                # node_mix = nodes.new("ShaderNodeMixShader")
                # node_mix.inputs[0].default_value = 0.5
                # links.new(node_mix.outputs[0], output.inputs[0])
                # node_trans = nodes.new("ShaderNodeBsdfTransparent")
                # links.new(node_trans.outputs[0], node_mix.inputs[1])
                # links.new(node_princ.outputs[0], node_mix.inputs[2])
                n_pr.inputs["Base Color"].default_value = Color("#0E86C7").lnrgba
                n_pr.inputs["Metallic"].default_value = 0.4
                n_pr.inputs["Roughness"].default_value = 0.5
                n_pr.inputs["Specular IOR Level"].default_value = 0.1
                n_pr.inputs["Sheen Weight"].default_value = 0.1
                n_pr.inputs["Sheen Roughness"].default_value = 0
            elif style == "VOID_DRY":
                links.clear()
                node_mix = nodes.new("ShaderNodeMixShader")
                node_mix.inputs["Fac"].default_value = 0.25
                links.new(node_mix.outputs[0], output.inputs["Surface"])
                node_trans = nodes.new("ShaderNodeBsdfTransparent")
                links.new(node_trans.outputs["BSDF"], node_mix.inputs[1])
                links.new(n_pr.outputs["BSDF"], node_mix.inputs[2])
                n_pr.inputs["Base Color"].default_value = Color("#E5BE0F").lnrgba
                n_pr.inputs["Metallic"].default_value = 0.4
                n_pr.inputs["Roughness"].default_value = 0.5
                n_pr.inputs["Specular IOR Level"].default_value = 0.1
                n_pr.inputs["Sheen Weight"].default_value = 0.1
                n_pr.inputs["Sheen Roughness"].default_value = 0
            elif style == "CELL_DEFAULT":
                n_bevel = nodes.new("ShaderNodeBevel")
                links.new(n_bevel.outputs["Normal"], n_pr.inputs["Normal"])
                n_bevel.inputs["Radius"].default_value = 0.025 * 2
                n_pr.inputs["Base Color"].default_value = Color("#947C5E").lnrgba
                n_pr.inputs["Metallic"].default_value = 0.2
                n_pr.inputs["Roughness"].default_value = 0.8
                n_pr.inputs["Alpha"].default_value = 0.8
            elif style == "CELL_TRANSPARENT":
                links.clear()
                node_mix = nodes.new("ShaderNodeMixShader")
                node_mix.inputs["Fac"].default_value = 0.5
                links.new(node_mix.outputs[0], output.inputs["Surface"])
                node_trans = nodes.new("ShaderNodeBsdfTransparent")
                links.new(node_trans.outputs["BSDF"], node_mix.inputs[1])
                links.new(n_pr.outputs["BSDF"], node_mix.inputs[2])
                n_bevel = nodes.new("ShaderNodeBevel")
                links.new(n_bevel.outputs["Normal"], n_pr.inputs["Normal"])
                n_bevel.inputs["Radius"].default_value = 0.025 * 5
                n_pr.inputs["Base Color"].default_value = Color("#947C5E").lnrgba
                n_pr.inputs["Metallic"].default_value = 0.2
                n_pr.inputs["Roughness"].default_value = 0.8
                n_pr.inputs["Alpha"].default_value = 0.8
            elif style == "SOLID_DEFAULT":
                # bevel node
                n_bevel = nodes.new("ShaderNodeBevel")
                n_bevel.inputs["Radius"].default_value = 0.02

                # ambient occlusion node
                n_ao = nodes.new("ShaderNodeAmbientOcclusion")
                n_ao.only_local = True
                n_ao.inputs["Distance"].default_value = 0.5

                # AO mixing node
                n_ao_mix = nodes.new("ShaderNodeMixRGB")
                n_ao_mix.blend_type = "MULTIPLY"
                n_ao_mix.inputs["Factor"].default_value = 0.3
                n_ao_mix.inputs["Color1"].default_value = Color("#C6A87A").lnrgba

                # principal node
                n_pr.inputs["Metallic"].default_value = 0
                n_pr.inputs["Roughness"].default_value = 0.5
                n_pr.inputs["Specular IOR Level"].default_value = 0.5
                n_pr.inputs["Sheen Weight"].default_value = 0.1
                n_pr.inputs["Sheen Roughness"].default_value = 0.3
                n_pr.inputs["Subsurface Weight"].default_value = 0.12
                n_pr.inputs["Subsurface Scale"].default_value = 0.15

                links.new(n_bevel.outputs["Normal"], n_pr.inputs["Normal"])
                links.new(n_ao.outputs["Color"], n_ao_mix.inputs["Color2"])
                links.new(n_ao_mix.outputs["Color"], n_pr.inputs["Base Color"])

            elif style == "SOLID_TRANSPARENT":
                links.clear()
                node_mix = nodes.new("ShaderNodeMixShader")
                node_mix.inputs["Fac"].default_value = 0.25
                links.new(node_mix.outputs[0], output.inputs["Surface"])
                node_trans = nodes.new("ShaderNodeBsdfTransparent")
                links.new(node_trans.outputs["BSDF"], node_mix.inputs[1])
                links.new(n_pr.outputs["BSDF"], node_mix.inputs[2])
                n_pr.inputs["Base Color"].default_value = Color("#947C5E").lnrgba
                n_pr.inputs["Metallic"].default_value = 0
                n_pr.inputs["Roughness"].default_value = 1
                n_pr.inputs["Specular IOR Level"].default_value = 0.5
            elif style == "BACTERIA_GREEN":
                n_pr.inputs["Base Color"].default_value = Color("#3F901A").lnrgba
                n_pr.inputs["Metallic"].default_value = 0.2
                n_pr.inputs["Roughness"].default_value = 1
                n_pr.inputs["Specular IOR Level"].default_value = 0
            elif style.startswith("ICE"):
                if "ICE_TILED" == style:
                    color = random.choice(
                        ["#7891e3", "#92b2e8", "#95c5e8", "#b7d2e7", "#d6edff"]
                    )
                    n_pr.inputs["Base Color"].default_value = Color(color).lnrgba
                else:
                    n_pr.inputs["Base Color"].default_value = Color("#85A2E6").lnrgba
                n_pr.inputs["Metallic"].default_value = 0
                n_pr.inputs["Roughness"].default_value = 1
                n_pr.inputs["Subsurface Weight"].default_value = 0.1
                n_pr.inputs["Specular IOR Level"].default_value = 1
                n_pr.inputs["Sheen Weight"].default_value = 0
                n_pr.inputs["Sheen Roughness"].default_value = 1
            elif style == "AXES":
                n_pr.inputs["Base Color"].default_value = Color("#0001").lnrgba
                n_pr.inputs["Metallic"].default_value = 0
                n_pr.inputs["Roughness"].default_value = 1
                n_pr.inputs["Specular IOR Level"].default_value = 0

            return mat

    def hide_axes(self) -> Self:
        """
        Hides axes from render scene."""
        col = bpy.data.collections.get("Axes")
        if col:
            col.hide_render = True
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
        return self

    def remove_defaults(self) -> Self:
        """Deletes the default cube and light of the blender scene."""
        names = ["Cube", "Light"]
        for name in names:
            obj = bpy.data.objects.get(name)
            if obj:
                bpy.data.objects.remove(obj)
        return self

    def remove_void(self, names: list[str] = ["void"]) -> Self:
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
        the scene's image configuration (``config_image``) and writes the result to
        ``pth_render``.

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

        with _get_spinner(f"[green]Rendering: {pth_render.name}") as p:
            p.add_task("render", total=None)
            with suppress_stdout():
                bpy.ops.render.render(write_still=True)
        if trim:
            image.img_trim(pth_render)

        return pth_render

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
        its own length. The z ruler sits at the corner shared by the
        current x and y edges, so it is snapped there in 90-degree steps
        the same way the whole assembly used to move.
        """
        self._orbit(bpy.data.objects["Camera"], math.radians(ang_rot))

        for obj in bpy.data.collections["Lights"].objects:
            rx, ry, rz = obj.rotation_euler
            obj.rotation_euler = (rx, ry, rz + math.radians(ang_rot))

        if self.has_axes:

            def _nearest_corner(deg: float) -> float:
                return math.floor((deg - 45) / 90 + 0.5) * 90 + 45

            def _side(deg: float, fn) -> bool:
                return fn(math.radians(deg)) >= 0

            ang_before = self._ang_azimuth
            corner_before = _nearest_corner(ang_before)
            self._ang_azimuth += ang_rot
            ang_after = self._ang_azimuth
            corner_after = _nearest_corner(ang_after)

            corner_delta = math.radians(corner_after - corner_before)
            flips = {
                "y": _side(ang_before, math.cos) != _side(ang_after, math.cos),
                "x": _side(ang_before, math.sin) != _side(ang_after, math.sin),
            }

            def _axis_of(name: str) -> str | None:
                for axis in ("x", "y", "z"):
                    if name == f"axis_{axis}" or name == f"axis label {axis}":
                        return axis
                    if name.startswith(f"{axis} "):
                        return axis
                return None

            if corner_delta or any(flips.values()):
                sbb = self.size_bounding_box

                for obj in bpy.data.collections["Axes"].objects:
                    axis = _axis_of(obj.name)
                    if axis is None:
                        continue

                    if axis == "z":
                        if corner_delta:
                            self._orbit(obj, corner_delta)
                        continue

                    if not flips[axis]:
                        continue

                    # record the object's own bounding-box center in world space
                    # before anything changes, to correct its position afterwards
                    # (see below)
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

        else:
            self._ang_azimuth += ang_rot

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
