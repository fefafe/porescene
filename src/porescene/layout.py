import abc
from pathlib import Path
from random import getrandbits
from typing import Self

import numpy as np
from porescene.color import Color
from porescene.color.gradient import SmoothGradient
from porescene.utility import CompassDirection, MultiplicationSymbol, Orientation


class Overlay(abc.ABC):
    pass


class BackgroundOverlay(Overlay):
    """
    Base class for different types of layouts.

    You can use this class to create a plain unicolored image without anything
    else. It is also possible to add an bitmap image like PNG to the center.

    Parameters
    ----------
    res
        Size of the image in pixels. The first entry specifies width, second
        height.
    pad
        The padding of the image. Does not apply to the background color.

    Examples
    --------

    This example creates the most simply overlay: just a simple colored image.

    .. code-block::
        :linenos:
        :caption: Create a simple colored image.

        from collib import Color

        res = (1600, 900)
        fpath = Path("unicolor_image.svg")
        ovl = BackgroundOverlay(res)
        ovl.background = Color("#382655")
        ovl.save(fpath)

    """

    _xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'

    __slots__ = ("_background", "_image", "_padding", "_resolution")

    def __init__(
        self,
        pth: Path,
        res: tuple[int, int] = (3000, 2000),
        pad: tuple[int, int, int, int] = (100, 100, 100, 100),
        bg: Color = Color("#FFF"),
    ):
        self.path = pth
        self.resolution = res
        self.padding = pad
        self.color_background = bg

    def get_svg(self) -> str:
        """
        Returns the SVG element without XML declaration.

        Get the <svg> element with all its childen elements.
        """

        svg = self._get_tag_svg_open()
        svg += self._build()
        svg += "</svg>"
        return svg

    def save(self) -> Self:
        """
        Saves the SVG image as file with specified filename.
        """
        with self.path.open(mode="w+", encoding="utf-8") as file:
            file.write(self._xml_declaration)
            file.write(self.get_svg())
        return self

    def _build(self) -> str:
        svg = ""
        if self.color_background:
            svg += self._get_tag_background()
        return svg

    def _get_tag_background(self):
        return ""
        return (
            f'<rect id="background" x="0" y="0" width="100%" '
            f'height="100%" fill="{self.color_background.str_rgba}"/>'
        )

    def _get_tag_svg_open(self):
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="'
            f'http://www.w3.org/1999/xlink" width="100%" height="100%" '
            f'viewBox="0 0 {self.resolution[0]} {self.resolution[1]} " '
            f'font-weight="400" font-variant-numeric="tabular-nums">'
        )

    @property
    def color_background(self) -> Color:
        """
        Image background color as :class:`Color` object or `None` for
        transparent background.
        """
        return self._background

    @color_background.setter
    def color_background(self, arg: Color):
        self._background = arg

    @property
    def padding(self) -> tuple[int, int, int, int]:
        """
        Padding of the image contained in a 4-element `tuple` of
        `int` in following order: top, right, bottom, left.

        The padding does not apply to the background color.
        """

        return self._padding

    @padding.setter
    def padding(self, arg: tuple[int, int, int, int]):
        """
        Padding of the image, i.e. the width of the outer blank space of the image.

        Padding must always grater than zero.
        """
        if not all([x > 0 for x in arg]):
            raise ValueError(f"{__name__}.padding must be positive")
        self._padding = arg

    @property
    def resolution(self) -> tuple[int, int]:
        """
        Resolution of the SVG file denoted as 2-element `tuple` containing
        width ad height.
        """
        return self._resolution

    @resolution.setter
    def resolution(self, arg: tuple[int, int]):
        if arg[0] < 1 or arg[1] < 1:
            raise ValueError(f"{__name__}.resolution must be greater than zero")
        self._resolution = arg


class TitleOverlay(BackgroundOverlay):
    """
    Create a overlay image with heading, subheading an some lines of text.

    Parameters
    ----------
    res
        Size of the image in pixels. The first entry specifies width, second
        height.

    Examples
    --------
    >>> from fefacolors import gray, red, light3
    >>> ovl = TitleOverlay()
    >>> ovl.heading = "My super topic!"
    >>> ovl.subheading = "Maybe its only interesting for me, not for you?"
    >>> ovl.text = [
            "I do not know what to write here.",
            "It's only a few lines",
            "of text nobody cares."]
    >>> ovl.color_text = gray
    >>> ovl.color_heading = red
    >>> ovl.background = light3
    >>> ovl.align = 'SE'
    >>> ovl.save('mytitle')
    *Look for the save file!*

    """

    __slots__ = [
        "_align",
        "_color_heading",
        "_color_subheading",
        "_color_text",
        "_font_family",
        "_font_size_heading",
        "_font_size_subheading",
        "_font_size_text",
        "_heading",
        "_line_height",
        "_spacing",
        "_subheading",
        "_text",
        "_x",
        "_y",
    ]

    def __init__(
        self,
        pth: Path,
        res: tuple[int, int] = (3000, 2000),
        pad: tuple[int, int, int, int] = (100, 100, 100, 100),
    ):
        super().__init__(pth, res, pad)
        self.align = CompassDirection.NORTH
        self.color_heading = Color("#000")
        self.color_subheading = Color("#000")
        self.color_text = Color("#000")
        self.font_family = "Inter, Arial, Helvetica Neue, Helvetica, sans-serif"
        self.font_size_heading = 150
        self.font_size_subheading = 100
        self.font_size_text = 55
        self.heading = None
        self.line_height = 1.15
        self.spacing = 50
        self.subheading = None
        self.text = []

    def _build(self) -> str:
        (
            self._x,
            self._y,
            sign_x,
            sign_y,
            anchor,
            baseline,
        ) = self._get_alignment_config()
        svg = super()._build()
        if self.heading:
            svg += self._get_tag_heading(anchor, baseline)
            self._y += self.font_size_heading * self._line_height * sign_y
        if self.subheading:
            svg += self._get_tag_subheading(anchor, baseline)
            self._y += self.font_size_subheading * self._line_height * sign_y
        if self.text:
            svg += self._get_tag_text(sign_y, anchor, baseline)
        return svg

    def _get_tag_heading(self, a, b):
        return (
            f'<text id="title" x="{self._x}" y="{self._y}" dominant-baseline="{b}" '
            f'text-anchor="{a}" fill="{self.color_heading.str_hex}" font-weight="400" '
            f'font-family="{self.font_family}" font-size="{self.font_size_heading}">'
            f"{self.heading}</text>"
        )

    def _get_tag_subheading(self, a, b):
        return (
            f'<text id="title" x="{self._x}" y="{self._y}" dominant-baseline="{b}" '
            f'text-anchor="{a}" fill="{self.color_subheading.str_hex}" '
            f'font-variant-numeric="oldstyle-nums proportional-nums" '
            f'font-weight="500" font-family="{self.font_family}" '
            f'font-size="{self.font_size_subheading}">{self.subheading}</text>'
        )

    def _get_tag_text(self, sign_y, a, b):
        text = reversed(self.text) if sign_y == -1 else self.text
        tag = ""
        y = self._y
        for i, line in enumerate(text):
            tag += (
                f'<text id="text-line-{i}" x="{self._x}" y="{y}" '
                f'dominant-baseline="{b}" text-anchor="{a}" '
                f'fill="{self.color_text.str_hex}" font-weight="400" '
                f'font-family="{self.font_family}" font-size="{self.font_size_text}">'
                f"{line}</text>"
            )
            y += self.font_size_text * self._line_height * sign_y
            self._y = y
        return tag

    def _get_alignment_config(self):
        match self.align:
            case CompassDirection.SOUTHWEST:
                x = self.padding[3]
                y = self.resolution[1] - self.padding[2]
                sign_x = 1
                sign_y = -1
                anchor = "start"
                baseline = "auto"
            case CompassDirection.SOUTH:
                x = (
                    self.padding[3]
                    + (self.resolution[0] - self.padding[1] - self.padding[3]) / 2
                )
                y = self.resolution[1] - self.padding[2]
                sign_x = 1
                sign_y = -1
                anchor = "middle"
                baseline = "auto"
            case CompassDirection.SOUTHEAST:
                x = self.resolution[0] - self.padding[1]
                y = self.resolution[1] - self.padding[2]
                sign_x = -1
                sign_y = -1
                anchor = "end"
                baseline = "auto"
            case CompassDirection.NORTHWEST:
                x = self.padding[3]
                y = self.padding[0]
                sign_x = 1
                sign_y = 1
                anchor = "start"
                baseline = "hanging"
            case CompassDirection.NORTH:
                x = (
                    self.padding[3]
                    + (self.resolution[0] - self.padding[1] - self.padding[3]) / 2
                )
                y = self.padding[0]
                sign_x = 1
                sign_y = 1
                anchor = "middle"
                baseline = "hanging"
            case CompassDirection.NORTHEAST:
                x = self.resolution[0] - self.padding[1]
                y = self.padding[0]
                sign_x = -1
                sign_y = 1
                anchor = "end"
                baseline = "hanging"
        return x, y, sign_x, sign_y, anchor, baseline

    @property
    def font_family(self) -> str:
        """
        Font family used for headings and text.
        """
        return self._font_family

    @font_family.setter
    def font_family(self, arg: str):
        self._font_family = arg

    @property
    def font_size_heading(self) -> float:
        """
        Font size of the heading.
        """
        return self._font_size_heading

    @font_size_heading.setter
    def font_size_heading(self, arg: float):
        self._font_size_heading = arg

    @property
    def font_size_subheading(self) -> float:
        """
        Font size of the subheading.
        """
        return self._font_size_subheading

    @font_size_subheading.setter
    def font_size_subheading(self, arg: float):
        self._font_size_subheading = arg

    @property
    def font_size_text(self) -> float:
        """
        Font size of the text.
        """
        return self._font_size_text

    @font_size_text.setter
    def font_size_text(self, arg: float):
        self._font_size_text = arg

    @property
    def heading(self) -> str | None:
        """
        Headline of the image.

        The text is displayed in bold typeface in a single line.
        It should not be too long.
        """

        return self._heading

    @heading.setter
    def heading(self, arg: str | None):
        self._heading = arg

    @property
    def line_height(self) -> float:
        """Line height of texts"""
        return self._line_height

    @line_height.setter
    def line_height(self, arg: float):
        self._line_height = arg

    @property
    def align(self) -> CompassDirection:
        """
        Location to place the text on the image.

        There are 4 available options to choose: 'NW', 'NE', 'SE', 'SW' (like the
        direction of compass). The default align is 'NW'.
        """
        return self._align

    @align.setter
    def align(self, arg: CompassDirection):
        self._align = arg

    @property
    def subheading(self) -> str | None:
        """
        Second headline of the image.

        The text is displayed in bold typeface but smaller font-size a heading in a
        single line.
        It should not be too long. You can minimize the property `font_size_subheading`
        to fit more word in the line.
        """

        return self._subheading

    @subheading.setter
    def subheading(self, arg: str | None):
        if not isinstance(arg, str) and arg is not None:
            raise TypeError(f"{__name__}.subheading expected 'str' or 'None'")
        self._subheading = arg

    @property
    def text(self) -> list[str]:
        """
        Multiline text on the image.

        Since linebreaks are not inserted automatically by SVG, a list of
        strings each representing a line is required.
        """
        return self._text

    @text.setter
    def text(self, arg: list[str]):
        self._text = arg

    @property
    def color_heading(self) -> Color:
        """
        Color of the heading as :class:`Color`.
        """
        return self._color_heading

    @color_heading.setter
    def color_heading(self, arg: Color):
        self._color_heading = arg

    @property
    def color_subheading(self) -> Color:
        """
        Color of the subheading as :class:`Color` object.
        """
        return self._color_subheading

    @color_subheading.setter
    def color_subheading(self, arg: Color):
        self._color_subheading = arg

    @property
    def color_text(self) -> Color:
        """
        Color of the text as :class:`Color` object.
        """
        return self._color_text

    @color_text.setter
    def color_text(self, arg: Color):
        self._color_text = arg

    @property
    def spacing(self) -> float:
        """
        Space between elements.
        """
        return self._spacing

    @spacing.setter
    def spacing(self, arg: float):
        self._spacing = arg


class Gradient(TitleOverlay, abc.ABC):
    """
    Create an overlay image with heading, subheading, text and a gradient
    with scaclebars.

    Parameters
    ----------
    project
        Directory of the current project. All other specified filepath are
        relative to this directory.
    res
        Size of the image in pixels. The first entry specifies width, second
        height.

    Examples
    --------
    >>> ovl = Gradient('myproject')
    >>> ovl.heading = 'My beautiful work:'
    >>> ovl.subheading = 'You can see a '
    >>>

    """

    __slots__ = [
        "_color_ticks",
        "_color_nan",
        "_exponent",
        "_font_size_ticks",
        "_gradient_colors",
        "_gradient_height",
        "_gradient_length",
        "_line_width",
        "_orientation",
        "_roundness",
        "_seperator_exponent",
        "_seperator_decimal",
        "_text_nan",
        "_tick_length",
        "_ticks",
    ]

    def __init__(
        self,
        pth: Path,
        res: tuple[int, int] = (3000, 2000),
        pad: tuple[int, int, int, int] = (100, 100, 100, 100),
    ):
        super().__init__(pth, res, pad)
        self.color_ticks = Color("#000")
        self.color_nan = None
        self.font_size_ticks = 100
        self.exponent = None
        self.gradient_colors = []
        self.gradient_height = 120
        self.gradient_length = 2000
        self.line_width = 12
        self.orientation = Orientation.VERTICAL
        self.roundness = 10
        self.seperator_exponent = MultiplicationSymbol.CROSS
        self.seperator_decimal = "DOT"
        self.text_nan = "NaN"
        self.tick_length = 50
        self.ticks = []

    def _build(self):
        x, y, sign_x, sign_y, anchor, baseline = self._get_alignment_config()
        self._x = x
        self._y = y
        svg, h = self._get_tag_defs()
        svg += super()._build()
        if any([self.text, self.heading, self.subheading]):
            self._y += self.spacing * sign_y
        svg += "<g>"
        if self.gradient_colors:
            svg += self._get_tag_gradient(self._x, self._y, h)
            if self.orientation is Orientation.VERTICAL:
                self._x += (self.gradient_height + self.spacing) * sign_x
            if self.orientation is Orientation.HORIZONTAL:
                self._y += (self.gradient_height + self.spacing) * sign_y
        if self.ticks:
            svg += self._get_tag_axis(self._x, self._y, sign_x, sign_y)
            svg += self._get_tag_ticks(self._x, self._y, sign_x, sign_y)
            if self.orientation is Orientation.VERTICAL:
                self._x += (
                    self.tick_length
                    + self.spacing * 3
                    + 29 * (sum(c.isdigit() for c in str(self.ticks[-1])))
                ) * sign_x
                if "." in str(self.ticks[-1]):
                    self._x += 15 * sign_x
                if "N" in self.align.value:
                    self._y += self.gradient_length
            if self.orientation is Orientation.HORIZONTAL:
                self._x += (self.gradient_length + self.spacing * 3) * sign_x
                self._y += (self.tick_length + self.spacing) * sign_y
            if self.exponent:
                svg += self._get_tag_exponent()
            if self.orientation is Orientation.VERTICAL:
                self._x = x
                if "E" in self.align.value:
                    self._x -= self.gradient_height
                self._y += self.spacing * sign_y
                if "S" in self.align.value:
                    self._y -= self.gradient_length + self.gradient_height
            if self.orientation is Orientation.HORIZONTAL:
                self._x = x
                if "E" in self.align.value:
                    self._x -= self.gradient_height
                self._y += self.spacing * sign_y
                if "N" in self.align.value:
                    self._y += self.font_size_ticks * 0.5 + self.spacing
                if "S" in self.align.value:
                    self._y -= (
                        self.font_size_ticks * 0.5 + self.tick_length + 2 * self.spacing
                    )
                    if "E" in self.align.value:
                        self._y += self.tick_length * 0.5 + self.spacing
        if self.color_nan:
            svg += self._get_tag_nan(sign_x, sign_y)
        svg += "</g>"
        return svg

    @abc.abstractmethod
    def _get_tag_defs(self):
        """<defs>"""

    # @abc.abstractmethod
    # def _get_tag_gradient(self, x, y):
    #     """<rect />"""

    def _get_tag_axis(self, x, y, sign_x, sign_y):
        if self.orientation is Orientation.HORIZONTAL:
            y1 = y2 = y
            x1 = x + (self.line_width / 2) * sign_x
            x2 = x + (self.gradient_length - self.line_width / 2) * sign_x
            if (
                self.align is CompassDirection.NORTH
                or self.align is CompassDirection.SOUTH
            ):
                x1 -= self.gradient_length / 2
                x2 -= self.gradient_length / 2
        else:
            y1 = y + (self.line_width / 2) * sign_y
            y2 = y + (self.gradient_length - self.line_width / 2) * sign_y
            x1 = x2 = x
        return (
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke-linecap="round" '
            f'stroke="{self.color_ticks.str_hex}" stroke-width="{self.line_width}">'
            f"</line>"
        )

    def _get_tag_ticks(self, x, y, sign_x, sign_y):
        svg = ""
        w = (
            self.gradient_length
            if self.orientation is Orientation.HORIZONTAL
            else self.gradient_height
        )
        h = (
            self.gradient_length
            if self.orientation is Orientation.VERTICAL
            else self.gradient_height
        )
        step = self.gradient_length / (len(self.ticks) - 1)
        if "E" in self.align.value and self.orientation is Orientation.HORIZONTAL:
            x -= w
        if "S" in self.align.value and self.orientation is Orientation.VERTICAL:
            y -= h
        if self.align is CompassDirection.NORTH or self.align is CompassDirection.SOUTH:
            x -= w / 2
        for i, tick in enumerate(self.ticks):
            if self.seperator_decimal == "COMMA":
                tick = str(tick).replace(".", ",")
            transform = ""
            a = (
                "middle"
                if self.orientation is Orientation.HORIZONTAL
                else ("start" if "W" in self.align.value else "end")
            )
            b = (
                "middle"
                if self.orientation is Orientation.VERTICAL
                else ("hanging" if "N" in self.align.value else "auto")
            )
            if self.orientation is Orientation.HORIZONTAL:
                x1 = x2 = x_tick = x
                y1 = y2 = y
                y2 += self.tick_length * sign_y
                y_tick = y2 + self.spacing * sign_y
            else:
                y1 = y2 = y_tick = y
                x1 = x2 = x
                x2 += self.tick_length * sign_x
                x_tick = x2 + self.spacing * sign_x
            if i == 0:
                transform = (
                    "translate(-6 0)"
                    if self.orientation is Orientation.HORIZONTAL
                    else "translate(0 -6)"
                )
                if self.orientation is Orientation.HORIZONTAL:
                    # a = "start"
                    x1 = x2 = x_tick = x + self.line_width / 2
                if self.orientation is Orientation.VERTICAL:
                    # b = "hanging"
                    y1 = y2 = y_tick = y + self.line_width / 2
            if i == len(self.ticks) - 1:
                transform = (
                    "translate(6 0)"
                    if self.orientation is Orientation.HORIZONTAL
                    else "translate(0 6)"
                )
                if self.orientation is Orientation.HORIZONTAL:
                    # a = "end"
                    x1 = x2 = x_tick = x - self.line_width / 2
                if self.orientation is Orientation.VERTICAL:
                    # b = "auto"
                    y1 = y2 = y_tick = y - self.line_width / 2
            svg += (
                f'<line id="tick-{i}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                f'stroke-linecap="round" stroke="{self.color_ticks.str_hex}" '
                f'stroke-width="{self.line_width}"></line>'
            )
            svg += (
                f'<text id="tick-label-{i}" x="{x_tick}" y="{y_tick}" '
                f'fill="{self.color_ticks.str_hex}" font-family="{self.font_family}" '
                f'font-weight="400" '
                f'font-size="{self.font_size_ticks}" text-anchor="{a}" '
                f'dominant-baseline="{b}">{tick}</text>'
            )
            if "V" == self.orientation:
                y += step
            else:
                x += step
        return svg

    def _get_tag_exponent(self):
        sep = self.seperator_exponent.value
        exponent = str(self.exponent)
        if self.seperator_decimal == "COMMA":
            exponent = exponent.replace(".", ",")
        anchor = "start" if "W" in self.align.value else "end"
        if self.orientation is Orientation.VERTICAL:
            baseline = "auto"
        else:
            baseline = "auto" if "S" in self.align.value else "hanging"
        transform = (
            "translate(0 0)"
            if self.orientation is Orientation.HORIZONTAL
            else "translate(0 4)"
        )
        if "E" in self.align.value:
            return (
                f'<text transform="{transform}" id="exponent" x="{self._x}" '
                f'y="{self._y}" fill="{self.color_ticks.str_hex}" '
                f'font-family="{self.font_family}" font-size="{self.font_size_ticks}" '
                f'text-anchor="{anchor}" dominant-baseline="{baseline}"><tspan '
                f'dominant-baseline="{baseline}">10</tspan><tspan dy="-15" '
                f'dominant-baseline="{baseline}" '
                f'font-size="{self.font_size_ticks * 0.8}">{exponent}</tspan><tspan '
                f'dy="15" dominant-baseline="{baseline}"> {sep}</tspan></text>'
            )
        else:
            return (
                f'<text transform="{transform}" id="exponent" x="{self._x}" '
                f'y="{self._y}" fill="{self.color_ticks.str_hex}" '
                f'font-family="{self.font_family}" font-size="{self.font_size_ticks}" '
                f'text-anchor="{anchor}" dominant-baseline="{baseline}">{sep} 10<tspan '
                f'dy="-15" dominant-baseline="{baseline}" '
                f'font-size="{self.font_size_ticks * 0.8}">{exponent}</tspan></text>'
            )

    def _get_tag_nan(self, sign_x, sign_y):
        anchor = "start" if "W" in self.align.value else "end"
        tag = (
            f'<rect x="{self._x}" y="{self._y}" rx="{self.roundness}" '
            f'ry="{self.roundness}" width="{self.gradient_height}" '
            f'height="{self.gradient_height}" fill="{self.color_nan.str_rgb}"/>'
        )
        self._x += self.spacing * sign_x
        if "W" in self.align.value:
            self._x += self.gradient_height * sign_x
        if self.align is CompassDirection.NORTH or self.align is CompassDirection.SOUTH:
            self._x -= self.gradient_height * 0.5 + self.spacing
        self._y += self.gradient_height / 2
        tag += (
            f'<text x="{self._x}" y="{self._y}" dy="6" '
            f'fill="{self.color_ticks.str_hex}" dominant-baseline="middle" '
            f'text-anchor="{anchor}" font-family="{self.font_family}" '
            f'font-size="{self.font_size_ticks}">{self.text_nan}</text>'
        )
        return tag

    def _get_tag_gradient(self, x, y, hsh):
        w = (
            self.gradient_length
            if self.orientation is Orientation.HORIZONTAL
            else self.gradient_height
        )
        h = (
            self.gradient_length
            if self.orientation is Orientation.VERTICAL
            else self.gradient_height
        )
        if "E" in self.align.value:
            x -= w
        if "S" in self.align.value:
            y -= h
        if self.align is CompassDirection.NORTH or self.align is CompassDirection.SOUTH:
            x -= w / 2
        return (
            f'<rect id="gradient" x="{x}" y="{y}" rx="{self.roundness}" '
            f'ry="{self.roundness}" width="{w}" height="{h}" '
            f'fill="url(#gradient-{hsh})"/>'
        )

    @property
    def align(self) -> CompassDirection:
        """
        Location to place the text on the image.

        There are 4 available options to choose: 'NW', 'NE', 'SE',
        'SW' (like the direction of compass).

        The default align is 'NW'.
        """
        return self._align

    @align.setter
    def align(self, arg: CompassDirection):
        self._align = arg

    @property
    def color_nan(self) -> Color | None:
        """
        :class:`Color` of NaN values.

        If `None`, the label won't beshown on the image.
        """
        return self._color_nan

    @color_nan.setter
    def color_nan(self, arg: Color | None):
        self._color_nan = arg

    @property
    def color_ticks(self) -> Color:
        """
        :class:`Color` of the ticks.
        """
        return self._color_ticks

    @color_ticks.setter
    def color_ticks(self, arg: Color):
        self._color_ticks = arg

    @property
    def exponent(self) -> float | int | str | None:
        """Exponent of the factor of the scale."""

        return self._exponent

    @exponent.setter
    def exponent(self, arg: int | float | str | None):
        if not (isinstance(arg, float | int | str) or arg is None):
            raise TypeError(
                f"{__name__}.exponent expected 'int', 'float', 'str' or 'None'"
            )
        self._exponent = arg

    @property
    def font_size_ticks(self) -> float:
        """
        Font size of the color gradient axis ticks.
        """
        return self._font_size_ticks

    @font_size_ticks.setter
    def font_size_ticks(self, arg: float):
        self._font_size_ticks = arg

    @property
    def gradient_colors(self) -> list[Color]:
        """
        Colors of the gradient bar.
        """
        return self._gradient_colors

    @gradient_colors.setter
    def gradient_colors(self, arg: list[Color]):
        self._gradient_colors = arg

    @property
    def gradient_height(self) -> float:
        """
        Height of the gradient bar (always referred to horizontal
        orientation).
        """
        return self._gradient_height

    @gradient_height.setter
    def gradient_height(self, arg: float):
        self._gradient_height = arg

    @property
    def gradient_length(self) -> float:
        """
        Length of the gradient bar (always referred to horizontal
        orientation).
        """
        return self._gradient_length

    @gradient_length.setter
    def gradient_length(self, arg: float):
        self._gradient_length = arg

    @property
    def line_width(self) -> float:
        """
        Line width of the scalebar.
        """
        return self._line_width

    @line_width.setter
    def line_width(self, arg: float):
        self._line_width = arg

    @property
    def orientation(self) -> Orientation:
        """
        Orientation of the text flow and gradient bar on the image.

        There are 2 available options to choose: 'H', 'V'.
        The default orientation is 'V'.
        """
        return self._orientation

    @orientation.setter
    def orientation(self, arg: Orientation):
        self._orientation = arg

    @property
    def roundness(self) -> float:
        """
        Roundness of the lines of the scalebar.
        """
        return self._roundness

    @roundness.setter
    def roundness(self, arg: float):
        self._roundness = arg

    @property
    def spacing(self) -> float | int:
        """
        Space between the individual components (heading, subheading,
        gradient bar...).
        """
        return self._spacing

    @spacing.setter
    def spacing(self, arg: float | int):
        self._spacing = arg

    @property
    def seperator_decimal(self) -> str:
        """
        The decimal seperator of numbers of the scalebar can be either
        'COMMA' or 'DOT'.
        """
        return self._seperator_decimal

    @seperator_decimal.setter
    def seperator_decimal(self, arg: str):
        self._seperator_decimal = arg

    @property
    def seperator_exponent(self) -> MultiplicationSymbol:
        """
        The multiplication sign of the scalebar exponent can be either
        'CROSS' or 'DOT'.
        """
        return self._seperator_exponent

    @seperator_exponent.setter
    def seperator_exponent(self, arg: MultiplicationSymbol):
        self._seperator_exponent = arg

    @property
    def text_nan(self) -> str:
        """Description of the NaN label. Default is 'NaN'."""
        return self._text_nan

    @text_nan.setter
    def text_nan(self, arg: str):
        self._text_nan = arg

    @property
    def tick_length(self) -> float:
        """
        Length of the ticks.
        """
        return self._tick_length

    @tick_length.setter
    def tick_length(self, arg: float):
        self._tick_length = arg

    @property
    def ticks(self) -> list[str]:
        """
        Ticks of the color scalebar.
        """
        return self._ticks

    @ticks.setter
    def ticks(self, arg: list[str]):
        self._ticks = arg


class SmoothGradientOverlay(Gradient):
    """ """

    def __init__(
        self,
        pth: Path,
        res: tuple[int, int] = (3000, 2000),
        pad: tuple[int, int, int, int] = (100, 100, 100, 100),
    ) -> None:
        super().__init__(pth, res, pad)

    def _get_tag_defs(self):
        h = getrandbits(32)
        p2 = (0, 1) if self.orientation is Orientation.VERTICAL else (1, 0)
        grad = SmoothGradient(self.gradient_colors)
        tag = "<defs>"
        tag += (
            f'<linearGradient id="gradient-{h}" x1="0" y1="0" '
            f'x2="{p2[0]}" y2="{p2[1]}">'
        )
        for value in np.linspace(0.0, 1.0, 100):
            tag += (
                f'<stop offset="{round(value * 100, 6)}%" '
                f'stop-color="{grad(value)[0].str_rgb}"/>'
            )
        tag += "</linearGradient>"
        tag += "</defs>"
        return tag, h


class SegmentedGradientOverlay(Gradient):
    """ """

    def __init__(
        self,
        pth: Path,
        res: tuple[int, int] = (3000, 2000),
        pad: tuple[int, int, int, int] = (100, 100, 100, 100),
    ) -> None:
        super().__init__(pth, res, pad)

    def _get_tag_defs(self):
        h = getrandbits(32)
        p2 = (0, 1) if self.orientation is Orientation.VERTICAL else (1, 0)
        tag = "<defs>"
        tag += (
            f'<linearGradient id="gradient-{h}" x1="0" y1="0" '
            f'x2="{p2[0]}" y2="{p2[1]}">'
        )
        length = len(self.gradient_colors)
        frag = 1 / length
        for i in range(length):
            tag += (
                f'<stop offset="{round(frag * i * 100, 6)}%" '
                f'stop-color="{self.gradient_colors[i].str_rgb}"/>'
            )
            if i < length - 1:
                tag += (
                    f'<stop offset="{round(frag * (i + 1) * 100, 6)}%" '
                    f'stop-color="{self.gradient_colors[i].str_rgb}"/>'
                )
        tag += "</linearGradient>"
        tag += "</defs>"
        return tag, h


class DiscreteGradientOverlay(SegmentedGradientOverlay):
    """ """

    def __init__(
        self,
        pth: Path,
        res: tuple[int, int] = (3000, 2000),
        pad: tuple[int, int, int, int] = (100, 100, 100, 100),
    ) -> None:
        super().__init__(pth, res, pad)

    def _get_tag_axis(self, x, y, sign_x, sign_y):
        return ""
        if self._orientation is Orientation.HORIZONTAL:
            y1 = y2 = y
            x1 = x + (self.line_width / 2) * sign_x
            x2 = x + (self.gradient_length - self.line_width / 2) * sign_x
        else:
            y1 = y + (self.line_width / 2) * sign_y
            y2 = y + (self.gradient_length - self.line_width / 2) * sign_y
            x1 = x2 = x
        dasharray = []
        stride = self.gradient_length / len(self.ticks) * 0.6
        dasharray.append(self.gradient_length / len(self.ticks) - stride)
        dasharray.append(stride)
        offset = -0.5 * stride
        return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke-dashoffset="{offset}" stroke-dasharray="{dasharray[0]} {dasharray[1]}" stroke-linecap="round" stroke="{self.color_ticks.hex_str}" stroke-width="{self.line_width}"></line>'

    def _get_tag_ticks(self, x, y, sign_x, sign_y):
        svg = ""
        w = (
            self.gradient_length
            if self.orientation is Orientation.HORIZONTAL
            else self.gradient_height
        )
        h = (
            self.gradient_length
            if self.orientation is Orientation.VERTICAL
            else self.gradient_height
        )
        step = self.gradient_length / len(self.ticks)
        if "E" in self.align.value and self.orientation is Orientation.HORIZONTAL:
            x -= w
        if "S" in self.align.value and self.orientation is Orientation.VERTICAL:
            y -= h
        if self.orientation is Orientation.VERTICAL:
            y += 0.5 * step
        if self.orientation is Orientation.HORIZONTAL:
            x += 0.5 * step
        if self.align is CompassDirection.NORTH or self.align is CompassDirection.SOUTH:
            x -= w / 2
        for i, tick in enumerate(self.ticks):
            if self.seperator_decimal == "COMMA":
                tick = str(tick).replace(".", ",")
            transform = ""
            a = (
                "middle"
                if self.orientation is Orientation.HORIZONTAL
                else ("start" if "W" in self.align.value else "end")
            )
            b = (
                "middle"
                if self.orientation is Orientation.VERTICAL
                else ("hanging" if "N" in self.align.value else "auto")
            )
            if self.orientation is Orientation.HORIZONTAL:
                x1 = x2 = x_tick = x
                y1 = y2 = y
                y2 += self.tick_length * sign_y
                y_tick = y2 + self.spacing * sign_y
            else:
                y1 = y2 = y_tick = y
                x1 = x2 = x
                x2 += self.tick_length * sign_x
                x_tick = x2 + self.spacing * sign_x
            svg += (
                f'<line id="tick-{i}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                f'stroke-linecap="round" stroke="{self.color_ticks.str_hex}" '
                f'stroke-width="{self.line_width}"></line>'
            )
            svg += (
                f'<text id="tick-label-{i}" x="{x_tick}" y="{y_tick}" '
                f'fill="{self.color_ticks.str_hex}" font-family="{self.font_family}" '
                f'font-weight="400" transform="{transform}" '
                f'font-size="{self.font_size_ticks}" text-anchor="{a}" '
                f'dominant-baseline="{b}">{tick}</text>'
            )
            if "V" == self.orientation:
                y += step
            else:
                x += step
        return svg


class LabelsOverlay(TitleOverlay):

    def __init__(
        self,
        pth: Path,
        res: tuple[int, int] = (3000, 2000),
        pad: tuple[int, int, int, int] = (100, 100, 100, 100),
    ) -> None:
        super().__init__(pth, res, pad)
        self._labels = []
        self.box_size = (120, 120)
        self.color_labeltext = Color("#000")
        self.font_size_labeltext = 100
        self.roundness = 20

    def add_label(self, color: Color, text: str):
        """Add a label to the overlay."""

        self._labels.append((color, text))
        return self

    def _build(self):
        svg = super()._build()
        _, _, sign_x, sign_y, anchor, _ = self._get_alignment_config()
        if any([self.text, self.heading, self.subheading]):
            self._y += sign_y * self.spacing
        for label in self._labels:
            if "EAST" in self.align.name:
                self._x -= self.box_size[0]
            if "SOUTH" in self.align.name:
                self._y -= self.box_size[1]
            svg += (
                f'<rect x="{self._x}" y="{self._y}" rx="{self.roundness}" '
                f'ry="{self.roundness}" width="{self.box_size[0]}" '
                f'height="{self.box_size[1]}" fill="{label[0].str_rgb}"/>'
            )
            if "EAST" in self.align.name:
                self._x += self.box_size[0]
            if "SOUTH" in self.align.name:
                self._y += self.box_size[1]
            self._x += (self.box_size[0] + self.spacing / 2) * sign_x
            self._y += self.box_size[1] / 2 * sign_y
            svg += (
                f'<text x="{self._x}" y="{self._y}" dy="6" '
                f'fill="{self.color_labeltext}" dominant-baseline="middle" '
                f'text-anchor="{anchor}" font-family="{self.font_family}" '
                f'font-size="{self.font_size_labeltext}">{label[1]}</text>'
            )
            self._x -= (self.box_size[0] + self.spacing / 2) * sign_x
            self._y += (self.spacing + self.box_size[1] / 2) * sign_y
        return svg

    @property
    def box_size(self) -> tuple[float, float]:
        """Size of each colored box."""
        return self._box_size

    @box_size.setter
    def box_size(self, arg: tuple[float, float]):
        self._box_size = arg

    @property
    def color_labeltext(self):
        return self._color_labeltext

    @color_labeltext.setter
    def color_labeltext(self, arg: Color):
        if isinstance(arg, Color):
            self._color_labeltext = arg
        else:
            raise TypeError

    @property
    def font_size_labeltext(self):
        return self._font_size_labeltext

    @font_size_labeltext.setter
    def font_size_labeltext(self, arg: int):
        if isinstance(arg, int):
            self._font_size_labeltext = arg
        else:
            raise TypeError

    @property
    def roundness(self) -> float:
        """Roundness of the lines of the scalebar."""
        return self._roundness

    @roundness.setter
    def roundness(self, arg: float):
        self._roundness = arg
