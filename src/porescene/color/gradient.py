# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Felix Faber /
# Otto von Guericke University Magdeburg, Thermal Process Engineering

from abc import ABC, abstractmethod
from typing import Self

import numpy as np
import numpy.typing as npt

from porescene.color import Color, ColorArray


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

    def __call__(self, values: npt.ArrayLike) -> ColorArray:
        """
        Returns the equivalent colors to ``values``, see :meth:`get_color`.
        """

        return self.get_color(values)

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

    def get_color(self, values: npt.ArrayLike) -> ColorArray:
        """
        Returns the equivalent colors to ``values``, one per value.

        ``values`` may be a single number or an array of any shape, which is
        flattened. NaN values get :attr:`color_nan`, and values beyond the boundaries
        get :attr:`color_below` or :attr:`color_above`, unless :attr:`fit` clips them
        onto the boundaries.

        Returns
        -------
        A :class:`ColorArray <porescene.color.ColorArray>`, also for a single value.
        """
        values = np.asarray(values, dtype=float).ravel()
        values = (values - self.boundary_lower) / self.range
        if self.fit:
            values = np.clip(values, 0.0, 1.0)

        colors = self._map(np.clip(np.nan_to_num(values), 0.0, 1.0))
        colors[values < 0] = self.color_below
        colors[values > 1] = self.color_above
        colors[np.isnan(values)] = self.color_nan
        return colors

    @abstractmethod
    def _map(self, values: np.ndarray) -> ColorArray:
        """
        Maps values, normalized onto the interval [0, 1], to their colors.
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

    def _map(self, values: np.ndarray) -> ColorArray:
        stops = ColorArray(self.colors).nrgba
        x = np.linspace(0.0, 1.0, len(stops))
        return ColorArray.from_nrgb(*(np.interp(values, x, ch) for ch in stops.T))

    @property
    def n_segments(self) -> int:
        return len(self) - 1


class SegmentedGradient(Gradient):
    """
    A gradient, which holds some segments with a color assigned to.
    Returns for a data-value the color of the corresponding segment.
    """

    def _map(self, values: np.ndarray) -> ColorArray:
        # the upper boundary belongs to the last segment
        idx = np.minimum(np.floor(values * self.n_segments), self.n_segments - 1)
        return ColorArray(self.colors)[idx.astype(int)]

    @property
    def n_segments(self) -> int:
        return len(self)


class DiscreteGradient(Gradient):
    """
    A gradient for quantities that take a fixed set of values, such as the coordination
    number.

    The colors stand for values spread evenly from :attr:`boundary_lower` to
    :attr:`boundary_upper`, see :attr:`levels`: the first color for the lower boundary,
    the last one for the upper. A value within the boundaries that lies on none of the
    levels gets :attr:`color_nan`.

    The limits a :class:`~porescene.config.QuantityConfiguration` works out from the
    data are rounded outward, so they rarely land on the levels. Pin
    :attr:`~porescene.config.QuantityConfiguration.limit_lower` and
    :attr:`~porescene.config.QuantityConfiguration.limit_upper` to the first and the
    last level instead.
    """

    def _map(self, values: np.ndarray) -> ColorArray:
        pos = values * (len(self) - 1)
        idx = np.rint(pos)
        colors = ColorArray(self.colors)[idx.astype(int)]
        colors[~np.isclose(pos, idx)] = self.color_nan
        return colors

    @property
    def levels(self) -> np.ndarray:
        """
        Values the colors stand for, one per color.
        """
        return np.linspace(self.boundary_lower, self.boundary_upper, len(self))

    @property
    def n_segments(self) -> int:
        return len(self)
