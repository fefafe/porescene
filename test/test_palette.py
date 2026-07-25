import random

import pytest

from porescene.color import Color
from porescene.color.palette import Colormap, Palette
from porescene.color.palette.fefa import FeFaPalette


@pytest.fixture
def palette():
    return Palette.load(Colormap.BATLOW)


# =============================================================================
# Construction


def test_palette_wraps_a_list_of_colors():
    colors = [Color("#f00"), Color("#0f0"), Color("#00f")]
    p = Palette(colors)
    assert len(p) == 3
    assert p.all() == colors


# =============================================================================
# Palette.load


def test_load_reads_every_row_of_the_colormap_file():
    assert len(Palette.load(Colormap.BATLOW)) == 256
    assert len(Palette.load(Colormap.TAB10)) == 10


def test_load_preserves_file_order(palette):
    assert palette.first().hex == "011959"
    assert palette.last().hex == "FACCFA"


def test_load_accepts_an_enum_member_or_its_name(palette):
    by_name = Palette.load("batlow")
    assert [c.hex for c in by_name] == [c.hex for c in palette]


@pytest.mark.parametrize("name", ["", "no-such-map", "bad name", "map.txt", "../secret"])
def test_load_rejects_names_outside_the_allowed_character_set(name):
    with pytest.raises(Exception, match="not available"):
        Palette.load(name)


def test_load_raises_when_an_allowed_name_has_no_data_file():
    with pytest.raises(FileNotFoundError):
        Palette.load("nosuchcolormap")


# =============================================================================
# Bundled colormap data


@pytest.mark.parametrize("colormap", list(Colormap), ids=lambda c: c.name)
def test_every_colormap_member_has_loadable_data(colormap):
    colors = Palette.load(colormap).all()
    assert len(colors) > 0
    assert all(isinstance(color, Color) for color in colors)


@pytest.mark.parametrize("colormap", list(Colormap), ids=lambda c: c.name)
def test_every_colormap_stays_within_the_unit_interval(colormap):
    for color in Palette.load(colormap):
        assert all(0.0 <= channel <= 1.0 for channel in color.nrgb)


# =============================================================================
# Container behaviour


def test_all_returns_the_underlying_list(palette):
    assert palette.all() is palette.colors


def test_first_and_last_match_the_underlying_list(palette):
    assert palette.first() is palette.colors[0]
    assert palette.last() is palette.colors[-1]


def test_iteration_yields_every_color_in_order(palette):
    assert [c.hex for c in palette] == [c.hex for c in palette.all()]


def test_palette_can_be_iterated_more_than_once(palette):
    assert len(list(palette)) == len(list(palette)) == len(palette)


@pytest.mark.xfail(
    strict=True,
    reason="__iter__ returns self and shares one cursor, so two concurrent "
    "iterations over the same palette consume each other's items",
)
def test_concurrent_iterations_are_independent(palette):
    assert len(list(zip(palette, palette, strict=True))) == len(palette)


# =============================================================================
# Sampling


@pytest.mark.parametrize("n", [1, 2, 5, 16, 256])
def test_subset_returns_the_requested_number_of_colors(palette, n):
    assert len(palette.subset(n)) == n


def test_subset_defaults_to_five_colors(palette):
    assert len(palette.subset()) == 5


def test_subset_spans_the_full_palette(palette):
    subset = palette.subset(5)
    assert subset[0] is palette.first()
    assert subset[-1] is palette.last()


def test_subset_samples_equidistantly(palette):
    expected = [palette.colors[i] for i in (0, 63, 127, 191, 255)]
    assert palette.subset(5) == expected


def test_subset_of_full_length_returns_every_color(palette):
    assert palette.subset(len(palette)) == palette.all()


def test_reversed_flips_the_order(palette):
    reversed_colors = palette.reversed()
    assert reversed_colors[0] is palette.last()
    assert reversed_colors[-1] is palette.first()


def test_reversed_leaves_the_palette_untouched(palette):
    before = palette.all()[:]
    palette.reversed()
    assert palette.all() == before


@pytest.mark.parametrize("n", [0, 1, 3, 10])
def test_random_returns_the_requested_number_of_colors(palette, n):
    assert len(palette.random(n)) == n


def test_random_defaults_to_a_single_color(palette):
    assert len(palette.random()) == 1


def test_random_draws_only_from_the_palette(palette):
    assert all(c in palette.all() for c in palette.random(20))


def test_random_is_reproducible_when_seeded(palette):
    random.seed(0)
    first = [c.hex for c in palette.random(5)]
    random.seed(0)
    assert [c.hex for c in palette.random(5)] == first


# =============================================================================
# FeFaPalette


def test_fefa_palette_holds_the_ten_documented_colors():
    p = FeFaPalette()
    assert len(p) == 10
    assert p.first().hex == "E5BE0F"
    assert p.last().hex == "81B413"
