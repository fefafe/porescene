"""
Sphinx extension: ``carousel``

Example::

    .. carousel::
       :interval: 2500

       .. figure:: /_static/image/carousel/slide-0.png
          :alt: Freeze-dried maltodextrin microstructure

          Microstructure of a freeze-dried sugar solution.

An image credit (copyright / license) is shown as a muted sub-line under each
caption. Per image, author the slide as ``.. slide::`` -- a ``figure`` that also
accepts ``:copyright:``, ``:license:`` and ``:license-url:``::

    .. carousel::
       :copyright: Felix Faber / OVGU          # shared default

       .. slide:: /_static/image/carousel/slide-0.png

          Own render (inherits the default copyright).

       .. slide:: /_static/image/carousel/slide-1.png
          :copyright: Jane Doe / ACME
          :license: CC BY 4.0

          A guest image with its own attribution.

The carousel's ``copyright`` / ``license`` options are the fallback used for any
slide that does not set its own, so a shared attribution need only be written
once. A ``license-url`` makes the license a link; well-known Creative Commons
names are linked automatically.
"""

from __future__ import annotations

from docutils import nodes
from docutils.parsers.rst import directives
from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective

# Default autoplay interval (ms) when ``:interval:`` is omitted
_DEFAULT_INTERVAL = 5000

# Canonical URLs for the Creative Commons names most likely on an image credit,
_CC_URLS = {
    "cc0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "cc0 1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "cc by 4.0": "https://creativecommons.org/licenses/by/4.0/",
    "cc by-sa 4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
    "cc by-nc 4.0": "https://creativecommons.org/licenses/by-nc/4.0/",
    "cc by-nc-sa 4.0": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
    "cc by-nd 4.0": "https://creativecommons.org/licenses/by-nd/4.0/",
}

# Copyright prefixes we should not double up with a leading "©".
_COPYRIGHT_PREFIXES = ("©", "(c)", "(C)", "Copyright")


_NEXT_BUTTON = (
    '<button class="ps-carousel-btn ps-carousel-prev" type="button" '
    'aria-label="Previous slide">&#10094;</button>'
    '<button class="ps-carousel-btn ps-carousel-next" type="button" '
    'aria-label="Next slide">&#10095;</button>'
    '<div class="ps-carousel-dots"></div>'
)


def _credit_inlines(
    copyright_: str | None, license_: str | None, license_url: str | None
) -> list[nodes.Node]:
    """
    Build the inline nodes for one slide's credit line (fresh per slide).

    Docutils nodes have a single parent, so this must be called once per slide
    rather than sharing one node list across figures.
    """
    parts: list[nodes.Node] = []
    if copyright_:
        text = copyright_.strip()
        if not text.startswith(_COPYRIGHT_PREFIXES):
            text = f"© {text}"
        parts.append(nodes.Text(text))
    if license_:
        name = license_.strip()
        url = license_url or _CC_URLS.get(name.lower())
        parts.append(nodes.reference("", name, refuri=url) if url else nodes.Text(name))

    credit: list[nodes.Node] = []
    for i, part in enumerate(parts):
        if i:
            credit.append(nodes.Text(" · "))
        credit.append(part)
    return credit


def _has_credit(figure: nodes.figure) -> bool:
    """Whether a slide already carries its own credit line."""
    return any(
        "ps-carousel-credit" in inline.get("classes", [])
        for inline in figure.findall(nodes.inline)
    )


def _add_credit(figure: nodes.figure, credit: list[nodes.Node]) -> None:
    """Append a credit sub-line into the figure's caption (creating one if needed)."""
    caption = next(figure.findall(nodes.caption), None)
    if caption is None:
        caption = nodes.caption()
        figure += caption
    caption += nodes.inline("", "", *credit, classes=["ps-carousel-credit"])


class SlideDirective(SphinxDirective):
    """A carousel slide: like ``figure``, plus per-image credit options."""

    required_arguments = 1
    final_argument_whitespace = True
    has_content = True
    option_spec = {
        "alt": directives.unchanged,
        "copyright": directives.unchanged,
        "license": directives.unchanged,
        "license-url": directives.uri,
    }

    def run(self) -> list[nodes.Node]:
        figure = nodes.figure()

        image = nodes.image(uri=directives.uri(self.arguments[0]))
        image["loading"] = "lazy"
        image["alt"] = self.options.get("alt", "")
        figure += image

        caption_nodes: list[nodes.Node] = []
        if self.content:
            parsed = nodes.Element()
            self.state.nested_parse(self.content, self.content_offset, parsed)
            if parsed.children and isinstance(parsed[0], nodes.paragraph):
                caption_nodes = parsed[0].children

        credit = _credit_inlines(
            self.options.get("copyright"),
            self.options.get("license"),
            self.options.get("license-url"),
        )
        if caption_nodes or credit:
            caption = nodes.caption("", "", *caption_nodes)
            if credit:
                caption += nodes.inline("", "", *credit, classes=["ps-carousel-credit"])
            figure += caption

        return [figure]


class CarouselDirective(SphinxDirective):
    """Wrap nested figures/images into a ``.ps-carousel`` slider."""

    has_content = True
    option_spec = {
        "interval": directives.positive_int,
        "class": directives.class_option,
        "copyright": directives.unchanged,
        "license": directives.unchanged,
        "license-url": directives.uri,
    }

    def run(self) -> list[nodes.Node]:
        parsed = nodes.Element()
        self.state.nested_parse(self.content, self.content_offset, parsed)

        slides: list[nodes.figure] = []
        for child in parsed.children:
            if isinstance(child, nodes.figure):
                slides.append(child)
            elif isinstance(child, nodes.image):
                # A bare `.. image::` becomes a slide too, wrapped so the
                # `.ps-carousel-slide img` selector still matches.
                slides.append(nodes.figure("", child))

        if not slides:
            error = self.state_machine.reporter.error(
                "carousel: expected at least one nested 'figure' or 'image'.",
                nodes.literal_block(self.block_text, self.block_text),
                line=self.lineno,
            )
            return [error]

        copyright_ = self.options.get("copyright")
        license_ = self.options.get("license")
        license_url = self.options.get("license-url")

        for i, figure in enumerate(slides):
            figure["classes"].append("ps-carousel-slide")
            if i == 0:
                figure["classes"].append("is-active")
            for image in figure.findall(nodes.image):
                image["loading"] = "lazy"
                # Without an explicit alt, Sphinx falls back to the file name;
                # treat un-described slides as decorative instead (the caption
                # is the text alternative).
                if not image.get("alt"):
                    image["alt"] = ""

            # Fall back to the carousel-wide credit only when the slide did not
            # supply its own (a `.. slide::` with :copyright:/:license:). The
            # credit reads as a sub-line inside the same <figcaption> bar.
            if not _has_credit(figure):
                credit = _credit_inlines(copyright_, license_, license_url)
                if credit:
                    _add_credit(figure, credit)

        interval = self.options.get("interval", _DEFAULT_INTERVAL)
        classes = " ".join(["ps-carousel", *self.options.get("class", [])])
        open_html = (
            f'<div class="{classes}" data-interval="{interval}">'
            '<div class="ps-carousel-track">'
        )
        close_html = f"</div>{_NEXT_BUTTON}</div>"

        return [
            nodes.raw("", open_html, format="html"),
            *slides,
            nodes.raw("", close_html, format="html"),
        ]


def setup(app: Sphinx) -> dict[str, object]:
    app.add_directive("carousel", CarouselDirective)
    app.add_directive("slide", SlideDirective)
    app.add_css_file("carousel.css")
    app.add_js_file("carousel.js")
    return {"parallel_read_safe": True, "parallel_write_safe": True}
