from pathlib import Path
from porescene.color.palette import fefa
from porescene.layout import DiscreteGradientOverlay, LabelsOverlay, SegmentedGradientOverlay, SmoothGradientOverlay
from porescene.utility import CompassDirection, Orientation, svg2png
from porescene.color import Color

pth = Path.cwd() / "data/overlay_smooth.svg"

ovl = SmoothGradientOverlay(pth)
ovl.gradient_colors = [fefa.lightgreen, fefa.orange]
ovl.ticks = ["1.0", "2.0", "3.0", "4.0"]
ovl.heading = "Duis nisi mollit cillum"
# ovl.subheading = "In occaecat incididunt"
ovl.text = [
    "Deserunt pariatur eu pariatur dolore consequat culpa "
    "laboris sit dolore proident laboris consectetur consequat.",
    "Qui est officia amet dolore voluptate irure laboris.",
]
ovl.align = CompassDirection.NORTH
ovl.orientation = Orientation.HORIZONTAL
# ovl.color_nan = fefa.red
ovl.exponent = -3
ovl.save()
svg2png(pth)


# ============================================================================

pth = Path.cwd() / "data/overlay_segmented.svg"

ovl = SegmentedGradientOverlay(pth)
ovl.gradient_colors = [
    fefa.lightgreen,
    fefa.orange,
    fefa.red,
    fefa.purple,
    fefa.lightblue,
]
ovl.ticks = ["10", "15", "20", "25", "30", "35"]
ovl.heading = "Duis nisi mollit cillum"
ovl.align = CompassDirection.NORTH
ovl.orientation = Orientation.HORIZONTAL
ovl.save()
svg2png(pth)


# ============================================================================

pth = Path.cwd() / "data/overlay_discrete.svg"

ovl = DiscreteGradientOverlay(pth)
ovl.gradient_colors = [
    fefa.lightgreen,
    fefa.orange,
    fefa.red,
    fefa.purple,
    fefa.lightblue,
    fefa.yellow,
]
ovl.ticks = ["10", "15", "20", "25", "30", "35"]
ovl.heading = "Duis nisi mollit cillum"
ovl.align = CompassDirection.NORTH
ovl.orientation = Orientation.HORIZONTAL
ovl.save()
svg2png(pth)

# ============================================================================

pth = Path.cwd() / "data/overlay_labels.svg"

ovl = LabelsOverlay(pth)
ovl.add_label(fefa.lightgreen, "frozen")
ovl.add_label(fefa.pink, "sublimation")
ovl.add_label(fefa.yellow, "dry")
ovl.heading = "Duis nisi mollit cillum"
ovl.align = CompassDirection.NORTHWEST
# ovl.orientation = Orientation.HORIZONTAL
ovl.save()
svg2png(pth)
