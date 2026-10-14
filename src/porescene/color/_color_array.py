# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Felix Faber /
# Otto von Guericke University Magdeburg, Thermal Process Engineering

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Self, overload

import numpy as np
import numpy.typing as npt

from porescene.color._color import Color
from porescene.color.conversion import nrgb2lnrgb_array


class ColorArray:
    """
    A sequence of colors, held in one :mod:`numpy` array.

    The vector form of :class:`Color`: it offers the same channels, color spaces and
    mixing, but every property returns an array with one row per color, and
    :meth:`mix` blends all colors at once. Use it wherever many colors are handled
    together, such as one color per pore -- the gradients in
    :mod:`porescene.color.gradient` return one.

    Indexing with an integer returns a single :class:`Color`, while a slice, an index
    array or a boolean mask returns a new :class:`ColorArray`. Iterating yields
    :class:`Color` instances.

    Parameters
    ----------
    colors
        The colors to hold, by default none.

    Examples
    --------
    Mix a white share into each color, a different one per color:

    :example:
        >>> colors = ColorArray([Color('#f00'), Color('#00f')])
        >>> colors.mix(Color('#fff'), [0.0, 0.5])[1]
        Color('#8080FF')

    Assign one color to every position a mask selects:

    :example:
        >>> colors[[False, True]] = Color('#0f0')
        >>> colors
        ColorArray([Color('#FF0000'), Color('#00FF00')])
    """

    def __init__(self, colors: Iterable[Color] = ()) -> None:
        self._nrgba = np.array([c.nrgba for c in colors], dtype=float).reshape(-1, 4)

    def __add__(self, other: Color | ColorArray) -> ColorArray:
        """
        Creates new colors by mixing the current instance with others.
        """
        return self.mix(other)

    @overload
    def __getitem__(self, key: int) -> Color: ...
    @overload
    def __getitem__(self, key: slice | npt.ArrayLike) -> ColorArray: ...
    def __getitem__(self, key):
        """
        Returns a single :class:`Color` for an integer, otherwise a new
        :class:`ColorArray`.
        """
        if isinstance(key, int | np.integer):
            return Color.from_nrgb(*self._nrgba[key].tolist())
        return ColorArray.from_nrgb(*self._nrgba[key].T)

    def __iter__(self) -> Iterator[Color]:
        for row in self._nrgba.tolist():
            yield Color.from_nrgb(*row)

    def __len__(self) -> int:
        """
        Return the number of colors.
        """
        return len(self._nrgba)

    def __repr__(self) -> str:
        if len(self) > 6:
            items = [repr(c) for c in self[:3]] + ["..."] + [repr(c) for c in self[-3:]]
        else:
            items = [repr(c) for c in self]
        return f"ColorArray([{', '.join(items)}])"

    def __setitem__(self, key: int | slice | npt.ArrayLike, value: Color | ColorArray):
        """
        Replaces the colors at ``key``, all with the same :class:`Color` or each with
        its own from a :class:`ColorArray`.
        """
        self._nrgba[key] = value.nrgba

    @classmethod
    def from_hex(cls, hexstrs: Iterable[str]) -> Self:
        """
        Creates colors from HEX strings, in any notation :class:`Color` accepts.
        """
        return cls([Color(h) for h in hexstrs])

    @classmethod
    def from_rgb(
        cls,
        r: npt.ArrayLike,
        g: npt.ArrayLike,
        b: npt.ArrayLike,
        a: npt.ArrayLike = 1.0,
    ) -> Self:
        """
        Creates colors from sRGB channels in the interval [0, 255], and alpha in the
        interval [0, 1].

        The channels are broadcast against each other, so a scalar applies to every
        color.
        """
        return cls.from_nrgb(
            np.asarray(r, dtype=float) / 255,
            np.asarray(g, dtype=float) / 255,
            np.asarray(b, dtype=float) / 255,
            a,
        )

    @classmethod
    def from_nrgb(
        cls,
        nr: npt.ArrayLike,
        ng: npt.ArrayLike,
        nb: npt.ArrayLike,
        a: npt.ArrayLike = 1.0,
    ) -> Self:
        """
        Creates colors from normalized sRGB channels in the interval [0, 1].

        The channels are broadcast against each other, so a scalar applies to every
        color, and flattened into one color per element.
        """
        channels = np.broadcast_arrays(
            *(np.asarray(c, dtype=float) for c in (nr, ng, nb, a))
        )
        ins = cls()
        ins._nrgba = np.stack(channels, axis=-1).reshape(-1, 4)
        return ins

    def mix(self, other: Color | ColorArray, ratio: npt.ArrayLike = 0.5) -> ColorArray:
        """
        Creates new colors by mixing the current instance with others.

        Parameters
        ----------
        other
            The colors to mix with: a single :class:`Color`, mixed into every color, or
            a :class:`ColorArray` of the same length, mixed color by color.
        ratio
            The amount of ``other`` to mix into the current instance, either one value
            for all colors or one per color.

        Returns
        -------
        A new instance of :class:`ColorArray`.
        """
        ratio = np.asarray(ratio, dtype=float)[..., None]
        nrgba = self._nrgba * (1 - ratio) + np.asarray(other.nrgba) * ratio
        return ColorArray.from_nrgb(*nrgba.T)

    @property
    def alpha(self) -> np.ndarray:
        """
        Normalized values from interval [0, 1] of the transparent (A) color channel.
        """
        return self._nrgba[:, 3].copy()

    @alpha.setter
    def alpha(self, arg: npt.ArrayLike):
        self._nrgba[:, 3] = arg

    @property
    def red(self) -> np.ndarray:
        """
        Normalized values from interval [0, 1] of the red (R) color channel.
        """
        return self._nrgba[:, 0].copy()

    @red.setter
    def red(self, arg: npt.ArrayLike):
        self._nrgba[:, 0] = arg

    @property
    def green(self) -> np.ndarray:
        """
        Normalized values from interval [0, 1] of the green (G) color channel.
        """
        return self._nrgba[:, 1].copy()

    @green.setter
    def green(self, arg: npt.ArrayLike):
        self._nrgba[:, 1] = arg

    @property
    def blue(self) -> np.ndarray:
        """
        Normalized values from interval [0, 1] of the blue (B) color channel.
        """
        return self._nrgba[:, 2].copy()

    @blue.setter
    def blue(self, arg: npt.ArrayLike):
        self._nrgba[:, 2] = arg

    @property
    def lnrgb(self) -> np.ndarray:
        """
        Returns the colors in normalized values from linear RGB color space, shaped
        (N, 3).
        """
        return nrgb2lnrgb_array(self._nrgba[:, :3])

    @property
    def lnrgba(self) -> np.ndarray:
        """
        Returns the colors in normalized values from linear RGBA color space, shaped
        (N, 4). Alpha is not transformed.
        """
        return nrgb2lnrgb_array(self._nrgba)

    @property
    def nrgb(self) -> np.ndarray:
        """
        Returns the colors in normalized values (interval [0, 1]) from sRGB color
        space, shaped (N, 3).
        """
        return self._nrgba[:, :3].copy()

    @property
    def nrgba(self) -> np.ndarray:
        """
        Returns the colors in normalized values (interval [0, 1]) from sRGBA color
        space, shaped (N, 4).
        """
        return self._nrgba.copy()

    @property
    def rgb(self) -> np.ndarray:
        """
        Returns the colors in integer values (interval [0, 255]) from sRGB color space,
        shaped (N, 3).
        """
        return np.rint(self._nrgba[:, :3] * 255).astype(int)

    @property
    def rgba(self) -> np.ndarray:
        """
        Returns the colors in values (interval [0, 255]) from sRGB color space, with
        alpha kept in the interval [0, 1] as in :attr:`Color.rgba`, shaped (N, 4).
        """
        return np.column_stack((self.rgb, self._nrgba[:, 3]))
