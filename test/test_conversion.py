import pytest

from porescene.color.conversion import (
    hex2rgb,
    lnrgb2nrgb,
    nrgb2lnrgb,
    nrgb2rgb,
    rgb2hex,
    rgb2nrgb,
)

# =============================================================================
# hex2rgb


@pytest.mark.parametrize(
    ("h", "expected"),
    [
        ("#000000", (0, 0, 0)),
        ("#FFFFFF", (255, 255, 255)),
        ("#85A2E6", (133, 162, 230)),
        ("#B0131B", (176, 19, 27)),
    ],
)
def test_hex2rgb_six_digit(h, expected):
    assert hex2rgb(h) == expected


def test_hex2rgb_hash_is_optional():
    assert hex2rgb("#85A2E6") == hex2rgb("85A2E6")


def test_hex2rgb_is_case_insensitive():
    assert hex2rgb("#85a2e6") == hex2rgb("#85A2E6")


def test_hex2rgb_three_digit_expands_by_duplication():
    assert hex2rgb("#abc") == hex2rgb("#aabbcc")
    assert hex2rgb("#abc") == (170, 187, 204)


def test_hex2rgb_four_digit_expands_by_duplication():
    assert hex2rgb("#abcd") == hex2rgb("#aabbccdd")


def test_hex2rgb_without_alpha_returns_three_channels():
    rgb = hex2rgb("#85A2E6")
    assert len(rgb) == 3
    assert all(isinstance(channel, int) for channel in rgb)


def test_hex2rgb_with_alpha_returns_four_channels():
    rgba = hex2rgb("#85A2E680")
    assert len(rgba) == 4
    assert rgba[:3] == (133, 162, 230)


@pytest.mark.parametrize(
    ("h", "alpha"),
    [
        ("#00000000", 0.0),
        ("#000000FF", 1.0),
        ("#00000080", 128 / 255),
        ("#0008", 136 / 255),
    ],
)
def test_hex2rgb_normalizes_alpha_to_unit_interval(h, alpha):
    assert hex2rgb(h)[3] == pytest.approx(alpha)


# =============================================================================
# rgb2hex


@pytest.mark.parametrize(
    ("rgb", "expected"),
    [
        ((0, 0, 0), "#000000"),
        ((255, 255, 255), "#FFFFFF"),
        ((133, 162, 230), "#85A2E6"),
        ((255, 0, 127), "#FF007F"),
    ],
)
def test_rgb2hex_returns_uppercase_with_hash(rgb, expected):
    assert rgb2hex(*rgb) == expected


def test_rgb2hex_appends_alpha_when_given():
    assert rgb2hex(0, 0, 0, 0.0) == "#00000000"
    assert rgb2hex(0, 0, 0, 1.0) == "#000000FF"
    assert rgb2hex(0, 0, 0, 0.5) == "#00000080"


def test_rgb2hex_clamps_out_of_range_channels():
    assert rgb2hex(300, -20, 127) == "#FF007F"


def test_rgb2hex_clamps_out_of_range_alpha():
    assert rgb2hex(0, 0, 0, 2.0) == "#000000FF"
    assert rgb2hex(0, 0, 0, -1.0) == "#00000000"


def test_rgb2hex_rounds_fractional_channels():
    assert rgb2hex(127.6, 127.4, 0) == "#807F00"


# =============================================================================
# rgb2nrgb / nrgb2rgb


def test_rgb2nrgb_maps_endpoints_to_unit_interval():
    assert rgb2nrgb(0, 0, 0) == (0.0, 0.0, 0.0)
    assert rgb2nrgb(255, 255, 255) == (1.0, 1.0, 1.0)


def test_rgb2nrgb_divides_each_channel_by_255():
    assert rgb2nrgb(133, 162, 230) == (133 / 255, 162 / 255, 230 / 255)


def test_rgb2nrgb_passes_alpha_through_unscaled():
    assert rgb2nrgb(0, 0, 0, 0.25) == (0.0, 0.0, 0.0, 0.25)


def test_nrgb2rgb_rounds_to_nearest_integer():
    assert nrgb2rgb(0.5, 0.5, 0.5) == (128, 128, 128)
    assert all(isinstance(channel, int) for channel in nrgb2rgb(0.5, 0.5, 0.5))


def test_nrgb2rgb_passes_alpha_through_unscaled():
    assert nrgb2rgb(0.0, 0.0, 0.0, 0.25) == (0, 0, 0, 0.25)


# =============================================================================
# nrgb2lnrgb / lnrgb2nrgb


def test_nrgb2lnrgb_preserves_endpoints():
    assert nrgb2lnrgb(0.0, 0.0, 0.0) == (0.0, 0.0, 0.0)
    assert nrgb2lnrgb(1.0, 1.0, 1.0) == (1.0, 1.0, 1.0)


def test_nrgb2lnrgb_uses_linear_segment_below_threshold():
    assert nrgb2lnrgb(0.02, 0.02, 0.02) == pytest.approx((0.02 / 12.92,) * 3)


def test_nrgb2lnrgb_uses_power_segment_above_threshold():
    expected = ((0.5 + 0.055) / 1.055) ** 2.4
    assert nrgb2lnrgb(0.5, 0.5, 0.5) == pytest.approx((expected,) * 3)


def test_nrgb2lnrgb_darkens_midtones():
    # sRGB 0.5 is perceptual middle grey, well below half the linear intensity
    assert nrgb2lnrgb(0.5, 0.5, 0.5)[0] < 0.5


def test_nrgb2lnrgb_is_continuous_across_the_segment_threshold():
    below = nrgb2lnrgb(0.04044, 0.0, 0.0)[0]
    above = nrgb2lnrgb(0.04046, 0.0, 0.0)[0]
    assert below == pytest.approx(above, abs=1e-5)


def test_nrgb2lnrgb_is_monotonic():
    values = [nrgb2lnrgb(v / 100, 0.0, 0.0)[0] for v in range(101)]
    assert values == sorted(values)


def test_nrgb2lnrgb_passes_alpha_through_untransformed():
    assert nrgb2lnrgb(0.5, 0.5, 0.5, 0.25)[3] == 0.25


def test_lnrgb2nrgb_preserves_endpoints():
    assert lnrgb2nrgb(0.0, 0.0, 0.0) == (0.0, 0.0, 0.0)
    assert lnrgb2nrgb(1.0, 1.0, 1.0) == pytest.approx((1.0, 1.0, 1.0))


def test_lnrgb2nrgb_uses_linear_segment_below_threshold():
    assert lnrgb2nrgb(0.002, 0.002, 0.002) == pytest.approx((0.002 * 12.92,) * 3)


def test_lnrgb2nrgb_passes_alpha_through_untransformed():
    assert lnrgb2nrgb(0.5, 0.5, 0.5, 0.25)[3] == 0.25


# =============================================================================
# Round-trips


def test_rgb_roundtrip_is_lossless_for_every_channel_value():
    for value in range(256):
        assert nrgb2rgb(*rgb2nrgb(value, value, value)) == (value, value, value)


def test_hex_roundtrip_is_lossless_for_every_channel_value():
    for value in range(256):
        h = rgb2hex(value, value, value)
        assert hex2rgb(h) == (value, value, value)


@pytest.mark.parametrize("value", [0.0, 0.001, 0.0031308, 0.04045, 0.3, 0.5, 0.9, 1.0])
def test_gamma_roundtrip_returns_the_original_value(value):
    assert lnrgb2nrgb(*nrgb2lnrgb(value, value, value)) == pytest.approx(
        (value, value, value)
    )
