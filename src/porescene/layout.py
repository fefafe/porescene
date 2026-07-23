# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Felix Faber /
# Otto von Guericke University Magdeburg, Thermal Process Engineering

import abc
import random
from pathlib import Path
from typing import Self

import numpy as np

from porescene.color import Color
from porescene.color.gradient import SmoothGradient
from porescene.utility import CompassDirection, MultiplicationSymbol, Orientation


class Annotation(abc.ABC):  # noqa: B024
    pass


class BackgroundAnnotation(Annotation):
    """
    Base class for the different annotation types.

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
        ovl = BackgroundAnnotation(res)
        ovl.background = Color("#382655")
        ovl.save(fpath)

    """

    _xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'

    def __init__(
        self,
        pth: Path,
        res: tuple[int, int] = (4096, 4096),
        pad: tuple[int, int, int, int] = (100, 100, 100, 100),
        bg: Color | None = None,
    ):
        self.path = pth
        self.resolution = res
        self.padding = pad
        self.color_background = bg

    def get_svg(self) -> str:
        """
        Returns the SVG element without XML declaration.

        Builds the ``<svg>`` element with all its child elements. The drawn
        content is centered on the canvas (see :meth:`_center`).
        """
        self._bbox_reset()
        content = self._build()
        svg = self._get_tag_svg_open()
        svg += self._get_tag_background()
        svg += self._center(content)
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
        # The plain background annotation draws no content of its own; the
        # background is emitted canvas-space in get_svg. Subclasses override
        # this to add their content (title, colorbar, labels ...).
        return ""

    def _center(self, content: str) -> str:
        """
        Wraps the drawn content in a group translated so that its bounding box
        is centered on the canvas.

        The bounding box is accumulated by every draw call (see
        :meth:`_bbox_add`). Centering keeps the content clear of the viewport
        edges, so -- unlike an edge-anchored layout -- no clipping margin around
        the drawing area is required.
        """
        if self._bbox is None:
            return content
        min_x, min_y, max_x, max_y = self._bbox
        dx = self.resolution[0] / 2 - (min_x + max_x) / 2
        dy = self.resolution[1] / 2 - (min_y + max_y) / 2
        return f'<g transform="translate({dx} {dy})">{content}</g>'

    def _bbox_reset(self) -> None:
        """Clears the accumulated content bounding box before a new build."""
        self._bbox: tuple[float, float, float, float] | None = None

    def _bbox_add(self, x: float, y: float, w: float = 0.0, h: float = 0.0) -> None:
        """Grows the content bounding box to include rectangle ``(x, y, w, h)``."""
        x0, y0, x1, y1 = x, y, x + w, y + h
        if self._bbox is None:
            self._bbox = (x0, y0, x1, y1)
            return
        bx0, by0, bx1, by1 = self._bbox
        self._bbox = (min(bx0, x0), min(by0, y0), max(bx1, x1), max(by1, y1))

    def _bbox_add_text(
        self,
        x: float,
        y: float,
        text: str,
        font_size: float,
        anchor: str,
        baseline: str,
    ) -> None:
        """
        Grows the bounding box to include a horizontal text run.

        SVG exposes no measured glyph metrics here, so the run's extent is
        estimated from the font size and character count. That is precise enough
        to center the group, since the image is cropped to its content afterwards.
        """
        w = 0.6 * font_size * len(str(text))
        left = {"start": x, "middle": x - w / 2, "end": x - w}.get(anchor, x)
        if baseline in ("hanging", "text-before-edge"):
            top = y
        elif baseline in ("middle", "central"):
            top = y - font_size / 2
        else:  # alphabetic / auto
            top = y - 0.75 * font_size
        self._bbox_add(left, top, w, font_size)

    def _get_tag_background(self) -> str:
        if self.color_background is None:
            return ""
        else:
            return (
                f'<rect id="background" x="0" y="0" width="100%" '
                f'height="100%" fill="{self.color_background.str_rgba}"/>'
            )

    def _get_tag_svg_open(self) -> str:
        width, height = self.resolution
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="'
            f'http://www.w3.org/1999/xlink" width="{width}px" height="{height}px" '
            f'viewBox="0 0 {width} {height}" font-weight="400">'
        )

    @property
    def color_background(self) -> Color | None:
        """
        Image background color as :class:`Color` object or `None` for
        transparent background.
        """
        return self._background

    @color_background.setter
    def color_background(self, arg: Color | None):
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


class TitleAnnotation(BackgroundAnnotation):
    """
    Create an annotation image with heading, subheading an some lines of text.

    Parameters
    ----------
    res
        Size of the image in pixels. The first entry specifies width, second
        height.

    Examples
    --------
    >>> from fefacolors import gray, red, light3
    >>> ovl = TitleAnnotation()
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

    def __init__(
        self,
        pth: Path,
        res: tuple[int, int] = (4096, 4096),
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
        if self._use_vertical_title():
            # Vertical-orientation gradients render the title rotated alongside
            # the colorbar (see Gradient._build). Leave the cursor at the top so
            # the bar is not pushed down by a would-be horizontal title here.
            return svg
        if self.heading:
            svg += self._get_tag_heading(anchor, baseline)
            self._y += self.font_size_heading * self._line_height * sign_y
        if self.subheading:
            svg += self._get_tag_subheading(anchor, baseline)
            self._y += self.font_size_subheading * self._line_height * sign_y
        if self.text:
            svg += self._get_tag_text(sign_y, anchor, baseline)
        return svg

    def _use_vertical_title(self) -> bool:
        """
        Whether the heading is rendered rotated (running vertically).

        Horizontal by default; orientation-aware subclasses override this.
        """
        return False

    def _get_tag_heading(self, a, b):
        self._bbox_add_text(self._x, self._y, self.heading, self.font_size_heading, a, b)
        return (
            f'<text id="title" x="{self._x}" y="{self._y}" dominant-baseline="{b}" '
            f'text-anchor="{a}" fill="{self.color_heading.str_hex}" font-weight="400" '
            f'font-family="{self.font_family}" font-size="{self.font_size_heading}">'
            f"{self.heading}</text>"
        )

    def _get_tag_subheading(self, a, b):
        self._bbox_add_text(
            self._x, self._y, self.subheading, self.font_size_subheading, a, b
        )
        return (
            f'<text id="title" x="{self._x}" y="{self._y}" dominant-baseline="{b}" '
            f'text-anchor="{a}" fill="{self.color_subheading.str_hex}" '
            f'font-weight="500" font-family="{self.font_family}" '
            f'font-size="{self.font_size_subheading}">{self.subheading}</text>'
        )

    def _get_tag_text(self, sign_y, a, b):
        text = reversed(self.text) if sign_y == -1 else self.text
        tag = ""
        y = self._y
        for i, line in enumerate(text):
            self._bbox_add_text(self._x, y, line, self.font_size_text, a, b)
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
            case CompassDirection.WEST:
                x = self.padding[3] + self.font_size_heading
                y = self.padding[0]
                sign_x = 1
                sign_y = 1
                anchor = "start"
                baseline = "auto"
            case CompassDirection.EAST:
                x = self.resolution[0] - self.padding[1] - self.font_size_heading
                y = self.padding[0]
                sign_x = -1
                sign_y = 1
                anchor = "end"
                baseline = "auto"
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


class Gradient(TitleAnnotation, abc.ABC):
    """
    Create an annotation image with heading, subheading, text and a gradient
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

    def __init__(
        self,
        pth: Path,
        res: tuple[int, int] = (4096, 4096),
        pad: tuple[int, int, int, int] = (100, 100, 100, 100),
    ):
        super().__init__(pth, res, pad)
        self.color_ticks = Color("#000")
        self.color_nan = None
        self.font_size_ticks = 90
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
        # A vertical colorbar has no sensible centered (north/south) layout -- the
        # bar collides with its own ticks and heading. Since img_add_colorbar places
        # north/south vertical bars on the outer (east) side of the scene anyway,
        # render them exactly like an east-aligned bar.
        if self.orientation is Orientation.VERTICAL and self.align in (
            CompassDirection.NORTH,
            CompassDirection.SOUTH,
        ):
            original_align = self.align
            self.align = CompassDirection.EAST
            try:
                return self._build_impl()
            finally:
                self.align = original_align
        return self._build_impl()

    def _build_impl(self):
        x, y, sign_x, sign_y, anchor, baseline = self._get_alignment_config()
        self._x = x
        self._y = y
        svg, id_grad = self._get_tag_defs()
        svg += super()._build()
        if any([self.text, self.heading, self.subheading]):
            self._y += self.spacing * sign_y
        svg += "<g>"
        if self.gradient_colors:
            svg += self._get_tag_gradient(self._x, self._y, id_grad)
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
        if self._use_vertical_title() and self.heading and self.gradient_colors:
            svg += self._get_tag_heading_vertical()
        svg += "</g>"
        return svg

    def _use_vertical_title(self) -> bool:
        return self.orientation is Orientation.VERTICAL

    def _get_tag_heading_vertical(self) -> str:
        """
        Renders the heading rotated 90 degrees, vertically centered on the
        gradient bar and placed on the outer side of the colorbar (the side
        facing away from the scene, opposite the ticks), so it runs alongside a
        vertical colorbar instead of sitting horizontally on top. West-aligned
        bars get the label on the left, east-aligned bars on the right.
        """
        gx, gy, gw, gh = self._grad_bbox
        center_y = gy + gh / 2

        offset = self.spacing + self.font_size_heading * 0.5
        if "W" in self.align.value:
            # west: bar near the left edge -> label on the outer (left) side
            x = gx - offset
            angle = -90
        else:
            # east: bar near the right edge -> label on the outer (right) side
            x = gx + gw + offset
            angle = 90

        # rotated run: extends along y by its length, along x by the font size
        run = 0.6 * self.font_size_heading * len(str(self.heading))
        self._bbox_add(
            x - self.font_size_heading / 2,
            center_y - run / 2,
            self.font_size_heading,
            run,
        )
        return (
            f'<text id="title" x="{x}" y="{center_y}" text-anchor="middle" '
            f'dominant-baseline="central" transform="rotate({angle} {x} {center_y})" '
            f'fill="{self.color_heading.str_hex}" font-weight="400" '
            f'font-family="{self.font_family}" font-size="{self.font_size_heading}">'
            f"{self.heading}</text>"
        )

    @abc.abstractmethod
    def _get_tag_defs(self) -> tuple[str, int]:
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
        ticks = self.ticks
        if self.orientation is Orientation.VERTICAL:
            ticks.reverse()
        for i, tick in enumerate(ticks):
            if self.seperator_decimal == "COMMA":
                tick = str(tick).replace(".", ",")
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
                if self.orientation is Orientation.HORIZONTAL:
                    # a = "start"
                    x1 = x2 = x_tick = x + self.line_width / 2
                if self.orientation is Orientation.VERTICAL:
                    # b = "hanging"
                    y1 = y2 = y_tick = y + self.line_width / 2
            if i == len(self.ticks) - 1:
                if self.orientation is Orientation.HORIZONTAL:
                    # a = "end"
                    x1 = x2 = x_tick = x - self.line_width / 2
                if self.orientation is Orientation.VERTICAL:
                    # b = "auto"
                    y1 = y2 = y_tick = y - self.line_width / 2
            self._bbox_add(x2, y2)
            self._bbox_add_text(x_tick, y_tick, tick, self.font_size_ticks, a, b)
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
            if self.orientation is Orientation.VERTICAL:
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
        self._bbox_add_text(
            self._x,
            self._y,
            f"10{exponent} {sep}",
            self.font_size_ticks,
            anchor,
            baseline,
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
        color_nan = self.color_nan.str_rgb if self.color_nan else ""
        self._bbox_add(self._x, self._y, self.gradient_height, self.gradient_height)
        tag = (
            f'<rect x="{self._x}" y="{self._y}" rx="{self.roundness}" '
            f'ry="{self.roundness}" width="{self.gradient_height}" '
            f'height="{self.gradient_height}" fill="{color_nan}"/>'
        )
        self._x += self.spacing * sign_x
        if "W" in self.align.value:
            self._x += self.gradient_height * sign_x
        if self.align is CompassDirection.NORTH or self.align is CompassDirection.SOUTH:
            self._x -= self.gradient_height * 0.5 + self.spacing
        self._y += self.gradient_height / 2
        self._bbox_add_text(
            self._x, self._y, self.text_nan, self.font_size_ticks, anchor, "middle"
        )
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
        # remember the bar's bounding box so a vertical title can be centered
        # on it and offset past the ticks (see _get_tag_heading_vertical)
        self._grad_bbox = (x, y, w, h)
        self._bbox_add(x, y, w, h)
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


class SmoothGradientAnnotation(Gradient):
    """ """

    def __init__(
        self,
        pth: Path,
        res: tuple[int, int] = (4096, 4096),
        pad: tuple[int, int, int, int] = (100, 100, 100, 100),
    ) -> None:
        super().__init__(pth, res, pad)

    def _get_tag_defs(self):
        id_grad = random.getrandbits(32)
        # Vertical gradients run bottom -> top; horizontal run left -> right.
        if self.orientation is Orientation.VERTICAL:
            p1, p2 = (0, 1), (0, 0)
        else:
            p1, p2 = (0, 0), (1, 0)
        grad = SmoothGradient(self.gradient_colors)
        tag = "<defs>"
        tag += (
            f'<linearGradient id="gradient-{id_grad}" x1="{p1[0]}" y1="{p1[1]}" '
            f'x2="{p2[0]}" y2="{p2[1]}">'
        )
        for value in np.linspace(0.0, 1.0, 100):
            tag += (
                f'<stop offset="{round(value * 100, 6)}%" '
                f'stop-color="{grad(value)[0].str_rgb}"/>'
            )
        tag += "</linearGradient>"
        tag += "</defs>"
        return tag, id_grad


class SegmentedGradientAnnotation(Gradient):
    """ """

    def __init__(
        self,
        pth: Path,
        res: tuple[int, int] = (4096, 4096),
        pad: tuple[int, int, int, int] = (100, 100, 100, 100),
    ) -> None:
        super().__init__(pth, res, pad)

    def _get_tag_defs(self):
        id_grad = random.getrandbits(32)
        # Vertical gradients run bottom -> top; horizontal run left -> right.
        if self.orientation is Orientation.VERTICAL:
            p1, p2 = (0, 1), (0, 0)
        else:
            p1, p2 = (0, 0), (1, 0)
        tag = "<defs>"
        tag += (
            f'<linearGradient id="gradient-{id_grad}" x1="{p1[0]}" y1="{p1[1]}" '
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
        return tag, id_grad


class DiscreteGradientAnnotation(SegmentedGradientAnnotation):
    """ """

    def __init__(
        self,
        pth: Path,
        res: tuple[int, int] = (4096, 4096),
        pad: tuple[int, int, int, int] = (100, 100, 100, 100),
    ) -> None:
        super().__init__(pth, res, pad)

    def _get_tag_axis(self, x, y, sign_x, sign_y):
        # return ""
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
        return (
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke-dashoffset="{offset}" '
            f'stroke-dasharray="{dasharray[0]} {dasharray[1]}" '
            f'stroke-linecap="round" stroke="{self.color_ticks.str_hex}" '
            f'stroke-width="{self.line_width}"></line>'
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
            self._bbox_add(x2, y2)
            self._bbox_add_text(x_tick, y_tick, tick, self.font_size_ticks, a, b)
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


class LabelsAnnotation(TitleAnnotation):
    def __init__(
        self,
        pth: Path,
        res: tuple[int, int] = (4096, 4096),
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
            self._bbox_add(self._x, self._y, self.box_size[0], self.box_size[1])
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
            self._bbox_add_text(
                self._x, self._y, label[1], self.font_size_labeltext, anchor, "middle"
            )
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
