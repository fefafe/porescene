# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Felix Faber /
# Otto von Guericke University Magdeburg, Thermal Process Engineering

import contextlib
import os
from enum import Enum
from math import ceil, floor, isclose
from pathlib import Path
from typing import Callable, Iterator, Sequence

import cairosvg
import numpy as np
from PIL import Image


@contextlib.contextmanager
def suppress_stdout() -> Iterator[None]:
    """
    Silences stdout at the OS file-descriptor level.
    """
    fd = os.dup(1)
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 1)
    os.close(devnull)
    try:
        yield
    finally:
        os.dup2(fd, 1)
        os.close(fd)


class CompassDirection(Enum):
    NORTH = "N"
    NORTHEAST = "NE"
    EAST = "E"
    SOUTHEAST = "SE"
    SOUTH = "S"
    SOUTHWEST = "SW"
    WEST = "W"
    NORTHWEST = "NW"


class Orientation(Enum):
    VERTICAL = "V"
    HORIZONTAL = "H"


class MultiplicationSymbol(Enum):
    CROSS = "×"
    DOT = "·"


class UnitExponentMetric(Enum):
    QUETTA = 30
    RONNA = 27
    YOTTA = 24
    ZETTA = 21
    EXA = 18
    PETA = 15
    TERA = 12
    GIGA = 9
    MEGA = 6
    KILO = 3
    HECTO = 2
    DECA = 1
    DECI = -1
    CENTI = -2
    MILLI = -3
    MICRO = -6
    NANO = -9
    PICO = -12
    FEMTO = -15
    ATTO = -18
    ZEPTO = -21
    YOCTO = -24
    RONTO = -27
    QUECTO = -30


class UnitPrefixMetric(Enum):
    QUETTA = "Q"
    RONNA = "R"
    YOTTA = "Y"
    ZETTA = "Z"
    EXA = "E"
    PETA = "P"
    TERA = "t"
    GIGA = "G"
    MEGA = "M"
    KILO = "k"
    HECTO = "h"
    DECA = "da"
    DECI = "d"
    CENTI = "c"
    MILLI = "m"
    MICRO = "µ"
    NANO = "n"
    PICO = "p"
    FEMTO = "f"
    ATTO = "a"
    ZEPTO = "z"
    YOCTO = "y"
    RONTO = "r"
    QUECTO = "q"


def n_equidistant(lst, n):
    indices = np.linspace(0, len(lst) - 1, n, dtype=int)
    return [lst[i] for i in indices]


class Mesh:
    """
    A simple container pairing a mesh's vertices with its faces.
    """

    def __init__(
        self, vertices: np.ndarray, faces: np.ndarray, name: str = "object"
    ) -> None:
        self._vertices = vertices
        self._faces = faces
        self._name = name

    @property
    def vertices(self) -> np.ndarray:
        """``(N, 3)`` array of vertex coordinates."""
        return self._vertices

    @vertices.setter
    def vertices(self, arg: np.ndarray) -> None:
        self._vertices = arg

    @property
    def faces(self) -> np.ndarray:
        """``(M, K)`` array of vertex indices, one row per polygon."""
        return self._faces

    @faces.setter
    def faces(self, arg: np.ndarray) -> None:
        self._faces = arg

    @property
    def name(self) -> str:
        """Name of the mesh."""
        return self._name

    @name.setter
    def name(self, arg: str) -> None:
        self._name = arg


def image2mesh(
    img: np.ndarray,
    voxel_size: float | Sequence[float] = (1.0, 1.0, 1.0),
    labels: int | Sequence[int] = 1,
    *,
    per_label: bool = False,
    name: str = "object",
) -> Mesh | dict[int, Mesh]:
    """
    Builds a rectangular (quad) surface mesh from a labeled voxel image.

    Extracts the axis-aligned boundary faces of the voxels whose label is included in
    ``labels`` -- every face between a selected voxel and a non-selected neighbour (or
    the volume border) -- as unit squares scaled by the voxel size. Coincident vertices
    are merged, so each position is stored once and shared between faces. This is a
    Python port of the MATLAB ``img2mesh``.

    Parameters
    ----------
    img : np.ndarray
        2D or 3D integer array of voxel labels. A 2D image is treated as a single
        slice, one voxel thick along the third axis.
    voxel_size : float | Sequence[float], optional
        Edge length of a voxel. A scalar applies to all three axes; a 3-element
        sequence gives the length along x, y and z, by default ``(1.0, 1.0, 1.0)``.
    labels : int | Sequence[int], optional
        Label value(s) to include in the mesh, by default 1.
    per_label : bool, optional
        If ``False`` (default), all selected labels are meshed into a single surface.
        If ``True``, a separate mesh is built per label and a ``{label: Mesh}`` mapping
        is returned.
    name : str, optional
        Name assigned to the resulting mesh. In ``per_label`` mode the label is appended
        as ``"{name}_{label}"``. By default ``"object"``.

    Returns
    -------
    Mesh | dict[int, Mesh]
        For a single mesh, a :class:`Mesh` whose ``vertices`` is an ``(N, 3)`` float
        array and ``faces`` an ``(M, 4)`` integer array of quad vertex indices. With
        ``per_label=True``, a ``{label: Mesh}`` dict.
    """
    img = np.asarray(img)
    if img.ndim == 2:
        img = img[:, :, np.newaxis]
    if img.ndim != 3:
        raise ValueError("img must be a 2D or 3D array")

    size = np.asarray(voxel_size, dtype=float)
    if size.ndim == 0:
        size = np.repeat(size, 3)

    label_values = np.atleast_1d(labels)

    if per_label:
        return {
            int(label): Mesh(*_mask2mesh(img == label, size), f"{name}_{label}")
            for label in label_values
        }
    return Mesh(*_mask2mesh(np.isin(img, label_values), size), name)


def _mask2mesh(
    mask: np.ndarray,
    voxel_size: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Builds the axis-aligned boundary quad mesh of a boolean voxel mask
    (see :func:`image2mesh`).
    """
    _FACE_CORNERS = (
        np.array([[0, 0, 0], [0, 0, 1], [0, 1, 1], [0, 1, 0]]),  # face normal to x
        np.array([[0, 0, 0], [1, 0, 0], [1, 0, 1], [0, 0, 1]]),  # face normal to y
        np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]]),  # face normal to z
    )
    # pad with a False border so faces on the outer boundary are detected too
    padded = np.pad(mask.astype(bool), 1)

    faces_corners = []
    for axis in range(3):
        # full extent along `axis`, interior along the other two
        window = [slice(1, -1)] * 3
        window[axis] = slice(None)
        layer = padded[tuple(window)]
        # a face sits wherever two neighbours along `axis` differ
        lo = [slice(None)] * 3
        hi = [slice(None)] * 3
        lo[axis] = slice(0, -1)
        hi[axis] = slice(1, None)
        boundary = layer[tuple(hi)] != layer[tuple(lo)]
        base = np.argwhere(boundary)
        faces_corners.append(base[:, np.newaxis, :] + _FACE_CORNERS[axis][np.newaxis])

    vertices = np.concatenate(faces_corners).reshape(-1, 3)
    vertices, inverse = np.unique(vertices, axis=0, return_inverse=True)
    faces = inverse.ravel().reshape(-1, 4)

    return vertices.astype(float) * voxel_size, faces


def _get_bounds(
    mn: float,
    mx: float,
    prec: int = 0,
    factor: float = 1.0,
    func_transform: Callable | None = None,
) -> tuple[float, float]:
    """
    Computes even boundaries for a gradient scale.

    Parameters
    ----------
    vals
            Values to compute boundaries for.
    prec
            The place to round numbers.
    factor
            Number to scale the values up or down, to convert the unit.
            An example would be `1e-6` to convert [μm] into [m].

    Returns
    -------
    bounds
            Two-element tuple with lower and upper boundary.
    """
    if func_transform is not None:
        mn = func_transform(mn)
        mx = func_transform(mx)
    mn *= factor
    mx *= factor
    lw = floor(mn * 10**prec)
    up = ceil(mx * 10**prec)
    if isclose(lw, up):
        up += 1
    lw /= 10**prec
    up /= 10**prec
    return (lw, up)


def _get_labels(model, config):
    labels = []
    for i in range(3):
        no = round(
            model.size[i] * config.factor_scalebars[i], config.precision_scalebars[i]
        )
        if config.precision_scalebars[i] >= 0:
            no = int(no)
        labels.append(f"{no} {config.unit_scalebars[i]}")
    return tuple(labels)


def svg2png(pth: Path, crop: bool = True) -> Path:
    """
    Convert a SVG file to PNG.

    Uses :mod:`cairosvg` for the conversion, so no external software is required.
    With ``crop=True`` the result is trimmed to its visible content by removing the
    surrounding transparent margin.

    Note that :mod:`cairosvg` only renders content inside the SVG viewport; anything
    drawn beyond the root ``<svg>`` ``width``/``height`` is clipped before the
    crop and cannot be recovered.

    Parameters
    ----------
    pth
        Path to the file to be converted.
    crop
        Trim the PNG to the bounding box of its non-transparent pixels.

    Returns
    -------
    Path to the written PNG file.
    """
    pth_png = pth.with_suffix(".png")
    cairosvg.svg2png(url=pth.as_posix(), write_to=pth_png.as_posix())

    if crop:
        with Image.open(pth_png) as img:
            img = img.convert("RGBA")
            bbox = img.getchannel("A").getbbox()
            if bbox is not None:
                img.crop(bbox).save(pth_png)

    return pth_png
