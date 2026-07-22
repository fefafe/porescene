# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Felix Faber /
# Otto von Guericke University Magdeburg, Thermal Process Engineering
"""Blender-based Python toolkit for reproducible, publication-quality 3D
visualization of porous media -- tomographic images, pore networks, and
tessellations."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("porescene")
except PackageNotFoundError:
    __version__ = "0.0.0.dev0"
