import numpy as np
import pytest

from porescene.utility import Mesh, merge_faces, volume2mesh

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
