import math
import random
from pathlib import Path
from typing import Self

import bmesh
import bpy
import numpy as np
from rich.progress import track

from porescene.color import Color
from porescene.config import AxesConfiguration, ImageConfiguration, SceneConfiguration


class Scene:

    def __init__(self) -> None:
        self.config_axes = AxesConfiguration()
        self.config_image = ImageConfiguration()
        self.config_scene = SceneConfiguration()
        self.size_bounding_box = 10
        self.n_segments = 48
        self.size = (10, 10, 10)
        self.shift = (0, 0, 0)
        self.scale = 1e5

        self.has_axes = False
        self.has_clusters = False
        self.has_cylinders = False
        self.has_lights = False
        self.has_solid = False
        self.has_spheres = False
        self.has_void = False

        bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[0].default_value = (
            1,
            1,
            1,
            1,
        )
        bpy.context.scene.render.engine = "CYCLES"
        bpy.context.preferences.addons["cycles"].preferences.compute_device_type = "CUDA"
        bpy.context.preferences.addons["cycles"].preferences.get_devices()
        bpy.context.scene.render.resolution_percentage = 100
        bpy.context.scene.render.film_transparent = True
        bpy.context.scene.render.use_persistent_data = True
        bpy.context.scene.render.image_settings.color_mode = "RGBA"
        bpy.context.scene.render.image_settings.color_depth = "8"
        bpy.context.scene.cycles.device = "GPU"
        bpy.context.scene.view_settings.look = "AgX - Medium High Contrast"
        # bpy.context.scene.cycles.transparent_max_bounces = 100
        # bpy.context.scene.cycles.transmission_bounces = 100

    def apply_colors(
        self,
        col_name: str,
        colors: list[Color],
        frame: int = 0,
    ) -> Self:
        """
        Sets the colors for all items in a collection for given frame.
        """
        col = bpy.data.collections.get(col_name)
        for [k, obj] in enumerate(
            track(col.objects, description=f"Coloring collection {col_name}")
        ):
            obj.data.materials[0].node_tree.nodes.get("Principled BSDF").inputs[
                0
            ].default_value = colors[k].lnrgba
        return self

    def create_axes(self) -> Self:
        """
        Adds axes with ticks and labels to the scene.
        """
        # axis material
        mat_axis = self.get_material("AXES", "axes")

        # axis font
        font = bpy.data.fonts.load(str(self.config_axes.font_family))

        # axis collection
        col = bpy.data.collections.new("Axes")

        # axis mesh
        mesh_axis = bpy.data.meshes.new("axis")
        mesh_axis.from_pydata(
            [
                (0, 0, 0),
                (self.config_axes.line_width, 0, 0),
                (self.config_axes.line_width, self.size_bounding_box, 0),
                (0, self.size_bounding_box, 0),
            ],
            [],
            [(0, 1, 2, 3)],
        )
        mesh_axis.update()

        # x axis object
        axis_x = bpy.data.objects.new("axis_x", mesh_axis)
        col.objects.link(axis_x)
        axis_x.location = (
            self.shift[0],
            self.size_bounding_box
            - self.shift[1]
            + self.config_axes.distance
            + self.config_axes.line_width,
            self.shift[2],
        )
        axis_x.rotation_euler = (math.radians(0), math.radians(0), math.radians(-90))
        axis_x.scale = (1, self.aspect[0], 1)

        # y axis object
        axis_y = bpy.data.objects.new("axis_y", mesh_axis)
        col.objects.link(axis_y)
        axis_y.location = (
            self.size_bounding_box - self.shift[0] + self.config_axes.distance,
            self.shift[1],
            self.shift[2],
        )
        axis_y.scale = (1, self.aspect[1], 1)

        # z axis object
        axis_z = bpy.data.objects.new("axis_z", mesh_axis)
        col.objects.link(axis_z)
        axis_z.location = (
            self.size_bounding_box - self.shift[0] + self.config_axes.distance,
            self.shift[1],
            self.shift[2],
        )
        axis_z.rotation_euler = (math.radians(90), math.radians(0), math.radians(0))
        axis_z.scale = (1, self.aspect[2], 1)

        # x axis label
        if self.config_axes.label_x:
            font_curve = bpy.data.curves.new(type="FONT", name="scale x")
            font_curve.body = self.config_axes.label_x
            font_curve.size = self.config_axes.font_size_labels
            font_curve.align_x = "CENTER"
            font_curve.align_y = "TOP"
            axis_label = bpy.data.objects.new(name="axis label x", object_data=font_curve)
            col.objects.link(axis_label)
            axis_label.data.font = font
            x = self.size_bounding_box / 2
            y = (
                self.size_bounding_box
                - self.shift[1]
                + self.config_axes.distance * 2
                + self.config_axes.line_width
            )
            z = self.shift[2]
            if self.config_axes.enable_ticks[0] and len(self.config_axes.ticks_x) > 0:
                y += self.config_axes.tick_length + self.config_axes.font_size_ticks
            axis_label.location = (x, y, z)
            axis_label.rotation_euler = (
                math.radians(0),
                math.radians(0),
                math.radians(180),
            )

        # y axis label
        if self.config_axes.label_y:
            font_curve = bpy.data.curves.new(type="FONT", name="scale y")
            font_curve.body = self.config_axes.label_y
            font_curve.size = self.config_axes.font_size_labels
            font_curve.align_x = "CENTER"
            font_curve.align_y = "TOP"
            axis_label = bpy.data.objects.new(name="axis label y", object_data=font_curve)
            col.objects.link(axis_label)
            axis_label.data.font = font
            x = (
                self.size_bounding_box
                - self.shift[0]
                + self.config_axes.distance * 2
                + self.config_axes.line_width
            )
            y = self.size_bounding_box / 2
            z = self.shift[2]
            if self.config_axes.enable_ticks[1] and len(self.config_axes.ticks_y) > 0:
                x += self.config_axes.tick_length + self.config_axes.font_size_ticks
            axis_label.location = (x, y, z)
            axis_label.rotation_euler = (
                math.radians(0),
                math.radians(0),
                math.radians(90),
            )

        # z axis label
        if self.config_axes.label_z:
            font_curve = bpy.data.curves.new(type="FONT", name="scale z")
            font_curve.body = self.config_axes.label_z
            font_curve.size = self.config_axes.font_size_labels
            font_curve.align_x = "CENTER"
            font_curve.align_y = "TOP"
            axis_label = bpy.data.objects.new(name="axis label z", object_data=font_curve)
            col.objects.link(axis_label)
            axis_label.data.font = font
            x = (
                self.size_bounding_box
                - self.shift[0]
                + self.config_axes.distance * 2
                + self.config_axes.line_width
            )
            y = self.shift[1]
            z = self.size_bounding_box / 2
            if self.config_axes.enable_ticks[2] and len(self.config_axes.ticks_z) > 0:
                x += self.config_axes.tick_length + self.config_axes.font_size_ticks
            axis_label.location = (x, y, z)
            axis_label.rotation_euler = (
                math.radians(0),
                math.radians(90),
                math.radians(90),
            )

        if any(self.config_axes.enable_ticks):
            # tick mesh
            mesh_tick = bpy.data.meshes.new("tick")
            mesh_tick.from_pydata(
                [
                    (0, 0, 0),
                    (self.config_axes.line_width, 0, 0),
                    (self.config_axes.line_width, self.config_axes.tick_length, 0),
                    (0, self.config_axes.tick_length, 0),
                ],
                [],
                [(0, 1, 2, 3)],
            )
            mesh_tick.update()

            # number of ticks in each dimension
            N_x = len(self.config_axes.ticks_x)
            N_y = len(self.config_axes.ticks_y)
            N_z = len(self.config_axes.ticks_z)

            # x axis ticks
            if self.config_axes.enable_ticks[0]:

                for [idx, label] in enumerate(self.config_axes.ticks_x):
                    tick = bpy.data.objects.new(f"x tick {idx}", mesh_tick)
                    col.objects.link(tick)
                    x = (
                        self.shift[0]
                        + self.size_bounding_box
                        * self.aspect[0]
                        * self.config_axes.position_tick_x[idx]
                        - 0.5 * self.config_axes.line_width
                    )
                    y = (
                        self.size_bounding_box
                        - self.shift[1]
                        + self.config_axes.distance
                        + self.config_axes.line_width
                    )
                    z = self.shift[2]
                    align_x = "CENTER"
                    if idx == 0 and self.config_axes.indent_ticks:
                        x += 0.5 * self.config_axes.line_width
                        align_x = "RIGHT"
                    if idx == N_x - 1 and self.config_axes.indent_ticks:
                        x -= 0.5 * self.config_axes.line_width
                        align_x = "LEFT"
                    tick.location = (x, y, z)

                    # minor ticks
                    if self.config_axes.enable_ticks_minor[0]:
                        spacing_ticks_minor = (
                            self.config_axes.position_tick_x[1]
                            - self.config_axes.position_tick_x[0]
                        ) / (self.config_axes.num_ticks_minor + 1)

                        is_last_tick = idx + 1 == len(self.config_axes.ticks_x)

                        if is_last_tick:
                            n_ticks = math.floor(
                                (1 - self.config_axes.position_tick_x[-1])
                                / spacing_ticks_minor
                            )
                        else:
                            n_ticks = self.config_axes.num_ticks_minor

                        for idx_minor in range(n_ticks):
                            tick = bpy.data.objects.new(f"x tick minor {idx}", mesh_tick)
                            col.objects.link(tick)

                            x_minor = (
                                self.shift[0]
                                + self.size_bounding_box
                                * self.aspect[0]
                                * (
                                    self.config_axes.position_tick_x[idx]
                                    + spacing_ticks_minor * (idx_minor + 1)
                                )
                                - 0.5 * self.config_axes.line_width
                            )
                            y_minor = (
                                self.size_bounding_box
                                - self.shift[1]
                                + self.config_axes.distance
                                + self.config_axes.line_width
                            )
                            z_minor = self.shift[2]

                            tick.location = (x_minor, y_minor, z_minor)
                            tick.scale = (1, 0.5, 1)

                    # axis labels
                    font_curve = bpy.data.curves.new(
                        type="FONT", name=f"x tick label {idx}"
                    )
                    font_curve.body = (
                        str(round(label, self.config_axes.precision[0]))
                        .rstrip("0")
                        .rstrip(".")
                    )
                    font_curve.size = self.config_axes.font_size_ticks
                    font_curve.align_x = align_x
                    font_curve.align_y = "TOP"
                    tick_label = bpy.data.objects.new(
                        name=f"x tick label {idx}", object_data=font_curve
                    )
                    col.objects.link(tick_label)
                    tick_label.data.font = font
                    tick_label.location = (
                        x,
                        y + self.config_axes.distance + self.config_axes.tick_length,
                        z,
                    )
                    tick_label.rotation_euler = (
                        math.radians(0),
                        math.radians(0),
                        math.radians(180),
                    )

            # y axis ticks
            if self.config_axes.enable_ticks[1]:

                for [idx, label] in enumerate(self.config_axes.ticks_y):
                    tick = bpy.data.objects.new(f"y tick {idx}", mesh_tick)
                    col.objects.link(tick)
                    x = (
                        self.size_bounding_box
                        - self.shift[0]
                        + self.config_axes.distance
                        + self.config_axes.line_width
                    )
                    y = (
                        self.shift[1]
                        + self.size_bounding_box
                        * self.aspect[1]
                        * self.config_axes.position_tick_y[idx]
                        + 0.5 * self.config_axes.line_width
                    )
                    z = self.shift[2]
                    align_x = "CENTER"
                    if idx == 0:
                        y += 0.5 * self.config_axes.line_width
                        align_x = "LEFT"
                    if idx == N_y - 1 and self.config_axes.indent_ticks:
                        y -= 0.5 * self.config_axes.line_width
                        align_x = "RIGHT"
                    tick.location = (x, y, z)
                    tick.rotation_euler = (
                        math.radians(0),
                        math.radians(0),
                        math.radians(-90),
                    )

                    # minor ticks
                    if self.config_axes.enable_ticks_minor[1]:
                        if self.config_axes.num_ticks_minor == 1:
                            spacing_ticks_minor = (
                                self.config_axes.position_tick_y[1]
                                - self.config_axes.position_tick_y[0] / 2
                            )
                        else:
                            spacing_ticks_minor = (
                                self.config_axes.position_tick_y[1]
                                - self.config_axes.position_tick_y[0]
                            ) / (self.config_axes.num_ticks_minor + 1)

                        is_last_tick = idx + 1 == len(self.config_axes.ticks_y)

                        if is_last_tick:
                            n_ticks = math.floor(
                                (1 - self.config_axes.position_tick_y[-1])
                                / spacing_ticks_minor
                            )
                        else:
                            n_ticks = self.config_axes.num_ticks_minor

                        for idx_minor in range(n_ticks):
                            tick = bpy.data.objects.new(f"y tick minor {idx}", mesh_tick)
                            col.objects.link(tick)

                            x_minor = (
                                self.size_bounding_box
                                - self.shift[0]
                                + self.config_axes.distance
                                + self.config_axes.line_width
                            )
                            y_minor = (
                                self.shift[1]
                                + self.size_bounding_box
                                * self.aspect[1]
                                * (
                                    self.config_axes.position_tick_y[idx]
                                    + spacing_ticks_minor * (idx_minor + 1)
                                )
                                + 0.5 * self.config_axes.line_width
                            )
                            z_minor = self.shift[2]

                            tick.rotation_euler = (
                                math.radians(0),
                                math.radians(0),
                                math.radians(-90),
                            )
                            tick.location = (x_minor, y_minor, z_minor)
                            tick.scale = (1, 0.5, 1)

                    # axis labels
                    font_curve = bpy.data.curves.new(
                        type="FONT", name=f"y tick label {idx}"
                    )
                    font_curve.body = (
                        str(round(label, self.config_axes.precision[1]))
                        .rstrip("0")
                        .rstrip(".")
                    )
                    font_curve.size = self.config_axes.font_size_ticks
                    font_curve.align_x = align_x
                    font_curve.align_y = "TOP"
                    tick_label = bpy.data.objects.new(
                        name=f"y tick label {idx}", object_data=font_curve
                    )
                    col.objects.link(tick_label)
                    tick_label.data.font = font
                    tick_label.location = (
                        x + self.config_axes.distance + self.config_axes.tick_length,
                        y,
                        z,
                    )
                    tick_label.rotation_euler = (
                        math.radians(0),
                        math.radians(0),
                        math.radians(90),
                    )

            # z axis ticks
            if self.config_axes.enable_ticks[2]:

                for [idx, label] in enumerate(self.config_axes.ticks_z):
                    tick = bpy.data.objects.new(f"z tick {idx}", mesh_tick)
                    col.objects.link(tick)
                    x = (
                        self.size_bounding_box
                        - self.shift[0]
                        + self.config_axes.distance
                        + self.config_axes.line_width
                    )
                    y = self.shift[1]
                    z = (
                        self.shift[2]
                        + self.size_bounding_box
                        * self.aspect[2]
                        * self.config_axes.position_tick_z[idx]
                        + 0.5 * self.config_axes.line_width
                    )
                    align_x = "CENTER"
                    if idx == 0:
                        z += 0.5 * self.config_axes.line_width
                        align_x = "RIGHT"
                    if idx == N_z - 1 and self.config_axes.indent_ticks:
                        z -= 0.5 * self.config_axes.line_width
                        align_x = "LEFT"
                    tick.location = (x, y, z)
                    tick.rotation_euler = (
                        math.radians(90),
                        math.radians(90),
                        math.radians(0),
                    )

                    # minor ticks
                    if self.config_axes.enable_ticks_minor[2]:
                        spacing_ticks_minor = (
                            self.config_axes.position_tick_z[1]
                            - self.config_axes.position_tick_z[0]
                        ) / (self.config_axes.num_ticks_minor + 1)

                        is_last_tick = idx + 1 == len(self.config_axes.ticks_z)

                        if is_last_tick:
                            n_ticks = math.floor(
                                (1 - self.config_axes.position_tick_z[-1])
                                / spacing_ticks_minor
                            )
                        else:
                            n_ticks = self.config_axes.num_ticks_minor

                        for idx_minor in range(n_ticks):
                            tick = bpy.data.objects.new(f"z tick minor {idx}", mesh_tick)
                            col.objects.link(tick)

                            x_minor = (
                                self.size_bounding_box
                                - self.shift[0]
                                + self.config_axes.distance
                                + self.config_axes.line_width
                            )
                            y_minor = self.shift[1]
                            z_minor = (
                                self.shift[2]
                                + self.size_bounding_box
                                * self.aspect[2]
                                * (
                                    self.config_axes.position_tick_z[idx]
                                    + spacing_ticks_minor * (idx_minor + 1)
                                )
                                + 0.5 * self.config_axes.line_width
                            )

                            tick.rotation_euler = (
                                math.radians(90),
                                math.radians(90),
                                math.radians(0),
                            )
                            tick.location = (x_minor, y_minor, z_minor)
                            tick.scale = (1, 0.5, 1)

                    # axis labels
                    font_curve = bpy.data.curves.new(
                        type="FONT", name=f"z tick label {idx}"
                    )
                    font_curve.body = (
                        str(round(label, self.config_axes.precision[2]))
                        .rstrip("0")
                        .rstrip(".")
                    )
                    font_curve.size = self.config_axes.font_size_ticks
                    font_curve.align_x = align_x
                    font_curve.align_y = "TOP"
                    tick_label = bpy.data.objects.new(
                        name=f"z tick label {idx}", object_data=font_curve
                    )
                    col.objects.link(tick_label)
                    tick_label.data.font = font
                    tick_label.location = (
                        x + self.config_axes.distance + self.config_axes.tick_length,
                        y,
                        z,
                    )
                    tick_label.rotation_euler = (
                        math.radians(0),
                        math.radians(90),
                        math.radians(90),
                    )

        # apply axis material
        for obj in col.objects:
            obj.data.materials.clear()
            obj.data.materials.append(mat_axis)
            obj.visible_shadow = False

        # add collection into context
        bpy.context.scene.collection.children.link(col)
        self.has_axes = True
        return self

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
        for p in track(p_selection, description="Creating cells"):
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

        bpy.ops.wm.obj_import(filepath=str(pth))
        mat = self.get_material(style, "default")
        col = bpy.data.collections.new("Clusters")
        col_default = bpy.data.collections.get("Collection")
        for obj in track(
            sorted(bpy.data.objects, key=lambda c: handler(c.name)),
            description="Creating cluster geometries",
        ):
            if "label_" in obj.name and obj.name != "label_0":
                obj.rotation_euler = (0, 0, 0)
                obj.scale = (self.scale, self.scale, self.scale)
                obj.location = self.shift
                col_default.objects.unlink(obj)
                col.objects.link(obj)

        for obj in track(col.objects, description="Creating cluster materials"):
            obj.data.materials.append(mat.copy())
            obj.data.materials[0].name = obj.name
        bpy.context.scene.collection.children.link(col)
        self.has_clusters = True
        return self

    def create_cylinders(
        self, pos: np.ndarray, r: np.ndarray, style="STRUCTURE_DEFAULT"
    ) -> Self:
        """
        Adds a cylinder for each throat in correct position and size to
        the scene.
        """
        bpy.ops.mesh.primitive_cylinder_add(vertices=self.n_segments, radius=1, depth=1)
        obj_template = bpy.context.view_layer.objects.active
        obj_template.data.polygons.foreach_set(
            "use_smooth", [True] * len(obj_template.data.polygons)
        )
        mat = self.get_material(style, "default")
        pos1 = pos[:, 0:3] * self.scale
        pos2 = pos[:, 3:6] * self.scale
        d = pos2 - pos1
        r = r * self.scale
        dist = np.linalg.norm(d, axis=1)
        theta = np.arccos(d[:, 2] / dist)
        phi = np.arctan2(d[:, 1], d[:, 0])
        loc = d / 2 + pos1 + self.shift
        col = bpy.data.collections.get("Cylinders")
        if not col:
            col = bpy.data.collections.new("Cylinders")
            bpy.context.scene.collection.children.link(col)
        offset = len(col.objects)
        for no in track(range(len(r)), description="Creating cylinders"):
            obj = bpy.data.objects.new(
                f"cylinder {no + offset}", obj_template.data.copy()
            )
            obj.location = loc[no, :]
            obj.scale = (r[no], r[no], dist[no])
            obj.rotation_euler[1] = theta[no]
            obj.rotation_euler[2] = phi[no]
            col.objects.link(obj)
            obj.data.materials.append(mat.copy())
            obj.data.materials[0].name = obj.name
        bpy.data.objects.remove(obj_template)
        self.has_cylinders = True
        return self

    def create_lights(self) -> Self:
        """
        Adds all nessecary lightnings to the scene.
        """
        bpy.ops.object.light_add(type="SUN")
        bpy.context.object.name = "Sun"
        obj = bpy.data.objects["Sun"]
        obj.data.energy = 9
        obj.data.angle = math.radians(10)
        obj.rotation_euler = (math.radians(-30), 0, math.radians(-70))
        self.has_lights = True
        return self

    def create_solid(self, pth: Path, style: str = "SOLID_DEFAULT"):
        """
        Adds the solid into the scene.
        """
        bpy.ops.wm.obj_import(filepath=str(pth))
        obj = bpy.data.objects["solid"]
        obj.rotation_euler = (math.radians(0), 0, math.radians(0))
        obj.scale = (self.scale, self.scale, self.scale)
        obj.location = self.shift
        # obj.location += Vector((10, 0, 0))
        obj.data.materials.clear()
        obj.data.materials.append(self.get_material(style, "solid"))
        self.has_solid = True

        return self

    def create_spheres(
        self, pos: np.ndarray, r: np.ndarray, style="STRUCTURE_DEFAULT"
    ) -> Self:
        """
        Adds a sphere for each pore in correct position and size.
        """
        bpy.ops.mesh.primitive_uv_sphere_add(
            segments=self.n_segments, ring_count=self.n_segments, radius=1
        )
        obj_template = bpy.context.view_layer.objects.active
        obj_template.data.polygons.foreach_set(
            "use_smooth", [True] * len(obj_template.data.polygons)
        )
        mat = self.get_material(style, "default")
        pos = pos * self.scale + self.shift
        r = r * self.scale
        col = bpy.data.collections.new("Spheres")
        for no in track(range(len(r)), description="Creating spheres"):
            obj = bpy.data.objects.new(f"sphere {no}", obj_template.data.copy())
            obj.location = pos[no, :]
            obj.scale = (r[no], r[no], r[no])
            col.objects.link(obj)
            obj.data.materials.append(mat.copy())
            obj.data.materials[0].name = obj.name
        bpy.data.objects.remove(obj_template)
        bpy.context.scene.collection.children.link(col)
        self.has_spheres = True
        return self

    def create_void(self, pth: Path, style: str = "ICE", name: str = "void") -> Self:
        """
        Adds a 3D object of the void space to the scene.
        """
        bpy.ops.wm.obj_import(filepath=str(pth))
        obj = bpy.data.objects["void"]
        obj.name = name
        msh = bpy.data.meshes["void"]
        msh.name = name
        obj.rotation_euler = (0, 0, 0)
        obj.scale = (self.scale, self.scale, self.scale)
        obj.location = self.shift
        obj.data.materials.clear()
        obj.data.materials.append(self.get_material(style, name))
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
            node_princ = nodes.get("Principled BSDF")
            node_princ.subsurface_method = "BURLEY"
            links.new(node_princ.outputs[0], output.inputs[0])

            if style in ["STRUCTURE_DEFAULT", "CLUSTER_DEFAULT"]:
                node_princ.inputs[0].default_value = Color("#58646E").lnrgba
                node_princ.inputs[1].default_value = 0.4  # metallic
                node_princ.inputs[2].default_value = 0.5  # roughness
                node_princ.inputs[7].default_value = 0.1  # subsurface ratio
                node_princ.inputs[8].default_value = Color("#D5D8D7").lnrgb  # subsurf
                node_princ.inputs[12].default_value = 0.1  # specular
                node_princ.inputs[23].default_value = 0.1  # sheen weight
                node_princ.inputs[24].default_value = 0  # sheen roughness
            elif style == "VOID_FROZEN":
                # links.clear()
                # node_mix = nodes.new("ShaderNodeMixShader")
                # node_mix.inputs[0].default_value = 0.5
                # links.new(node_mix.outputs[0], output.inputs[0])
                # node_trans = nodes.new("ShaderNodeBsdfTransparent")
                # links.new(node_trans.outputs[0], node_mix.inputs[1])
                # links.new(node_princ.outputs[0], node_mix.inputs[2])
                node_princ.inputs[0].default_value = Color("#0E86C7").lnrgba
                node_princ.inputs[1].default_value = 0.4  # metallic
                node_princ.inputs[2].default_value = 0.5  # roughness
                node_princ.inputs[12].default_value = 0.1  # specular
                node_princ.inputs[23].default_value = 0.1  # sheen weight
                node_princ.inputs[24].default_value = 0  # sheen roughness
            elif style == "VOID_DRY":
                links.clear()
                node_mix = nodes.new("ShaderNodeMixShader")
                node_mix.inputs[0].default_value = 0.25
                links.new(node_mix.outputs[0], output.inputs[0])
                node_trans = nodes.new("ShaderNodeBsdfTransparent")
                links.new(node_trans.outputs[0], node_mix.inputs[1])
                links.new(node_princ.outputs[0], node_mix.inputs[2])
                node_princ.inputs[0].default_value = Color("#E5BE0F").lnrgba
                node_princ.inputs[1].default_value = 0.4  # metallic
                node_princ.inputs[2].default_value = 0.5  # roughness
                node_princ.inputs[12].default_value = 0.1  # specular
                node_princ.inputs[23].default_value = 0.1  # sheen weight
                node_princ.inputs[24].default_value = 0  # sheen roughness
            elif style == "CELL_DEFAULT":
                node_bevel = nodes.new("ShaderNodeBevel")
                links.new(node_bevel.outputs["Normal"], node_princ.inputs["Normal"])
                node_bevel.inputs[0].default_value = 0.025 * 2
                node_princ.inputs[0].default_value = Color("#947C5E").lnrgba
                node_princ.inputs[1].default_value = 0.2  # metallic
                node_princ.inputs[2].default_value = 0.8  # roughness
                node_princ.inputs[4].default_value = 0.8  # alpha
            elif style == "CELL_TRANSPARENT":
                links.clear()
                node_mix = nodes.new("ShaderNodeMixShader")
                node_mix.inputs[0].default_value = 0.5
                links.new(node_mix.outputs[0], output.inputs[0])
                node_trans = nodes.new("ShaderNodeBsdfTransparent")
                links.new(node_trans.outputs[0], node_mix.inputs[1])
                links.new(node_princ.outputs[0], node_mix.inputs[2])
                node_bevel = nodes.new("ShaderNodeBevel")
                links.new(node_bevel.outputs["Normal"], node_princ.inputs["Normal"])
                node_bevel.inputs[0].default_value = 0.025 * 5
                node_princ.inputs[0].default_value = Color("#947C5E").lnrgba
                node_princ.inputs[1].default_value = 0.2  # metallic
                node_princ.inputs[2].default_value = 0.8  # roughness
                node_princ.inputs[4].default_value = 0.8  # alpha
            elif style == "SOLID_DEFAULT":
                # node_bevel = nodes.new("ShaderNodeBevel")
                # links.new(node_bevel.outputs["Normal"], node_princ.inputs["Normal"])
                # node_bevel.inputs[0].default_value = 0.025 * 2
                node_princ.inputs[0].default_value = Color("#947C5E").lnrgba
                node_princ.inputs[1].default_value = 0  # metallic
                node_princ.inputs[2].default_value = 1  # roughness
                node_princ.inputs[12].default_value = 0.5  # specular
            elif style == "SOLID_TRANSPARENT":
                links.clear()
                node_mix = nodes.new("ShaderNodeMixShader")
                node_mix.inputs[0].default_value = 0.25
                links.new(node_mix.outputs[0], output.inputs[0])
                node_trans = nodes.new("ShaderNodeBsdfTransparent")
                links.new(node_trans.outputs[0], node_mix.inputs[1])
                links.new(node_princ.outputs[0], node_mix.inputs[2])
                node_princ.inputs[0].default_value = Color("#947C5E").lnrgba
                node_princ.inputs[1].default_value = 0  # metallic
                node_princ.inputs[2].default_value = 1  # roughness
                node_princ.inputs[12].default_value = 0.5  # specular
            elif style == "BACTERIA_GREEN":
                node_princ.inputs[0].default_value = Color("#3F901A").lnrgba
                node_princ.inputs[1].default_value = 0.2  # metallic
                node_princ.inputs[2].default_value = 1  # roughness
                node_princ.inputs[12].default_value = 0  # specular
            elif style.startswith("ICE"):
                if "ICE_TILED" == style:
                    color = random.choice(
                        ["#7891e3", "#92b2e8", "#95c5e8", "#b7d2e7", "#d6edff"]
                    )
                    node_princ.inputs[0].default_value = Color(color).lnrgba
                else:
                    node_princ.inputs[0].default_value = Color("#85A2E6").lnrgba
                node_princ.inputs[1].default_value = 0  # metallic
                node_princ.inputs[2].default_value = 1  # roughness
                node_princ.inputs[7].default_value = 0.1  # subsurface ratio
                node_princ.inputs[12].default_value = 1  # specular
                node_princ.inputs[23].default_value = 0  # sheen weight
                node_princ.inputs[24].default_value = 1  # sheen roughness
            elif style == "AXES":
                node_princ.inputs[0].default_value = Color("#0001").lnrgba
                node_princ.inputs[1].default_value = 0  # metallic
                node_princ.inputs[2].default_value = 1  # roughness
                node_princ.inputs[12].default_value = 0  # specular
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
        col = bpy.data.collections.get("Cylinders")
        if col:
            col.hide_render = True
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
        col = bpy.data.collections.get("Spheres")
        if col:
            col.hide_render = True
        return self

    def hide_void(self) -> Self:
        """
        Hides the void from render scene."""
        obj = bpy.data.objects.get("void")
        if obj:
            obj.hide_render = True
        return self

    def remove_axes(self) -> Self:
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

    def render(self, folder: Path, filename: str) -> Path:
        """
        Renders the scene.
        """
        pth = (
            folder / f"{filename}_"
            f"{self.config_image.width}x{self.config_image.height}.png"
        )
        bpy.context.scene.render.resolution_x = self.config_image.width
        bpy.context.scene.render.resolution_y = self.config_image.height
        bpy.context.scene.render.filepath = str(pth)
        bpy.ops.render.render(write_still=True)
        return pth

    def save(self, pth: Path) -> Self:
        """
        Saves the current scene as BLEND file.
        """
        bpy.ops.wm.save_as_mainfile(filepath=str(pth))
        return self

    def load(self, pth: Path) -> Self:
        """
        Saves the current scene as BLEND file.
        """
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
        """Hides all cylinders from render scene."""
        col = bpy.data.collections.get("Cylinders")
        if col:
            col.hide_render = False
        return self

    def show_solid(self) -> Self:
        """
        Hides the solid from render scene."""
        obj = bpy.data.objects.get("solid")
        if obj:
            obj.hide_render = False
        return self

    def show_spheres(self) -> Self:
        """Hides all spheres from render scene."""
        col = bpy.data.collections.get("Spheres")
        if col:
            col.hide_render = False
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
        return self._aspect

    @aspect.setter
    def aspect(self, arg: tuple[float, float, float]):
        self._aspect = arg

    @property
    def config_axes(self) -> AxesConfiguration:
        return self._config_axes

    @config_axes.setter
    def config_axes(self, arg: AxesConfiguration):
        self._config_axes = arg

    @property
    def config_image(self) -> ImageConfiguration:
        return self._config_image

    @config_image.setter
    def config_image(self, arg: ImageConfiguration):
        self._config_image = arg

    @property
    def config_scene(self) -> SceneConfiguration:
        return self._config_scene

    @config_scene.setter
    def config_scene(self, arg: SceneConfiguration):
        self._config_scene = arg
