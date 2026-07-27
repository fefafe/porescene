# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Felix Faber /
# Otto von Guericke University Magdeburg, Thermal Process Engineering

import contextlib
import os
from collections.abc import Callable, Generator, Mapping, Sequence
from enum import Enum
from math import ceil, floor, isclose
from pathlib import Path
from typing import Literal, overload

import numpy as np
import resvg_py
from PIL import Image
from rich import progress
from rich.console import Console


@contextlib.contextmanager
def suppress_stdout() -> Generator[None]:
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


def _get_spinner(text: str) -> progress.Progress:
    return progress.Progress(
        progress.SpinnerColumn(style="white"),
        progress.TextColumn(text),
        progress.TimeElapsedColumn(),
        console=Console(stderr=True),
    )


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
    """
    Decadic exponent of each metric prefix. ``BASE`` denotes the unprefixed unit.
    """

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
    BASE = 0
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
    """
    Symbol of each metric prefix. ``BASE`` is the unprefixed unit and carries no symbol.
    """

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
    BASE = ""
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


@overload
def volume2mesh(
    img: np.ndarray,
    voxel_size: float | Sequence[float] = ...,
    labels: int | Sequence[int] | np.ndarray = ...,
    *,
    per_label: Literal[False] = ...,
    merge: bool = ...,
    swap_axes: bool = ...,
    name: str = ...,
) -> Mesh: ...
@overload
def volume2mesh(
    img: np.ndarray,
    voxel_size: float | Sequence[float] = ...,
    labels: int | Sequence[int] | np.ndarray = ...,
    *,
    per_label: Literal[True],
    merge: bool = ...,
    swap_axes: bool = ...,
    name: str = ...,
) -> dict[int, Mesh]: ...
def volume2mesh(
    img: np.ndarray,
    voxel_size: float | Sequence[float] = (1.0, 1.0, 1.0),
    labels: int | Sequence[int] | np.ndarray = 1,
    *,
    per_label: bool = False,
    merge: bool = True,
    swap_axes: bool = False,
    name: str = "object",
) -> Mesh | dict[int, Mesh]:
    """
    Builds a rectangular (quad) surface mesh from a labeled voxel image.

    Extracts the axis-aligned boundary faces of the voxels whose label is included in
    ``labels`` -- every face between a selected voxel and a non-selected neighbour (or
    the volume border) -- as unit squares scaled by the voxel size. Coincident vertices
    are merged, so each position is stored once and shared between faces. Unless
    ``merge`` is disabled, coplanar faces are additionally fused into maximal rectangles,
    which leaves only the vertices a render actually needs (see :func:`merge_faces`).

    Parameters
    ----------
    img : np.ndarray
        2D or 3D integer array of voxel labels. A 2D image is treated as a single
        slice, one voxel thick along the third axis.
    voxel_size : float | Sequence[float], optional
        Edge length of a voxel. A scalar applies to all three axes; a 3-element
        sequence gives the length along x, y and z, by default ``(1.0, 1.0, 1.0)``.
    labels : int | Sequence[int] | np.ndarray, optional
        Label value(s) to include in the mesh, by default 1.
    per_label : bool, optional
        If ``False`` (default), all selected labels are meshed into a single surface.
        If ``True``, a separate mesh is built per label and a ``{label: Mesh}`` mapping
        is returned.
    merge : bool, optional
        If ``True`` (default), coplanar faces are fused into as few axis-aligned
        rectangles as possible, and every vertex that ends up inside one of them is
        dropped -- typically halving the face count of a tomographic surface and
        collapsing a flat wall to a single quad, at no cost in accuracy, since the merged
        faces cover exactly the same area (see :func:`merge_faces`). Set to ``False`` to
        keep one unit quad per voxel face, e.g. to carry per-voxel data on the faces.
    swap_axes : bool, optional
        If ``True``, swaps the first and third axes of ``img`` before meshing, leaving
        the second axis untouched, by default ``False``. This compensates for the
        axis-order mismatch between MATLAB's column-major and numpy's row-major array
        storage (see the corresponding ``swap_axes`` option of
        :meth:`porescene.model.PoreNetwork.from_mat`): a voxel image loaded straight
        from a ``.mat`` file has its first and third (spatial) axes swapped relative to
        the coordinate frame the file's own position variables (e.g. ``pos_p``) were
        written in. Enable this to build the mesh in that same, un-swapped coordinate
        frame, matching position data imported with ``swap_axes=False``.
    name : str, optional
        Name assigned to the resulting mesh. In ``per_label`` mode the label is appended
        as ``"{name}_{label}"``. By default ``"object"``.

    Returns
    -------
    Mesh | dict[int, Mesh]
        For a single mesh, a :class:`Mesh` whose ``vertices`` is an ``(N, 3)`` float
        array and ``faces`` an ``(M, 4)`` integer array of quad vertex indices -- unit
        squares, or larger rectangles where faces were merged. With ``per_label=True``, a
        ``{label: Mesh}`` dict.
    """
    img = np.asarray(img)
    if img.ndim == 2:
        img = img[:, :, np.newaxis]
    if img.ndim != 3:
        raise ValueError("img must be a 2D or 3D array")
    if swap_axes:
        img = img.transpose(2, 1, 0)

    size = np.asarray(voxel_size, dtype=float)
    if size.ndim == 0:
        size = np.repeat(size, 3)

    label_values = np.atleast_1d(labels)

    if per_label:
        return {
            int(label): Mesh(*_label2mesh(img == label, size, merge), f"{name}_{label}")
            for label in progress.track(
                label_values,
                description="Building meshes",
                console=Console(stderr=True),
            )
        }

    with _get_spinner(f"[green]Building mesh: {name}") as p:
        p.add_task("mesh", total=None)
        return Mesh(*_label2mesh(np.isin(img, label_values), size, merge), name)


def _label2mesh(
    mask: np.ndarray,
    voxel_size: np.ndarray,
    merge: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Builds the axis-aligned boundary quad mesh of a boolean voxel mask, optionally fusing
    the coplanar faces of every plane into maximal rectangles (see :func:`volume2mesh`).
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

        if merge:
            # every plane along `axis` is a grid of unit faces to be fused; `axis` holds
            # the plane index, the other two the in-plane cell, in ascending order
            plane, i_lo, i_hi, j_lo, j_hi = _merge_grid(np.moveaxis(boundary, axis, 0))
            faces_corners.append(_rectangles2corners(axis, plane, i_lo, i_hi, j_lo, j_hi))
            continue

        base = np.argwhere(boundary)
        faces_corners.append(base[:, np.newaxis, :] + _FACE_CORNERS[axis][np.newaxis])

    vertices = np.concatenate(faces_corners).reshape(-1, 3)
    vertices, inverse = np.unique(vertices, axis=0, return_inverse=True)
    faces = inverse.ravel().reshape(-1, 4)

    return vertices.astype(float) * voxel_size, faces


@overload
def merge_faces(mesh: Mesh) -> Mesh: ...
@overload
def merge_faces(mesh: Mapping[int, Mesh]) -> dict[int, Mesh]: ...
def merge_faces(mesh: Mesh | Mapping[int, Mesh]) -> Mesh | dict[int, Mesh]:
    """
    Merges the coplanar quads of a voxel mesh into as few large rectangles as possible.

    With ``merge=False``, :func:`volume2mesh` emits one unit quad per voxel face, so a
    flat patch of surface carries a dense grid of vertices although its shape is defined
    by its corners alone -- a flat ``100 x 100`` voxel wall costs 10,000 quads and 10,201
    vertices instead of one quad and four vertices. This function rebuilds the same
    surface from maximal axis-aligned rectangles: neighbouring quads lying in a common
    plane are fused, and every vertex that ends up inside a merged rectangle is dropped,
    together with any vertex left unreferenced. The remaining vertices are corners of at
    least one face.

    The surface itself is not approximated -- the merged faces cover exactly the same
    area as the original quads, so silhouette, volume and watertightness are preserved
    and the render is unchanged. Only the vertex and face count drop.

    :func:`volume2mesh` applies this by default, straight on the voxel grid, which is
    both faster and the recommended route. Reach for this function to merge a mesh that
    was built with ``merge=False``, or one assembled elsewhere.

    Rectangles are merged greedily, which is not always the decomposition with the
    fewest faces: a non-rectangular flat region (an L-shaped patch, say) is split into
    several rectangles, and where two of them meet, the vertices along the shared edge
    survive as corners of the smaller rectangle.

    Parameters
    ----------
    mesh : Mesh | Mapping[int, Mesh]
        Mesh of axis-aligned quads to simplify, as produced by :func:`volume2mesh`. Its
        ``faces`` must have shape ``(M, 4)`` and each face must be a rectangle
        perpendicular to one of the coordinate axes. Pass the ``{label: Mesh}`` mapping
        of :func:`volume2mesh(..., per_label=True) <volume2mesh>` to simplify every mesh
        in it. Face winding -- and with it the face normals -- is kept as
        :func:`volume2mesh` lays it out.

    Returns
    -------
    Mesh | dict[int, Mesh]
        A new :class:`Mesh` holding the merged surface under the input's ``name``; the
        input is left untouched. For a mapping, a ``{label: Mesh}`` dict with the same
        keys.

    Raises
    ------
    ValueError
        If ``faces`` is not an ``(M, 4)`` array, or if a face is not an axis-aligned
        rectangle.
    """
    if isinstance(mesh, Mapping):
        return {
            key: Mesh(*_merge_quads(item.vertices, item.faces), item.name)
            for key, item in progress.track(
                sorted(mesh.items()),
                description="Merging faces",
                console=Console(stderr=True),
            )
        }

    with _get_spinner(f"[green]Merging faces: {mesh.name}") as p:
        p.add_task("merge", total=None)
        return Mesh(*_merge_quads(mesh.vertices, mesh.faces), mesh.name)


def _merge_quads(
    vertices: np.ndarray,
    faces: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Fuses coplanar axis-aligned quads into maximal rectangles
    (see :func:`merge_faces`).
    """
    vertices = np.asarray(vertices, dtype=float)
    faces = np.asarray(faces)
    if faces.ndim != 2 or faces.shape[1] != 4:
        raise ValueError("faces must have shape (M, 4)")
    if faces.size == 0:
        return np.zeros((0, 3)), np.zeros((0, 4), dtype=int)

    corners = vertices[faces]  # (M, 4, 3)
    lower = corners.min(axis=1)
    upper = corners.max(axis=1)
    # a rectangle perpendicular to one axis has no extent along exactly that axis
    flat = lower == upper
    if not np.all(flat.sum(axis=1) == 1):
        raise ValueError("faces must be axis-aligned rectangles")
    normal = np.argmax(flat, axis=1)

    quads = []
    for axis in range(3):
        selection = np.flatnonzero(normal == axis)
        if selection.size == 0:
            continue
        # in-plane axes, in ascending order
        u, v = (a for a in range(3) if a != axis)
        # group the faces by the plane they sit in
        selection = selection[np.argsort(lower[selection, axis], kind="stable")]
        offsets = lower[selection, axis]
        splits = np.flatnonzero(offsets[1:] != offsets[:-1]) + 1

        for plane in np.split(selection, splits):
            bounds = _merge_rectangles(
                lower[plane, u], upper[plane, u], lower[plane, v], upper[plane, v]
            )
            quads.append(_rectangles2corners(axis, lower[plane[0], axis], *bounds))

    vertices = np.concatenate(quads).reshape(-1, 3)
    vertices, inverse = np.unique(vertices, axis=0, return_inverse=True)

    return vertices, inverse.ravel().reshape(-1, 4)


def _merge_rectangles(
    u_lo: np.ndarray,
    u_hi: np.ndarray,
    v_lo: np.ndarray,
    v_hi: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Fuses the axis-aligned rectangles of a single plane, given by their bounds along the
    two in-plane axes ``u`` and ``v``, into fewer and larger ones covering the same area.
    Returns the bounds of the merged rectangles.
    """
    # the rectangles tile a (generally non-uniform) lattice spanned by their own bounds,
    # which turns the plane into a boolean occupancy grid
    grid_u = np.unique(np.concatenate([u_lo, u_hi]))
    grid_v = np.unique(np.concatenate([v_lo, v_hi]))
    cell_u = np.searchsorted(grid_u, u_lo)
    cell_v = np.searchsorted(grid_v, v_lo)
    span_u = np.searchsorted(grid_u, u_hi)
    span_v = np.searchsorted(grid_v, v_hi)

    occupied = np.zeros((1, grid_u.size - 1, grid_v.size - 1), dtype=bool)
    # single-cell rectangles -- all of them, for a mesh straight out of `volume2mesh` --
    # are marked in one pass; larger ones fill their whole cell range
    single = (span_u == cell_u + 1) & (span_v == cell_v + 1)
    occupied[0, cell_u[single], cell_v[single]] = True
    for i_lo, i_hi, j_lo, j_hi in zip(
        cell_u[~single], span_u[~single], cell_v[~single], span_v[~single], strict=True
    ):
        occupied[0, i_lo:i_hi, j_lo:j_hi] = True

    _, i_lo, i_hi, j_lo, j_hi = _merge_grid(occupied)

    return grid_u[i_lo], grid_u[i_hi], grid_v[j_lo], grid_v[j_hi]


def _merge_grid(
    occupied: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Greedily fuses the occupied cells of a stack of boolean grids into maximal rectangles:
    runs of cells along the last axis are stacked wherever they cover the same columns in
    adjacent rows. Returns, per rectangle, the index of its grid within the stack and its
    half-open cell bounds ``[i_lo, i_hi)`` along the rows and ``[j_lo, j_hi)`` along the
    columns.
    """
    # padding by an empty column on either side turns every run of occupied cells into a
    # rising and a falling edge of the row
    padded = np.pad(occupied, ((0, 0), (0, 0), (1, 1)))
    change = padded[:, :, 1:] != padded[:, :, :-1]
    # both are ordered by grid, row and column, so the two halves of a run line up
    grids, rows, starts = np.nonzero(change & padded[:, :, 1:])
    ends = np.nonzero(change & padded[:, :, :-1])[2]

    # a rectangle is a stack of runs covering the same columns in adjacent rows
    order = np.lexsort((rows, ends, starts, grids))
    grids, rows, starts, ends = grids[order], rows[order], starts[order], ends[order]
    head = np.ones(rows.size, dtype=bool)
    head[1:] = (
        (grids[1:] != grids[:-1])
        | (starts[1:] != starts[:-1])
        | (ends[1:] != ends[:-1])
        | (rows[1:] != rows[:-1] + 1)
    )
    first = np.flatnonzero(head)
    last = np.append(first, rows.size)[1:] - 1

    return grids[first], rows[first], rows[last] + 1, starts[first], ends[first]


def _rectangles2corners(
    axis: int,
    offset: np.ndarray | float,
    u_lo: np.ndarray,
    u_hi: np.ndarray,
    v_lo: np.ndarray,
    v_hi: np.ndarray,
) -> np.ndarray:
    """
    Turns rectangles lying in a plane perpendicular to ``axis``, given by their position
    ``offset`` along it and their bounds along the two remaining axes ``u`` and ``v``,
    into an ``(K, 4, 3)`` array of corner coordinates.
    """
    u, v = (a for a in range(3) if a != axis)
    # keep the corner order of `_FACE_CORNERS`, so the face normals point the same way
    if axis == 0:
        order = ((u_lo, v_lo), (u_lo, v_hi), (u_hi, v_hi), (u_hi, v_lo))
    else:
        order = ((u_lo, v_lo), (u_hi, v_lo), (u_hi, v_hi), (u_lo, v_hi))

    corners = np.empty((len(u_lo), 4, 3), dtype=np.result_type(offset, u_lo, v_lo))
    corners[:, :, axis] = np.reshape(offset, (-1, 1))
    for corner, (pos_u, pos_v) in enumerate(order):
        corners[:, corner, u] = pos_u
        corners[:, corner, v] = pos_v

    return corners


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

    Uses :mod:`resvg_py` for the conversion, which ships as a self-contained wheel,
    so ``pip install`` pulls in everything and no external software is required.
    With ``crop=True`` the result is trimmed to its visible content by removing the
    surrounding transparent margin.

    Note that :mod:`resvg_py` only renders content inside the SVG viewport; anything
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
    pth_png.write_bytes(bytes(resvg_py.svg_to_bytes(svg_path=pth.as_posix())))

    if crop:
        with Image.open(pth_png) as img:
            img = img.convert("RGBA")
            bbox = img.getchannel("A").getbbox()
            if bbox is not None:
                img.crop(bbox).save(pth_png)

    return pth_png
