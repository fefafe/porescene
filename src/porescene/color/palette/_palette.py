# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Felix Faber /
# Otto von Guericke University Magdeburg, Thermal Process Engineering

import random
import re
from enum import Enum
from importlib import resources
from typing import Self

import numpy as np

import porescene.utility as util
from porescene.color import Color


class Colormap(Enum):
    """
    All colormaps bundled with :mod:`porescene`.

    Each member's value is the file name (without extension) of the
    corresponding colormap in ``porescene/data/colormap`` and can be passed
    to :meth:`Palette.load`. The collection comprises

    - `Fabio Crameri's scientific colour maps
      <https://www.fabiocrameri.ch/colourmaps/>`_,
    - `cmocean <https://matplotlib.org/cmocean/>`_,
    - `colorcet <https://colorcet.holoviz.org/>`_,
    - `ColorBrewer <https://colorbrewer2.org/>`_, and
    - a selection of :mod:`matplotlib` colormaps.

    See ``porescene/data/colormap/README.txt`` for the per-collection
    provenance and licenses.
    """

    ACTON = "acton"
    ACTONS = "actonS"
    BAM = "bam"
    BAMO = "bamO"
    BAMAKO = "bamako"
    BAMAKOS = "bamakoS"
    BATLOW = "batlow"
    BATLOWK = "batlowK"
    BATLOWKS = "batlowKS"
    BATLOWS = "batlowS"
    BATLOWW = "batlowW"
    BATLOWWS = "batlowWS"
    BERLIN = "berlin"
    BILBAO = "bilbao"
    BILBAOS = "bilbaoS"
    BROC = "broc"
    BROCO = "brocO"
    BUDA = "buda"
    BUDAS = "budaS"
    BUKAVU = "bukavu"
    CIVIDIS = "cividis"
    CORK = "cork"
    CORKO = "corkO"
    CUBEHELIX = "cubehelix"
    DAVOS = "davos"
    DAVOSS = "davosS"
    DEVON = "devon"
    DEVONS = "devonS"
    EMBER = "ember"
    FES = "fes"
    GLASGOW = "glasgow"
    GLASGOWS = "glasgowS"
    GRAYC = "grayC"
    GRAYCS = "grayCS"
    HAWAII = "hawaii"
    HAWAIIS = "hawaiiS"
    IMOLA = "imola"
    IMOLAS = "imolaS"
    INFERNO = "inferno"
    LAJOLLA = "lajolla"
    LAJOLLAS = "lajollaS"
    LAPAZ = "lapaz"
    LAPAZS = "lapazS"
    LIPARI = "lipari"
    LIPARIS = "lipariS"
    LISBON = "lisbon"
    MAGMA = "magma"
    MANAGUA = "managua"
    NAVIA = "navia"
    NAVIAS = "naviaS"
    NUUK = "nuuk"
    NUUKS = "nuukS"
    OLERON = "oleron"
    OSLO = "oslo"
    OSLOS = "osloS"
    PLASMA = "plasma"
    ROMA = "roma"
    ROMAO = "romaO"
    SET1 = "Set1"
    SET2 = "Set2"
    SET3 = "Set3"
    TAB10 = "tab10"
    TOFINO = "tofino"
    TOKYO = "tokyo"
    TOKYOS = "tokyoS"
    TURBO = "turbo"
    TURKU = "turku"
    TURKUS = "turkuS"
    TWILIGHT = "twilight"
    VANIMO = "vanimo"
    VIK = "vik"
    VIKO = "vikO"
    VIRIDIS = "viridis"

    # cmocean maps (Kristen M. Thyng) -- https://matplotlib.org/cmocean/
    ALGAE = "algae"
    AMP = "amp"
    BALANCE = "balance"
    CURL = "curl"
    DEEP = "deep"
    DELTA = "delta"
    DENSE = "dense"
    DIFF = "diff"
    GRAY = "gray"
    HALINE = "haline"
    ICE = "ice"
    MATTER = "matter"
    OXY = "oxy"
    PHASE = "phase"
    RAIN = "rain"
    SOLAR = "solar"
    SPEED = "speed"
    TARN = "tarn"
    TEMPO = "tempo"
    THERMAL = "thermal"
    TOPO = "topo"
    TURBID = "turbid"

    # Additional ColorBrewer maps (Cynthia A. Brewer) -- see Set1/2/3 above
    ACCENT = "Accent"
    BLUES = "Blues"
    BRBG = "BrBG"
    BUGN = "BuGn"
    BUPU = "BuPu"
    DARK2 = "Dark2"
    GNBU = "GnBu"
    GREENS = "Greens"
    GREYS = "Greys"
    ORANGES = "Oranges"
    ORRD = "OrRd"
    PAIRED = "Paired"
    PASTEL1 = "Pastel1"
    PASTEL2 = "Pastel2"
    PIYG = "PiYG"
    PRGN = "PRGn"
    PUBU = "PuBu"
    PUBUGN = "PuBuGn"
    PUOR = "PuOr"
    PURD = "PuRd"
    PURPLES = "Purples"
    RDBU = "RdBu"
    RDGY = "RdGy"
    RDPU = "RdPu"
    RDYLBU = "RdYlBu"
    RDYLGN = "RdYlGn"
    REDS = "Reds"
    SPECTRAL = "Spectral"
    YLGN = "YlGn"
    YLGNBU = "YlGnBu"
    YLORBR = "YlOrBr"
    YLORRD = "YlOrRd"

    # colorcet perceptually uniform maps (Peter Kovesi) -- https://colorcet.holoviz.org/
    BGY = "bgy"
    BGYW = "bgyw"
    BJY = "bjy"
    BKR = "bkr"
    BKY = "bky"
    BMW = "bmw"
    BMY = "bmy"
    BWY = "bwy"
    COLORWHEEL = "colorwheel"
    COOLWARM = "coolwarm"
    CWR = "cwr"
    DIMGRAY = "dimgray"
    FIRE = "fire"
    GOULDIAN = "gouldian"
    GWV = "gwv"
    ISOLUM = "isolum"
    KB = "kb"
    KBC = "kbc"
    KBGYW = "kbgyw"
    KG = "kg"
    KGY = "kgy"
    KR = "kr"
    RAINBOW = "rainbow"
    RAINBOW4 = "rainbow4"


class Palette:
    """
    A basic wrapper for a collection of selected colors.
    """

    def __init__(self, colors: list[Color]) -> None:
        self.colors = colors

    def __iter__(self) -> Self:
        self.__i = 0
        return self

    def __len__(self) -> int:
        return len(self.colors)

    def __next__(self) -> Color:
        if self.__i < len(self.colors) and self.__i >= 0:
            color = self.colors[self.__i]
            self.__i += 1
            return color
        else:
            raise StopIteration

    @classmethod
    def load(cls, name: str | Colormap) -> Self:
        """
        Creates a :class:`Palette` instance by loading colormap data from file.

        :mod:`porescene` includes a large set of scientific colormaps, including:

        - `Fabio Crameri's collection <https://www.fabiocrameri.ch/colourmaps/>`_
        - :mod:`matplotlib` colormaps

        Parameters
        ----------
        name : str | Colormap
            Colormap to be loaded from file, either as a :class:`Colormap`
            member or the corresponding colormap name.
        """
        colorlist: list[Color] = []

        if isinstance(name, Colormap):
            name = name.value

        pattern = re.compile("^[a-zA-Z0-9]+$")

        if not pattern.match(name):
            raise Exception("Specified colormap is not available")

        ref = resources.files("porescene").joinpath("data/colormap/" + name + ".txt")

        with resources.as_file(ref) as pth:

            colors = np.fromfile(pth, sep=" ").reshape((-1, 3))

            for color in colors:
                colorlist.append(Color.from_nrgb(*color))

            ins = cls(colorlist)

        return ins

    def all(self) -> list[Color]:
        """
        Returns the full color palette.
        """
        return self.colors

    def first(self) -> Color:
        """
        Returns the first color of the palette.
        """
        return self.colors[0]

    def last(self) -> Color:
        """
        Returns the last color of the palette.
        """
        return self.colors[-1]

    def subset(self, n: int = 5) -> list[Color]:
        """
        Returns a subset of ``n`` equidistant sampled colors from the palette.

        Parameters
        ----------
        n : int, optional
            Number of colors in the subset, by default 5
        """
        return util.n_equidistant(self.colors, n)

    def random(self, n: int = 1) -> list[Color]:
        """
        Returns randomly selected colors from the palette.

        Parameters
        ----------
        n : int, optional
            Number of colors to return, by default 1
        """
        colors = []
        for k in range(n):
            colors.append(random.choice(self.colors))
        return colors

    def reversed(self) -> list[Color]:
        """
        Returns the colors from the palette in reversed order.
        """
        return list(reversed(self.colors))
