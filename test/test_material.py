from dataclasses import FrozenInstanceError, replace

import pytest

from porescene import material
from porescene.color import Color
from porescene.material import (
    SOLID,
    BlendMaterial,
    Material,
    color_inputs,
    lookup,
    names,
    register,
)

BUILTIN = [
    "STRUCTURE",
    "SOLID",
    "SOLID_TRANSPARENT",
    "VOID",
    "CELL",
    "CELL_TRANSPARENT",
    "AXES",
]


@pytest.fixture(autouse=True)
def registry(monkeypatch):
    """Lets every test change the registry without affecting the others."""
    monkeypatch.setattr(material, "_REGISTRY", dict(material._REGISTRY))


@pytest.fixture
def bpy():
    """Blender, with every material a test creates removed afterwards."""
    bpy = pytest.importorskip("bpy")
    before = {m.name for m in bpy.data.materials}
    yield bpy
    for mat in [m for m in bpy.data.materials if m.name not in before]:
        bpy.data.materials.remove(mat)


def test_builtin_materials_are_registered():
    assert set(BUILTIN) <= set(names())


def test_names_are_sorted():
    assert names() == sorted(names())


def test_lookup_ignores_case():
    assert lookup("solid") is SOLID


def test_lookup_passes_material_through():
    custom = Material("CUSTOM")
    assert lookup(custom) is custom


def test_lookup_unknown_name_lists_registered_names():
    with pytest.raises(ValueError, match="SOLID_TRANSPARENT"):
        lookup("PLASTIC_ROUGH")


def test_lookup_rejects_other_types():
    with pytest.raises(TypeError):
        lookup(42)


def test_register_makes_material_available_by_name():
    custom = register(Material("bacteria_green", base_color="#3F901A"))
    assert lookup("BACTERIA_GREEN") is custom


def test_register_refuses_to_replace_by_default():
    with pytest.raises(ValueError, match="overwrite"):
        register(Material("solid"))


def test_register_replaces_with_overwrite():
    custom = Material("SOLID", base_color="#808080")
    register(custom, overwrite=True)
    assert lookup("SOLID") is custom


def test_register_accepts_any_object_with_name_and_build():
    class Custom:
        name = "CUSTOM"

        def build(self):
            raise NotImplementedError

    custom = register(Custom())
    assert lookup("custom") is custom


def test_register_rejects_other_types():
    with pytest.raises(TypeError):
        register("SOLID")


def test_material_parses_hex_color():
    assert Material("X", base_color="#3F901A").base_color.lnrgba == pytest.approx(
        Color("#3F901A").lnrgba
    )


def test_material_keeps_color_object():
    color = Color("#3F901A")
    assert Material("X", base_color=color).base_color is color


def test_material_needs_a_name():
    with pytest.raises(ValueError):
        Material("")


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("opacity", -0.1),
        ("opacity", 1.1),
        ("occlusion", 2),
        ("bevel", -0.01),
        ("occlusion_distance", -1),
    ],
)
def test_material_rejects_values_out_of_range(key, value):
    with pytest.raises(ValueError, match=key):
        Material("X", **{key: value})


def test_material_is_immutable():
    with pytest.raises(FrozenInstanceError):
        SOLID.roughness = 1


def test_replace_derives_a_variant():
    grey = replace(SOLID, name="SOLID_GREY", base_color="#808080")
    assert grey.bevel == SOLID.bevel
    assert grey.base_color.lnrgba == pytest.approx(Color("#808080").lnrgba)


def test_replace_validates_the_variant():
    with pytest.raises(ValueError):
        replace(SOLID, opacity=2)


@pytest.mark.parametrize("name", BUILTIN)
def test_builtin_materials_build(bpy, name):
    assert lookup(name).build().name == name


def test_build_sets_principled_inputs(bpy):
    mat = Material(
        "TEST_INPUTS",
        base_color="#3F901A",
        metallic=0.2,
        roughness=1,
        opacity=0.5,
        inputs={"Coat Weight": 0.3},
    ).build()
    n_pr = mat.node_tree.nodes["Principled BSDF"]
    assert tuple(n_pr.inputs["Base Color"].default_value) == pytest.approx(
        Color("#3F901A").lnrgba
    )
    assert n_pr.inputs["Metallic"].default_value == pytest.approx(0.2)
    assert n_pr.inputs["Roughness"].default_value == pytest.approx(1)
    assert n_pr.inputs["Alpha"].default_value == pytest.approx(0.5)
    assert n_pr.inputs["Coat Weight"].default_value == pytest.approx(0.3)


def test_build_adds_no_nodes_by_default(bpy):
    mat = Material("TEST_PLAIN").build()
    assert {n.type for n in mat.node_tree.nodes} == {"BSDF_PRINCIPLED", "OUTPUT_MATERIAL"}


def test_build_adds_bevel_and_occlusion(bpy):
    mat = Material("TEST_EXTRAS", bevel=0.02, occlusion=0.3).build()
    types = {n.type for n in mat.node_tree.nodes}
    assert {"BEVEL", "AMBIENT_OCCLUSION", "MIX_RGB", "RGB"} <= types


def test_color_inputs_default_to_base_color(bpy):
    mat = Material("TEST_PLAIN").build()
    assert [(s.node.type, s.name) for s in color_inputs(mat)] == [
        ("BSDF_PRINCIPLED", "Base Color")
    ]


def test_color_inputs_keep_ambient_occlusion(bpy):
    mat = Material("TEST_OCCLUSION", occlusion=0.3).build()
    assert [(s.node.type, s.name) for s in color_inputs(mat)] == [("MIX_RGB", "Color1")]


def test_color_inputs_need_principled_or_color_node(bpy):
    mat = bpy.data.materials.new("TEST_EMPTY")
    mat.node_tree.nodes.remove(mat.node_tree.nodes["Principled BSDF"])
    with pytest.raises(ValueError, match=material.COLOR_NODE):
        color_inputs(mat)


@pytest.fixture
def pth_blend(bpy, tmp_path):
    """A ``.blend`` file holding the single material ``TEST_SOURCE``."""
    src = Material("TEST_SOURCE", base_color="#3F901A").build()
    pth = tmp_path / "materials.blend"
    bpy.data.libraries.write(str(pth), {src})
    bpy.data.materials.remove(src)
    return pth


def test_blend_material_appends_from_file(bpy, pth_blend):
    mat = BlendMaterial("TEST_BLEND", pth_blend, source="TEST_SOURCE").build()
    assert mat.name == "TEST_BLEND"
    n_pr = mat.node_tree.nodes["Principled BSDF"]
    assert tuple(n_pr.inputs["Base Color"].default_value) == pytest.approx(
        Color("#3F901A").lnrgba
    )


def test_blend_material_source_defaults_to_name(bpy, pth_blend):
    assert BlendMaterial("TEST_SOURCE", pth_blend).build().name == "TEST_SOURCE"


def test_blend_material_lists_materials_in_file(bpy, pth_blend):
    with pytest.raises(ValueError, match="TEST_SOURCE"):
        BlendMaterial("MISSING", pth_blend).build()
