import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

with (Path(__file__).resolve().parents[2] / "pyproject.toml").open("rb") as f:
    _pyproject = tomllib.load(f)

project = "PoreScene"
author = "Felix Faber"
copyright = (
    "2026, Felix Faber / Otto von Guericke University Magdeburg, "
    "Thermal Process Engineering"
)
release = _pyproject["project"]["version"]
version = release

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
]

pygments_style = "ayu-light"
pygments_dark_style = "ayu-dark"

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
    "cairosvg",
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
html_css_files = ["porescene.css", "carousel.css"]
html_js_files = ["carousel.js", "copybutton.js"]


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
