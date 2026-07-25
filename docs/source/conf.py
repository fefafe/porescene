import sys
import tomllib
from pathlib import Path

import yaml
from pybtex.plugin import register_plugin

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent / "_ext"))

with (Path(__file__).resolve().parents[2] / "pyproject.toml").open("rb") as f:
    _pyproject = tomllib.load(f)

project = "PoreScene"
author = "Felix Faber"
copyright = (
    "%Y, Felix Faber / Otto von Guericke University Magdeburg, "
    "Thermal Process Engineering"
)
release = _pyproject["project"]["version"]
version = release

# --- Citation metadata for the Zotero Connector -----------------------------
# Sourced from CITATION.cff (single source of truth) and injected into the HTML
# <head> by _templates/page.html, so readthedocs.io is recognised as software.
with (Path(__file__).resolve().parents[2] / "CITATION.cff").open(encoding="utf-8") as f:
    _citation = yaml.safe_load(f)


def _cff_author(entry: dict) -> str:
    """Render one CITATION.cff author as ``Family, Given`` for citation_author."""
    family = str(entry.get("family-names", "")).strip()
    given = str(entry.get("given-names", "")).strip()
    if family and given:
        return f"{family}, {given}"
    return family or given or str(entry.get("name", "")).strip()


html_context = {
    "zotero_meta": {
        "title": _citation.get("title", project),
        "version": str(_citation.get("version", release)),
        "date": str(_citation.get("date-released", "")),
        "doi": str(_citation.get("doi", "")),
        "url": _citation.get("url", ""),
        "authors": [_cff_author(a) for a in _citation.get("authors", [])],
    }
}

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
    "sphinxcontrib.bibtex",
    "colormap_strips",
    "carousel",
]

pygments_style = "porescene_pygments.PoreSceneLight"
pygments_dark_style = "porescene_pygments.PoreSceneDark"

napoleon_numpy_docstring = True
napoleon_google_docstring = True

add_module_names = True

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}
autodoc_member_order = "groupwise"  # or "bysource" / "alphabetical"
autodoc_mock_imports = [
    "bpy",
    "bmesh",
    "mathutils",
    "resvg_py",
]


intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "h5py": ("https://docs.h5py.org/en/stable/", None),
    "pillow": ("https://pillow.readthedocs.io/en/stable/", None),
    "rich": ("https://rich.readthedocs.io/en/stable/", None),
    "bpy": ("https://docs.blender.org/api/current/", None),
    "matplotlib": ("https://matplotlib.org/stable/", None),
}

html_theme = "furo"
html_theme_options = {
    "source_repository": "https://github.com/fefafe/porescene",
    "source_branch": "main",
    "source_directory": "docs/source/",
}
templates_path = ["_templates"]
html_static_path = ["_static"]
html_css_files = ["porescene.css"]
html_js_files = ["copybutton.js", "references.js"]


# Furo's default sidebar, with a persistent "Home" link added above the
# navigation tree (see _templates/sidebar/home-link.html).
html_sidebars = {
    "**": [
        "sidebar/scroll-start.html",
        "sidebar/brand.html",
        "sidebar/search.html",
        "sidebar/home-link.html",
        "sidebar/navigation.html",
        "sidebar/ethical-ads.html",
        "sidebar/scroll-end.html",
    ]
}

exclude_patterns = ["api/modules.rst"]

from apa7_style import APAStyle  # type: ignore # noqa: E402

register_plugin("pybtex.style.formatting", "apa7", APAStyle)

bibtex_bibfiles = ["references.bib"]
bibtex_default_style = "apa7"
bibtex_reference_style = "label"
