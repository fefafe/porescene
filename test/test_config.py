import numpy as np
import pytest

from porescene.color import Color
from porescene.color.palette import Palette
from porescene.config import (
    AxesConfiguration,
    ImageConfiguration,
    QuantityConfiguration,
    SceneConfiguration,
)
from porescene.utility import CompassDirection, Orientation

EXTENT = np.array((200e-06, 400e-06, 500e-06))


@pytest.fixture
def axes():
    return AxesConfiguration(EXTENT)


# =============================================================================
# QuantityConfiguration


def test_quantity_only_requires_a_name():
    assert QuantityConfiguration("radius").name == "radius"


def test_quantity_default_transform_is_the_identity():
    assert QuantityConfiguration("radius").func_transform(7) == 7


def test_quantity_stores_the_given_settings():
    colors = [Color("#f00"), Color("#00f")]
    p = QuantityConfiguration(
        "saturation",
        colors,
        heading="Saturation",
        subheading="per pore",
        text=["a", "b"],
        align=CompassDirection.SOUTHEAST,
        orientation=Orientation.VERTICAL,
        precision=3,
        min=0.0,
        max=1.0,
        use_global_boundaries=True,
        factor=1e6,
        fit=False,
    )
    assert p.colors is colors
    assert p.heading == "Saturation"
    assert p.subheading == "per pore"
    assert p.text == ["a", "b"]
    assert p.align is CompassDirection.SOUTHEAST
    assert p.orientation is Orientation.VERTICAL
    assert p.precision == 3
    assert (p.min, p.max) == (0.0, 1.0)
    assert p.use_global_boundaries is True
    assert p.factor == 1e6
    assert p.fit is False


def test_quantity_out_of_range_colors_default_to_none():
    p = QuantityConfiguration("radius")
    assert p.color_nan is None
    assert p.color_below is None
    assert p.color_above is None


def test_quantity_out_of_range_colors_are_stored():
    nan, below, above = Color("#f00"), Color("#0f0"), Color("#00f")
    p = QuantityConfiguration(
        "radius", color_nan=nan, color_below=below, color_above=above
    )
    assert (p.color_nan, p.color_below, p.color_above) == (nan, below, above)


def test_quantity_transform_is_applied_by_the_caller_not_stored_eagerly():
    p = QuantityConfiguration("radius", func_transform=lambda v: v * 2)
    assert p.func_transform(21) == 42


# =============================================================================
# ImageConfiguration


def test_image_defaults_to_square():
    im = ImageConfiguration()
    assert im.aspect_ratio == 1.0


def test_image_resolution_follows_the_channels():
    im = ImageConfiguration()
    im.width, im.height = 1920, 1080
    assert im.resolution == [1920, 1080]
    assert im.aspect_ratio == pytest.approx(1920 / 1080)


def test_image_from_dict_reads_width_and_height():
    im = ImageConfiguration.from_dict({"width": 1920, "height": 1080})
    assert im.resolution == [1920, 1080]


def test_image_from_dict_ignores_unknown_keys():
    im = ImageConfiguration.from_dict({"width": 800, "depth": 3, "bogus": "x"})
    assert im.resolution == [800, im.height]
    assert not hasattr(im, "depth")


# =============================================================================
# SceneConfiguration


def test_scene_defaults():
    sc = SceneConfiguration()
    assert sc.enable_spheres is True
    assert sc.enable_cylinders is True
    assert sc.enable_clusters is True
    assert sc.enable_axes is True
    assert sc.enable_solid is True
    assert sc.enable_void is False
    assert len(sc) == 0


def test_scene_instances_do_not_share_mutable_defaults():
    a, b = SceneConfiguration(), SceneConfiguration()
    a.add_quantity(QuantityConfiguration("radius"))
    assert len(b) == 0
    assert a.versions_solid is not b.versions_solid


def test_scene_toggles_are_coerced_to_bool():
    sc = SceneConfiguration(enable_solid=0, enable_void=1)
    assert sc.enable_solid is False
    assert sc.enable_void is True


@pytest.mark.parametrize(
    "material",
    ["material_spheres", "material_cylinders", "material_clusters", "material_solid"],
)
def test_scene_material_names_are_upper_cased(material):
    sc = SceneConfiguration(**{material: "plastic_rough"})
    assert getattr(sc, material) == "PLASTIC_ROUGH"


def test_scene_void_material_is_coerced_to_str():
    sc = SceneConfiguration()
    sc.material_void = "ice"
    assert sc.material_void == "ICE"


def test_scene_palette_is_replaceable():
    sc = SceneConfiguration()
    palette = Palette([Color("#f00")])
    sc.palette = palette
    assert sc.palette is palette


# -----------------------------------------------------------------------------
# SceneConfiguration -- quantity container


def test_add_quantity_grows_the_configuration():
    sc = SceneConfiguration()
    sc.add_quantity(QuantityConfiguration("radius"))
    sc.add_quantity(QuantityConfiguration("saturation"))
    assert len(sc) == 2


def test_get_quantity_looks_up_by_name():
    sc = SceneConfiguration()
    quant = QuantityConfiguration("radius")
    sc.add_quantity(quant)
    assert sc.get_quantity("radius") is quant
    assert sc["radius"] is quant


def test_get_quantity_raises_for_an_unknown_name():
    with pytest.raises(ValueError, match="Unknown quantity with name 'nope'"):
        SceneConfiguration().get_quantity("nope")


def test_setitem_ignores_the_key_and_files_under_the_quantity_name():
    sc = SceneConfiguration()
    sc["ignored"] = QuantityConfiguration("radius")
    assert sc["radius"].name == "radius"
    with pytest.raises(ValueError, match="Unknown quantity"):
        sc["ignored"]


def test_iteration_yields_the_quantities_in_insertion_order():
    sc = SceneConfiguration()
    for name in ("radius", "saturation", "temperature"):
        sc.add_quantity(QuantityConfiguration(name))
    assert [p.name for p in sc] == ["radius", "saturation", "temperature"]


def test_configuration_can_be_iterated_more_than_once():
    sc = SceneConfiguration()
    sc.add_quantity(QuantityConfiguration("radius"))
    assert len(list(sc)) == len(list(sc)) == 1


def test_concurrent_iterations_are_independent():
    sc = SceneConfiguration()
    for name in ("radius", "saturation"):
        sc.add_quantity(QuantityConfiguration(name))
    assert len(list(zip(sc, sc, strict=True))) == len(sc)


# =============================================================================
# AxesConfiguration -- tick interval rounding


@pytest.mark.parametrize(
    ("span", "expected"),
    [
        (500, 100),  # residual 1.0 -> magnitude
        (1000, 200),  # residual 2.0 -> 2 x magnitude
        (300, 50),  # residual 6.0 -> 5 x magnitude
        (400, 100),  # residual 8.0 -> 10 x magnitude
        (7, 1),
    ],
)
def test_interval_round_snaps_to_the_1_2_5_10_series(span, expected):
    assert AxesConfiguration._interval_round(span, 6) == expected


@pytest.mark.parametrize("span", [0, -1, float("nan"), float("inf")])
def test_interval_round_falls_back_to_one_for_degenerate_spans(span):
    assert AxesConfiguration._interval_round(span, 6) == 1.0


# =============================================================================
# AxesConfiguration -- unit selection


@pytest.mark.parametrize(
    ("span", "expected"),
    [
        (500e-06, "MICRO"),  # 500 µm
        (100e-06, "MICRO"),  # 100 µm
        (10e-06, "MICRO"),  # 10 µm, the lower end of the target range
        (9e-06, "NANO"),  # 9000 nm, just below it
        (2e-03, "MICRO"),  # 2000 µm rather than 2 mm
        (20e-03, "MILLI"),  # 20 mm
        (5.0, "MILLI"),  # 5000 mm
    ],
)
def test_unit_metric_picks_the_prefix_the_span_reads_best_in(span, expected):
    assert AxesConfiguration._unit_metric(span) == expected


@pytest.mark.parametrize(
    ("span", "expected"),
    [
        (500.0, "BASE"),  # 500 m
        (5e03, "BASE"),  # 5000 m
        (5e04, "KILO"),  # 50 km
    ],
)
def test_unit_metric_reaches_the_unprefixed_base_unit(span, expected):
    assert AxesConfiguration._unit_metric(span) == expected


@pytest.mark.parametrize(("span", "expected"), [(1e40, "QUETTA"), (1e-40, "QUECTO")])
def test_unit_metric_clamps_to_the_outermost_prefixes(span, expected):
    assert AxesConfiguration._unit_metric(span) == expected


@pytest.mark.parametrize("span", [0, -1, float("nan"), float("inf")])
def test_unit_metric_falls_back_to_micro_for_degenerate_spans(span):
    assert AxesConfiguration._unit_metric(span) == "MICRO"


# =============================================================================
# AxesConfiguration -- decimals of the tick labels


@pytest.mark.parametrize(
    ("ticks", "expected"),
    [
        ((), 0),
        ((0.0, 100.0, 200.0), 0),
        ((0.0, 2.5, 5.0), 1),
        ((0.0, 0.25, 0.5), 2),
        ((0.0, 1.0, 2.5, 0.125), 3),  # the widest tick of the axis wins
    ],
)
def test_decimals_counts_what_it_takes_to_write_every_tick(ticks, expected):
    assert AxesConfiguration._decimals(ticks) == expected


def test_decimals_ignores_the_noise_of_a_binary_representation():
    # 0.1 + 0.2 lands on 0.30000000000000004, which must not claim 17 decimals
    assert AxesConfiguration._decimals((0.0, 0.1, 0.2, 0.1 + 0.2)) == 1


def test_decimals_is_capped():
    assert AxesConfiguration._decimals((1 / 3,)) == 6
    assert AxesConfiguration._decimals((1 / 3,), limit=2) == 2


# =============================================================================
# AxesConfiguration -- calibration


def test_axes_unit_display_selects_the_metric_prefix():
    assert AxesConfiguration(EXTENT, unit_display="MILLI").label_x == "x [mm]"
    assert AxesConfiguration(EXTENT, unit_display="NANO").label_x == "x [nm]"


def test_axes_unit_display_is_derived_from_the_extent(axes):
    assert axes.unit_display == "MICRO"

    ax = AxesConfiguration(np.array((20e-03, 40e-03, 50e-03)))
    assert ax.unit_display == "MILLI"
    assert ax.label_x == "x [mm]"
    assert ax.value_end == pytest.approx((20.0, 40.0, 50.0))


def test_axes_unit_display_can_be_the_unprefixed_base_unit():
    ax = AxesConfiguration(np.array((200.0, 400.0, 500.0)))
    assert ax.unit_display == "BASE"
    assert ax.label_x == "x [m]"
    assert ax.factor == (1.0, 1.0, 1.0)
    assert ax.value_end == pytest.approx((200.0, 400.0, 500.0))


def test_axes_unit_display_follows_the_longest_axis():
    ax = AxesConfiguration(np.array((5e-06, 5e-06, 2e-03)))
    assert ax.unit_display == "MICRO"
    assert ax.tick_interval == 500


def test_axes_factor_scales_meters_to_the_displayed_unit(axes):
    assert axes.factor == (1e6, 1e6, 1e6)


def test_axes_value_end_is_the_extent_in_the_displayed_unit(axes):
    assert axes.value_end == (200.0, 400.0, 500.0)
    assert axes.value_start == (0.0, 0.0, 0.0)


def test_axes_derive_one_shared_interval_from_the_longest_axis(axes):
    assert axes.tick_interval == 100


def test_axes_ticks_run_from_zero_in_steps_of_the_interval(axes):
    assert axes.ticks_x == (0.0, 100.0, 200.0)
    assert axes.ticks_y == (0.0, 100.0, 200.0, 300.0, 400.0)
    assert axes.ticks_z == (0.0, 100.0, 200.0, 300.0, 400.0, 500.0)


def test_axes_keep_the_final_tick_when_the_extent_lands_on_it(axes):
    # the calibration nudges the stop value so the closing tick survives
    assert axes.ticks_z[-1] == pytest.approx(axes.value_end[2])


def test_axes_accept_an_explicit_tick_interval():
    ax = AxesConfiguration(EXTENT, tick_interval=250)
    assert ax.tick_interval == 250.0
    assert ax.ticks_z == (0.0, 250.0, 500.0)


def test_axes_num_ticks_is_clamped_to_at_least_two():
    assert AxesConfiguration(EXTENT, num_ticks=1).num_ticks == 2
    assert AxesConfiguration(EXTENT, num_ticks=-5).num_ticks == 2


def test_axes_num_ticks_sizes_the_interval_only_at_construction(axes):
    interval = axes.tick_interval
    axes.num_ticks = 20
    assert axes.tick_interval == interval


# =============================================================================
# AxesConfiguration -- toggles


@pytest.mark.parametrize("attr", ["enable_ticks", "enable_ticks_minor"])
def test_axes_tick_toggles_broadcast_a_single_bool(axes, attr):
    setattr(axes, attr, False)
    assert getattr(axes, attr) == (False, False, False)


@pytest.mark.parametrize("attr", ["enable_ticks", "enable_ticks_minor"])
def test_axes_tick_toggles_accept_one_value_per_axis(axes, attr):
    setattr(axes, attr, (True, False, True))
    assert getattr(axes, attr) == (True, False, True)


def test_axes_label_ticks_defaults_to_the_axes_that_carry_ticks(axes):
    assert axes.enable_labels_ticks == (True, True, True)


def test_axes_label_ticks_is_disabled_for_an_axis_whose_ticks_were_cleared(axes):
    axes.ticks_x = ()
    assert axes.enable_labels_ticks == (False, True, True)


def test_axes_label_ticks_can_be_overridden(axes):
    axes.ticks_x = ()
    axes.enable_labels_ticks = True
    assert axes.enable_labels_ticks == (True, True, True)


# =============================================================================
# AxesConfiguration -- fonts


def test_axes_font_family_points_at_the_bundled_font(axes):
    assert axes.font_family.name == "Inter-Regular.ttf"


# =============================================================================
# AxesConfiguration -- tick fallbacks


def test_axes_cleared_ticks_fall_back_to_even_spacing(axes):
    axes.ticks_x = ()
    assert axes.ticks_x == (0.0, 40.0, 80.0, 120.0, 160.0, 200.0)


def test_axes_tick_fallback_honours_num_ticks(axes):
    axes.num_ticks = 3
    axes.ticks_z = ()
    assert axes.ticks_z == (0.0, 250.0, 500.0)


def test_axes_explicit_ticks_are_returned_verbatim(axes):
    axes.ticks_y = (0.0, 42.0)
    assert axes.ticks_y == (0.0, 42.0)


# =============================================================================
# AxesConfiguration -- precision


def test_axes_precision_needs_no_decimals_for_calibrated_ticks(axes):
    assert axes.precision == (0, 0, 0)


def test_axes_precision_follows_a_fractional_tick_interval():
    ax = AxesConfiguration(EXTENT, tick_interval=2.5)
    assert ax.precision == (1, 1, 1)


def test_axes_precision_follows_a_unit_coarser_than_the_domain():
    ax = AxesConfiguration(EXTENT, unit_display="MILLI")
    assert ax.ticks_z[-1] == pytest.approx(0.5)
    assert ax.precision == (1, 1, 1)


def test_axes_precision_is_derived_per_axis(axes):
    axes.ticks_x = (0.0, 0.25, 0.5)
    assert axes.precision == (2, 0, 0)


def test_axes_precision_accepts_one_value_for_all_axes(axes):
    axes.precision = 3
    assert axes.precision == (3, 3, 3)


def test_axes_precision_returns_to_the_derived_value_when_cleared(axes):
    axes.precision = 3
    axes.precision = None
    assert axes.precision == (0, 0, 0)


# =============================================================================
# AxesConfiguration -- minor ticks


def test_axes_minor_ticks_split_a_leading_1_or_5_into_five(axes):
    assert axes.tick_interval == 100
    assert axes.num_ticks_minor == 4


def test_axes_minor_ticks_split_any_other_step_into_four():
    ax = AxesConfiguration(np.array((100e-06, 100e-06, 100e-06)))
    assert ax.tick_interval == 20
    assert ax.num_ticks_minor == 3


def test_axes_minor_ticks_can_be_set_explicitly(axes):
    axes.num_ticks_minor = 7
    assert axes.num_ticks_minor == 7


def test_axes_minor_ticks_return_to_the_derived_value_when_cleared(axes):
    axes.num_ticks_minor = 7
    axes.num_ticks_minor = None
    assert axes.num_ticks_minor == 4


# =============================================================================
# AxesConfiguration -- tick positions


def test_axes_tick_positions_are_normalized_to_the_extent(axes):
    assert axes.position_tick_x == (0.0, 0.5, 1.0)
    assert axes.position_tick_z == (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)


def test_axes_tick_positions_fall_back_to_even_spacing_without_span():
    ax = AxesConfiguration(np.array((0.0, 400e-06, 500e-06)))
    assert ax.position_tick_x == (0.0,)


def test_axes_tick_positions_can_be_set_explicitly(axes):
    axes.position_tick_y = (0.1, 0.9)
    assert axes.position_tick_y == (0.1, 0.9)


# =============================================================================
# AxesConfiguration -- from_dict


def test_axes_from_dict_calibrates_from_the_extent():
    ax = AxesConfiguration.from_dict(EXTENT, {})
    assert ax.label_x == "x [µm]"
    assert ax.tick_interval == 100


def test_axes_from_dict_reads_the_calibration_keys():
    ax = AxesConfiguration.from_dict(
        EXTENT, {"unit_display": "MILLI", "tick_interval": 0.25, "num_ticks": 3}
    )
    assert ax.label_x == "x [mm]"
    assert ax.tick_interval == 0.25
    assert ax.num_ticks == 3


def test_axes_from_dict_overrides_derived_values():
    ax = AxesConfiguration.from_dict(
        EXTENT, {"label_x": "custom", "precision": (1, 2, 3), "line_width": 0.5}
    )
    assert ax.label_x == "custom"
    assert ax.label_y == "y [µm]"
    assert ax.precision == (1, 2, 3)
    assert ax.line_width == 0.5


def test_axes_from_dict_ignores_unknown_keys():
    ax = AxesConfiguration.from_dict(EXTENT, {"bogus": 5})
    assert not hasattr(ax, "bogus")
