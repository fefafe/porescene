"""
Sphinx extension: show a color strip under each ``Colormap`` enum member.

At build time this reads every colormap table from
``src/porescene/data/colormap`` and renders a horizontal strip PNG into
``docs/source/_static/image/colormap/<name>.png``. An
``autodoc-process-docstring`` handler then appends an ``.. image::`` directive
to each :class:`porescene.color.palette.Colormap` member so the strip appears
directly below that member in the API documentation.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from docutils import nodes
from PIL import Image
from sphinx import addnodes
from sphinx.application import Sphinx
from sphinx.util import logging

logger = logging.getLogger(__name__)

# Matches the ``ids`` of an enum-member attribute definition, e.g.
# ``porescene.color.palette.Colormap.ACTON`` -> member name ``ACTON``.
_MEMBER_ID = re.compile(r"\.Colormap\.([A-Za-z0-9_]+)$")

_STRIP_WIDTH = 512
_STRIP_HEIGHT = 28

# This file lives at docs/source/_ext/colormap_strips.py, so:
#   parents[1] -> docs/source     parents[3] -> repository root
_HERE = Path(__file__).resolve()
_COLORMAP_SRC = _HERE.parents[3] / "src" / "porescene" / "data" / "colormap"
_STRIP_OUT = _HERE.parents[1] / "_static" / "image" / "colormap"

# Source-relative URI used in the injected ``.. image::`` directive.
_STRIP_URI = "/_static/image/colormap/{name}.png"


def _render_strip(table: Path, out: Path) -> None:
    """
    Render a single colormap table to a horizontal strip PNG.
    """
    colors = np.fromfile(table, sep=" ").reshape((-1, 3))
    n = colors.shape[0]

    # Map each output column to its nearest sample. Continuous maps look
    # smooth; categorical maps show discrete blocks.
    idx = np.rint(np.linspace(0, n - 1, _STRIP_WIDTH)).astype(int)
    row = np.rint(colors[idx] * 255).astype(np.uint8)
    strip = np.broadcast_to(row, (_STRIP_HEIGHT, _STRIP_WIDTH, 3))

    Image.fromarray(strip, mode="RGB").save(out, optimize=True)


def generate_strips(app: Sphinx) -> None:
    """
    Render a strip for every colormap table (``builder-inited`` handler).
    """
    if not _COLORMAP_SRC.is_dir():
        logger.warning("colormap_strips: colormap source %s not found", _COLORMAP_SRC)
        return

    _STRIP_OUT.mkdir(parents=True, exist_ok=True)

    built = 0
    for table in sorted(_COLORMAP_SRC.glob("*.txt")):
        # Skip the LICENSE_*.txt / README.txt bookkeeping files.
        if table.stem.startswith("LICENSE") or table.stem == "README":
            continue

        out = _STRIP_OUT / f"{table.stem}.png"
        # Rebuild only when the source table is newer than the existing strip.
        if out.exists() and out.stat().st_mtime >= table.stat().st_mtime:
            continue

        try:
            _render_strip(table, out)
            built += 1
        except Exception:
            logger.warning(
                "colormap_strips: failed to render %s", table.name, exc_info=True
            )

    logger.info("colormap_strips: %d strip(s) rendered into %s", built, _STRIP_OUT)


def inject_strips(app: Sphinx, doctree: nodes.document) -> None:
    """
    Add a strip image under every documented ``Colormap`` member.

    autodoc does not emit ``autodoc-process-docstring`` for attributes (which
    is how enum members are documented), so the doctree is post-processed
    instead: each member's definition node gets an :class:`docutils.nodes.image`
    with a source-relative URI, added before the image collector runs (see the
    ``priority`` in :func:`setup`) so Sphinx copies and resolves it normally.
    """
    try:
        from porescene.color.palette import Colormap
    except Exception:
        return

    for signature in doctree.findall(addnodes.desc_signature):
        member = next(
            (m.group(1) for i in signature.get("ids", []) if (m := _MEMBER_ID.search(i))),
            None,
        )
        if member is None:
            continue
        try:
            value = Colormap[member].value
        except KeyError:
            continue
        if not (_STRIP_OUT / f"{value}.png").exists():
            continue

        desc = signature.parent
        content = next(
            (c for c in desc.children if isinstance(c, addnodes.desc_content)), None
        )
        if content is None:
            content = addnodes.desc_content()
            desc += content

        content += nodes.image(
            uri=_STRIP_URI.format(name=value),
            alt=f"{value} colormap",
            classes=["ps-colormap-strip"],
        )


def setup(app: Sphinx) -> dict[str, object]:
    app.connect("builder-inited", generate_strips)
    app.connect("doctree-read", inject_strips, priority=400)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
