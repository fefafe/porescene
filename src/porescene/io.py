# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Felix Faber /
# Otto von Guericke University Magdeburg, Thermal Process Engineering

"""
Reading and writing of mesh and geometry files.
===============================================
"""

from pathlib import Path

import numpy as np

from porescene.utility import Mesh


def mesh2obj(pth_obj: Path, mesh: Mesh) -> Path:
    """
    Writes a mesh to a Wavefront ``.obj`` file in text format.

    Parameters
    ----------
    pth_obj : Path
        Output path of the OBJ file.
    mesh : Mesh
        The mesh to write. Its faces hold **0-based** vertex indices (e.g. from
        :func:`volume2mesh() <porescene.utility.volume2mesh>`); OBJ indices are 1-based, so
        the values are offset by one on write. The mesh ``name`` becomes the ``o`` record.

    Returns
    -------
    Path
        File path of the written OBJ file.
    """
    vertices = mesh.vertices
    faces = mesh.faces

    if vertices.ndim != 2 or vertices.shape[1] != 3:
        raise ValueError("vertices must have shape (N, 3)")
    if faces.ndim != 2:
        raise ValueError("faces must have shape (M, K)")

    fmt_faces = "f " + " ".join(["%d"] * faces.shape[1])
    fmt_vertices = "v %.10g %.10g %.10g"

    with pth_obj.open("w", encoding="utf-8", newline="\n") as file:
        file.write("# Written by PoreScene\n")
        file.write(f"o {mesh.name}\n")
        np.savetxt(file, vertices, fmt=fmt_vertices)
        np.savetxt(file, faces + 1, fmt=fmt_faces)

    return pth_obj


def mesh2ply(pth_ply: Path, mesh: Mesh, binary: bool = True) -> Path:
    """
    Writes a mesh to a Stanford ``.ply`` file.

    Parameters
    ----------
    pth_ply : Path
        Output path of the PLY file.
    mesh : Mesh
        The mesh to write. Its faces hold **0-based** vertex indices (e.g. from
        :func:`porescene.utility.volume2mesh`); PLY indices are 0-based too, so they are
        written unchanged. The mesh ``name`` is written as a PLY comment.
    binary : bool, optional
        If ``True`` (default), the vertex and face data are written as packed
        little-endian binary -- far smaller and faster to load than the ``ascii``
        variant produced when ``False``. Defaults to ``True``.

    Returns
    -------
    Path
        File path of the written PLY file.
    """
    vertices = mesh.vertices
    faces = mesh.faces

    if vertices.ndim != 2 or vertices.shape[1] != 3:
        raise ValueError("vertices must have shape (N, 3)")
    if faces.ndim != 2:
        raise ValueError("faces must have shape (M, K)")

    n_corners = faces.shape[1]
    header = "\n".join(
        [
            "ply",
            f"format {'binary_little_endian' if binary else 'ascii'} 1.0",
            "comment Written by PoreScene",
            f"comment name {mesh.name}",
            f"element vertex {len(vertices)}",
            "property float x",
            "property float y",
            "property float z",
            f"element face {len(faces)}",
            "property list uchar int vertex_indices",
            "end_header",
            "",
        ]
    )

    if binary:
        face_dtype = np.dtype([("count", "u1"), ("indices", "<i4", (n_corners,))])
        faces_bin = np.empty(len(faces), dtype=face_dtype)
        faces_bin["count"] = n_corners
        faces_bin["indices"] = faces
        with pth_ply.open("wb") as file:
            file.write(header.encode("ascii"))
            file.write(np.ascontiguousarray(vertices, dtype="<f4").tobytes())
            file.write(faces_bin.tobytes())
    else:
        faces_ascii = np.hstack([np.full((len(faces), 1), n_corners, dtype=int), faces])
        with pth_ply.open("w", encoding="utf-8", newline="\n") as file:
            file.write(header)
            np.savetxt(file, vertices, fmt="%.10g %.10g %.10g")
            np.savetxt(file, faces_ascii, fmt="%d")

    return pth_ply
