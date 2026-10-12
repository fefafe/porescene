import numpy as np
import pytest

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
