# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Felix Faber /
# Otto von Guericke University Magdeburg, Thermal Process Engineering

"""
Configuration objects that control how a :class:`PoreNetwork
<porescene.model.PoreNetwork>` and its images are rendered.

This module bundles the settings used throughout :mod:`porescene`:

* :class:`PropertyConfiguration` -- visualization of a single property.
* :class:`ImageConfiguration` -- resolution of the rendered images.
* :class:`VideoConfiguration` -- frame settings for rendered videos.
* :class:`SceneConfiguration` -- overall scene, material and property settings.
* :class:`AxesConfiguration` -- coordinate axes, ticks and labels.
"""

from importlib import resources
from pathlib import Path
from typing import Callable, Self, Sequence, Type

import numpy as np

from porescene.color import Color
from porescene.color.gradient import Gradient, SmoothGradient
from porescene.color.palette import Colormap, Palette
from porescene.utility import (
    CompassDirection,
    Orientation,
    UnitExponentMetric,
    UnitPrefixMetric,
)


class PropertyConfiguration:
    """
    Settings for the visualization of a specific property of the system.
    """

    def __init__(
        self,
        name: str,
        colors: list[Color] = [],
        /,
        gradient_class: Type[Gradient] = SmoothGradient,
        heading: str | None = None,
        subheading: str | None = None,
        text: list[str] = [],
        align: CompassDirection = CompassDirection.NORTH,
        orientation: Orientation = Orientation.HORIZONTAL,
        precision: int = 0,
        min: float | None = None,
        max: float | None = None,
        use_global_boundaries: bool = False,
        factor: float = 1.0,
        func_transform: Callable = lambda v: v,
        fit: bool = True,
        color_nan: Color | None = None,
        color_below: Color | None = None,
        color_above: Color | None = None,
    ) -> None:
        self.name = name
        self.colors = colors
        self.color_nan = color_nan
        self.color_above = color_above
        self.color_below = color_below
        self.gradient_class = gradient_class
        self.align = align
        self.orientation = orientation
        self.precision = precision
        self.min = min
        self.max = max
        self.use_global_boundaries = use_global_boundaries
        self.factor = factor
        self.func_transform = func_transform
        self.fit = fit
        self.heading = heading
        self.subheading = subheading
        self.text = text

    @property
    def align(self) -> CompassDirection:
        """Point of alignment of the layout image."""
        return self._align

    @align.setter
    def align(self, arg: CompassDirection):
        self._align = arg

    @property
    def color_nan(self) -> Color | None:
        """
        Color of NaN values.

        See also :attr:`Gradient.color_nan <porescene.color.gradient.Gradient.color_nan>`.
        """
        return self._color_nan

    @color_nan.setter
    def color_nan(self, arg: Color | None):
        self._color_nan = arg

    @property
    def color_below(self) -> Color | None:
        """
        Color of values below the range.

        See also :attr:`.Gradient.color_below`.
        """
        return self._color_below

    @color_below.setter
    def color_below(self, arg: Color | None):
        self._color_below = arg

    @property
    def color_above(self) -> Color | None:
        """
        Color of values above the range.

        See also :attr:`.Gradient.color_above`.
        """
        return self._color_above

    @color_above.setter
    def color_above(self, arg: Color | None):
        self._color_above = arg

    @property
    def colors(self) -> list[Color]:
        """
        Colors of the gradient to visualize the property.

        See also :attr:`.Gradient.colors`.
        """
        return self._colors

    @colors.setter
    def colors(self, arg: list[Color]):
        self._colors = arg

    @property
    def factor(self) -> float:
        """A factor to scale the values of a property on overlays. Does not
        apply to anything rendering or model related.
        """
        return self._factor

    @factor.setter
    def factor(self, arg: float):
        self._factor = arg

    @property
    def func_transform(self) -> Callable:
        """A transformation function to scale the values of a property on overlays. Does
        not apply to anything rendering or model related.
        """
        return self._func_transform

    @func_transform.setter
    def func_transform(self, arg: Callable):
        self._func_transform = arg

    @property
    def fit(self) -> bool:
        """
        If ``True``, the gradient truncates all values in specified range.
        """
        return self._fit

    @fit.setter
    def fit(self, arg: bool):
        self._fit = arg

    @property
    def use_global_boundaries(self) -> bool:
        """Whether to use colorbar limits across all states or per state."""
        return self._use_global_boundaries

    @use_global_boundaries.setter
    def use_global_boundaries(self, arg: bool):
        self._use_global_boundaries = arg

    @property
    def max(self) -> float | None:
        """Maximum of the property."""
        return self._max

    @max.setter
    def max(self, arg: float | None):
        self._max = arg

    @property
    def min(self) -> float | None:
        """Minimum of the property."""
        return self._min

    @min.setter
    def min(self, arg: float | None):
        self._min = arg

    @property
    def name(self) -> str:
        """Name of the property."""
        return self._name

    @name.setter
    def name(self, arg: str):
        self._name = arg

    @property
    def orientation(self) -> Orientation:
        """
        Orientation of the layout image. There are two types
        available: vertical ('V') and horizontal ('H').
        """
        return self._orientation

    @orientation.setter
    def orientation(self, arg: Orientation):
        self._orientation = arg

    @property
    def precision(self) -> int:
        """Precision of the gradient boundaries on a layout."""
        return self._precision

    @precision.setter
    def precision(self, arg: int):
        self._precision = arg

    @property
    def heading(self) -> str | None:
        """Heading of the layout image."""
        return self._heading

    @heading.setter
    def heading(self, arg: str | None):
        self._heading = arg

    @property
    def subheading(self) -> str | None:
        """Subheading of the layout image."""
        return self._subheading

    @subheading.setter
    def subheading(self, arg: str | None):
        self._subheading = arg

    @property
    def text(self) -> list[str]:
        """Text lines on the layout image."""
        return self._text

    @text.setter
    def text(self, arg: list[str]):
        self._text = arg


class ImageConfiguration:
    """
    Settings for the resolution of the rendered images.
    """

    def __init__(self) -> None:
        self.width = 4096
        self.height = 4096

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        """
        Creates an :class:`ImageConfiguration` from a dictionary.

        Only the ``width`` and ``height`` keys are read; other keys are ignored.
        """
        ins = cls()

        keys_valid = [
            "width",
            "height",
        ]

        for key, value in data.items():
            if key in keys_valid:
                setattr(ins, key, value)

        return ins

    @property
    def width(self) -> int:
        """Width of the image in px."""
        return self._width

    @width.setter
    def width(self, arg: int):
        self._width = arg

    @property
    def height(self) -> int:
        """Height of the image in px."""
        return self._height

    @height.setter
    def height(self, arg: int):
        self._height = arg

    @property
    def resolution(self) -> list[int]:
        """Image resolution in px [width,height]."""
        return [self._width, self.height]

    @property
    def aspect_ratio(self) -> float:
        """Image aspect ratio."""
        return self._width / self.height


class VideoConfiguration:
    """
    Settings for the frames of a rendered video.
    """

    @property
    def frames_fps(self) -> int:
        """Frames per second of the video."""
        return self._frames_fps

    @frames_fps.setter
    def frames_fps(self, arg: int):
        self._frames_fps = arg

    @property
    def frames_solid(self) -> int:
        """Type of solid to display in generated frames."""
        return self._frames_solid

    @frames_solid.setter
    def frames_solid(self, arg: int):
        self._frames_solid = arg

    @property
    def frames_speed(self) -> int:
        """Number of steps between two frames of the video."""
        return self._frames_speed

    @frames_speed.setter
    def frames_speed(self, arg: int):
        self._frames_speed = arg


class SceneConfiguration:
    """
    Settings for the visualization of a :class:`PoreNetwork
    <porescene.model.PoreNetwork>`.
    """

    def __init__(
        self,
        enable_spheres: bool = True,
        enable_cylinders: bool = True,
        enable_clusters: bool = True,
        enable_axes: bool = True,
        enable_solid: bool = True,
        enable_void: bool = False,
        versions_solid={"COMPLETE", "BOTTOM", "LEFT", "RIGHT"},
        versions_void={"COMPLETE", "BOTTOM", "LEFT", "RIGHT"},
        material_spheres: str = "PLASTIC_ROUGH",
        material_cylinders: str = "PLASTIC_ROUGH",
        material_clusters: str = "PLASTIC_ROUGH",
        material_solid: str = "SOLID_DEFAULT",
        material_void: str = "ICE",
        palette: Palette = Palette.load(Colormap.BATLOW),
    ):
        self._properties = []
        self.enable_spheres = enable_spheres
        self.enable_cylinders = enable_cylinders
        self.enable_clusters = enable_clusters
        self.enable_axes = enable_axes
        self.enable_solid = enable_solid
        self.enable_void = enable_void
        self.material_spheres = material_spheres
        self.material_solid = material_solid
        self.material_cylinders = material_cylinders
        self.material_clusters = material_clusters
        self.material_void = material_void
        self.palette = palette
        self.versions_solid = versions_solid
        self.versions_void = versions_void

    def __iter__(self) -> Self:
        """Resets and returns the iterator over the configured properties."""
        self.__i = 0
        return self

    def __len__(self) -> int:
        """Returns the number of configured properties."""
        return len(self._properties)

    def __next__(self) -> PropertyConfiguration:
        """Returns the next :class:`PropertyConfiguration` while iterating."""
        if self.__i < len(self._properties) and self.__i >= 0:
            prop = self._properties[self.__i]
            self.__i += 1
            return prop
        else:
            raise StopIteration

    def __setitem__(self, _, prop: PropertyConfiguration):
        """Adds a :class:`PropertyConfiguration`, see :meth:`add_property`."""
        return self.add_property(prop)

    def __getitem__(self, name: str) -> PropertyConfiguration:
        """Returns the :class:`PropertyConfiguration` for given name."""
        return self.get_property(name)

    def add_property(self, prop: PropertyConfiguration):
        """
        Add the :class:`PropertyConfiguration` for a property of the pnm.
        """
        self._properties.append(prop)

    def get_property(self, name: str) -> PropertyConfiguration:
        """Returns the :class:`PropertyConfiguration` for given name."""
        for prop in self._properties:
            if prop.name == name:
                return prop
        raise ValueError(f"Unknown property with name '{name}'")

    @property
    def enable_axes(self) -> bool:
        """Toggle to enable/disable scalebars in plots."""
        return bool(self._enable_axes)

    @enable_axes.setter
    def enable_axes(self, arg: bool):
        self._enable_axes = arg

    @property
    def enable_clusters(self) -> bool:
        """Toggle to enable/disable clusters in plots."""
        return bool(self._enable_clusters)

    @enable_clusters.setter
    def enable_clusters(self, arg: bool):
        self._enable_clusters = arg

    @property
    def enable_cylinders(self) -> bool:
        """Toggle to enable/disable cylinders in plots."""
        return bool(self._enable_cylinders)

    @enable_cylinders.setter
    def enable_cylinders(self, arg: bool):
        self._enable_cylinders = arg

    @property
    def enable_solid(self) -> bool:
        """Toggle to enable/disable the solid structure in plots."""
        return bool(self._enable_solid)

    @enable_solid.setter
    def enable_solid(self, arg: bool):
        self._enable_solid = arg

    @property
    def enable_spheres(self) -> bool:
        """Toggle to enable/disable spheres in plots."""
        return bool(self._enable_spheres)

    @enable_spheres.setter
    def enable_spheres(self, arg: bool):
        self._enable_spheres = arg

    @property
    def enable_void(self) -> bool:
        """Toggle to enable/disable the void structure in plots."""
        return bool(self._enable_void)

    @enable_void.setter
    def enable_void(self, arg: bool):
        self._enable_void = arg

    @property
    def material_spheres(self) -> str:
        """Returns the material type to render the pores with."""
        return self._material_spheres.upper()

    @material_spheres.setter
    def material_spheres(self, arg):
        self._material_spheres = arg

    @property
    def material_solid(self) -> str:
        """Returns the material type to render the solid with."""
        return self._material_solid.upper()

    @material_solid.setter
    def material_solid(self, arg):
        self._material_solid = arg

    @property
    def material_cylinders(self) -> str:
        """Returns the material type to render the throats with."""
        return self._material_cylinders.upper()

    @material_cylinders.setter
    def material_cylinders(self, arg):
        self._material_cylinders = arg

    @property
    def material_void(self) -> str:
        """Returns the material type to render the void with."""
        return self._material_void.upper()

    @material_void.setter
    def material_void(self, arg: str):
        self._material_void = str(arg)

    @property
    def palette(self) -> Palette:
        """Color palette used to render the network."""
        return self._palette

    @palette.setter
    def palette(self, arg: Palette):
        self._palette = arg

    @property
    def versions_solid(self) -> list[Path]:
        """Clipping versions of the solid structure to render."""
        return self._versions_solid

    @versions_solid.setter
    def versions_solid(self, arg: list[Path]):
        self._versions_solid = arg

    @property
    def versions_void(self) -> list[Path]:
        """Clipping versions of the void structure to render."""
        return self._versions_void

    @versions_void.setter
    def versions_void(self, arg: list[Path]):
        self._versions_void = arg


class AxesConfiguration:
    """
    Settings for the coordinate axes, ticks and labels of a scene.
    """

    def __init__(self) -> None:
        self.font_size_labels = 1.5
        self.font_size_ticks = 1
        self.line_width = 0.1
        self.distance = 0.2
        self.tick_length = 0.3
        self.label_x = ""
        self.label_y = ""
        self.label_z = ""
        self.ticks_x = []
        self.ticks_y = []
        self.ticks_z = []
        self.enable_ticks = (True, True, True)
        self.enable_ticks_minor = (True, True, True)
        self.factor = (1e6, 1e6, 1e6)
        self.precision = (0, 0, 0)
        self.indent_ticks = False
        self.num_ticks_minor = 4
        self.value_start = (0, 0, 0)
        self.value_end = (1, 1, 1)

        ref = resources.files("porescene").joinpath("data/font/Inter-Regular.ttf")
        with resources.as_file(ref) as font_path:
            self.font_family = font_path

    @classmethod
    def from_dict(cls, extent: np.ndarray, data: dict) -> Self:
        """
        Creates an :class:`AxesConfiguration` from a dictionary.

        Ticks and axis labels are derived from ``extent`` (the size of the
        volume) together with the optional ``tick_interval`` and
        ``unit_display`` keys.
        """
        ins = cls()

        keys_valid = [
            "font_size_labels",
            "font_size_ticks",
            "line_width",
            "distance",
            "tick_length",
            "tick_interval",
            "label_x",
            "label_y",
            "label_z",
            "ticks_x",
            "ticks_y",
            "ticks_z",
            "enable_ticks",
            "enable_ticks_minor",
            "precision",
            "num_ticks_minor",
            "indent_ticks",
        ]

        for key, value in data.items():
            if key in keys_valid:
                setattr(ins, key, value)

        if "tick_interval" in data:
            tick_interval = data["tick_interval"]
        else:
            tick_interval = 100

        if "unit_display" in data:
            unit_display = data["unit_display"]
        else:
            unit_display = "MICRO"

        fac_unit = 10 ** UnitExponentMetric[unit_display].value
        fac_axis = 1 / fac_unit
        label_axis = UnitPrefixMetric[unit_display].value + "m"

        if "label_x" not in data:
            ins.label_x = f"y [{label_axis}]"
        if "label_y" not in data:
            ins.label_y = f"x [{label_axis}]"
        if "label_z" not in data:
            ins.label_z = f"z [{label_axis}]"

        ins.factor = (fac_axis, fac_axis, fac_axis)

        tick_start = (0, 0, 0)
        tick_end = np.array(
            (
                extent[0] * ins.factor[0],
                extent[1] * ins.factor[1],
                extent[2] * ins.factor[2],
            )
        )

        margin = tick_interval * 1e-6
        ticks_x = np.arange(tick_start[0], tick_end[0] + margin, tick_interval)
        ticks_y = np.arange(tick_start[1], tick_end[1] + margin, tick_interval)
        ticks_z = np.arange(tick_start[2], tick_end[2] + margin, tick_interval)

        if "ticks_x" not in data:
            ins.ticks_x = ticks_x
        if "ticks_y" not in data:
            ins.ticks_y = ticks_y
        if "ticks_z" not in data:
            ins.ticks_z = ticks_z

        ins.position_tick_x = ticks_x / extent[0] / fac_axis
        ins.position_tick_y = ticks_y / extent[1] / fac_axis
        ins.position_tick_z = ticks_z / extent[2] / fac_axis

        ins.value_start = tick_start
        ins.value_end = tuple(tick_end)

        return ins

    @property
    def factor(self) -> tuple[float, float, float]:
        """Factor to scale axis labels."""
        return self._factor

    @factor.setter
    def factor(self, arg: tuple[float, float, float]):
        self._factor = arg

    @property
    def precision(self) -> tuple[int, int, int]:
        """Precision of axis labels. Applies after scaling."""
        return self._precision

    @precision.setter
    def precision(self, arg: tuple[int, int, int]):
        self._precision = arg

    @property
    def enable_ticks(self) -> tuple[bool, bool, bool]:
        """Toggle to show/hide major axis ticks."""
        return self._enable_ticks

    @enable_ticks.setter
    def enable_ticks(self, arg: bool | tuple[bool, bool, bool]):
        if isinstance(arg, bool):
            arg = (arg, arg, arg)
        self._enable_ticks = arg

    @property
    def enable_ticks_minor(self) -> tuple[bool, bool, bool]:
        """Toggle to show/hide minor axis ticks."""
        return self._enable_ticks_minor

    @enable_ticks_minor.setter
    def enable_ticks_minor(self, arg: bool | tuple[bool, bool, bool]):
        if isinstance(arg, bool):
            arg = (arg, arg, arg)
        self._enable_ticks_minor = arg

    @property
    def line_width(self) -> float:
        """Axis line width."""
        return self._line_width

    @line_width.setter
    def line_width(self, arg: float):
        self._line_width = arg

    @property
    def label_x(self) -> str:
        """x-axis label."""
        return self._label_x

    @label_x.setter
    def label_x(self, arg: str):
        self._label_x = arg

    @property
    def label_y(self) -> str:
        """y-axis label."""
        return self._label_y

    @label_y.setter
    def label_y(self, arg: str):
        self._label_y = arg

    @property
    def label_z(self) -> str:
        """z-axis label."""
        return self._label_z

    @label_z.setter
    def label_z(self, arg: str):
        self._label_z = arg

    @property
    def font_family(self) -> Path | None:
        """
        Font family for axis labels specified as :class:`Path <pathlib.Path>` to TTF file.
        """
        return self._font_family

    @font_family.setter
    def font_family(self, arg: Path | None):
        self._font_family = arg

    @property
    def font_size_labels(self) -> float:
        """Axis label font-size."""
        return self._font_size

    @font_size_labels.setter
    def font_size_labels(self, arg: float):
        self._font_size = arg

    @property
    def font_size_ticks(self) -> float:
        """Tick label font-size."""
        return self._font_size

    @font_size_ticks.setter
    def font_size_ticks(self, arg: float):
        self._font_size = arg

    @property
    def tick_length(self) -> float:
        """Tick length."""
        return self._tick_length

    @tick_length.setter
    def tick_length(self, arg: float):
        self._tick_length = arg

    @property
    def ticks_x(self) -> Sequence[float]:
        """Tick values shown along the x-axis."""
        return self._ticks_x

    @ticks_x.setter
    def ticks_x(self, arg: Sequence[float]):
        self._ticks_x = arg

    @property
    def ticks_y(self) -> list[float]:
        """Tick values shown along the y-axis."""
        return self._ticks_y

    @ticks_y.setter
    def ticks_y(self, arg: list[float]):
        self._ticks_y = arg

    @property
    def ticks_z(self) -> list[float]:
        """Tick values shown along the z-axis."""
        return self._ticks_z

    @ticks_z.setter
    def ticks_z(self, arg: list[float]):
        self._ticks_z = arg

    @property
    def indent_ticks(self) -> bool:
        """Whether tick labels are indented."""
        return self._indent_ticks

    @indent_ticks.setter
    def indent_ticks(self, arg: bool):
        self._indent_ticks = arg

    @property
    def position_tick_x(self) -> tuple[float, ...]:
        """Normalized positions (0-1) of the x-axis ticks."""
        if hasattr(self, "_position_tick_x"):
            return self._position_tick_x
        else:
            N = len(self.ticks_x)
            return tuple(x / (N - 1) for x in range(N))

    @position_tick_x.setter
    def position_tick_x(self, arg: tuple[float, ...]):
        self._position_tick_x = arg

    @property
    def position_tick_y(self) -> tuple[float, ...]:
        """Normalized positions (0-1) of the y-axis ticks."""
        if hasattr(self, "_tick_positions_y"):
            return self._tick_positions_y
        else:
            N = len(self.ticks_y)
            return tuple(y / (N - 1) for y in range(N))

    @position_tick_y.setter
    def position_tick_y(self, arg: tuple[float, ...]):
        self._tick_positions_y = arg

    @property
    def position_tick_z(self) -> Sequence[float]:
        """Normalized positions (0-1) of the z-axis ticks."""
        if hasattr(self, "_tick_positions_z"):
            return self._tick_positions_z
        else:
            N = len(self.ticks_z)
            return tuple(z / (N - 1) for z in range(N))

    @position_tick_z.setter
    def position_tick_z(self, arg: Sequence[float]):
        self._tick_positions_z = arg

    @property
    def value_start(self) -> Sequence[float]:
        """Tick value at the start of each axis (x, y, z)."""
        return self._value_start

    @value_start.setter
    def value_start(self, arg: Sequence[float]):
        self._value_start = arg

    @property
    def value_end(self) -> Sequence[float]:
        """Tick value at the end of each axis (x, y, z)."""
        return self._value_end

    @value_end.setter
    def value_end(self, arg: Sequence[float]):
        self._value_end = arg


default_config = SceneConfiguration()
# default_config.add_property(
#     PropertyConfiguration(
#         "coordination_number",
#         [
#             fefacolors.lightblue,
#             fefacolors.lightgreen,
#             fefacolors.orange,
#         ],
#         heading="Coordination Number",
#         # gradient_class=DiscreteGradient,
#     )
# )
# default_config.add_property(
#     PropertyConfiguration(
#         "radius",
#         FeFaPalette().all(),
#         heading="Radius [μm]",
#         orientation=Orientation.HORIZONTAL,
#         factor=1e6,
#         precision=-1,
#     )
# )
# default_config.add_property(
#     PropertyConfiguration(
#         "saturation",
#         [
#             fefacolors.yellow,
#             fefacolors.pink,
#         ],
#         heading="Saturation [-]",
#         precision=3,
#         frames_solid="LEFT",
#     )
# )
# default_config.add_property(
#     PropertyConfiguration(
#         "temperature",
#         [
#             fefacolors.darkblue,
#             fefacolors.red,
#         ],
#         heading="Temperature [\u00B0C]",  # \u00BC = degree
#         precision=0,
#         frames_solid="RIGHT",
#     )
# )
# default_config.add_property(
#     PropertyConfiguration(
#         "vapor_pressure",
#         [
#             fefacolors.darkgreen,
#             fefacolors.orange,
#         ],
#         heading="Pressure [Pa]",
#         precision=0,
#     )
# )
