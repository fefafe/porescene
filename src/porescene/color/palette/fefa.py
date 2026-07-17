from porescene.color import Color
from porescene.color.palette import Palette

yellow = Color("#e5be0f")
orange = Color("#d97b09")
red = Color("#c30444")
pink = Color("#b70c92")
purple = Color("#8704c8")
darkblue = Color("#044eb6")
lightblue = Color("#0e86c7")
teal = Color("#02aba8")
darkgreen = Color("#039c48")
lightgreen = Color("#81b413")
gray = Color("#6F6F7B")

light0 = Color("#FFF")
light1 = Color("#FBFCFE")
light2 = Color("#f2f4f8")
light3 = Color("#e7e7ef")
light4 = Color("#d4d7e2")
light5 = Color("#c2c9d6")

dark0 = Color("#000000")
dark1 = Color("#151719")
dark2 = Color("#1D1D20")
dark3 = Color("#212226")
dark4 = Color("#25252A")
dark5 = Color("#2A292D")


class FeFaPalette(Palette):
    """
    fefa color palette

    The fefa color palette consists of the following colors:

    - yellow
    - orange
    - red
    - pink
    - purple
    - darkblue
    - lightblue
    - teal
    - darkgreen
    - lightgreen

    """

    def __init__(self) -> None:
        super().__init__(
            [
                yellow,
                orange,
                red,
                pink,
                purple,
                darkblue,
                lightblue,
                teal,
                darkgreen,
                lightgreen,
            ]
        )
