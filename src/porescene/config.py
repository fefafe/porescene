from pathlib import Path
from typing import Callable, Self, Sequence, Type

from porescene.color import Color
from porescene.color.gradient import Gradient, SmoothGradient
from porescene.color.palette import Palette
from porescene.utility import CompassDirection, Orientation


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
        """
        Point of alignment of the layout image.
        """
        return self._align

    @align.setter
    def align(self, arg: CompassDirection):
        self._align = arg

    @property
    def color_nan(self) -> Color | None:
        """Color of NaN values. See :attr:``.Gradient.color_nan``."""
        return self._color_nan

    @color_nan.setter
    def color_nan(self, arg: Color | None):
        self._color_nan = arg

    @property
    def color_below(self) -> Color | None:
        """
        Color of values below the range. See :attr:`.Gradient.color_below`.
        """
        return self._color_below

    @color_below.setter
    def color_below(self, arg: Color | None):
        self._color_below = arg

    @property
    def color_above(self) -> Color | None:
        """
        Color of values above the range. See :attr:``.Gradient.color_above``.
        """
        return self._color_above

    @color_above.setter
    def color_above(self, arg: Color | None):
        self._color_above = arg

    @property
    def colors(self) -> list[Color]:
        """
        Colors of the gradient to visualize the property.

        See :attr:``.Gradient.colors``.
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
    def __init__(self) -> None:
        self.width = 4096
        self.height = 4096

    @property
    def width(self) -> int:
        return self._width

    @width.setter
    def width(self, arg: int):
        self._width = arg

    @property
    def height(self) -> int:
        return self._height

    @height.setter
    def height(self, arg: int):
        self._height = arg

    @property
    def resolution(self) -> list[int]:
        return [self._width, self.height]

    @property
    def aspect_ratio(self) -> float:
        return self._width / self.height


class VideoConfiguration:

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
    Settings for the visualization of a :class:`PoreNetwork`.
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
        palette: Palette = Palette.load("batlow"),
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
        self.__i = 0
        return self

    def __len__(self) -> int:
        return len(self._properties)

    def __next__(self) -> PropertyConfiguration:
        if self.__i < len(self._properties) and self.__i >= 0:
            prop = self._properties[self.__i]
            self.__i += 1
            return prop
        else:
            raise StopIteration

    def __setitem__(self, _, prop: PropertyConfiguration):
        return self.add_property(prop)

    def __getitem__(self, name: str) -> PropertyConfiguration:
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
        return self._palette

    @palette.setter
    def palette(self, arg: Palette):
        self._palette = arg

    @property
    def versions_solid(self) -> list[Path]:
        return self._versions_solid

    @versions_solid.setter
    def versions_solid(self, arg: list[Path]):
        self._versions_solid = arg

    @property
    def versions_void(self) -> list[Path]:
        return self._versions_void

    @versions_void.setter
    def versions_void(self, arg: list[Path]):
        self._versions_void = arg


class AxesConfiguration:

    def __init__(self) -> None:
        self.font_size_labels = 1.5
        self.font_size_ticks = 1
        self.font_family = None
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
        self.indent_ticks = True
        self.num_ticks_minor = 4
        self.value_start = (0, 0, 0)
        self.value_end = (1, 1, 1)

    def set_labels(self, L_x: float, L_y: float, L_z: float) -> Self:
        label_x = round(L_x * self.factor[0], self.precision[0])
        label_y = round(L_y * self.factor[1], self.precision[1])
        label_z = round(L_z * self.factor[2], self.precision[2])
        unit_x = "µm" if self.factor[0] == 1e6 else "mm"
        unit_y = "µm" if self.factor[1] == 1e6 else "mm"
        unit_z = "µm" if self.factor[2] == 1e6 else "mm"
        self.label_x = f"{label_x:.{self.precision[0]}f}" + " " + unit_x
        self.label_y = f"{label_y:.{self.precision[1]}f}" + " " + unit_y
        self.label_z = f"{label_z:.{self.precision[2]}f}" + " " + unit_z
        return self

    @property
    def factor(self) -> tuple[float, float, float]:
        """
        Factor to scale axis labels.
        """
        return self._factor

    @factor.setter
    def factor(self, arg: tuple[float, float, float]):
        self._factor = arg

    @property
    def precision(self) -> tuple[int, int, int]:
        """
        Precision of axis labels. Applies after scaling.
        """
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
        return self._line_width

    @line_width.setter
    def line_width(self, arg: float):
        self._line_width = arg

    @property
    def label_x(self) -> str:
        return self._label_x

    @label_x.setter
    def label_x(self, arg: str):
        self._label_x = arg

    @property
    def label_y(self) -> str:
        return self._label_y

    @label_y.setter
    def label_y(self, arg: str):
        self._label_y = arg

    @property
    def label_z(self) -> str:
        return self._label_z

    @label_z.setter
    def label_z(self, arg: str):
        self._label_z = arg

    @property
    def font_family(self) -> Path | None:
        return self._font_family

    @font_family.setter
    def font_family(self, arg: Path | None):
        self._font_family = arg

    @property
    def font_size_labels(self) -> float:
        return self._font_size

    @font_size_labels.setter
    def font_size_labels(self, arg: float):
        self._font_size = arg

    @property
    def font_size_ticks(self) -> float:
        return self._font_size

    @font_size_ticks.setter
    def font_size_ticks(self, arg: float):
        self._font_size = arg

    @property
    def tick_length(self) -> float:
        return self._tick_length

    @tick_length.setter
    def tick_length(self, arg: float):
        self._tick_length = arg

    @property
    def ticks_x(self) -> Sequence[float]:
        return self._ticks_x

    @ticks_x.setter
    def ticks_x(self, arg: Sequence[float]):
        self._ticks_x = arg

    @property
    def ticks_y(self) -> list[float]:
        return self._ticks_y

    @ticks_y.setter
    def ticks_y(self, arg: list[float]):
        self._ticks_y = arg

    @property
    def ticks_z(self) -> list[float]:
        return self._ticks_z

    @ticks_z.setter
    def ticks_z(self, arg: list[float]):
        self._ticks_z = arg

    @property
    def indent_ticks(self) -> bool:
        return self._indent_ticks

    @indent_ticks.setter
    def indent_ticks(self, arg: bool):
        self._indent_ticks = arg

    @property
    def position_tick_x(self) -> tuple[float, ...]:
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
        return self._value_start

    @value_start.setter
    def value_start(self, arg: Sequence[float]):
        self._value_start = arg

    @property
    def value_end(self) -> Sequence[float]:
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
