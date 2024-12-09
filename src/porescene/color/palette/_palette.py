from random import choice
from typing import Self
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
            colors.append(choice(self.colors))
        return colors
