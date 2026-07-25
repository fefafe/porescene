import pytest

from porescene.color import Color

# =============================================================================
# Construction from hex


def test_default_color_is_opaque_black():
    c = Color()
    assert c.nrgb == (0.0, 0.0, 0.0)
    assert c.alpha == 1.0


@pytest.mark.parametrize("h", ["#f00", "f00", "#ff0000", "ff0000", "#FF0000"])
def test_accepts_every_hex_notation(h):
    assert Color(h).rgb == (255, 0, 0)


def test_hex_without_alpha_is_fully_opaque():
    assert Color("#85A2E6").alpha == 1.0


def test_alpha_is_read_from_eight_digit_hex():
    assert Color("#FF000080").alpha == pytest.approx(128 / 255)


def test_alpha_is_read_from_four_digit_hex():
    assert Color("#F000").alpha == 0.0


# =============================================================================
# Alternative constructors


def test_from_rgb_normalizes_channels():
    c = Color.from_rgb(133, 162, 230)
    assert c.nrgb == (133 / 255, 162 / 255, 230 / 255)


def test_from_rgb_defaults_to_opaque():
    assert Color.from_rgb(255, 0, 0).alpha == 1.0


def test_from_rgb_takes_alpha_on_the_unit_interval():
    assert Color.from_rgb(255, 0, 0, 0.5).alpha == 0.5


def test_from_nrgb_stores_channels_verbatim():
    c = Color.from_nrgb(0.1, 0.2, 0.3)
    assert c.nrgb == (0.1, 0.2, 0.3)


def test_from_nrgb_defaults_to_opaque():
    assert Color.from_nrgb(0.1, 0.2, 0.3).alpha == 1.0


# =============================================================================
# Channel properties


def test_channels_are_readable_and_writable():
    c = Color("#000")
    c.red, c.green, c.blue, c.alpha = 0.1, 0.2, 0.3, 0.4
    assert c.nrgba == (0.1, 0.2, 0.3, 0.4)


def test_nrgba_appends_alpha_to_nrgb():
    c = Color("#FF000080")
    assert c.nrgba == (*c.nrgb, c.alpha)


def test_rgb_returns_integer_channels():
    c = Color("#85A2E6")
    assert c.rgb == (133, 162, 230)
    assert all(isinstance(channel, int) for channel in c.rgb)


def test_rgba_keeps_alpha_on_the_unit_interval():
    c = Color("#FF000080")
    assert c.rgba[:3] == (255, 0, 0)
    assert c.rgba[3] == pytest.approx(128 / 255)


# =============================================================================
# String representations


def test_hex_properties_omit_the_hash():
    c = Color("#85A2E6")
    assert c.hex == "85A2E6"
    assert c.hexa == "85A2E6FF"


def test_str_hex_properties_include_the_hash():
    c = Color("#85A2E6")
    assert c.str_hex == "#85A2E6"
    assert c.str_hexa == "#85A2E6FF"


def test_hex_output_is_uppercase():
    assert Color("#85a2e6").hex == "85A2E6"


def test_str_returns_the_hash_prefixed_hex():
    assert str(Color("#f00")) == "#FF0000"


def test_repr_shows_the_constructor_call():
    assert repr(Color("#85A2E6")) == "Color('#85A2E6')"


def test_str_rgb_formatting():
    assert Color("#FF007F").str_rgb == "rgb(255, 0, 127)"


def test_str_rgba_formatting():
    c = Color.from_rgb(255, 0, 127, 0.5)
    assert c.str_rgba == "rgba(255, 0, 127, 0.5)"


def test_lnrgba_str_formatting():
    c = Color.from_nrgb(1.0, 0.0, 0.0, 1.0)
    assert c.lnrgba_str == "lnrgba(1.0, 0.0, 0.0, 1.0)"


@pytest.mark.xfail(
    strict=True,
    reason="lnrgb_str formats the nrgb channels under an lnrgb(...) label; "
    "lnrgba_str uses the linear values, so the two disagree",
)
def test_lnrgb_str_reports_linear_values():
    c = Color("#808080")
    assert c.lnrgb_str == f"lnrgb({c.lnrgb[0]}, {c.lnrgb[1]}, {c.lnrgb[2]})"


# =============================================================================
# Linear RGB


def test_lnrgb_preserves_pure_channels():
    # 0.0 and 1.0 are fixed points of the transfer function, so this alone would
    # still pass if lnrgb returned the nrgb channels unchanged
    assert Color("#f00").lnrgb == (1.0, 0.0, 0.0)


def test_lnrgb_applies_the_transfer_function_per_channel():
    c = Color("#85A2E6")
    assert c.lnrgb == pytest.approx(
        (0.23455058216100522, 0.3613067797835095, 0.7912979403326302)
    )


def test_lnrgb_darkens_midtones():
    c = Color("#808080")
    assert c.lnrgb[0] < c.nrgb[0]


def test_lnrgba_appends_untransformed_alpha():
    c = Color("#FF000080")
    assert c.lnrgba[:3] == c.lnrgb
    assert c.lnrgba[3] == c.alpha


# =============================================================================
# Mixing


def test_mix_defaults_to_equal_parts():
    assert Color("#000").mix(Color("#fff")).hex == "808080"


def test_mix_with_ratio_zero_returns_the_receiver():
    c = Color("#f00").mix(Color("#00f"), 0.0)
    assert c.nrgba == Color("#f00").nrgba


def test_mix_with_ratio_one_returns_the_argument():
    c = Color("#f00").mix(Color("#00f"), 1.0)
    assert c.nrgba == Color("#00f").nrgba


def test_mix_interpolates_linearly_in_nrgb():
    c = Color.from_nrgb(0.0, 0.0, 0.0).mix(Color.from_nrgb(1.0, 1.0, 1.0), 0.25)
    assert c.nrgb == pytest.approx((0.25, 0.25, 0.25))


def test_mix_also_interpolates_alpha():
    a = Color.from_nrgb(0.0, 0.0, 0.0, 0.0)
    b = Color.from_nrgb(0.0, 0.0, 0.0, 1.0)
    assert a.mix(b).alpha == pytest.approx(0.5)


def test_mix_returns_a_new_instance_and_leaves_operands_untouched():
    a = Color("#f00")
    b = Color("#00f")
    c = a.mix(b)
    assert c is not a and c is not b
    assert a.nrgb == (1.0, 0.0, 0.0)
    assert b.nrgb == (0.0, 0.0, 1.0)


def test_add_operator_is_an_equal_parts_mix():
    a = Color("#f00")
    b = Color("#00f")
    assert (a + b).nrgba == a.mix(b).nrgba


def test_add_operator_is_commutative():
    assert (Color("#f00") + Color("#00f")).hex == (Color("#00f") + Color("#f00")).hex
