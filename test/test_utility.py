import numpy as np
import pytest

from porescene.utility import (
    Mesh,
    colorbar_limits,
    colorbar_ticks,
    count_decimals,
    interval_round,
    merge_faces,
    tick_labels,
    unit_metric,
    volume2mesh,
)

# =============================================================================
# Helpers


def face_areas(mesh: Mesh) -> np.ndarray:
    """Area of every face, from its (axis-aligned) bounding box."""
    corners = mesh.vertices[mesh.faces]
    extent = corners.max(axis=1) - corners.min(axis=1)
    extent = np.sort(extent, axis=1)
    # the smallest extent is zero for an axis-aligned face
    return extent[:, 1] * extent[:, 2]


def as_quads(mesh: Mesh) -> set[tuple]:
    """The faces as a set of coordinate tuples, independent of vertex numbering."""
    return {tuple(sorted(map(tuple, corners))) for corners in mesh.vertices[mesh.faces]}


# =============================================================================
# merge_faces


def test_merge_faces_leaves_a_single_voxel_untouched():
    mesh = volume2mesh(np.ones((1, 1, 1), dtype=int), merge=False)
    merged = merge_faces(mesh)

    assert len(merged.faces) == 6
    assert len(merged.vertices) == 8
    assert as_quads(merged) == as_quads(mesh)


@pytest.mark.parametrize("res", [(2, 2, 2), (5, 3, 4), (10, 10, 10)])
def test_merge_faces_reduces_a_box_to_its_six_sides(res):
    merged = merge_faces(volume2mesh(np.ones(res, dtype=int), merge=False))

    assert len(merged.faces) == 6
    assert len(merged.vertices) == 8


def test_merge_faces_reduces_a_flat_slab_to_its_six_sides():
    # a one voxel thick plate: two large faces plus four rims
    merged = merge_faces(volume2mesh(np.ones((8, 6, 1), dtype=int), merge=False))

    assert len(merged.faces) == 6
    assert len(merged.vertices) == 8


def test_merge_faces_keeps_the_corners_of_a_box():
    size = 1e-6
    mesh = volume2mesh(np.ones((4, 4, 4), dtype=int), size, merge=False)
    merged = merge_faces(mesh)
    expected = np.array(np.meshgrid([0, 4], [0, 4], [0, 4], indexing="ij"))

    assert np.allclose(
        np.sort(merged.vertices, axis=0),
        np.sort(expected.reshape(3, -1).T * size, axis=0),
    )


def test_merge_faces_scales_with_voxel_size():
    img = np.ones((3, 3, 3), dtype=int)
    unit = merge_faces(volume2mesh(img, merge=False))
    scaled = merge_faces(volume2mesh(img, 2.5, merge=False))

    assert np.allclose(scaled.vertices, unit.vertices * 2.5)


def test_merge_faces_handles_anisotropic_voxels():
    size = (1.0, 2.0, 4.0)
    merged = merge_faces(volume2mesh(np.ones((2, 2, 2), dtype=int), size, merge=False))

    # the box measures 2 x 4 x 8, so each pair of opposite sides spans the two axes it
    # is not normal to
    assert np.allclose(sorted(face_areas(merged)), [8.0] * 2 + [16.0] * 2 + [32.0] * 2)


def test_merge_faces_preserves_the_surface_of_a_random_volume():
    rng = np.random.default_rng(0)
    img = (rng.random((12, 14, 10)) > 0.4).astype(int)
    mesh = volume2mesh(img, 1e-6, merge=False)
    merged = merge_faces(mesh)

    assert len(merged.vertices) < len(mesh.vertices)
    assert np.isclose(face_areas(merged).sum(), face_areas(mesh).sum())


def test_merge_faces_preserves_the_surface_of_a_plate_with_a_hole():
    img = np.ones((7, 7, 1), dtype=int)
    img[3, 3, 0] = 0
    mesh = volume2mesh(img, merge=False)
    merged = merge_faces(mesh)

    assert len(merged.faces) < len(mesh.faces)
    assert np.isclose(face_areas(merged).sum(), face_areas(mesh).sum())


def test_merge_faces_drops_no_vertex_of_a_stair_shaped_surface():
    # a staircase has no coplanar neighbours to merge along its steps
    img = np.tril(np.ones((6, 6), dtype=int))[:, :, np.newaxis]
    mesh = volume2mesh(img, merge=False)
    merged = merge_faces(mesh)

    assert np.isclose(face_areas(merged).sum(), face_areas(mesh).sum())


def test_merge_faces_is_idempotent():
    rng = np.random.default_rng(1)
    img = (rng.random((9, 9, 9)) > 0.5).astype(int)
    merged = merge_faces(volume2mesh(img, merge=False))
    again = merge_faces(merged)

    assert as_quads(again) == as_quads(merged)
    assert np.allclose(again.vertices, merged.vertices)


def test_merge_faces_keeps_every_vertex_referenced():
    rng = np.random.default_rng(2)
    img = (rng.random((8, 8, 8)) > 0.5).astype(int)
    merged = merge_faces(volume2mesh(img, merge=False))

    assert np.array_equal(np.unique(merged.faces), np.arange(len(merged.vertices)))


def test_merge_faces_keeps_the_face_winding():
    mesh = volume2mesh(np.ones((1, 1, 1), dtype=int), merge=False)
    merged = merge_faces(mesh)
    winding = {
        tuple(sorted(map(tuple, corners))): tuple(map(tuple, corners))
        for corners in mesh.vertices[mesh.faces]
    }

    for corners in merged.vertices[merged.faces]:
        key = tuple(sorted(map(tuple, corners)))
        assert winding[key] == tuple(map(tuple, corners))


def test_merge_faces_keeps_the_mesh_name():
    mesh = volume2mesh(np.ones((2, 2, 2), dtype=int), name="solid", merge=False)

    assert merge_faces(mesh).name == "solid"


def test_merge_faces_leaves_the_input_untouched():
    mesh = volume2mesh(np.ones((3, 3, 3), dtype=int), merge=False)
    vertices = mesh.vertices.copy()
    faces = mesh.faces.copy()
    merge_faces(mesh)

    assert np.array_equal(mesh.vertices, vertices)
    assert np.array_equal(mesh.faces, faces)


def test_merge_faces_accepts_a_label_mapping():
    img = np.zeros((4, 4, 2), dtype=int)
    img[:2, :, :] = 1
    img[2:, :, :] = 2
    meshes = merge_faces(
        volume2mesh(img, labels=[1, 2], per_label=True, name="label", merge=False)
    )

    assert sorted(meshes) == [1, 2]
    assert all(len(m.faces) == 6 for m in meshes.values())
    assert meshes[2].name == "label_2"


def test_merge_faces_handles_an_empty_mesh():
    merged = merge_faces(volume2mesh(np.zeros((3, 3, 3), dtype=int), merge=False))

    assert merged.faces.shape == (0, 4)
    assert merged.vertices.shape == (0, 3)


def test_merge_faces_rejects_non_quad_faces():
    mesh = Mesh(np.zeros((3, 3)), np.array([[0, 1, 2]]))

    with pytest.raises(ValueError, match=r"\(M, 4\)"):
        merge_faces(mesh)


def test_merge_faces_rejects_faces_that_are_not_axis_aligned():
    # a quad tilted out of the xy plane
    vertices = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0]]
    )
    mesh = Mesh(vertices, np.array([[0, 1, 2, 3]]))

    with pytest.raises(ValueError, match="axis-aligned"):
        merge_faces(mesh)


# =============================================================================
# volume2mesh -- merge


def test_volume2mesh_merges_by_default():
    merged = volume2mesh(np.ones((10, 10, 10), dtype=int))

    assert len(merged.faces) == 6
    assert len(merged.vertices) == 8


@pytest.mark.parametrize(
    ("res", "faces"),
    [((1, 1, 1), 6), ((2, 2, 2), 24), ((8, 6, 1), 124)],
)
def test_volume2mesh_without_merge_keeps_one_quad_per_voxel_face(res, faces):
    mesh = volume2mesh(np.ones(res, dtype=int), merge=False)

    assert len(mesh.faces) == faces
    assert np.all(np.isclose(face_areas(mesh), 1.0))


@pytest.mark.parametrize("threshold", [0.3, 0.5, 0.7])
def test_volume2mesh_merge_matches_merge_faces(threshold):
    rng = np.random.default_rng(3)
    img = (rng.random((11, 13, 9)) > threshold).astype(int)
    merged = volume2mesh(img, 1e-6)
    expected = merge_faces(volume2mesh(img, 1e-6, merge=False))

    assert np.allclose(merged.vertices, expected.vertices)
    assert np.array_equal(merged.faces, expected.faces)


def test_volume2mesh_merge_matches_merge_faces_with_swapped_axes():
    rng = np.random.default_rng(4)
    img = (rng.random((7, 9, 5)) > 0.5).astype(int)
    merged = volume2mesh(img, (1.0, 2.0, 3.0), swap_axes=True)
    expected = merge_faces(volume2mesh(img, (1.0, 2.0, 3.0), swap_axes=True, merge=False))

    assert np.allclose(merged.vertices, expected.vertices)
    assert np.array_equal(merged.faces, expected.faces)


def test_volume2mesh_merge_matches_merge_faces_per_label():
    rng = np.random.default_rng(5)
    img = rng.integers(0, 4, (8, 8, 8))
    labels = [1, 2, 3]
    merged = volume2mesh(img, 1e-6, labels, per_label=True)
    expected = merge_faces(volume2mesh(img, 1e-6, labels, per_label=True, merge=False))

    for label in labels:
        assert np.allclose(merged[label].vertices, expected[label].vertices)
        assert np.array_equal(merged[label].faces, expected[label].faces)


def test_volume2mesh_merge_preserves_the_surface_of_a_random_volume():
    rng = np.random.default_rng(6)
    img = (rng.random((12, 14, 10)) > 0.4).astype(int)
    merged = volume2mesh(img, 1e-6)
    raw = volume2mesh(img, 1e-6, merge=False)

    assert len(merged.faces) < len(raw.faces)
    assert np.isclose(face_areas(merged).sum(), face_areas(raw).sum())


def test_volume2mesh_merge_handles_an_empty_volume():
    merged = volume2mesh(np.zeros((3, 3, 3), dtype=int))

    assert merged.faces.shape == (0, 4)
    assert merged.vertices.shape == (0, 3)


def test_volume2mesh_merge_handles_a_2d_image():
    merged = volume2mesh(np.ones((5, 4), dtype=int))

    assert len(merged.faces) == 6
    assert len(merged.vertices) == 8


# =============================================================================
# interval_round


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
    assert interval_round(span, 6) == expected


@pytest.mark.parametrize("span", [0, -1, float("nan"), float("inf")])
def test_interval_round_falls_back_to_one_for_degenerate_spans(span):
    assert interval_round(span, 6) == 1.0


# =============================================================================
# unit_metric


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
    assert unit_metric(span) == expected


@pytest.mark.parametrize(
    ("span", "expected"),
    [
        (500.0, "BASE"),  # 500 m
        (5e03, "BASE"),  # 5000 m
        (5e04, "KILO"),  # 50 km
    ],
)
def test_unit_metric_reaches_the_unprefixed_base_unit(span, expected):
    assert unit_metric(span) == expected


@pytest.mark.parametrize(("span", "expected"), [(1e40, "QUETTA"), (1e-40, "QUECTO")])
def test_unit_metric_clamps_to_the_outermost_prefixes(span, expected):
    assert unit_metric(span) == expected


@pytest.mark.parametrize("span", [0, -1, float("nan"), float("inf")])
def test_unit_metric_falls_back_to_micro_for_degenerate_spans(span):
    assert unit_metric(span) == "MICRO"


# =============================================================================
# count_decimals


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
def test_count_decimals_counts_what_it_takes_to_write_every_tick(ticks, expected):
    assert count_decimals(ticks) == expected


def test_count_decimals_ignores_the_noise_of_a_binary_representation():
    # 0.1 + 0.2 lands on 0.30000000000000004, which must not claim 17 decimals
    assert count_decimals((0.0, 0.1, 0.2, 0.1 + 0.2)) == 1


def test_count_decimals_is_capped():
    assert count_decimals((1 / 3,)) == 6
    assert count_decimals((1 / 3,), limit=2) == 2


# =============================================================================
# colorbar_limits


@pytest.mark.parametrize(
    ("mn", "mx", "precision", "expected"),
    [
        (0.3, 4.2, 0, (0.0, 5.0)),  # whole numbers
        (0.3, 4.2, 1, (0.3, 4.2)),  # tenths, already even
        (0.34, 4.21, 1, (0.3, 4.3)),
        (12.0, 87.0, -1, (10.0, 90.0)),  # whole tens
    ],
)
def test_colorbar_limits_round_outward_to_the_precision(mn, mx, precision, expected):
    assert colorbar_limits(mn, mx, precision) == expected


def test_colorbar_limits_never_narrow_the_range():
    lower, upper = colorbar_limits(0.34, 4.21, 0)
    assert lower <= 0.34
    assert upper >= 4.21


def test_colorbar_limits_widen_a_range_that_collapses():
    assert colorbar_limits(2.0, 2.0, 0) == (2.0, 3.0)
    assert colorbar_limits(2.4, 2.4, 0) == (2.0, 3.0)


def test_colorbar_limits_apply_the_factor_and_the_transform():
    # 2 µm .. 7 µm, given in meters and displayed in µm
    assert colorbar_limits(2e-06, 7e-06, 0, 1e6) == (2.0, 7.0)
    assert colorbar_limits(2.0, 3.0, 0, 1.0, lambda v: v**2) == (4.0, 9.0)


@pytest.mark.parametrize(
    ("mn", "mx", "expected"),
    [
        (3.0, 68.0, (0.0, 70.0)),  # interval 10
        (0.012, 0.087, (0.0, 0.1)),  # interval 0.02
        (0.11, 0.34, (0.1, 0.35)),  # interval 0.05, free of binary noise
        (-7.0, 23.0, (-10.0, 25.0)),  # interval 5
    ],
)
def test_colorbar_limits_derive_an_even_interval_without_a_precision(mn, mx, expected):
    assert colorbar_limits(mn, mx) == expected


def test_colorbar_limits_derived_from_a_collapsed_range_stay_apart():
    lower, upper = colorbar_limits(2.0, 2.0)
    assert lower < upper


@pytest.mark.parametrize("mn", [float("nan"), float("inf")])
def test_colorbar_limits_reject_a_range_that_is_not_finite(mn):
    with pytest.raises(ValueError, match="must be finite"):
        colorbar_limits(mn, 1.0)


def test_colorbar_limits_reject_an_inverted_range():
    with pytest.raises(ValueError, match="lies below"):
        colorbar_limits(4.0, 1.0)


# =============================================================================
# colorbar_ticks


def test_colorbar_ticks_span_the_limits():
    ticks = colorbar_ticks(0.0, 70.0, 8)
    assert len(ticks) == 8
    assert (ticks[0], ticks[-1]) == (0.0, 70.0)


def test_colorbar_ticks_are_equidistant():
    # the annotation places the ticks by their position in the sequence, so their
    # values have to be evenly spaced for the colorbar to tell the truth
    ticks = colorbar_ticks(-10.0, 25.0, 8)
    steps = np.diff(ticks)
    assert steps == pytest.approx(steps[0])


def test_colorbar_ticks_land_on_even_values_for_even_limits():
    assert colorbar_ticks(*colorbar_limits(3.0, 68.0), 8) == (
        0.0,
        10.0,
        20.0,
        30.0,
        40.0,
        50.0,
        60.0,
        70.0,
    )


def test_colorbar_ticks_are_rounded_to_the_given_precision():
    assert colorbar_ticks(0.0, 1.0, 3, precision=1) == (0.0, 0.5, 1.0)
    assert colorbar_ticks(0.0, 2.0, 4, precision=1) == (0.0, 0.7, 1.3, 2.0)


def test_colorbar_ticks_need_both_limits():
    with pytest.raises(ValueError, match="at least 2 ticks"):
        colorbar_ticks(0.0, 1.0, 1)


# =============================================================================
# tick_labels


def test_tick_labels_drop_the_decimals_of_a_whole_value():
    assert tick_labels((0.0, 17.5, 35.0)) == ("0", "17.5", "35")


def test_tick_labels_derive_the_decimals_from_the_values():
    assert tick_labels((0.0, 0.25, 0.5)) == ("0", "0.25", "0.5")
    assert tick_labels((0.0, 100.0, 200.0)) == ("0", "100", "200")


def test_tick_labels_honour_a_given_number_of_decimals():
    assert tick_labels((1 / 3, 2 / 3), decimals=2) == ("0.33", "0.67")
    assert tick_labels((1 / 3, 2 / 3), decimals=0) == ("0", "1")


def test_tick_labels_keep_a_rounded_value_whole():
    # 20.001 written with two decimals is "20.00", which must not read as "2"
    assert tick_labels((20.001,), decimals=2) == ("20",)
