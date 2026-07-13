# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Felix Faber /
# Otto von Guericke University Magdeburg, Thermal Process Engineering

from abc import ABC, abstractmethod
from typing import Self

import numpy as np

from porescene.color import Color


class Gradient(ABC):
    """
    Abstract base class for all types of gradient.
    """

    def __init__(
        self,
        colors: list[Color] = [Color("#FFF"), Color("#000")],
        boundary_lower: float = 0.0,
        boundary_upper: float = 1.0,
        /,
        color_nan: Color = Color("#888888"),
        color_below: Color = Color("#FFFFFF"),
        color_above: Color = Color("#000000"),
        fit: bool = False,
    ) -> None:
        self.colors = colors
        self.boundary_lower = boundary_lower
        self.boundary_upper = boundary_upper
        self.color_nan = color_nan
        self.color_below = color_below
        self.color_above = color_above
        self.fit = fit

    def __call__(self, value) -> list[Color]:
        """
        Returns the equivalent :class:`Color <porescene.color.Color>` to ``value``.
        """

        return self.get_color(value)

    def __iter__(self) -> Self:
        self.__i = 0
        return self

    def __len__(self) -> int:
        """
        Return the number of colors of the gradient.
        """
        return len(self.colors)

    def __next__(self) -> Color:
        if self.__i < len(self.colors) and self.__i >= 0:
            color = self.colors[self.__i]
            self.__i += 1
            return color
        else:
            raise StopIteration

    def __repr__(self) -> str:
        return (
            f"{__name__}({self.colors.__repr__()}, {self.boundary_lower}, "
            f"{self.boundary_upper}, "
            f"color_nan={self.color_nan.__repr__()}, "
            f"color_below={self.color_below.__repr__()}, "
            f"color_above={self.color_above.__repr__()}, "
            f"fit={self.fit.__repr__()})"
        )

    @abstractmethod
    def get_color(self, values) -> list[Color]:
        """
        Returns the equivalent :class:`Color <porescene.color.Color>` to ``values``.

        Returns :class:`list` of :class:`Color <porescene.color.Color>`, if several
        ``values`` given.
        """

    @property
    def boundary_lower(self) -> float:
        """
        Minimum of the covered numerical range.
        """
        return self._boundary_lower

    @boundary_lower.setter
    def boundary_lower(self, arg: float):
        self._boundary_lower = arg

    @property
    def boundary_upper(self) -> float:
        """
        Maximum of the covered numerical range.
        """
        return self._boundary_upper

    @boundary_upper.setter
    def boundary_upper(self, arg: float):
        self._boundary_upper = arg

    @property
    def colors(self) -> list[Color]:
        return self._colors

    @colors.setter
    def colors(self, arg: list[Color]):
        self._colors = []
        if len(arg) < 2:
            raise ValueError(f"{__name__}.colors expects at least 2 colors")
        for col in arg:
            self._colors.append(col)

    @property
    def color_above(self) -> Color:
        """
        Color for values that exceed the nominal range at the upper boundary.
        """
        return self._color_above

    @color_above.setter
    def color_above(self, arg: Color):
        self._color_above = arg

    @property
    def color_below(self) -> Color:
        """
        Color for values that exceed the nominal range at the lower boundary.
        """
        return self._color_below

    @color_below.setter
    def color_below(self, arg: Color):
        self._color_below = arg

    @property
    def color_nan(self) -> Color:
        """
        :class:`Color <porescene.color.Color>` of NaN values.
        """
        return self._color_nan

    @color_nan.setter
    def color_nan(self, arg: Color):
        self._color_nan = arg

    @property
    def fit(self) -> bool:
        """
        If true, values which exceed the given range, will be clipped to
        either the lower or upper boundary.
        """
        return self._fit

    @fit.setter
    def fit(self, arg: bool):
        self._fit = arg

    @property
    def len_segment(self) -> float:
        """
        Length of each segment.
        """
        return 1 / self.n_segments

    @property
    @abstractmethod
    def n_segments(self) -> int:
        """
        Number of color segments.
        """

    @property
    def range(self):
        """
        Nominal range which needs to be covered with colors.
        """
        return self.boundary_upper - self.boundary_lower


class SmoothGradient(Gradient):
    """
    A gradient which maps numerical values to a range of colors.
    Each numerical value has a distinct corresponding color.
    """

    def get_color(self, values) -> list[Color]:
        values = np.array(values).flatten()
        colors = []
        for value in values:
            value = (float(value) - self.boundary_lower) / self.range
            if np.isnan(value):
                colors.append(self.color_nan)
            elif value < 0:
                if not self.fit:
                    colors.append(self.color_below)
                else:
                    colors.append(self.colors[0])
            elif value > 1:
                if not self.fit:
                    colors.append(self.color_above)
                else:
                    colors.append(self.colors[-1])
            elif np.isclose(value, 0).item():
                colors.append(self.colors[0])
            elif np.isclose(value, 1).item():
                colors.append(self.colors[-1])
            else:
                idx_before = int(value // self.len_segment)
                idx_after = idx_before + 1
                color_before = self.colors[idx_before]
                color_after = self.colors[idx_after]
                ratio = (value % self.len_segment) / self.len_segment
                color = color_before.mix(color_after, ratio)
                colors.append(color)
        return colors

    @property
    def n_segments(self) -> int:
        return len(self) - 1


class SegmentedGradient(Gradient):
    """
    A gradient, which holds some segments with a color assigned to.
    Returns for a data-value the color of the corresponding segment.
    """

    def get_color(self, values) -> list[Color]:
        values = np.array(values).flatten()
        colors = []
        for value in values:
            value = (float(value) - self.boundary_lower) / self.range
            if np.isnan(value):
                colors.append(self.color_nan)
            elif value < 0:
                if not self.fit:
                    colors.append(self.color_below)
                else:
                    colors.append(self.colors[0])
            elif value > 1:
                if not self.fit:
                    colors.append(self.color_above)
                else:
                    colors.append(self.colors[-1])
            elif np.isclose(value, 0).item():
                colors.append(self.colors[0])
            elif np.isclose(value, 1).item():
                colors.append(self.colors[-1])
            else:
                idx = int(value // self.len_segment)
                colors.append(self.colors[idx])
        return colors

    @property
    def n_segments(self) -> int:
        return len(self)


class DiscreteGradient:
    """
    This gradient can be used to map colors to a fixed set of values.
    """

    def __init__(self, pairs, /, color_nan=Color("#888")):
        self._colors = list(pairs.values())
        self._labels = list(pairs.keys())

    def __call__(self, value) -> Color | list[Color]:
        """
        Returns the equivalent :class:`Color <porescene.color.Color>` for ``value``.
        """
        return self.get_color(value)

    def get_color(self, values) -> list[Color]:
        values = np.array(values).flatten()
        colors = []
        for value in values:
            if np.isnan(value):
                colors.append(self.color_nan)
            else:
                for idx, label in enumerate(self.labels):
                    if np.isclose(value, label).item():
                        colors.append(self.colors[idx])
                        break
        return colors

    @property
    def colors(self) -> list[Color]:
        return self._colors

    @colors.setter
    def colors(self, arg: list[Color]):
        self._colors = []
        for color in arg:
            if not isinstance(color, Color):
                raise TypeError(f"{__name__}.colors expects a 'list' of " "'Color'")
            else:
                self._colors.append(color)

    @property
    def color_nan(self) -> Color:
        """Color of NaN values."""
        return self._color_nan

    @color_nan.setter
    def color_nan(self, arg: Color):
        if isinstance(arg, Color):
            self._color_nan = arg
        else:
            raise TypeError(f"{__name__}.color_nan expected 'Color'")

    @property
    def labels(self) -> list[str]:
        return self._labels

    @labels.setter
    def labels(self, arg: list[str]):
        self._labels = []
        for label in arg:
            if not isinstance(label, str):
                raise TypeError(f"{__name__}.labels expects a 'list' of " "'str'")
            else:
                self._labels.append(label)
