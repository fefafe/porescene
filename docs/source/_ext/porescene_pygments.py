"""
Pygments styles for the PoreScene docs, built from the fefafe palette.
"""

from pygments.style import Style
from pygments.token import (
    Comment,
    Error,
    Generic,
    Keyword,
    Name,
    Number,
    Operator,
    String,
    Text,
    Token,
)

# fefafe brand swatches
LIGHTGREEN = "#81b413"
DARKGREEN = "#039c48"
TEAL = "#02aba8"
LIGHTBLUE = "#0e86c7"
DARKBLUE = "#044eb6"
PURPLE = "#8704c8"
PINK = "#b70c92"
RED = "#c30444"
ORANGE = "#d97b09"
YELLOW = "#e5be0f"

# Neutrals
GRAY = "#64748b"  # comments, line numbers
FG_LIGHT = "#181f29"  # default code text, light theme
FG_DARK = "#e2e8f0"  # default code text, dark theme

# Code-block backgrounds
BG_LIGHT = "#e7f5f4"  # --color-ps-tint-400
BG_DARK = "#0d1e1d"  # --color-ps-shade-700

# Emphasized-line background
HL_LIGHT = "#d4eceb"  # --color-ps-tint-800
HL_DARK = "#093b3a"  # --color-ps-shade-200

_SHARED = {
    Comment: GRAY,
    Comment.Preproc: ORANGE,
    Comment.Special: f"bold {GRAY}",
    Keyword: ORANGE,
    Keyword.Constant: RED,
    Keyword.Namespace: ORANGE,
    Keyword.Pseudo: RED,
    Operator: YELLOW,
    Operator.Word: ORANGE,
    Name.Builtin: PINK,
    Name.Builtin.Pseudo: TEAL,
    Name.Function: LIGHTBLUE,
    Name.Function.Magic: LIGHTBLUE,
    Name.Class: f"bold {PURPLE}",
    Name.Decorator: PINK,
    Name.Namespace: DARKGREEN,
    Name.Exception: f"bold {RED}",
    Name.Constant: RED,
    Name.Attribute: LIGHTBLUE,
    Name.Tag: ORANGE,
    String: LIGHTGREEN,
    String.Doc: f"italic {LIGHTGREEN}",
    String.Escape: DARKGREEN,
    String.Interpol: DARKGREEN,
    String.Regex: DARKGREEN,
    String.Affix: ORANGE,
    Number: RED,
    Generic.Heading: f"bold {DARKBLUE}",
    Generic.Subheading: f"bold {LIGHTBLUE}",
    Generic.Deleted: RED,
    Generic.Inserted: DARKGREEN,
    Generic.Emph: "italic",
    Generic.Strong: "bold",
    Generic.Prompt: f"bold {GRAY}",
    Generic.Error: RED,
    Generic.Traceback: RED,
}


class PoreSceneLight(Style):
    """Light-theme code highlighting (Sphinx ``pygments_style``)."""

    name = "porescene-light"
    background_color = BG_LIGHT
    highlight_color = HL_LIGHT
    line_number_color = GRAY

    styles = {
        **_SHARED,
        Token: FG_LIGHT,
        Text: FG_LIGHT,
        Error: f"bg:#ffd4d4 {RED}",
    }


class PoreSceneDark(Style):
    """Dark-theme code highlighting (Furo ``pygments_dark_style``)."""

    name = "porescene-dark"
    background_color = BG_DARK
    highlight_color = HL_DARK
    line_number_color = GRAY

    styles = {
        **_SHARED,
        Token: FG_DARK,
        Text: FG_DARK,
        Error: f"bg:#3d1414 {RED}",
    }
