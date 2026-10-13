import numpy as np
import pytest

from porescene.color import Color, ColorArray

HEX = ["#85A2E6", "#B0131B80", "#000", "#FFF"]


@pytest.fixture
def colors():
    return ColorArray.from_hex(HEX)


# =============================================================================
# Construction


def test_default_is_empty():
    c = ColorArray()
    assert len(c) == 0
    assert c.nrgba.shape == (0, 4)


def test_holds_the_channels_of_the_given_colors(colors):
    assert colors.nrgba.tolist() == [list(Color(h).nrgba) for h in HEX]


def test_from_hex_matches_construction_from_colors(colors):
    assert colors.nrgba.tolist() == ColorArray([Color(h) for h in HEX]).nrgba.tolist()


def test_from_nrgb_takes_one_array_per_channel():
    c = ColorArray.from_nrgb([0.1, 0.2], [0.3, 0.4], [0.5, 0.6], [0.7, 0.8])
    assert c.nrgba.tolist() == [[0.1, 0.3, 0.5, 0.7], [0.2, 0.4, 0.6, 0.8]]


def test_from_nrgb_defaults_to_opaque():
    assert ColorArray.from_nrgb([0.1, 0.2], 0.0, 0.0).alpha.tolist() == [1.0, 1.0]


def test_from_nrgb_broadcasts_scalars():
    c = ColorArray.from_nrgb(0.5, [0.0, 1.0], 0.5)
    assert c.nrgb.tolist() == [[0.5, 0.0, 0.5], [0.5, 1.0, 0.5]]


def test_from_rgb_normalizes_channels():
    c = ColorArray.from_rgb([133, 255], [162, 0], [230, 0])
    assert c[0].nrgb == Color.from_rgb(133, 162, 230).nrgb
    assert c[1].nrgb == (1.0, 0.0, 0.0)


def test_from_rgb_takes_alpha_on_the_unit_interval():
    assert ColorArray.from_rgb([255], [0], [0], 0.5).alpha.tolist() == [0.5]


# =============================================================================
# Sequence protocol


def test_len_counts_the_colors(colors):
    assert len(colors) == len(HEX)


def test_integer_index_returns_a_color(colors):
    c = colors[1]
    assert isinstance(c, Color)
    assert c.nrgba == Color(HEX[1]).nrgba


def test_numpy_integer_index_returns_a_color(colors):
    assert isinstance(colors[np.int64(0)], Color)


def test_negative_index_counts_from_the_end(colors):
    assert colors[-1].hex == "FFFFFF"


def test_slice_returns_a_color_array(colors):
    c = colors[1:3]
    assert isinstance(c, ColorArray)
    assert c.nrgba.tolist() == colors.nrgba[1:3].tolist()


def test_index_array_and_mask_return_color_arrays(colors):
    assert colors[[3, 0]].nrgba.tolist() == colors.nrgba[[3, 0]].tolist()
    assert len(colors[np.array([True, False, True, False])]) == 2


def test_slice_does_not_share_memory_with_the_original(colors):
    c = colors[:2]
    c.red = 0.0
    assert colors[0].red == Color(HEX[0]).red


def test_iteration_yields_colors(colors):
    assert [c.str_hexa for c in colors] == [Color(h).str_hexa for h in HEX]


def test_setitem_with_a_color_broadcasts_over_the_selection(colors):
    colors[[True, False, True, False]] = Color("#0f0")
    assert [c.hex for c in colors] == ["00FF00", "B0131B", "00FF00", "FFFFFF"]


def test_setitem_with_a_color_array_assigns_color_by_color(colors):
    colors[:2] = ColorArray.from_hex(["#f00", "#00f"])
    assert [c.hex for c in colors] == ["FF0000", "0000FF", "000000", "FFFFFF"]


def test_repr_lists_the_colors():
    assert repr(ColorArray.from_hex(["#f00", "#00f"])) == (
        "ColorArray([Color('#FF0000'), Color('#0000FF')])"
    )


def test_repr_truncates_long_arrays():
    r = repr(ColorArray.from_hex(["#000"] * 100))
    assert r.count("Color(") == 6
    assert "..." in r


# =============================================================================
# Channels and color spaces match Color, color by color


@pytest.mark.parametrize(
    "prop",
    ["red", "green", "blue", "alpha", "nrgb", "nrgba", "lnrgb", "lnrgba", "rgb", "rgba"],
)
def test_properties_match_color(colors, prop):
    expected = [getattr(Color(h), prop) for h in HEX]
    np.testing.assert_allclose(getattr(colors, prop), expected, rtol=0, atol=1e-15)


def test_rgb_is_integer(colors):
    assert colors.rgb.dtype.kind == "i"


def test_channel_setter_broadcasts(colors):
    colors.alpha = 0.25
    assert colors.alpha.tolist() == [0.25] * len(HEX)


def test_channel_setter_takes_one_value_per_color(colors):
    colors.red = [0.0, 0.1, 0.2, 0.3]
    assert colors.red.tolist() == [0.0, 0.1, 0.2, 0.3]


def test_properties_return_copies(colors):
    colors.nrgba[:] = 0.0
    colors.red[:] = 0.0
    assert colors[0].nrgba == Color(HEX[0]).nrgba


# =============================================================================
# Mixing


def test_mix_matches_color_mix_for_each_color(colors):
    other = ColorArray.from_hex(["#fff", "#f00", "#00f8", "#000"])
    ratio = [0.0, 0.25, 0.5, 1.0]
    mixed = colors.mix(other, ratio)
    for no, (h, o) in enumerate(zip(HEX, other, strict=True)):
        assert mixed[no].nrgba == pytest.approx(Color(h).mix(o, ratio[no]).nrgba)


def test_mix_with_a_single_color_mixes_it_into_every_color(colors):
    mixed = colors.mix(Color("#fff"), 0.5)
    for no, h in enumerate(HEX):
        assert mixed[no].nrgba == pytest.approx(Color(h).mix(Color("#fff")).nrgba)


def test_mix_defaults_to_equal_parts():
    c = ColorArray.from_hex(["#000"]).mix(ColorArray.from_hex(["#fff"]))
    assert c[0].hex == "808080"


def test_mix_returns_a_new_instance_and_leaves_operands_untouched(colors):
    before = colors.nrgba
    other = ColorArray.from_hex(["#fff"] * len(HEX))
    mixed = colors.mix(other)
    assert mixed is not colors and mixed is not other
    assert colors.nrgba.tolist() == before.tolist()
    assert other.nrgba.tolist() == [[1.0, 1.0, 1.0, 1.0]] * len(HEX)


def test_add_operator_is_an_equal_parts_mix(colors):
    other = ColorArray.from_hex(["#f00"] * len(HEX))
    assert (colors + other).nrgba.tolist() == colors.mix(other).nrgba.tolist()
