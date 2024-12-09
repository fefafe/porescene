"""
Colors and Color Gradients
--------------------------

"""

from typing import Self
from .conversion import hex2rgb, nrgb2lnrgb, nrgb2rgb, rgb2hex, rgb2nrgb


class Color:
    """
    Simple representation of a color.

    Parameters
    ----------
    hexstr
        HEX color string

    Examples
    ------------
    Suppose you have two :class:``Color`` instances, just mix them by literal
    addition operation ``+``:

    :example:
        >>> blue = Color('#00f')
        >>> red = Color('#f00')
        >>> purple = red + blue
        >>> print(purple)

    Be aware that all properties of the color, which includes `alpha`, will be
    mixed.
    """

    def __init__(self, h: str = "#000"):
        rgb = rgb2nrgb(*hex2rgb(h))
        if len(rgb) == 3:
            rgb += (1.0,)
        self.red = rgb[0]
        self.green = rgb[1]
        self.blue = rgb[2]
        self.alpha = rgb[3]

    def __add__(self, other) -> Self:
        """
        Creates a new color by mixing the current instance with another.
        """
        return self.mix(other)

    def __str__(self) -> str:
        return self.str_hex

    def __repr__(self) -> str:
        return f"Color('{self.str_hex}')"

    @classmethod
    def from_rgb(cls, r: int, g: int, b: int, a: float = 1.0) -> Self:
        ins = cls()
        rgb = rgb2nrgb(r, g, b)
        ins.red = rgb[0]
        ins.green = rgb[1]
        ins.blue = rgb[2]
        ins.alpha = a
        return ins

    @classmethod
    def from_nrgb(cls, nr: float, ng: float, nb: float, a: float = 1.0) -> Self:
        ins = cls()
        ins.red = nr
        ins.green = ng
        ins.blue = nb
        ins.alpha = a
        return ins

    def mix(self, other: Self, ratio: float = 0.5) -> Self:
        """
        Create a new color by mixing the current instance with others.

        Parameters
        ----------
        other
            The color to mix with.
        ratio
            The amount of color `other` to mix to the current instance.
        space
            The colorspace to use for mixing the colors. Mixing in RGB space
            is *subtractive*, while Lab is *additive*. Lab mixes more accurate
            but still does not reach real color mixing results.

        Returns
        -------
        A new instance of :class:``color``.

        ToDo
        ----
        * Implementation of real world color mixing like described by `MixBox`_.

        :: _MixBox: https://scrtwpns.com/mixbox.pdf
        """
        r = self.red * (1 - ratio) + other.red * ratio
        g = self.green * (1 - ratio) + other.green * ratio
        b = self.blue * (1 - ratio) + other.blue * ratio
        a = self.alpha * (1 - ratio) + other.alpha * ratio
        return Color.from_nrgb(r, g, b, a)

    @property
    def alpha(self) -> float:
        """
        Normalized value from interval [0, 1] of the transparent (A) color channel.
        """
        return self._alpha

    @alpha.setter
    def alpha(self, arg: float):
        self._alpha = arg

    @property
    def red(self) -> float:
        """
        Normalized value from interval [0, 1] of the red (R) color channel.
        """
        return self._red

    @red.setter
    def red(self, arg: float):
        self._red = arg

    @property
    def green(self) -> float:
        """
        Normalized value from interval [0, 1] of the green (G) color channel.
        """
        return self._green

    @green.setter
    def green(self, arg: float):
        self._green = arg

    @property
    def blue(self) -> float:
        """
        Normalized value from interval [0, 1] of the blue (B) color channel.
        """
        return self._blue

    @blue.setter
    def blue(self, arg: float):
        self._blue = arg

    @property
    def hex(self) -> str:
        """HEX `str` without hash."""
        return rgb2hex(*nrgb2rgb(self.red, self.green, self.blue))[1:]

    @property
    def hexa(self) -> str:
        """HEXA `str` without hash."""
        return rgb2hex(*nrgb2rgb(self.red, self.green, self.blue, self.alpha))[1:]

    @property
    def lnrgb(self) -> tuple[float, float, float]:
        """
        Returns current color in normalized values fom linear RGB color space.
        """
        return nrgb2lnrgb(*self.nrgb)

    @property
    def lnrgb_str(self) -> str:
        return f"lnrgb({self.nrgb[0]}, {self.nrgb[1]}, {self.nrgb[2]})"

    @property
    def lnrgba(self) -> tuple[float, float, float, float]:
        return nrgb2lnrgb(*self.nrgba)

    @property
    def lnrgba_str(self) -> str:
        return f"lnrgba({self.lnrgba[0]}, {self.lnrgba[1]}, {self.lnrgba[2]}, {self.lnrgba[3]})"

    @property
    def nrgb(self) -> tuple[float, float, float]:
        """
        Returns current color in normlized values (interval [0, 1]) from sRGB
        color space.
        """
        return (self.red, self.green, self.blue)

    @property
    def nrgba(self) -> tuple[float, float, float, float]:
        """
        Returns current color in normlized values (interval [0, 1]) from sRGBA color
        space.
        """
        return (self.red, self.green, self.blue, self.alpha)

    @property
    def rgb(self) -> tuple[int, int, int]:
        """
        Returns current color in values (interval [0, 255]) from sRGB color space.
        """
        return nrgb2rgb(*self.nrgb)

    @property
    def rgba(self) -> tuple[int, int, int, float]:
        return nrgb2rgb(*self.nrgba)

    @property
    def str_hex(self) -> str:
        """HEX `str` with hash."""
        return rgb2hex(*nrgb2rgb(*self.rgb)).upper()

    @property
    def str_hexa(self) -> str:
        """HEXA `str` with hash."""
        return f"#{self.hexa}"

    @property
    def str_rgb(self) -> str:
        """
        Current color formatted as `rgb(R, G, B)`.
        """
        return f"rgb({self.rgb[0]}, {self.rgb[1]}, {self.rgb[2]})"

    @property
    def str_rgba(self) -> str:
        """
        Current color formatted as `rgb(R, G, B, A)`.
        """
        return (
            f"rgba({self.rgba[0]}, {self.rgba[1]}, " f"{self.rgba[2]}, {self.rgba[3]})"
        )
