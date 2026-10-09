# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Felix Faber /
# Otto von Guericke University Magdeburg, Thermal Process Engineering

"""
Composition of annotated figures as SVG.

A figure is assembled on an :class:`SVGCanvas`: the rendered image goes into the middle,
and the annotations that explain it -- a colorbar, a title, a legend, the timestamp of a
video frame -- are positioned onto the canvas by compass direction.

Every annotation is an :class:`AnnotationElement`. It draws itself in a coordinate system
of its own and reports the rectangle it fills through :meth:`AnnotationElement.bbox`,
knowing nothing about where on the canvas it ends up. The canvas reads those boxes,
reserves a strip along every edge an annotation was hung onto, lines the annotations up
in it, and scales the rendered image into whatever room is left in the middle. Sizing an
annotation therefore never involves the canvas, and moving one from one edge to another
is a matter of the direction it is added under.

A figure is described the way it is meant to be printed: every length in centimeters,
every font size in points. The canvas states its physical size in the file it writes, so
it arrives at that size in a manuscript, and how many pixels it is rasterized into is
settled when it is converted (see :func:`~porescene.utility.svg2png`) rather than when it
is composed. Inside, everything is drawn in the user units of the SVG -- what a
:class:`BoundingBox` speaks, and what :func:`~porescene.utility.cm2px` and
:func:`~porescene.utility.pt2px` convert into.

Examples
--------
.. code-block:: python
    :caption: A colorbar below the render, the frame time in the upper right corner.
    :linenos:

    cb = SmoothGradientAnnotation([fefa.yellow, fefa.red], ["0", "1"])
    cb.orientation = Orientation.HORIZONTAL
    cb.heading = "Saturation [-]"

    canvas = SVGCanvas((16, 12))          # centimeters
    canvas.add_image(pth_render)
    canvas.add(cb, CompassDirection.SOUTH)
    canvas.add(TimestampAnnotation(12.5), CompassDirection.NORTHEAST)
    canvas.save(Path("figure.svg"))
"""

import abc
import base64
import functools
import io
import math
import mimetypes
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import NamedTuple, Self

import numpy as np
import PIL.Image
import PIL.ImageFont

from porescene.color import Color
from porescene.color.gradient import SmoothGradient
from porescene.utility import (
    PATH_FONT,
    CompassDirection,
    MultiplicationSymbol,
    Orientation,
    cm2px,
    make_id,
    pt2px,
    px2cm,
    px2pt,
)
from porescene.utility import filepath_add_id as _stamp_id

#: Font stack the annotations are drawn in unless told otherwise.
FONT_FAMILY = "Inter, Arial, Helvetica Neue, Helvetica, sans-serif"

#: Width of a glyph as a fraction of the font size.
#:
#: Falls back to this where a :class:`Font` names no file to measure, since a family that
#: is only named cannot be looked at. Rounded up off the digits of Inter: prose comes out
#: narrower and reserves too much room, capitals come out wider and reserve too little,
#: which is why measuring is worth the file it takes.
_ADVANCE = 0.6

#: Height of a capital letter, fallback for :attr:`Font.cap`.
_CAP = 0.728

#: Depth of a descender below the baseline, fallback for :attr:`Font.descent`.
_DESCENT = 0.204

#: Font size the metrics of a typeface are read at.
#:
#: Outlines scale, so one reading serves every size; taking it at a large size keeps the
#: rounding of the integers the metrics come back as far below what a figure can show.
_REF_SIZE = 1000


@functools.lru_cache(maxsize=1)
def _path_font_bundled() -> Path | None:
    """
    Returns the path of the typeface shipped with the package.

    Materializes it as a file the way :class:`~porescene.config.AxesConfiguration` does,
    so an installation that keeps the package zipped would have to unpack it.
    """
    try:
        ref = resources.files("porescene").joinpath(PATH_FONT)
        with resources.as_file(ref) as pth:
            return Path(pth)
    except (OSError, ValueError, ModuleNotFoundError):
        return None


@functools.lru_cache(maxsize=8)
def _measure(path: str) -> tuple[PIL.ImageFont.FreeTypeFont, float, float] | None:
    """
    Opens a font file for measuring and reads the metrics off it.

    Returns the face together with its cap height and the depth of its descenders, both as
    a fraction of the font size, or ``None`` where the file cannot be read -- which leaves
    the caller with the estimates of :data:`_ADVANCE`, :data:`_CAP` and :data:`_DESCENT`.

    The faces are kept, since opening one costs far more than measuring with it and a
    figure measures every run of text on it twice: once to draw it, once to find out how
    much room it takes.
    """
    try:
        face = PIL.ImageFont.truetype(io.BytesIO(Path(path).read_bytes()), _REF_SIZE)
        # `getbbox` measures the ink from the top of the ascender, so the baseline sits at
        # the ascent: the box of a capital is the cap height, and what a descender reaches
        # past the ascent is the descent
        ascent = face.getmetrics()[0]
        box_cap = face.getbbox("H")
        cap = (box_cap[3] - box_cap[1]) / _REF_SIZE
        descent = (face.getbbox("p")[3] - ascent) / _REF_SIZE
    except (OSError, ValueError):
        return None

    return face, cap, descent


class Font:
    """
    The typeface an annotation is set in.

    Carries the two things a figure needs of a font and keeps them together: the family
    written into the markup, which decides what the renderer draws with, and the file the
    text is measured against, which decides how much room the layout reserves for it.
    Naming a family without handing over the file it stands for leaves the measurements to
    a rough estimate -- a family cannot be measured by its name, since finding the file
    behind it is the business of the operating system rather than of a font library.

    Parameters
    ----------
    family
        Font stack written into the markup, in CSS notation.
    path
        Font file the text is measured against. ``None`` falls back to estimating the
        extent of a text run from its character count.

    See Also
    --------
    font_default : The bundled typeface, which every annotation starts out with.

    Examples
    --------
    .. code-block:: python
        :caption: Setting a figure in a typeface of one's own.
        :linenos:

        font = Font("Libertinus Serif, serif", Path("LibertinusSerif-Regular.otf"))
        cb.font = font

        # the renderer has to be handed the very same file to draw with
        svg2png(canvas.save(pth), fonts=[font.path])
    """

    def __init__(self, family: str = FONT_FAMILY, path: Path | None = None) -> None:
        self.family = family
        self.path = path

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.family!r}, {self.path!r})"

    def advance(self, text: object, font_size: float) -> float:
        """
        Returns how far a run of text advances the pen, in the unit of ``font_size``.

        The advance rather than the extent of the ink, so that a run reserves the room it
        would take in a line of text, side bearings included, instead of ending flush
        against whatever follows it.
        """
        measured = self._measured

        if measured is None:
            return _ADVANCE * font_size * len(str(text))

        return measured[0].getlength(str(text)) / _REF_SIZE * font_size

    @property
    def _measured(self) -> tuple[PIL.ImageFont.FreeTypeFont, float, float] | None:
        """The face and its metrics, ``None`` where there is no file to read."""
        if self.path is None:
            return None

        return _measure(str(self.path))

    @property
    def cap(self) -> float:
        """Height of a capital letter, as a fraction of the font size."""
        measured = self._measured

        return _CAP if measured is None else measured[1]

    @property
    def descent(self) -> float:
        """Depth of a descender below the baseline, as a fraction of the font size."""
        measured = self._measured

        return _DESCENT if measured is None else measured[2]

    @property
    def baseline(self) -> float:
        """
        Distance from the top of a line of text down to its baseline, as a fraction of
        the font size.

        A line is treated as one font size tall, which leaves a little more room than
        :attr:`cap` and :attr:`descent` need; the slack is split evenly above and below,
        so the ink sits centered in the box the layout reserves for it.
        """
        return (1 + self.cap - self.descent) / 2

    @property
    def family(self) -> str:
        """Font stack written into the markup, in CSS notation."""
        return self._family

    @family.setter
    def family(self, arg: str):
        self._family = arg

    @property
    def path(self) -> Path | None:
        """
        Font file the text is measured against, ``None`` to estimate instead.

        Hand the same file to :func:`~porescene.utility.svg2png` where it is not one the
        machine has installed, so that what is measured and what is drawn agree.
        """
        return self._path

    @path.setter
    def path(self, arg: Path | None):
        self._path = None if arg is None else Path(arg)


def font_default() -> Font:
    """
    Returns the typeface the annotations start out with: the stack of :data:`FONT_FAMILY`,
    measured against the copy of Inter bundled with the package.

    A fresh instance every time, so that setting a size or a family on one annotation
    leaves the others alone.
    """
    return Font(FONT_FAMILY, _path_font_bundled())


def _baseline(y: float, font_size: float, valign: str, font: Font) -> float:
    """
    Turns the vertical anchor of a text run into the ``y`` of its alphabetic baseline.

    Every run is written on the alphabetic baseline rather than through
    ``dominant-baseline``, which is the one baseline every SVG renderer has agreed on
    since SVG 1.0 -- a viewer that quietly ignores the property, as vector editors are
    prone to do, would otherwise lift every run by three quarters of its size and drop
    the tick labels into the colorbar.

    ``"top"`` hangs the run off the top edge of its line, ``"middle"`` centers the height
    of a capital on ``y``, so that digits come out visually centered on whatever they
    are placed against.
    """
    if valign == "middle":
        return y + font.cap / 2 * font_size

    return y + font.baseline * font_size


def _escape(text: object) -> str:
    """Escapes the characters that would otherwise open or close an XML node."""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _num(value: float) -> str:
    """
    Writes a coordinate without the noise of its binary representation.

    Keeps the markup readable and, more importantly, stable: a value that is arrived at
    by two different routes writes the same either way, so the fingerprint of a canvas
    (see :attr:`SVGCanvas.id`) does not change with the arithmetic that produced it.
    """
    return f"{float(value):.4f}".rstrip("0").rstrip(".") or "0"


def _translate(content: str, dx: float, dy: float, scale: float = 1.0) -> str:
    """
    Moves drawn content to ``(dx, dy)``, optionally scaling it about its own origin.

    A point ``p`` of ``content`` ends up at ``(dx, dy) + scale * p``, which is how the
    canvas turns the local coordinates of an annotation into canvas coordinates.
    """
    if dx == 0 and dy == 0 and scale == 1.0:
        return content

    transform = f"translate({_num(dx)} {_num(dy)})"
    if scale != 1.0:
        transform += f" scale({_num(scale)})"

    return f'<g transform="{transform}">{content}</g>'


def _tag_text(
    x: float,
    y: float,
    text: object,
    font_size: float,
    color: Color,
    font: Font,
    *,
    anchor: str = "start",
    valign: str = "top",
    weight: int = 400,
    name: str | None = None,
    content: str | None = None,
) -> str:
    """
    Writes a single ``<text>`` run, anchored at ``(x, y)`` by ``anchor`` and ``valign``
    (see :func:`_baseline`).

    ``content`` replaces the escaped ``text`` in the body of the node, for a run that
    carries markup of its own -- a superscript, say -- while still being measured by the
    plain ``text`` it reads as. ``name`` labels the run in the markup, as a class rather
    than an identifier, since a figure carrying two colorbars carries every part of one
    twice and identifiers have to stay unique across the document.
    """
    marker = f' class="{name}"' if name else ""

    return (
        f'<text{marker} x="{_num(x)}" '
        f'y="{_num(_baseline(y, font_size, valign, font))}" '
        f'fill="{color.str_hex}" font-family="{font.family}" '
        f'font-size="{_num(font_size)}" font-weight="{weight}" '
        f'text-anchor="{anchor}">'
        f"{_escape(text) if content is None else content}</text>"
    )


@dataclass(frozen=True)
class BoundingBox:
    """
    The rectangle a piece of drawn content occupies.

    What an :class:`AnnotationElement` reports about itself and what the canvas arranges
    by, in the coordinate system the content was drawn in -- so its origin is wherever
    the content happens to sit, and both ``x`` and ``y`` may well be negative.

    Measured in the user units of the SVG rather than in the centimeters an annotation is
    sized in, since that is the unit the drawing itself is written in. Use
    :func:`~porescene.utility.px2cm` to read one as a physical length.
    """

    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0

    @property
    def right(self) -> float:
        """Coordinate of the right edge."""
        return self.x + self.width

    @property
    def bottom(self) -> float:
        """Coordinate of the bottom edge."""
        return self.y + self.height

    @property
    def center_x(self) -> float:
        """Horizontal center of the box."""
        return self.x + self.width / 2

    @property
    def center_y(self) -> float:
        """Vertical center of the box."""
        return self.y + self.height / 2

    @property
    def size(self) -> tuple[float, float]:
        """Width and height of the box."""
        return (self.width, self.height)

    @classmethod
    def from_corners(cls, x0: float, y0: float, x1: float, y1: float) -> Self:
        """Builds the box spanned by two opposite corners, in any order."""
        return cls(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))

    def union(self, other: "BoundingBox") -> "BoundingBox":
        """Returns the smallest box holding both this one and ``other``."""
        return BoundingBox.from_corners(
            min(self.x, other.x),
            min(self.y, other.y),
            max(self.right, other.right),
            max(self.bottom, other.bottom),
        )

    def translated(self, dx: float, dy: float) -> "BoundingBox":
        """Returns the box moved by ``(dx, dy)``."""
        return BoundingBox(self.x + dx, self.y + dy, self.width, self.height)

    def scaled(self, factor: float) -> "BoundingBox":
        """Returns the box scaled about the origin of its coordinate system."""
        return BoundingBox(
            self.x * factor, self.y * factor, self.width * factor, self.height * factor
        )


class _Bounds:
    """
    Accumulates the extent of drawn content while it is being written.

    Every draw call reports what it covers, so that an element ends up knowing the box it
    fills without the geometry having to be worked out a second time.
    """

    def __init__(self) -> None:
        self._box: BoundingBox | None = None

    def add(self, x: float, y: float, width: float = 0.0, height: float = 0.0) -> None:
        """Grows the box to include the rectangle ``(x, y, width, height)``."""
        self.add_box(BoundingBox(x, y, width, height))

    def add_box(self, box: BoundingBox | None) -> None:
        """Grows the box to include ``box``, ignoring ``None``."""
        if box is None:
            return
        self._box = box if self._box is None else self._box.union(box)

    def add_text(
        self,
        x: float,
        y: float,
        text: object,
        font_size: float,
        font: "Font",
        anchor: str,
        valign: str = "top",
    ) -> None:
        """Grows the box to include a text run, see :func:`_text_box`."""
        self.add_box(_text_box(x, y, text, font_size, font, anchor, valign))

    @property
    def box(self) -> BoundingBox:
        """The accumulated box, empty as long as nothing was drawn."""
        return self._box if self._box is not None else BoundingBox()


def _text_box(
    x: float,
    y: float,
    text: object,
    font_size: float,
    font: Font,
    anchor: str,
    valign: str = "top",
) -> BoundingBox:
    """
    Returns the box a text run drawn at ``(x, y)`` covers.

    Measured against the very font the run is set in and derived from the very baseline it
    is written on (see :func:`_baseline`), so that what the layout reserves and what the
    renderer draws cannot drift apart.
    """
    width = font.advance(text, font_size)
    left = {"start": x, "middle": x - width / 2, "end": x - width}.get(anchor, x)
    top = _baseline(y, font_size, valign, font) - font.baseline * font_size

    return BoundingBox(left, top, width, font_size)


def _rotate(content: str, box: BoundingBox, angle: float) -> tuple[str, BoundingBox]:
    """
    Turns drawn content about the center of its own box.

    Rotating about the center rather than about the origin keeps the content where it is,
    so an element can hand the result on unchanged -- only the box it reports grows and
    shrinks with the turn.
    """
    if not angle:
        return content, box

    cx, cy = box.center_x, box.center_y
    cos, sin = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    corners = [
        (
            cx + (px - cx) * cos - (py - cy) * sin,
            cy + (px - cx) * sin + (py - cy) * cos,
        )
        for px, py in (
            (box.x, box.y),
            (box.right, box.y),
            (box.right, box.bottom),
            (box.x, box.bottom),
        )
    ]
    xs = [corner[0] for corner in corners]
    ys = [corner[1] for corner in corners]

    return (
        f'<g transform="rotate({_num(angle)} {_num(cx)} {_num(cy)})">{content}</g>',
        BoundingBox.from_corners(min(xs), min(ys), max(xs), max(ys)),
    )


class AnnotationElement(abc.ABC):
    """
    A single piece of annotation drawn onto an :class:`SVGCanvas`.

    An element draws itself in a coordinate system of its own -- with the origin wherever
    it is convenient, since the canvas moves the whole drawing into place -- and reports
    the rectangle it fills through :meth:`bbox`. That box is the only thing the canvas
    needs to arrange a figure, so an element never has to be told the size of the canvas,
    the padding around it, or what else is on it.

    An element is sized the way a figure is described: lengths in centimeters, font sizes
    in points. Those are what its properties take and return; the drawing itself, and with
    it every :class:`BoundingBox`, is written in the user units of the SVG.

    What an element *is* told is the direction it was hung onto the canvas under, through
    :attr:`placement`. Elements read it where a detail genuinely depends on which edge
    they sit at: which side of a colorbar its ticks face, which way a text block is
    anchored. Everything else stays independent of it.

    Subclasses implement :meth:`_render`, which draws the element and returns its markup
    together with its box.
    """

    def __init__(self) -> None:
        self._placement: CompassDirection | None = None

    @abc.abstractmethod
    def _render(self) -> tuple[str, BoundingBox]:
        """
        Draws the element in its own coordinate system.

        Returns
        -------
        tuple[str, BoundingBox]
            The SVG markup of the element and the rectangle it fills, both in the same
            local coordinates.
        """

    def draw(self) -> str:
        """Returns the SVG markup of the element, in its own coordinate system."""
        return self._render()[0]

    def bbox(self) -> BoundingBox:
        """
        Returns the rectangle the element fills, in its own coordinate system.

        What :class:`SVGCanvas` arranges a figure by: the boxes of the annotations decide
        how thick a strip along an edge has to be and, with that, how much room is left
        for the rendered image in the middle.
        """
        return self._render()[1]

    def fonts(self) -> list["Font"]:
        """
        Returns the typefaces the element sets its text in, none by default.

        Collected by :attr:`SVGCanvas.fonts` so that the renderer can be handed the very
        files the layout measured against.
        """
        return []

    @property
    def placement(self) -> CompassDirection | None:
        """
        Direction the element was added to a canvas under, ``None`` while unplaced.

        Set by :meth:`SVGCanvas.add`; there is rarely a reason to assign it directly.
        """
        return self._placement

    @placement.setter
    def placement(self, arg: CompassDirection | None):
        self._placement = arg

    def _faces(self, point: str) -> bool:
        """Whether the element is placed towards the given compass point."""
        return self._placement is not None and point in self._placement.value

    @property
    def _toward_center_x(self) -> int:
        """
        Direction the middle of the canvas lies in horizontally: ``1`` for an element on
        the western edge, ``-1`` for one on the eastern edge.

        An element that is placed north or south is not on either side, and is treated
        like an eastern one -- which is where a scene tall enough to warrant a north or
        south placement of a vertical colorbar leaves the room for it.
        """
        return 1 if self._faces("W") else -1

    @property
    def _toward_center_y(self) -> int:
        """
        Direction the middle of the canvas lies in vertically: ``1`` for an element on the
        northern edge, ``-1`` for one on the southern edge.

        An element that is placed west or east is on neither, and is treated like a
        northern one.
        """
        return -1 if self._faces("S") else 1


class _TextLine(NamedTuple):
    """One line of a :class:`TextAnnotation`, as it is handed to the layout."""

    text: str
    font_size: float
    color: Color
    weight: int
    name: str


class TextAnnotation(AnnotationElement):
    """
    A block of text: a heading, a subheading and any number of body lines.

    The lines are stacked from the top down, each in its own size and color, and the
    block is anchored as a whole -- left, centered or right, following the edge of the
    canvas it is placed at unless :attr:`anchor` says otherwise. SVG breaks no lines by
    itself, so :attr:`text` is a line per entry.

    Parameters
    ----------
    heading
        First and largest line of the block.
    subheading
        Second line, smaller than the heading.
    text
        Body lines, one entry per line.

    Examples
    --------
    .. code-block:: python
        :caption: A title in the upper left corner.
        :linenos:

        title = TextAnnotation("Freeze drying", "Sublimation front after 12 s")
        title.color_heading = fefa.darkblue
        canvas.add(title, CompassDirection.NORTHWEST)
    """

    def __init__(
        self,
        heading: str | None = None,
        subheading: str | None = None,
        text: Sequence[str] = (),
    ) -> None:
        super().__init__()
        self.heading = heading
        self.subheading = subheading
        self.text = text
        self.anchor = None
        self.rotation = 0.0
        self.color_heading = Color("#000")
        self.color_subheading = Color("#000")
        self.color_text = Color("#000")
        self.font = font_default()
        self.font_size_heading = 21
        self.font_size_subheading = 14
        self.font_size_text = 8
        self.line_height = 1.15

    def _lines(self) -> list[_TextLine]:
        """
        Returns the lines of the block, from top to bottom.

        The single place the content of a text block is put together, so a subclass adds
        a line of its own by extending it rather than by touching the layout. Font sizes
        are handed on in user units, the unit everything is drawn in.
        """
        lines = []

        if self.heading:
            lines.append(
                _TextLine(
                    self.heading,
                    self._font_size_heading,
                    self.color_heading,
                    400,
                    "title",
                )
            )
        if self.subheading:
            lines.append(
                _TextLine(
                    self.subheading,
                    self._font_size_subheading,
                    self.color_subheading,
                    500,
                    "subtitle",
                )
            )
        for no, line in enumerate(self.text):
            lines.append(
                _TextLine(
                    line, self._font_size_text, self.color_text, 400, f"text-line-{no}"
                )
            )

        return lines

    def fonts(self) -> list[Font]:
        return [self.font]

    def _render(self) -> tuple[str, BoundingBox]:
        lines = self._lines()
        if not lines:
            return "", BoundingBox()

        anchor = self.anchor_resolved
        bounds = _Bounds()
        svg = ""
        y = 0.0

        for line in lines:
            svg += _tag_text(
                0,
                y,
                line.text,
                line.font_size,
                line.color,
                self.font,
                anchor=anchor,
                weight=line.weight,
                name=line.name,
            )
            bounds.add_text(0, y, line.text, line.font_size, self.font, anchor)
            y += line.font_size * self.line_height

        return _rotate(svg, bounds.box, self.rotation)

    @property
    def anchor_resolved(self) -> str:
        """
        The text anchor the block is actually drawn with.

        Follows :attr:`anchor` where it is set. Otherwise the block is anchored towards
        the edge of the canvas it sits at -- left at a western placement, right at an
        eastern one, centered anywhere else -- so that its lines line up with the edge
        instead of drifting away from it. A rotated block is always centered, since it
        runs along the edge rather than against it.
        """
        if self.anchor is not None:
            return self.anchor
        if self.rotation:
            return "middle"
        if self._faces("W"):
            return "start"
        if self._faces("E"):
            return "end"

        return "middle"

    @property
    def anchor(self) -> str | None:
        """
        Horizontal anchor of the block: ``"start"``, ``"middle"`` or ``"end"``.

        ``None`` (default) derives it from the placement, see :attr:`anchor_resolved`.
        """
        return self._anchor

    @anchor.setter
    def anchor(self, arg: str | None):
        self._anchor = arg

    @property
    def rotation(self) -> float:
        """
        Angle the block is turned by, in degrees, clockwise about its own center.

        ``-90`` makes the text read bottom-to-top, ``90`` top-to-bottom, which is how a
        heading is set alongside a vertical colorbar. The reported box turns with it.
        """
        return self._rotation

    @rotation.setter
    def rotation(self, arg: float):
        self._rotation = float(arg)

    @property
    def heading(self) -> str | None:
        """
        First line of the block, in the largest of its sizes.

        It is set as a single line, so it should not run long.
        """
        return self._heading

    @heading.setter
    def heading(self, arg: str | None):
        self._heading = arg

    @property
    def subheading(self) -> str | None:
        """
        Second line of the block, smaller than the heading and set in a single line.
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
        Body of the block, one entry per line.

        SVG inserts no line breaks of its own, so a paragraph has to arrive already
        broken into lines.
        """
        return self._text

    @text.setter
    def text(self, arg: Sequence[str]):
        self._text = list(arg)

    @property
    def color_heading(self) -> Color:
        """:class:`Color` of the heading."""
        return self._color_heading

    @color_heading.setter
    def color_heading(self, arg: Color):
        self._color_heading = arg

    @property
    def color_subheading(self) -> Color:
        """:class:`Color` of the subheading."""
        return self._color_subheading

    @color_subheading.setter
    def color_subheading(self, arg: Color):
        self._color_subheading = arg

    @property
    def color_text(self) -> Color:
        """:class:`Color` of the body lines."""
        return self._color_text

    @color_text.setter
    def color_text(self, arg: Color):
        self._color_text = arg

    @property
    def font(self) -> Font:
        """
        Typeface the block is set in, see :class:`Font`.

        Assign one carrying a file to have the block measured rather than estimated.
        """
        return self._font

    @font.setter
    def font(self, arg: Font):
        self._font = arg

    @property
    def font_family(self) -> str:
        """
        Font stack the block is set in, i.e. the family of its :attr:`font`.

        A way into the stack, for adding a fallback to it or reordering it. It leaves the
        file the block is measured against where it is, so switching to a typeface of a
        different width means assigning a whole :attr:`font` rather than a family alone.
        """
        return self._font.family

    @font_family.setter
    def font_family(self, arg: str):
        self._font.family = arg

    @property
    def font_size_heading(self) -> float:
        """Font size of the heading, in points."""
        return px2pt(self._font_size_heading)

    @font_size_heading.setter
    def font_size_heading(self, arg: float):
        self._font_size_heading = pt2px(arg)

    @property
    def font_size_subheading(self) -> float:
        """Font size of the subheading, in points."""
        return px2pt(self._font_size_subheading)

    @font_size_subheading.setter
    def font_size_subheading(self, arg: float):
        self._font_size_subheading = pt2px(arg)

    @property
    def font_size_text(self) -> float:
        """Font size of the body lines, in points."""
        return px2pt(self._font_size_text)

    @font_size_text.setter
    def font_size_text(self, arg: float):
        self._font_size_text = pt2px(arg)

    @property
    def line_height(self) -> float:
        """Distance between two lines, as a multiple of the font size."""
        return self._line_height

    @line_height.setter
    def line_height(self, arg: float):
        self._line_height = arg


class TimestampAnnotation(TextAnnotation):
    """
    The point in time a frame of a video stands at.

    A text block whose last line carries the time itself, so that a frame states what it
    shows while the rest of the figure stays as it is. Rendering a sequence means setting
    :attr:`time` per frame and leaving everything else alone -- the label keeps its
    number of decimals throughout, so it does not jitter in width from frame to frame.

    Parameters
    ----------
    time
        Point in time the frame shows, in the unit it is labelled in.
    unit
        Unit written after the value, ``""`` for none.
    precision
        Number of decimals the value is written with.
    prefix
        Text written in front of the value, e.g. ``"t ="``.

    Examples
    --------
    .. code-block:: python
        :caption: The frame time in the upper right corner.
        :linenos:

        stamp = TimestampAnnotation(0.0, unit="s", prefix="t =")
        canvas.add(stamp, CompassDirection.NORTHEAST)

        for no, time in enumerate(times):
            stamp.time = time
            canvas.save(pth / f"frame-{no:05d}.svg")
    """

    def __init__(
        self,
        time: float = 0.0,
        *,
        unit: str = "s",
        precision: int = 1,
        prefix: str = "",
        heading: str | None = None,
    ) -> None:
        super().__init__(heading=heading)
        self.time = time
        self.unit = unit
        self.precision = precision
        self.prefix = prefix
        self.format = None
        self.color_time = Color("#000")
        self.font_size_time = 14

    def _lines(self) -> list[_TextLine]:
        return [
            *super()._lines(),
            _TextLine(
                self.label, self._font_size_time, self.color_time, 400, "timestamp"
            ),
        ]

    @property
    def label(self) -> str:
        """
        The time as it is written on the figure.

        Assembled from :attr:`prefix`, :attr:`time` at :attr:`precision` decimals and
        :attr:`unit`, unless :attr:`format` takes over.
        """
        if self.format is not None:
            if callable(self.format):
                return str(self.format(self.time))
            return self.format.format(self.time)

        value = f"{float(self.time):.{max(self.precision, 0)}f}"

        return " ".join(part for part in (self.prefix, value, self.unit) if part)

    @property
    def time(self) -> float:
        """Point in time the frame shows, in the unit it is labelled in."""
        return self._time

    @time.setter
    def time(self, arg: float):
        self._time = float(arg)

    @property
    def format(self) -> str | None:
        """
        How the time is written, overriding :attr:`prefix`, :attr:`precision` and
        :attr:`unit`.

        Either a format string applied as ``format.format(time)`` -- ``"{:.2f} min"`` --
        or a callable turning the time into the label. ``None`` (default) assembles the
        label from the individual parts.
        """
        return self._format

    @format.setter
    def format(self, arg):
        self._format = arg

    @property
    def prefix(self) -> str:
        """Text written in front of the value."""
        return self._prefix

    @prefix.setter
    def prefix(self, arg: str):
        self._prefix = arg

    @property
    def precision(self) -> int:
        """Number of decimals the value is written with."""
        return self._precision

    @precision.setter
    def precision(self, arg: int):
        self._precision = int(arg)

    @property
    def unit(self) -> str:
        """Unit written after the value, ``""`` for none."""
        return self._unit

    @unit.setter
    def unit(self, arg: str):
        self._unit = arg

    @property
    def color_time(self) -> Color:
        """:class:`Color` of the time itself."""
        return self._color_time

    @color_time.setter
    def color_time(self, arg: Color):
        self._color_time = arg

    @property
    def font_size_time(self) -> float:
        """Font size of the time itself, in points."""
        return px2pt(self._font_size_time)

    @font_size_time.setter
    def font_size_time(self, arg: float):
        self._font_size_time = pt2px(arg)


class TitledAnnotation(AnnotationElement, abc.ABC):
    """
    Base of the annotations that carry a title of their own.

    A colorbar and its heading belong together -- the heading names the quantity the bar
    reports, and moving one without the other makes no sense -- so instead of being two
    elements on the canvas they are one, with the title composed into it as a
    :class:`TextAnnotation`. :attr:`heading`, :attr:`subheading` and :attr:`text` reach
    straight through to it; :attr:`title` exposes it in full, for its colors and sizes.

    Where the title comes to rest is up to the subclass, which places it through
    :meth:`_render_title` -- generally on the side of the content that faces the edge of
    the canvas, leaving the side facing the middle to whatever has to be read together
    with the figure.
    """

    def __init__(self) -> None:
        super().__init__()
        self._title = TextAnnotation()
        self._font = font_default()
        self.spacing = 0.25

    def fonts(self) -> list[Font]:
        return [self._font, *self._title.fonts()]

    def _render_title(
        self,
        content: BoundingBox,
        side: str,
        *,
        align_to: BoundingBox | None = None,
        rotation: float = 0.0,
    ) -> tuple[str, BoundingBox]:
        """
        Draws the title just outside ``content``, on the given ``side``.

        The title is set off from the content by :attr:`spacing` and lined up with
        ``align_to`` (``content`` by default) across that side: on the anchor of the title
        for a side above or below, centered for one to the left or right.

        Parameters
        ----------
        content
            Box the title is placed against.
        side
            Compass point of the side, one of ``"N"``, ``"E"``, ``"S"``, ``"W"``.
        align_to
            Box the title is lined up with across the side, e.g. the bar of a colorbar
            rather than everything drawn around it. Defaults to ``content``.
        rotation
            Angle the title is turned by, see :attr:`TextAnnotation.rotation`.
        """
        self._title.placement = self.placement
        self._title.rotation = rotation

        markup, box = self._title._render()
        if not markup:
            return "", BoundingBox()

        align_to = content if align_to is None else align_to

        if side in ("N", "S"):
            anchor = self._title.anchor_resolved
            if anchor == "start":
                dx = align_to.x - box.x
            elif anchor == "end":
                dx = align_to.right - box.right
            else:
                dx = align_to.center_x - box.center_x
            dy = (
                content.y - self._spacing - box.bottom
                if side == "N"
                else content.bottom + self._spacing - box.y
            )
        else:
            dy = align_to.center_y - box.center_y
            dx = (
                content.x - self._spacing - box.right
                if side == "W"
                else content.right + self._spacing - box.x
            )

        return _translate(markup, dx, dy), box.translated(dx, dy)

    @property
    def title(self) -> TextAnnotation:
        """
        The title block of the annotation.

        Assign a :class:`TextAnnotation` of its own to it, or reach into the one that is
        there to set its colors and sizes.
        """
        return self._title

    @title.setter
    def title(self, arg: TextAnnotation):
        self._title = arg

    @property
    def heading(self) -> str | None:
        """Heading of the annotation, see :attr:`TextAnnotation.heading`."""
        return self._title.heading

    @heading.setter
    def heading(self, arg: str | None):
        self._title.heading = arg

    @property
    def subheading(self) -> str | None:
        """Subheading of the annotation, see :attr:`TextAnnotation.subheading`."""
        return self._title.subheading

    @subheading.setter
    def subheading(self, arg: str | None):
        self._title.subheading = arg

    @property
    def text(self) -> list[str]:
        """Text lines of the annotation, see :attr:`TextAnnotation.text`."""
        return self._title.text

    @text.setter
    def text(self, arg: Sequence[str]):
        self._title.text = arg

    @property
    def font(self) -> Font:
        """
        Typeface the annotation is set in, title included, see :class:`Font`.

        Assign a font to the :attr:`title` itself afterwards to set it apart from the
        rest.
        """
        return self._font

    @font.setter
    def font(self, arg: Font):
        self._font = arg
        self._title.font = arg

    @property
    def font_family(self) -> str:
        """
        Font stack the annotation is set in, i.e. the family of its :attr:`font`.

        A way into the stack, for adding a fallback to it or reordering it. It leaves the
        file the annotation is measured against where it is, so switching to a typeface of
        a different width means assigning a whole :attr:`font` rather than a family alone.
        """
        return self._font.family

    @font_family.setter
    def font_family(self, arg: str):
        self._font.family = arg
        self._title.font_family = arg

    @property
    def spacing(self) -> float:
        """Gap kept between the parts of the annotation, in centimeters."""
        return px2cm(self._spacing)

    @spacing.setter
    def spacing(self, arg: float):
        self._spacing = cm2px(arg)


class GradientAnnotation(TitledAnnotation, abc.ABC):
    """
    A colorbar: a bar of color with an axis, ticks and a heading.

    The bar is drawn along its own origin -- from ``(0, 0)`` to the far corner of the bar
    -- with everything else arranged around it:

    * The ticks face the middle of the canvas, so they are read between the bar and the
      figure they belong to, and the heading faces the edge, where nothing else competes
      for the room. Which side that is follows the :attr:`~AnnotationElement.placement`
      the canvas hands over.
    * A vertical bar carries its heading rotated alongside it rather than on top, since a
      tall bar leaves no width for a horizontal line of text.
    * The exponent, where one is given, sits at the high end of the axis, and the NaN
      swatch at the low end -- outside the scale it does not belong to.

    Parameters
    ----------
    colors
        Colors of the gradient, see :attr:`gradient_colors`.
    ticks
        Tick labels, in ascending order, see :attr:`ticks`.

    See Also
    --------
    SmoothGradientAnnotation : Colors blended continuously.
    SegmentedGradientAnnotation : Colors in bands, ticks on their boundaries.
    DiscreteGradientAnnotation : Colors in bands, ticks in their middle.
    """

    def __init__(
        self,
        colors: Sequence[Color] = (),
        ticks: Sequence[str] = (),
    ) -> None:
        super().__init__()
        self.gradient_colors = colors
        self.ticks = ticks
        self.orientation = Orientation.VERTICAL
        self.color_ticks = Color("#000")
        self.color_nan = None
        self.exponent = None
        self.font_size_ticks = 12
        self.gradient_height = 0.6
        self.gradient_length = 10
        self.line_width = 0.06
        self.roundness = 0.05
        self.seperator_decimal = "DOT"
        self.seperator_exponent = MultiplicationSymbol.CROSS
        self.text_nan = "NaN"
        self.tick_length = 0.25

    @abc.abstractmethod
    def _stops(self) -> str:
        """Returns the ``<stop>`` elements the gradient is built from."""

    def _tick_fractions(self) -> list[float]:
        """
        Returns the position of every tick along the bar, as a fraction of its length
        measured from the low end.

        The ticks are spread evenly and include both ends, since a colorbar is drawn as a
        band between its limits and the ends of that band are values in their own right.
        """
        count = len(self.ticks)
        if count < 2:
            return [0.5] * count

        return [no / (count - 1) for no in range(count)]

    @property
    def _bar(self) -> BoundingBox:
        """The bar itself, the box everything else is arranged around."""
        if self.orientation is Orientation.VERTICAL:
            return BoundingBox(0, 0, self._gradient_height, self._gradient_length)

        return BoundingBox(0, 0, self._gradient_length, self._gradient_height)

    def _render(self) -> tuple[str, BoundingBox]:
        bounds = _Bounds()
        svg = ""

        if self.gradient_colors:
            svg += self._tag_gradient()
            bounds.add_box(self._bar)

        if self.ticks:
            svg += self._tag_axis()
            svg += self._tag_ticks(bounds)

        if self.exponent is not None:
            svg += self._tag_exponent(bounds)

        if self.color_nan is not None:
            svg += self._tag_nan(bounds)

        svg = f"<g>{svg}</g>" if svg else svg

        side, rotation = self._side_title()
        title, box = self._render_title(
            bounds.box, side, align_to=self._bar, rotation=rotation
        )
        bounds.add_box(box)

        return svg + title, bounds.box

    def _side_title(self) -> tuple[str, float]:
        """
        Returns the side the heading is placed on and the angle it is turned by.

        The heading takes the side of the bar the ticks leave free, i.e. the one facing
        away from the middle of the canvas. Alongside a vertical bar it runs bottom-to-top
        on the left and top-to-bottom on the right, so it always reads from the outside
        in.
        """
        if self.orientation is Orientation.VERTICAL:
            if self._toward_center_x > 0:
                return "W", -90.0
            return "E", 90.0

        return ("N" if self._toward_center_y > 0 else "S"), 0.0

    def _tag_gradient(self) -> str:
        """
        Writes the bar together with the ``<linearGradient>`` filling it.

        The gradient is named after its own definition rather than at random, so that the
        same gradient always yields the same markup. Two gradients that differ in any way
        still end up with distinct names, and two that do not describe the very same
        element, so sharing a name does them no harm.
        """
        # a vertical gradient runs bottom to top, a horizontal one left to right
        if self.orientation is Orientation.VERTICAL:
            (x1, y1), (x2, y2) = (0, 1), (0, 0)
        else:
            (x1, y1), (x2, y2) = (0, 0), (1, 0)

        stops = self._stops()
        name = make_id((x1, y1), (x2, y2), stops)
        bar = self._bar

        return (
            f"<defs>"
            f'<linearGradient id="gradient-{name}" x1="{x1}" y1="{y1}" '
            f'x2="{x2}" y2="{y2}">{stops}</linearGradient>'
            f"</defs>"
            f'<rect class="gradient" x="{_num(bar.x)}" y="{_num(bar.y)}" '
            f'rx="{_num(self._roundness)}" ry="{_num(self._roundness)}" '
            f'width="{_num(bar.width)}" height="{_num(bar.height)}" '
            f'fill="url(#gradient-{name})"/>'
        )

    def _tag_axis(self) -> str:
        """Writes the axis line running along the tick side of the bar."""
        bar = self._bar
        inset = self._line_width / 2

        if self.orientation is Orientation.VERTICAL:
            x1 = x2 = bar.right if self._toward_center_x > 0 else bar.x
            y1, y2 = bar.y + inset, bar.bottom - inset
        else:
            y1 = y2 = bar.bottom if self._toward_center_y > 0 else bar.y
            x1, x2 = bar.x + inset, bar.right - inset

        return (
            f'<line class="axis" x1="{_num(x1)}" y1="{_num(y1)}" x2="{_num(x2)}" '
            f'y2="{_num(y2)}" stroke-linecap="round" '
            f'stroke="{self.color_ticks.str_hex}" '
            f'stroke-width="{_num(self._line_width)}"/>'
        )

    def _tag_ticks(self, bounds: _Bounds) -> str:
        """Writes the tick marks and their labels along the tick side of the bar."""
        bar = self._bar
        svg = ""

        for no, (fraction, tick) in enumerate(
            zip(self._tick_fractions(), self.ticks, strict=True)
        ):
            label = str(tick)
            if self.seperator_decimal == "COMMA":
                label = label.replace(".", ",")

            if self.orientation is Orientation.VERTICAL:
                sign = self._toward_center_x
                # the low end of a vertical bar is its bottom
                y1 = y2 = bar.bottom - self._along_bar(fraction)
                x1 = bar.right if sign > 0 else bar.x
                x2 = x1 + self._tick_length * sign
                x_label = x2 + self._spacing * sign
                y_label = y1
                anchor = "start" if sign > 0 else "end"
                valign = "middle"
            else:
                sign = self._toward_center_y
                x1 = x2 = bar.x + self._along_bar(fraction)
                y1 = bar.bottom if sign > 0 else bar.y
                y2 = y1 + self._tick_length * sign
                x_label = x1
                y_label = self._row_labels()
                anchor = "middle"
                valign = "top"

            bounds.add(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
            bounds.add_text(
                x_label, y_label, label, self._font_size_ticks, self.font, anchor, valign
            )

            svg += (
                f'<line class="tick tick-{no}" x1="{_num(x1)}" y1="{_num(y1)}" '
                f'x2="{_num(x2)}" y2="{_num(y2)}" stroke-linecap="round" '
                f'stroke="{self.color_ticks.str_hex}" '
                f'stroke-width="{_num(self._line_width)}"/>'
            )
            svg += _tag_text(
                x_label,
                y_label,
                label,
                self._font_size_ticks,
                self.color_ticks,
                self.font,
                anchor=anchor,
                valign=valign,
                name=f"tick-label-{no}",
            )

        return svg

    def _row_labels(self) -> float:
        """
        Returns the top of the row the labels of a horizontal bar are written in.

        Every run is hung off its own top edge, so a row below the bar starts where the
        ticks end, while one above it has to be lifted by its own height on top of that to
        come to rest clear of them.
        """
        bar = self._bar
        offset = self._tick_length + self._spacing

        if self._toward_center_y > 0:
            return bar.bottom + offset

        return bar.y - offset - self._font_size_ticks

    def _along_bar(self, fraction: float) -> float:
        """
        Turns a position along the bar into a distance from its low end.

        The two outermost ticks are pulled inwards by half a line width, so that they come
        to rest inside the rounded cap of the axis rather than on top of it.
        """
        position = self._gradient_length * fraction

        if fraction <= 0:
            return position + self._line_width / 2
        if fraction >= 1:
            return position - self._line_width / 2

        return position

    def _tag_exponent(self, bounds: _Bounds) -> str:
        """
        Writes the power of ten the tick values are to be read with.

        It goes at the high end of the axis -- to the right of a horizontal bar, above a
        vertical one -- in line with the tick labels, and is set off from the outermost of
        them by twice the usual gap, so that it reads as the factor of the whole scale
        rather than as part of the value it stands next to.
        """
        bar = self._bar
        separator = self.seperator_exponent.value
        exponent = str(self.exponent)
        if self.seperator_decimal == "COMMA":
            exponent = exponent.replace(".", ",")

        if self.orientation is Orientation.VERTICAL:
            offset = self._tick_length + self._spacing
            if self._toward_center_x > 0:
                x, anchor = bar.right + offset, "start"
            else:
                x, anchor = bar.x - offset, "end"
            y = bar.y - 2 * self._spacing - self._font_size_ticks
        else:
            x, anchor = bar.right + 2 * self._spacing, "start"
            y = self._row_labels()

        text = f"{separator} 10{exponent}"
        bounds.add_text(x, y, text, self._font_size_ticks, self.font, anchor)

        content = (
            f"{_escape(separator)} 10"
            f'<tspan dy="{_num(-0.2 * self._font_size_ticks)}" '
            f'font-size="{_num(0.8 * self._font_size_ticks)}">{_escape(exponent)}</tspan>'
        )

        return _tag_text(
            x,
            y,
            text,
            self._font_size_ticks,
            self.color_ticks,
            self.font,
            anchor=anchor,
            name="exponent",
            content=content,
        )

    def _tag_nan(self, bounds: _Bounds) -> str:
        """
        Writes the swatch standing for the values that are not on the scale.

        It sits beyond the low end of the bar -- below a vertical one, to the left of a
        horizontal one -- separated from it by a gap, since it reports a value the
        gradient itself says nothing about. Its label goes next to the swatch rather than
        in the row or column of the tick labels, which keeps the two from running into
        each other where the swatch ends up alongside the outermost tick.
        """
        bar = self._bar
        size = self._gradient_height
        color = self.color_nan.str_rgb if self.color_nan else "none"
        valign = "middle"

        if self.orientation is Orientation.VERTICAL:
            inward = self._toward_center_x > 0
            x, y = bar.x, bar.bottom + self._spacing
            x_label = (bar.right + self._spacing) if inward else (bar.x - self._spacing)
            y_label = y + size / 2
            anchor = "start" if inward else "end"
        else:
            x, y = bar.x - self._spacing - size, bar.y
            x_label = x - self._spacing
            y_label = y + size / 2
            anchor = "end"

        bounds.add(x, y, size, size)
        bounds.add_text(
            x_label,
            y_label,
            self.text_nan,
            self._font_size_ticks,
            self.font,
            anchor,
            valign,
        )

        return (
            f'<rect class="nan" x="{_num(x)}" y="{_num(y)}" rx="{_num(self._roundness)}" '
            f'ry="{_num(self._roundness)}" width="{_num(size)}" height="{_num(size)}" '
            f'fill="{color}"/>'
        ) + _tag_text(
            x_label,
            y_label,
            self.text_nan,
            self._font_size_ticks,
            self.color_ticks,
            self.font,
            anchor=anchor,
            valign=valign,
            name="nan-label",
        )

    @property
    def color_nan(self) -> Color | None:
        """
        :class:`Color` standing for the values that are not on the scale.

        ``None`` (default) leaves the swatch off the colorbar.
        """
        return self._color_nan

    @color_nan.setter
    def color_nan(self, arg: Color | None):
        self._color_nan = arg

    @property
    def color_ticks(self) -> Color:
        """:class:`Color` of the axis, its ticks and their labels."""
        return self._color_ticks

    @color_ticks.setter
    def color_ticks(self, arg: Color):
        self._color_ticks = arg

    @property
    def exponent(self) -> float | int | str | None:
        """
        Power of ten the tick values are to be read with, ``None`` (default) for none.
        """
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
        """Font size of the tick labels, in points."""
        return px2pt(self._font_size_ticks)

    @font_size_ticks.setter
    def font_size_ticks(self, arg: float):
        self._font_size_ticks = pt2px(arg)

    @property
    def gradient_colors(self) -> list[Color]:
        """Colors of the bar, from its low end to its high end."""
        return self._gradient_colors

    @gradient_colors.setter
    def gradient_colors(self, arg: Sequence[Color]):
        self._gradient_colors = list(arg)

    @property
    def gradient_height(self) -> float:
        """Thickness of the bar across the axis it carries, in centimeters."""
        return px2cm(self._gradient_height)

    @gradient_height.setter
    def gradient_height(self, arg: float):
        self._gradient_height = cm2px(arg)

    @property
    def gradient_length(self) -> float:
        """Length of the bar along the axis it carries, in centimeters."""
        return px2cm(self._gradient_length)

    @gradient_length.setter
    def gradient_length(self, arg: float):
        self._gradient_length = cm2px(arg)

    @property
    def line_width(self) -> float:
        """Stroke width of the axis and its ticks, in centimeters."""
        return px2cm(self._line_width)

    @line_width.setter
    def line_width(self, arg: float):
        self._line_width = cm2px(arg)

    @property
    def orientation(self) -> Orientation:
        """
        Whether the bar runs from bottom to top (:attr:`~.Orientation.VERTICAL`, the
        default) or from left to right (:attr:`~.Orientation.HORIZONTAL`).
        """
        return self._orientation

    @orientation.setter
    def orientation(self, arg: Orientation):
        self._orientation = arg

    @property
    def roundness(self) -> float:
        """Corner radius of the bar and of the NaN swatch, in centimeters."""
        return px2cm(self._roundness)

    @roundness.setter
    def roundness(self, arg: float):
        self._roundness = cm2px(arg)

    @property
    def seperator_decimal(self) -> str:
        """Decimal separator of the tick labels, either ``"COMMA"`` or ``"DOT"``."""
        return self._seperator_decimal

    @seperator_decimal.setter
    def seperator_decimal(self, arg: str):
        self._seperator_decimal = arg

    @property
    def seperator_exponent(self) -> MultiplicationSymbol:
        """Multiplication sign written in front of the exponent."""
        return self._seperator_exponent

    @seperator_exponent.setter
    def seperator_exponent(self, arg: MultiplicationSymbol):
        self._seperator_exponent = arg

    @property
    def text_nan(self) -> str:
        """Label of the NaN swatch, ``"NaN"`` by default."""
        return self._text_nan

    @text_nan.setter
    def text_nan(self, arg: str):
        self._text_nan = arg

    @property
    def tick_length(self) -> float:
        """Length of the tick marks, in centimeters."""
        return px2cm(self._tick_length)

    @tick_length.setter
    def tick_length(self, arg: float):
        self._tick_length = cm2px(arg)

    @property
    def ticks(self) -> list[str]:
        """
        Tick labels, in ascending order.

        They are placed by their position in the sequence rather than by their value, and
        the first of them lands on the low end of the bar -- at the bottom of a vertical
        one, at the left of a horizontal one.
        """
        return self._ticks

    @ticks.setter
    def ticks(self, arg: Sequence[str]):
        self._ticks = list(arg)


class SmoothGradientAnnotation(GradientAnnotation):
    """
    A colorbar whose colors blend continuously into one another.

    The counterpart of :class:`~porescene.color.gradient.SmoothGradient`: the colors are
    sampled along the same blend the data was colored with, so the bar reports the scale
    as it was applied.
    """

    def _stops(self) -> str:
        gradient = SmoothGradient(self.gradient_colors)

        return "".join(
            f'<stop offset="{_num(round(value * 100, 6))}%" '
            f'stop-color="{gradient(value)[0].str_rgb}"/>'
            for value in np.linspace(0.0, 1.0, 100)
        )


class SegmentedGradientAnnotation(GradientAnnotation):
    """
    A colorbar whose colors stand in bands of equal width, with hard edges between them.

    The counterpart of :class:`~porescene.color.gradient.SegmentedGradient`. The ticks
    fall on the boundaries between the bands, so a band is read off the two values it
    lies between -- give one tick more than there are colors.
    """

    def _stops(self) -> str:
        count = len(self.gradient_colors)
        width = 1 / count if count else 1.0
        stops = ""

        for no, color in enumerate(self.gradient_colors):
            stops += (
                f'<stop offset="{_num(round(width * no * 100, 6))}%" '
                f'stop-color="{color.str_rgb}"/>'
            )
            if no < count - 1:
                stops += (
                    f'<stop offset="{_num(round(width * (no + 1) * 100, 6))}%" '
                    f'stop-color="{color.str_rgb}"/>'
                )

        return stops


class DiscreteGradientAnnotation(SegmentedGradientAnnotation):
    """
    A colorbar whose colors stand for values of their own rather than for ranges.

    Drawn in bands like :class:`SegmentedGradientAnnotation`, but ticked in the middle of
    every band instead of on its boundaries, and with the axis broken up to match -- one
    tick per color, each naming what its band stands for.
    """

    def _tick_fractions(self) -> list[float]:
        count = len(self.ticks)

        return [(no + 0.5) / count for no in range(count)]

    def _tag_axis(self) -> str:
        """Writes the axis as one dash per tick, centered under its band."""
        bar = self._bar
        count = len(self.ticks)
        step = self._gradient_length / count
        dash = 0.6 * step

        if self.orientation is Orientation.VERTICAL:
            x1 = x2 = bar.right if self._toward_center_x > 0 else bar.x
            y1, y2 = bar.y, bar.bottom
        else:
            y1 = y2 = bar.bottom if self._toward_center_y > 0 else bar.y
            x1, x2 = bar.x, bar.right

        return (
            f'<line class="axis" x1="{_num(x1)}" y1="{_num(y1)}" x2="{_num(x2)}" '
            f'y2="{_num(y2)}" stroke-dashoffset="{_num(-0.5 * dash)}" '
            f'stroke-dasharray="{_num(step - dash)} {_num(dash)}" '
            f'stroke-linecap="round" stroke="{self.color_ticks.str_hex}" '
            f'stroke-width="{_num(self._line_width)}"/>'
        )


class LabelsAnnotation(TitledAnnotation):
    """
    A legend: a column of colored boxes, each with what it stands for written next to it.

    What a colorbar is for a continuous quantity, this is for a handful of named states --
    frozen, sublimating, dry -- that carry no scale to put ticks on.

    The boxes take the side of the column that faces the edge of the canvas, so the labels
    read towards the figure they explain.

    Parameters
    ----------
    labels
        Pairs of :class:`Color` and label to start with, see :meth:`add_label`.

    Examples
    --------
    .. code-block:: python
        :caption: A legend in the upper left corner.
        :linenos:

        legend = LabelsAnnotation()
        legend.add_label(fefa.lightgreen, "frozen")
        legend.add_label(fefa.pink, "sublimation")
        legend.add_label(fefa.yellow, "dry")
        legend.heading = "Cluster state"
        canvas.add(legend, CompassDirection.NORTHWEST)
    """

    def __init__(self, labels: Iterable[tuple[Color, str]] = ()) -> None:
        super().__init__()
        self._labels = [(color, text) for color, text in labels]
        self.box_size = (0.6, 0.6)
        self.color_labeltext = Color("#000")
        self.font_size_labeltext = 14
        self.roundness = 0.1

    def __iter__(self) -> Iterator[tuple[Color, str]]:
        """Returns a fresh iterator over the ``(color, label)`` pairs."""
        return iter(self._labels)

    def __len__(self) -> int:
        """Returns the number of labels."""
        return len(self._labels)

    def add_label(self, color: Color, text: str) -> Self:
        """Adds a label of the given :class:`Color` to the bottom of the column."""
        self._labels.append((color, text))
        return self

    def _render(self) -> tuple[str, BoundingBox]:
        bounds = _Bounds()
        width, height = self._box_size
        svg = ""
        y = 0.0

        # the boxes face the edge of the canvas, so the labels read towards the figure
        flipped = self._faces("E")

        for no, (color, text) in enumerate(self._labels):
            x_box = -width if flipped else 0.0
            x_label = x_box - self._spacing if flipped else width + self._spacing
            y_label = y + height / 2
            anchor = "end" if flipped else "start"

            bounds.add(x_box, y, width, height)
            bounds.add_text(
                x_label,
                y_label,
                text,
                self._font_size_labeltext,
                self.font,
                anchor,
                "middle",
            )

            svg += (
                f'<rect class="label-box label-box-{no}" x="{_num(x_box)}" y="{_num(y)}" '
                f'rx="{_num(self._roundness)}" ry="{_num(self._roundness)}" '
                f'width="{_num(width)}" height="{_num(height)}" '
                f'fill="{color.str_rgb}"/>'
            )
            svg += _tag_text(
                x_label,
                y_label,
                text,
                self._font_size_labeltext,
                self.color_labeltext,
                self.font,
                anchor=anchor,
                valign="middle",
                name=f"label-text-{no}",
            )

            y += height + self._spacing

        svg = f"<g>{svg}</g>" if svg else svg

        title, box = self._render_title(bounds.box, "N")
        bounds.add_box(box)

        return svg + title, bounds.box

    @property
    def labels(self) -> list[tuple[Color, str]]:
        """The ``(color, label)`` pairs of the legend, top to bottom."""
        return list(self._labels)

    @property
    def box_size(self) -> tuple[float, float]:
        """Width and height of a single colored box, in centimeters."""
        return (px2cm(self._box_size[0]), px2cm(self._box_size[1]))

    @box_size.setter
    def box_size(self, arg: tuple[float, float]):
        self._box_size = (cm2px(arg[0]), cm2px(arg[1]))

    @property
    def color_labeltext(self) -> Color:
        """:class:`Color` of the labels."""
        return self._color_labeltext

    @color_labeltext.setter
    def color_labeltext(self, arg: Color):
        if not isinstance(arg, Color):
            raise TypeError(f"{__name__}.color_labeltext expected 'Color'")
        self._color_labeltext = arg

    @property
    def font_size_labeltext(self) -> float:
        """Font size of the labels, in points."""
        return px2pt(self._font_size_labeltext)

    @font_size_labeltext.setter
    def font_size_labeltext(self, arg: float):
        self._font_size_labeltext = pt2px(arg)

    @property
    def roundness(self) -> float:
        """Corner radius of the colored boxes, in centimeters."""
        return px2cm(self._roundness)

    @roundness.setter
    def roundness(self, arg: float):
        self._roundness = cm2px(arg)


class ImageAnnotation(AnnotationElement):
    """
    A raster image on the canvas -- typically the render the annotations explain.

    Handed to :meth:`SVGCanvas.add_image`, it becomes the middle of the figure and is
    scaled into whatever room the annotations leave. Added through :meth:`SVGCanvas.add`
    instead, it is placed against an edge at its own size, like any other annotation.

    The image is embedded in the SVG as a data URI by default, so the file stands on its
    own and can be moved, converted or handed on without dragging its render along.

    Parameters
    ----------
    path
        Path of the image file.
    size
        Width and height the image is drawn at, in centimeters. When ``None`` (default)
        it is read off the file, whose pixels are taken at
        :data:`~porescene.utility.DPI_CSS`. In the middle of a canvas only the ratio of
        the two matters, since the image is scaled to the room it is given either way.
    embed
        Whether to embed the image in the markup, by default ``True``. With ``False`` it
        is linked by its path instead, and the SVG only renders where that path resolves.
    """

    def __init__(
        self,
        path: Path,
        size: tuple[float, float] | None = None,
        *,
        embed: bool = True,
    ) -> None:
        super().__init__()
        self.path = Path(path)
        self.size = size
        self.embed = embed

    def _render(self) -> tuple[str, BoundingBox]:
        width, height = self._pixels()

        return (
            f'<image class="render" x="0" y="0" width="{_num(width)}" '
            f'height="{_num(height)}" preserveAspectRatio="xMidYMid meet" '
            f'href="{self._href()}"/>',
            BoundingBox(0, 0, width, height),
        )

    def _pixels(self) -> tuple[float, float]:
        """Returns the size the image is drawn at, in user units."""
        if self._size is None:
            with PIL.Image.open(self.path) as img:
                self._size = (float(img.width), float(img.height))

        return self._size

    def _href(self) -> str:
        """Returns what the ``<image>`` points at, see :attr:`embed`."""
        if not self.embed:
            return _escape(self.path.as_posix())

        mime = mimetypes.guess_type(self.path.name)[0] or "image/png"
        data = base64.b64encode(self.path.read_bytes()).decode()

        return f"data:{mime};base64,{data}"

    @property
    def size(self) -> tuple[float, float]:
        """
        Width and height the image is drawn at, in centimeters.

        Read off the file the first time it is asked for unless it was set, taking its
        pixels at :data:`~porescene.utility.DPI_CSS`. Assigning ``None`` reads it off the
        file again.
        """
        width, height = self._pixels()

        return (px2cm(width), px2cm(height))

    @size.setter
    def size(self, arg: tuple[float, float] | None):
        self._size = None if arg is None else (cm2px(arg[0]), cm2px(arg[1]))

    @property
    def path(self) -> Path:
        """Path of the image file."""
        return self._path

    @path.setter
    def path(self, arg: Path):
        self._path = Path(arg)
        self._size = None

    @property
    def embed(self) -> bool:
        """Whether the image is embedded in the markup rather than linked."""
        return self._embed

    @embed.setter
    def embed(self, arg: bool):
        self._embed = bool(arg)


class _Placement(NamedTuple):
    """An annotation together with the direction it was hung onto the canvas under."""

    element: AnnotationElement
    align: CompassDirection


class SVGCanvas:
    """
    The sheet a figure is composed on.

    Annotations are hung onto it by compass direction and the rendered image goes into the
    middle. What holds the two apart is the strip an edge with annotations on it claims:
    the canvas reads the box every annotation reports (:meth:`AnnotationElement.bbox`),
    reserves a strip as thick as the widest of them along that edge, lines them up in it,
    and scales the image into the rectangle left over -- so the image never runs under a
    colorbar, however large either of them turns out to be.

    Which edge an annotation claims follows the direction it was added under.
    :attr:`~porescene.utility.CompassDirection.NORTH` and
    :attr:`~porescene.utility.CompassDirection.SOUTH` claim the top and the bottom,
    :attr:`~porescene.utility.CompassDirection.WEST` and
    :attr:`~porescene.utility.CompassDirection.EAST` the left and the right. A corner
    direction names two edges, and the annotation takes the one it lies along: a wide one
    -- a horizontal colorbar, a line of text -- claims the top or bottom edge and is
    flushed left or right in it, a tall one claims the left or right edge and is flushed
    to the top or bottom. Several annotations on one edge are lined up along it in the
    order they were added.

    The canvas is measured in centimeters, and states that size in the file it writes, so
    a figure is laid out at the size it is meant to be printed at and lands at that size
    when it is placed in a manuscript. What resolution it is rasterized at is a separate
    question, answered when it is converted (see
    :func:`~porescene.utility.svg2png`), not when it is composed.

    Parameters
    ----------
    size
        Width and height of the canvas in centimeters, :attr:`DEFAULT_SIZE` by default.
    padding
        Margin in centimeters kept clear along the top, right, bottom and left edge. Does
        not apply to the background, which covers the canvas in full.
    background
        :class:`Color` the canvas is filled with, ``None`` (default) for a transparent
        one.
    spacing
        Gap in centimeters kept between two annotations on one edge, and between an edge
        and the image.

    Examples
    --------
    .. code-block:: python
        :caption: A render with a colorbar underneath it.
        :linenos:

        cb = SmoothGradientAnnotation(conf.colors, ["0", "0.5", "1"])
        cb.orientation = Orientation.HORIZONTAL
        cb.heading = "Saturation [-]"

        canvas = SVGCanvas()
        canvas.add_image(pth_render)
        canvas.add(cb, CompassDirection.SOUTH)
        pth = canvas.save(Path("saturation.svg"), stamp_id=True)
    """

    #: Width and height in centimeters of a canvas that is not sized explicitly.
    DEFAULT_SIZE = (20.0, 20.0)

    #: Margin in centimeters kept clear along the top, right, bottom and left edge.
    DEFAULT_PADDING = (0.5, 0.5, 0.5, 0.5)

    #: Gap in centimeters kept between the annotations, and between them and the image.
    DEFAULT_SPACING = 0.5

    _xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'

    def __init__(
        self,
        size: tuple[float, float] | None = None,
        padding: tuple[float, float, float, float] | None = None,
        *,
        background: Color | None = None,
        spacing: float | None = None,
    ) -> None:
        self.size = self.DEFAULT_SIZE if size is None else size
        self.padding = self.DEFAULT_PADDING if padding is None else padding
        self.background = background
        self.spacing = self.DEFAULT_SPACING if spacing is None else spacing
        self._placements: list[_Placement] = []
        self._image: ImageAnnotation | None = None

    def __iter__(self) -> Iterator[AnnotationElement]:
        """Returns a fresh iterator over the annotations, in the order they were added."""
        return (placement.element for placement in self._placements)

    def __len__(self) -> int:
        """Returns the number of annotations on the canvas, image excluded."""
        return len(self._placements)

    def add(
        self,
        element: AnnotationElement,
        align: CompassDirection = CompassDirection.NORTH,
    ) -> Self:
        """
        Hangs an annotation onto the canvas.

        Parameters
        ----------
        element
            The annotation to place.
        align
            Direction of the edge it is placed at, see the class documentation for how a
            corner direction is resolved.

        Returns
        -------
        Self
            The canvas, so that several annotations can be added in one go.
        """
        element.placement = align
        self._placements.append(_Placement(element, align))

        return self

    def add_image(self, image: Path | ImageAnnotation, **kwargs) -> Self:
        """
        Puts a rendered image into the middle of the canvas.

        The image is scaled -- keeping its aspect ratio -- to fill the room the
        annotations leave, and centered in it. Only one image sits in the middle; adding
        another replaces it.

        Parameters
        ----------
        image
            Path of the image file, or a prepared :class:`ImageAnnotation`.
        **kwargs
            Passed on to :class:`ImageAnnotation` when a path is given.

        Returns
        -------
        Self
            The canvas.
        """
        if not isinstance(image, ImageAnnotation):
            image = ImageAnnotation(image, **kwargs)

        self._image = image

        return self

    def center_region(self) -> BoundingBox:
        """
        Returns the rectangle in the middle that is left over for the image, in user
        units (see :class:`BoundingBox`).

        The canvas minus its padding minus the strips the annotations claim along the
        edges they were placed at. Collapses to an empty box where the annotations take
        up more room than there is.
        """
        return self._arrange()[1]

    def get_svg(self) -> str:
        """
        Returns the ``<svg>`` element of the figure, without the XML declaration.

        Everything is drawn from scratch, so a canvas can be rendered again after any of
        its annotations was changed -- which is what makes a series of video frames a
        matter of setting the time on a :class:`TimestampAnnotation` and saving again.
        """
        fragments, _ = self._arrange()

        return self._tag_open() + self._tag_background() + "".join(fragments) + "</svg>"

    @property
    def id(self) -> str:
        """
        Fingerprint of the figure, derived from the SVG markup it renders to.

        Since the markup describes the figure in full, canvases that differ in any respect
        -- color palette, limits, ticks, headings, geometry -- carry different
        fingerprints, while one that is left alone keeps its own across renders. Pass
        ``stamp_id`` to :meth:`save` to name the file after it.
        """
        return make_id(self.get_svg())

    def save(self, pth: Path, *, stamp_id: bool = False) -> Path:
        """
        Writes the figure to an SVG file.

        Parameters
        ----------
        pth
            Path of the file to write.
        stamp_id
            If ``True``, an ``id-<fingerprint>`` part is appended to the stem of the file
            (see :attr:`id`), so that figures differing in any respect are written side by
            side instead of overwriting each other. An already stamped path is restamped
            rather than extended, by default ``False``.

        Returns
        -------
        Path
            Path the file was written to, stamped where ``stamp_id`` asked for it.
        """
        svg = self.get_svg()

        if stamp_id:
            pth = _stamp_id(pth, make_id(svg))

        with pth.open(mode="w+", encoding="utf-8") as file:
            file.write(self._xml_declaration)
            file.write(svg)

        return pth

    def _arrange(self) -> tuple[list[str], BoundingBox]:
        """
        Lays the figure out.

        Every annotation is drawn once, sorted into the strip along the edge it claims,
        and moved into place there. What the strips leave over in the middle is the
        rectangle the image is scaled into.

        Returns
        -------
        tuple[list[str], BoundingBox]
            The markup of everything on the canvas, already moved into place, and the
            rectangle that was left for the image.
        """
        inner = BoundingBox.from_corners(
            self._padding[3],
            self._padding[0],
            self._size[0] - self._padding[1],
            self._size[1] - self._padding[2],
        )

        bands: dict[str, list[tuple[CompassDirection, str, BoundingBox]]] = {
            "N": [],
            "S": [],
            "W": [],
            "E": [],
        }
        for placement in self._placements:
            markup, box = placement.element._render()
            bands[_band_of(placement.align, box)].append((placement.align, markup, box))

        thickness = {
            "N": max((box.height for _, _, box in bands["N"]), default=0.0),
            "S": max((box.height for _, _, box in bands["S"]), default=0.0),
            "W": max((box.width for _, _, box in bands["W"]), default=0.0),
            "E": max((box.width for _, _, box in bands["E"]), default=0.0),
        }

        fragments = []
        for band, entries in bands.items():
            fragments += self._place_band(band, entries, inner)

        def _claimed(band: str) -> float:
            return thickness[band] + self._spacing if bands[band] else 0.0

        region = BoundingBox.from_corners(
            inner.x + _claimed("W"),
            inner.y + _claimed("N"),
            max(inner.right - _claimed("E"), inner.x + _claimed("W")),
            max(inner.bottom - _claimed("S"), inner.y + _claimed("N")),
        )

        # an image is left off rather than drawn at a scale of zero where the annotations
        # took up every last bit of the canvas
        if self._image is not None and region.width > 0 and region.height > 0:
            fragments.append(self._place_image(self._image, region))

        return fragments, region

    def _place_band(
        self,
        band: str,
        entries: list[tuple[CompassDirection, str, BoundingBox]],
        inner: BoundingBox,
    ) -> list[str]:
        """
        Moves the annotations of one strip into place.

        They are lined up along the strip -- side by side in a northern or southern one,
        one below the other in a western or eastern one -- and flushed against its ends
        according to the corner they were placed at, with the ones placed at the plain
        direction centered between them. Across the strip they all sit against the edge
        the strip runs along.
        """
        if not entries:
            return []

        along_x = band in ("N", "S")

        # a corner direction names the edge the strip runs along and the end of it the
        # annotation is flushed against; a plain one leaves that end open, i.e. centered
        groups: dict[str, list[tuple[str, BoundingBox]]] = {"-": [], "+": [], "0": []}
        for align, markup, box in entries:
            if along_x:
                key = "-" if "W" in align.value else ("+" if "E" in align.value else "0")
            else:
                key = "-" if "N" in align.value else ("+" if "S" in align.value else "0")
            groups[key].append((markup, box))

        fragments = []
        for key, group in groups.items():
            if not group:
                continue

            extent = sum(
                (box.width if along_x else box.height) for _, box in group
            ) + self._spacing * (len(group) - 1)

            if along_x:
                start = {
                    "-": inner.x,
                    "+": inner.right - extent,
                    "0": inner.center_x - extent / 2,
                }[key]
            else:
                start = {
                    "-": inner.y,
                    "+": inner.bottom - extent,
                    "0": inner.center_y - extent / 2,
                }[key]

            for markup, box in group:
                if along_x:
                    dx = start - box.x
                    dy = (inner.y if band == "N" else inner.bottom - box.height) - box.y
                    start += box.width + self._spacing
                else:
                    dy = start - box.y
                    dx = (inner.x if band == "W" else inner.right - box.width) - box.x
                    start += box.height + self._spacing

                fragments.append(_translate(markup, dx, dy))

        return fragments

    def _place_image(self, image: ImageAnnotation, region: BoundingBox) -> str:
        """
        Scales the image into ``region``, keeping its aspect ratio, and centers it there.
        """
        markup, box = image._render()

        if not box.width or not box.height:
            return markup

        scale = min(region.width / box.width, region.height / box.height)

        return _translate(
            markup,
            region.center_x - box.center_x * scale,
            region.center_y - box.center_y * scale,
            scale,
        )

    def _tag_open(self) -> str:
        """
        Writes the opening ``<svg>`` element.

        The physical size of the canvas goes on ``width`` and ``height``, so the figure
        arrives at the size it was composed at wherever it is placed, while the
        ``viewBox`` states the same size in the user units everything inside is drawn in.
        A renderer that is handed no resolution to measure a centimeter against cannot
        size such a file -- see the ``dpi`` of :func:`~porescene.utility.svg2png`.
        """
        width, height = self.size

        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" width="{_num(width)}cm" '
            f'height="{_num(height)}cm" '
            f'viewBox="0 0 {_num(self._size[0])} {_num(self._size[1])}" '
            f'font-weight="400">'
        )

    def _tag_background(self) -> str:
        """Writes the rectangle filling the canvas, empty for a transparent one."""
        if self.background is None:
            return ""

        return (
            f'<rect id="background" x="0" y="0" width="100%" height="100%" '
            f'fill="{self.background.str_rgba}"/>'
        )

    @property
    def fonts(self) -> list[Path]:
        """
        Font files everything on the canvas is set in, without duplicates.

        Hand them to :func:`~porescene.utility.svg2png` to render a figure in a typeface
        the machine has no copy of, so that the renderer draws with the very file the
        layout measured against instead of substituting one of its own:

        .. code-block:: python

            svg2png(canvas.save(pth), fonts=canvas.fonts)
        """
        paths: list[Path] = []
        for element in self:
            for font in element.fonts():
                if font.path is not None and font.path not in paths:
                    paths.append(font.path)

        return paths

    @property
    def image(self) -> ImageAnnotation | None:
        """The image in the middle of the canvas, see :meth:`add_image`."""
        return self._image

    @image.setter
    def image(self, arg: ImageAnnotation | None):
        self._image = arg

    @property
    def background(self) -> Color | None:
        """
        :class:`Color` the canvas is filled with, ``None`` for a transparent one.

        Covers the canvas in full, :attr:`padding` included.
        """
        return self._background

    @background.setter
    def background(self, arg: Color | None):
        self._background = arg

    @property
    def padding(self) -> tuple[float, float, float, float]:
        """
        Margin in centimeters kept clear along the top, right, bottom and left edge, in
        that order.

        The annotations are placed inside it and the image is scaled into what is left
        after that, so nothing but the background reaches the edge of the canvas.
        """
        return tuple(px2cm(value) for value in self._padding)

    @padding.setter
    def padding(self, arg: tuple[float, float, float, float]):
        if any(value < 0 for value in arg):
            raise ValueError(f"{__name__}.padding must not be negative")
        self._padding = tuple(cm2px(value) for value in arg)

    @property
    def size(self) -> tuple[float, float]:
        """
        Width and height of the canvas in centimeters.

        The size the figure is printed at, which the written file states as its own
        (see :meth:`get_svg`).
        """
        return (px2cm(self._size[0]), px2cm(self._size[1]))

    @size.setter
    def size(self, arg: tuple[float, float]):
        if arg[0] <= 0 or arg[1] <= 0:
            raise ValueError(f"{__name__}.size must be greater than zero")
        self._size = (cm2px(arg[0]), cm2px(arg[1]))

    @property
    def spacing(self) -> float:
        """Gap in centimeters kept between two annotations on one edge, and between an
        edge and the image."""
        return px2cm(self._spacing)

    @spacing.setter
    def spacing(self, arg: float):
        self._spacing = cm2px(arg)


def _band_of(align: CompassDirection, box: BoundingBox) -> str:
    """
    Returns the edge an annotation claims: ``"N"``, ``"E"``, ``"S"`` or ``"W"``.

    A plain direction names its edge outright. A corner names two, and the annotation
    takes the one it lies along -- a wide one the top or bottom edge, a tall one the left
    or right -- which is what puts a horizontal colorbar placed at
    :attr:`~porescene.utility.CompassDirection.SOUTHEAST` along the bottom of the figure
    and a vertical one down its right-hand side.
    """
    vertical = "N" if "N" in align.value else ("S" if "S" in align.value else "")
    horizontal = "W" if "W" in align.value else ("E" if "E" in align.value else "")

    if not horizontal:
        return vertical
    if not vertical:
        return horizontal

    return vertical if box.width >= box.height else horizontal
