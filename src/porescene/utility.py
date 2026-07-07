import contextlib
import os
import subprocess
from enum import Enum
from math import ceil, floor, isclose
from pathlib import Path
from typing import Callable, Iterator

import numpy as np


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


def svg2png(pth: Path):
    """
    Convert a SVG file to PNG with Inkscape.

    Make sure that Inkscape is installed and accessible via PATH.

    Parameters
    ----------
    pth
        Path to the file to be converted.
    """
    subprocess.call(
        [
            "inkscape",
            "--export-type=png,svg,pdf",
            "--export-area-drawing",
            "--export-overwrite",
            str(pth),
        ]
    )
