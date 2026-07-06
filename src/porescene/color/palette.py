import random
import re
from pathlib import Path
from typing import Self

import numpy as np

from porescene.color import Color


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
    def load(cls, name: str) -> Self:

        colorlist: list[Color] = []

        pattern = re.compile("^[a-z0-9]+$")

        if not pattern.match(name):
            raise Exception("Specified colormap is not available")

        pth = Path("./src/porescene/data/colormap/" + name + ".txt")

        colors = np.fromfile(pth, sep=" ").reshape((256, 3))

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

    def random(self, n: int = 1) -> list[Color]:
        """
        Returns :arg:`n` randomly selected color from the palette.
        """
        colors = []
        for k in range(n):
            colors.append(random.choice(self.colors))
        return colors
