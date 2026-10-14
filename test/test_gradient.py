import numpy as np
import pytest

from porescene.color import Color, ColorArray
from porescene.color.gradient import DiscreteGradient, SegmentedGradient, SmoothGradient

RED = Color("#f00")
GREEN = Color("#0f0")
BLUE = Color("#00f")
NAN = Color("#888")
BELOW = Color("#fff")
ABOVE = Color("#000")


def make(cls, colors=(RED, GREEN, BLUE), lower=0.0, upper=1.0, **kwargs):
    return cls(
        list(colors),
        lower,
        upper,
        color_nan=NAN,
        color_below=BELOW,
        color_above=ABOVE,
        **kwargs,
    )


def hexes(colors):
    return [c.hex for c in colors]


# =============================================================================
# Shared by all gradients


@pytest.mark.parametrize("cls", [SmoothGradient, SegmentedGradient, DiscreteGradient])
class TestAllGradients:
    def test_returns_a_color_array(self, cls):
        assert isinstance(make(cls)([0.0, 1.0]), ColorArray)

    def test_returns_one_color_per_value(self, cls):
        assert len(make(cls)(np.linspace(-1, 2, 37))) == 37

    def test_single_value_returns_a_color_array_of_one(self, cls):
        colors = make(cls)(0.0)
        assert isinstance(colors, ColorArray)
        assert len(colors) == 1

    def test_empty_input_returns_no_colors(self, cls):
        assert len(make(cls)([])) == 0

    def test_values_of_any_shape_are_flattened(self, cls):
        assert len(make(cls)(np.zeros((3, 4)))) == 12

    def test_boundaries_get_the_first_and_last_color(self, cls):
        assert hexes(make(cls, lower=2.0, upper=5.0)([2.0, 5.0])) == ["FF0000", "0000FF"]

    def test_nan_gets_color_nan(self, cls):
        assert hexes(make(cls)([np.nan])) == ["888888"]

    def test_values_beyond_the_boundaries_get_color_below_and_above(self, cls):
        colors = make(cls, lower=2.0, upper=5.0)([1.0, 6.0, -np.inf, np.inf])
        assert hexes(colors) == ["FFFFFF", "000000", "FFFFFF", "000000"]

    def test_fit_clips_onto_the_boundaries(self, cls):
        colors = make(cls, lower=2.0, upper=5.0, fit=True)([1.0, 6.0, np.nan])
        assert hexes(colors) == ["FF0000", "0000FF", "888888"]

    def test_constructor_takes_colors_and_boundaries(self, cls):
        grad = cls([RED, BLUE], 1.0, 3.0)
        assert grad.boundary_lower == 1.0
        assert grad.boundary_upper == 3.0
        assert len(grad) == 2


# =============================================================================
# SmoothGradient


def test_smooth_interpolates_between_neighboring_colors():
    colors = make(SmoothGradient)([0.25, 0.5, 0.75])
    expected = [RED.mix(GREEN, 0.5), GREEN, GREEN.mix(BLUE, 0.5)]
    for c, e in zip(colors, expected, strict=True):
        assert c.nrgba == pytest.approx(e.nrgba)


def test_smooth_matches_color_mix_everywhere():
    stops = [Color(h) for h in ("#011959", "#226061", "#808133", "#FDB4B4", "#FACCFA")]
    grad = SmoothGradient(stops, -3.0, 7.0)
    values = np.random.default_rng(0).uniform(-3.0, 7.0, 500)
    for value, color in zip(values, grad(values), strict=True):
        v = (value + 3.0) / 10.0
        idx = min(int(v * 4), 3)
        expected = stops[idx].mix(stops[idx + 1], v * 4 - idx)
        assert color.nrgba == pytest.approx(expected.nrgba)


def test_smooth_interpolates_alpha():
    grad = SmoothGradient([Color("#0000"), Color("#000F")])
    assert grad(0.5)[0].alpha == pytest.approx(0.5)


# =============================================================================
# SegmentedGradient


def test_segmented_returns_the_color_of_each_segment():
    colors = make(SegmentedGradient)([0.1, 0.4, 0.7, 0.99])
    assert hexes(colors) == ["FF0000", "00FF00", "0000FF", "0000FF"]


def test_segmented_value_on_a_segment_boundary_starts_the_next_segment():
    # integer values on the boundaries of ten segments spanning 0..20, as for a
    # coordination number; 0.6 // 0.1 == 5.0 in floating point would pick segment 5
    colors = [Color.from_nrgb(i / 10, 0.0, 0.0) for i in range(10)]
    grad = SegmentedGradient(colors, 0.0, 20.0)
    values = np.arange(0, 20, 2)
    assert hexes(grad(values)) == hexes(colors)


# =============================================================================
# DiscreteGradient


def test_discrete_levels_spread_evenly_between_the_boundaries():
    grad = make(DiscreteGradient, lower=1.0, upper=5.0)
    assert grad.levels.tolist() == [1.0, 3.0, 5.0]


def test_discrete_maps_each_level_to_its_color():
    grad = make(DiscreteGradient, lower=1.0, upper=5.0)
    assert hexes(grad([5, 1, 3, 3])) == ["0000FF", "FF0000", "00FF00", "00FF00"]


def test_discrete_value_between_levels_gets_color_nan():
    grad = make(DiscreteGradient, lower=1.0, upper=5.0)
    colors = grad([1.0, 2.0, 4.5])
    assert hexes(colors) == ["FF0000", "888888", "888888"]


def test_discrete_tolerates_rounding_noise_on_the_levels():
    grad = make(DiscreteGradient, lower=0.0, upper=0.3)
    assert hexes(grad([0.1 + 0.05, 0.3])) == ["00FF00", "0000FF"]


def test_discrete_nan_gets_color_nan():
    grad = make(DiscreteGradient)
    assert hexes(grad([0.0, np.nan])) == ["FF0000", "888888"]
