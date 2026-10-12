from pathlib import Path

from porescene.color.palette import Colormap, Palette
from porescene.layout import SmoothGradientAnnotation, SVGCanvas
from porescene.utility import (
    CompassDirection,
    Orientation,
    colorbar_limits,
    colorbar_ticks,
    px2cm,
    svg2png,
    tick_labels,
)

# =============================================================================
# Import Parameters

# repository root, so the example runs from any working directory
pth_root = Path(__file__).resolve().parents[1]

# output directory, named after this example
pth_out = pth_root / "tmp" / "example" / Path(__file__).stem
pth_out.mkdir(parents=True, exist_ok=True)

# [µm] range of the values the colorbar has to cover, e.g. the smallest and the largest
# pore diameter of a network
val_min, val_max = 2.7, 37.4

# [cm] margin kept around the colorbar, so the strokes on its outline are not clipped
margin = 0.1


# =============================================================================
# Scale

# widen the range outward to round limits and spread the ticks evenly between them
limit_lower, limit_upper = colorbar_limits(val_min, val_max)
ticks = tick_labels(colorbar_ticks(limit_lower, limit_upper, num_ticks=5))


# =============================================================================
# Colorbar

# one colorbar per orientation, each hung onto the edge it is meant to sit at next to a
# figure, so that its ticks face the figure and its heading faces away from it
for orientation, align in (
    (Orientation.VERTICAL, CompassDirection.EAST),
    (Orientation.HORIZONTAL, CompassDirection.SOUTH),
):
    cb = SmoothGradientAnnotation(Palette.load(Colormap.BATLOW).all(), ticks)
    cb.heading = "Diameter [µm]"
    cb.orientation = orientation

    canvas = SVGCanvas(padding=(margin,) * 4)
    canvas.add(cb, align)

    # the canvas is shrunk onto the colorbar, so the file holds nothing else and lands in
    # a manuscript at the colorbar's own size; the box is read only after the colorbar is
    # added, since the edge it sits at decides which sides its ticks and heading take
    box = cb.bbox()
    canvas.size = (px2cm(box.width) + 2 * margin, px2cm(box.height) + 2 * margin)

    pth = pth_out / f"cb-diameter+{orientation.name.lower()}.svg"
    svg2png(canvas.save(pth))
