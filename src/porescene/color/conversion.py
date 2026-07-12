# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Felix Faber /
# Otto von Guericke University Magdeburg, Thermal Process Engineering

"""
Color Space Conversion
----------------------

Some functions to convert color tuples between following color spaces:

- HEX
- Standard RGB
- Normalized standard RGB
- Normalized linear RGB
"""

from typing import overload

from ._types import (
    ColorTupleFloat3,
    ColorTupleFloat4,
    ColorTupleInt3,
    ColorTupleInt3Float1,
)


def hex2rgb(h: str) -> ColorTupleInt3 | ColorTupleInt3Float1:
    """
    Convert HEX into sRGB.

    Returns a three-element or four-element ``tuple`` depending on whether or
    not a ``alpha`` value is given.

    Parameters
    ----------
    h
        The color value in HEX notation. The function supports
        following forms of HEX string always with and without a prefixed
        hash (#):

        * #RGB
        * #RGBA
        * #RRGGBB
        * #RRGGBBAA
    """
    if h.startswith("#"):
        h = h.strip("#")
    if len(h) in [3, 4]:
        he = h[0] + h[0] + h[1] + h[1] + h[2] + h[2]
        if len(h) == 4:
            he += h[3] + h[3]
    else:
        he = h
    r = int(he[0:2], 16)
    g = int(he[2:4], 16)
    b = int(he[4:6], 16)
    if len(he) == 8:
        a = int(he[6:8], 16) / 255
        rgb = (r, g, b, a)
    else:
        rgb = (r, g, b)
    return rgb


def rgb2hex(r: int, g: int, b: int, a: float | None = None) -> str:
    """
    Convert sRGB into HEX.

    Returns a three-element or four-element `tuple` depending on whether or
    not a ``alpha`` value is given.
    """
    if a is None:
        h = "#%02x%02x%02x" % (r, g, b)
    else:
        h = "#%02x%02x%02x%02x" % (r, g, b, int(a * 255))
    return h.upper()


@overload
def rgb2nrgb(r: int, g: int, b: int, a: None = None) -> ColorTupleFloat3: ...
@overload
def rgb2nrgb(r: int, g: int, b: int, a: float) -> ColorTupleFloat4: ...
def rgb2nrgb(
    r: int, g: int, b: int, a: float | None = None
) -> ColorTupleFloat3 | ColorTupleFloat4:
    """
    Converts sRGB from range [0, 255] into range [0, 1].
    """
    rn = float(r) / 255
    gn = float(g) / 255
    bn = float(b) / 255
    if a is None:
        nrgb = (rn, gn, bn)
    else:
        nrgb = (rn, gn, bn, a)
    return nrgb


@overload
def nrgb2rgb(r: float, g: float, b: float, a: None = None) -> ColorTupleInt3: ...
@overload
def nrgb2rgb(r: float, g: float, b: float, a: float) -> ColorTupleInt3Float1: ...
def nrgb2rgb(
    r: float,
    g: float,
    b: float,
    a: float | None = None,
) -> ColorTupleInt3 | ColorTupleInt3Float1:
    """
    Converts sRGB from range [0, 1] into range [0, 255].
    """
    r = int(round(r * 255))
    g = int(round(g * 255))
    b = int(round(b * 255))
    if a is None:
        rgb = r, g, b
    else:
        rgb = r, g, b, a
    return rgb


@overload
def nrgb2lnrgb(r: float, g: float, b: float, a: None = None) -> ColorTupleFloat3: ...
@overload
def nrgb2lnrgb(r: float, g: float, b: float, a: float) -> ColorTupleFloat4: ...
def nrgb2lnrgb(
    r: float,
    g: float,
    b: float,
    a: float | None = None,
) -> ColorTupleFloat3 | ColorTupleFloat4:
    """
    Converts normalized sRGB into normalized linear RGB.
    """
    r = r / 12.92 if r < 0.04045 else ((r + 0.055) / 1.055) ** 2.4
    g = g / 12.92 if g < 0.04045 else ((g + 0.055) / 1.055) ** 2.4
    b = b / 12.92 if b < 0.04045 else ((b + 0.055) / 1.055) ** 2.4
    if a is None:
        lnrgb = (r, g, b)
    else:
        lnrgb = (r, g, b, a)
    return lnrgb


@overload
def lnrgb2nrgb(r: float, g: float, b: float, a: None = None) -> ColorTupleFloat3: ...
@overload
def lnrgb2nrgb(r: float, g: float, b: float, a: float) -> ColorTupleFloat4: ...
def lnrgb2nrgb(
    r: float,
    g: float,
    b: float,
    a: float | None = None,
) -> ColorTupleFloat3 | ColorTupleFloat4:
    """
    Converts normalized linear RGB into sRGB in range [0, 1].
    """
    r = r * 12.92 if r < 0.04045 / 12.92 else r ** (1 / 2.4) * 1.055 - 0.055
    g = g * 12.92 if g < 0.04045 / 12.92 else g ** (1 / 2.4) * 1.055 - 0.055
    b = b * 12.92 if b < 0.04045 / 12.92 else b ** (1 / 2.4) * 1.055 - 0.055
    if a is None:
        nrgb = (r, g, b)
    else:
        nrgb = (r, g, b, a)
    return nrgb
