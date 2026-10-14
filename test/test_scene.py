import numpy as np
import pytest

from porescene.color import Color, ColorArray
from porescene.material import Material

bpy = pytest.importorskip("bpy")

from porescene.scene import Scene  # noqa: E402

EXTENT = np.array((1e-4, 1e-4, 1e-4))
POS = np.array([[2e-5, 2e-5, 2e-5], [5e-5, 5e-5, 5e-5], [8e-5, 5e-5, 3e-5]])
R = np.full(3, 5e-6)


@pytest.fixture
def scene():
    bpy.ops.wm.read_factory_settings()
    return Scene(EXTENT)


def color_links(mat, node_type, socket):
    """Returns the attribute names linked into ``socket`` of the node of the type."""
    node = next(n for n in mat.node_tree.nodes if n.type == node_type)
    return [link.from_node.attribute_name for link in node.inputs[socket].links]


def test_spheres_and_cylinders_keep_their_own_materials(scene):
    scene.create_cylinders(np.hstack([POS[:-1], POS[1:]]), R[:-1], material="AXES")
    scene.create_spheres(POS, R, material="STRUCTURE")
    mat_cyl = bpy.data.objects["Cylinder_AXES"].data.materials[0]
    mat_sph = bpy.data.objects["Sphere_STRUCTURE"].data.materials[0]
    assert mat_cyl.name.startswith("AXES")
    assert mat_sph.name.startswith("STRUCTURE")


def test_layers_default_to_the_scene_configuration(scene):
    scene.config_scene.material_spheres = Material("MINE", base_color="#3F901A")
    scene.create_spheres(POS, R)
    mat = bpy.data.objects["Sphere_MINE"].data.materials[0]
    assert mat.name.startswith("MINE")


def test_per_item_colors_pass_through_ambient_occlusion(scene):
    scene.create_spheres(POS, R, material="SOLID")
    mat = bpy.data.objects["Sphere_SOLID"].data.materials[0]
    assert color_links(mat, "MIX_RGB", "Color1") == ["color"]


@pytest.mark.parametrize("as_array", [True, False])
def test_apply_colors_writes_linear_rgba_per_item(scene, as_array):
    scene.create_spheres(POS, R)
    colors = [Color("#f00"), Color("#80808080"), Color("#00f")]
    scene.apply_colors("Spheres", ColorArray(colors) if as_array else colors)
    written = np.zeros(len(colors) * 4, dtype=np.float32)
    bpy.data.meshes["Spheres"].attributes["color"].data.foreach_get("color", written)
    expected = [c.lnrgba for c in colors]
    np.testing.assert_allclose(written.reshape(-1, 4), expected, rtol=1e-6)


def test_clusters_leave_the_shared_material_untouched(scene, tmp_path):
    for i, x in enumerate((2e-5, 7e-5), start=1):
        bpy.ops.mesh.primitive_ico_sphere_add(radius=2e-5, location=(x, 5e-5, 5e-5))
        bpy.context.active_object.name = f"label_{i}"
    pth = tmp_path / "clusters.obj"
    bpy.ops.wm.obj_export(filepath=str(pth), export_materials=False)
    for obj in [o for o in bpy.data.objects if o.name.startswith("label_")]:
        bpy.data.objects.remove(obj)

    scene.create_clusters(pth, material="STRUCTURE")

    mat = bpy.data.collections["Clusters"].objects[0].data.materials[0]
    assert color_links(mat, "BSDF_PRINCIPLED", "Base Color") == ["cluster_color"]
    shared = bpy.data.materials["STRUCTURE"]
    assert not any(n.type == "ATTRIBUTE" for n in shared.node_tree.nodes)


def test_unknown_material_name_raises(scene):
    with pytest.raises(ValueError, match="Unknown material"):
        scene.create_spheres(POS, R, material="PLASTIC_ROUGH")


# two boxes splitting the domain in half along x, the second with an extra corner in the
# middle of its top facet, which is no corner of the hull
CORNERS_POS = np.array(
    [[x, y, z] for x in (0, 5e-5, 1e-4) for y in (0, 1e-4) for z in (0, 1e-4)]
    + [[7.5e-5, 5e-5, 1e-4]]
)
CORNERS = [np.arange(0, 8), np.r_[np.arange(4, 12), 12]]


def cell_faces(mesh):
    """Returns the cell index of every face of the cells' mesh."""
    cells = np.empty(len(mesh.polygons), dtype=np.int32)
    mesh.attributes["cell"].data.foreach_get("value", cells)
    return cells


def test_cells_are_convex_hulls_fanned_out_from_their_facets(scene):
    scene.create_cells(CORNERS_POS, CORNERS)
    mesh = bpy.data.meshes["Cells"]
    assert scene.has_cells
    # six facets of four triangles each, around the eight corners and six centers
    np.testing.assert_array_equal(np.bincount(cell_faces(mesh)), [24, 24])
    assert len(mesh.vertices) == 28


def test_cells_know_the_distance_to_the_edge_of_their_facets(scene):
    scene.create_cells(CORNERS_POS, CORNERS)
    dist = np.empty(len(bpy.data.meshes["Cells"].loops), dtype=np.float32)
    bpy.data.meshes["Cells"].attributes["cell_edge"].data.foreach_get("value", dist)
    # in scene units, the cells are 5 x 10 x 10 boxes
    np.testing.assert_allclose(np.unique(dist.round(4)), [0, 2.5, 5])


def test_cells_build_only_the_selection(scene):
    scene.create_cells(CORNERS_POS, CORNERS, selection=np.array([1]), bevel=0)
    assert set(cell_faces(bpy.data.meshes["Cells"])) == {1}


def test_cells_take_the_color_of_their_cell(scene):
    scene.create_cells(CORNERS_POS, CORNERS, selection=np.array([1]))
    colors = [Color("#f00"), Color("#00f")]
    scene.apply_colors("Cells", colors)
    mesh = bpy.data.meshes["Cells"]
    written = np.zeros(len(mesh.polygons) * 4, dtype=np.float32)
    mesh.attributes["cell_color"].data.foreach_get("color", written)
    np.testing.assert_allclose(
        written.reshape(-1, 4), np.tile(colors[1].lnrgba, (len(mesh.polygons), 1))
    )


def test_cells_need_a_color_per_cell(scene):
    scene.create_cells(CORNERS_POS, CORNERS, selection=np.array([1]))
    with pytest.raises(ValueError, match="each of the 2 cells"):
        scene.apply_colors("Cells", [Color("#00f")])


def test_cells_are_colored_through_their_material(scene):
    scene.config_scene.material_cells = Material("MINE", base_color="#3F901A")
    scene.create_cells(CORNERS_POS, CORNERS, bevel=0)
    mat = bpy.data.objects["Cells"].data.materials[0]
    assert mat.name.startswith("MINE")
    assert color_links(mat, "BSDF_PRINCIPLED", "Base Color") == ["cell_color"]


def test_cells_round_their_edges_off_in_the_shading(scene):
    scene.create_cells(CORNERS_POS, CORNERS, bevel=0.05)
    mat = bpy.data.objects["Cells"].data.materials[0]
    n_pr = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    n_bump = n_pr.inputs["Normal"].links[0].from_node
    assert n_bump.type == "BUMP"
    assert n_bump.inputs["Distance"].default_value == 1
    n_mix = n_pr.inputs["Base Color"].links[0].from_node
    assert color_links(mat, n_mix.type, "Color1") == ["cell_color"]


def test_cells_without_volume_raise(scene):
    flat = CORNERS_POS.copy()
    flat[:, 2] = 0
    with pytest.raises(ValueError, match="cell 0 span no volume"):
        scene.create_cells(flat, CORNERS)
