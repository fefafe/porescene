# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Felix Faber /
# Otto von Guericke University Magdeburg, Thermal Process Engineering

"""
Materials the elements of a :class:`~porescene.scene.Scene` are rendered with.

A material is anything with a ``name`` and a ``build()`` method that creates it in
Blender, see :class:`MaterialSpec`. PoreScene ships two kinds:

* :class:`Material` -- a Principled BSDF surface described by a handful of numbers,
  with optional bevel, ambient occlusion and transparency. The built-in materials are
  all of this kind.
* :class:`BlendMaterial` -- a material taken from a ``.blend`` file, for shaders
  designed in Blender's node editor.

The ``create_*`` methods of :class:`~porescene.scene.Scene` accept a material or the
name of a registered one. :func:`register` adds a material to the registry, so it can
also be named in :class:`~porescene.config.SceneConfiguration`.

Spheres, cylinders and clusters are colored per item, e.g. one color per pore. The
scene feeds these colors into the inputs that the node named :data:`COLOR_NODE`
connects to or, if the material has no such node, into the ``Base Color`` of its
Principled BSDF, see :func:`color_inputs`. A material with neither can only render the
solid, the void, the cells and the axes.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from porescene.color import Color

if TYPE_CHECKING:
    import bpy

COLOR_NODE = "PoreScene Color"
"""
Name of the node whose output per-item colors replace, see :func:`color_inputs`.
"""


@runtime_checkable
class MaterialSpec(Protocol):
    """
    Interface of a material: a name and a method that builds it in Blender.

    :class:`Material` and :class:`BlendMaterial` implement it, but any object with
    these two members can be passed to the scene or to :func:`register`.
    """

    @property
    def name(self) -> str:
        """
        Name of the material. A scene builds each name once and reuses the result.
        """
        ...

    def build(self) -> bpy.types.Material:
        """Creates the material in Blender's data and returns it."""
        ...


@dataclass(frozen=True)
class Material:
    """
    A Principled BSDF surface described by its main inputs.

    Fields not given take the defaults of Blender's Principled BSDF. Derive a
    variant of an existing material with :func:`dataclasses.replace`::

        from dataclasses import replace

        mine = replace(SOLID, name="SOLID_GREY", base_color="#808080")

    Parameters
    ----------
    name : str
        Name of the material, see :attr:`MaterialSpec.name`.
    base_color : Color | str
        Color of the surface, as :class:`~porescene.color.Color` or HEX string. Per-item
        colors replace it.
    metallic : float
        ``Metallic`` input, from ``0`` (dielectric) to ``1`` (metal).
    roughness : float
        ``Roughness`` input, from ``0`` (mirror-like) to ``1`` (matte).
    specular : float
        ``Specular IOR Level`` input, the strength of the specular highlights.
    subsurface : float
        ``Subsurface Weight`` input, the share of light scattered below the surface.
    subsurface_scale : float
        ``Subsurface Scale`` input, how far that light travels, in scene units.
    sheen : float
        ``Sheen Weight`` input, a soft velvet-like layer seen at grazing angles.
    sheen_roughness : float
        ``Sheen Roughness`` input.
    opacity : float
        ``Alpha`` input, from ``0`` (invisible) to ``1`` (opaque).
    bevel : float
        Radius over which edges are rounded off in the shading, in scene units; ``0``
        turns it off. Makes the facets of a coarse mesh look smooth.
    occlusion : float
        Strength of the ambient occlusion that darkens creases and cavities, from
        ``0`` (off) to ``1``.
    occlusion_distance : float
        Distance up to which nearby geometry counts as occluding, in scene units.
    inputs : Mapping[str, float | tuple[float, ...]]
        Values for further inputs of the Principled BSDF, keyed by their name in
        Blender, such as ``{"Coat Weight": 0.5}``. They take precedence over the
        fields above.
    """

    name: str
    base_color: Color | str = "#E7E7E7"
    metallic: float = 0.0
    roughness: float = 0.5
    specular: float = 0.5
    subsurface: float = 0.0
    subsurface_scale: float = 0.05
    sheen: float = 0.0
    sheen_roughness: float = 0.5
    opacity: float = 1.0
    bevel: float = 0.0
    occlusion: float = 0.0
    occlusion_distance: float = 0.5
    inputs: Mapping[str, float | tuple[float, ...]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("A material needs a name")
        if isinstance(self.base_color, str):
            object.__setattr__(self, "base_color", Color(self.base_color))
        for key in ("opacity", "occlusion"):
            value = getattr(self, key)
            if not 0 <= value <= 1:
                raise ValueError(f"{key} must lie between 0 and 1, got {value}")
        for key in ("bevel", "occlusion_distance"):
            value = getattr(self, key)
            if value < 0:
                raise ValueError(f"{key} must not be negative, got {value}")

    def build(self) -> bpy.types.Material:
        """
        Creates the material in Blender's data and returns it.
        """
        import bpy

        mat = bpy.data.materials.new(self.name)
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        n_pr = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
        n_pr.subsurface_method = "BURLEY"

        values = {
            "Metallic": self.metallic,
            "Roughness": self.roughness,
            "Specular IOR Level": self.specular,
            "Subsurface Weight": self.subsurface,
            "Subsurface Scale": self.subsurface_scale,
            "Sheen Weight": self.sheen,
            "Sheen Roughness": self.sheen_roughness,
            "Alpha": self.opacity,
        }
        for key, value in {**values, **self.inputs}.items():
            n_pr.inputs[key].default_value = value

        color = self.base_color.lnrgba
        if self.occlusion > 0:
            # the base color enters through a named node, so per-item colors are
            # darkened by the ambient occlusion as well, see color_inputs
            n_color = nodes.new("ShaderNodeRGB")
            n_color.name = COLOR_NODE
            n_color.outputs["Color"].default_value = color

            n_ao = nodes.new("ShaderNodeAmbientOcclusion")
            n_ao.only_local = True
            n_ao.inputs["Distance"].default_value = self.occlusion_distance

            n_ao_mix = nodes.new("ShaderNodeMixRGB")
            n_ao_mix.blend_type = "MULTIPLY"
            n_ao_mix.inputs["Factor"].default_value = self.occlusion

            links.new(n_color.outputs["Color"], n_ao_mix.inputs["Color1"])
            links.new(n_ao.outputs["Color"], n_ao_mix.inputs["Color2"])
            links.new(n_ao_mix.outputs["Color"], n_pr.inputs["Base Color"])
        elif "Base Color" not in self.inputs:
            n_pr.inputs["Base Color"].default_value = color

        if self.bevel > 0:
            n_bevel = nodes.new("ShaderNodeBevel")
            n_bevel.inputs["Radius"].default_value = self.bevel
            links.new(n_bevel.outputs["Normal"], n_pr.inputs["Normal"])

        return mat


@dataclass(frozen=True)
class BlendMaterial:
    """
    A material appended from a ``.blend`` file.

    Lets a shader be designed in Blender's node editor and saved to a file, then used
    from a script. To be colored per item, the material needs a node named
    :data:`COLOR_NODE` or a Principled BSDF, see :func:`color_inputs`.

    Parameters
    ----------
    name : str
        Name of the material in PoreScene, see :attr:`MaterialSpec.name`.
    path : Path
        Path to the ``.blend`` file.
    source : str | None
        Name of the material inside the file; defaults to :attr:`name`.
    """

    name: str
    path: Path
    source: str | None = None

    def build(self) -> bpy.types.Material:
        """
        Appends the material from :attr:`path` and returns it, renamed to
        :attr:`name`.
        """
        import bpy

        source = self.source or self.name
        with bpy.data.libraries.load(str(self.path), link=False) as (src, dst):
            if source not in src.materials:
                raise ValueError(
                    f"There is no material named '{source}' in {self.path.name}, "
                    f"found: {', '.join(src.materials) or 'none'}"
                )
            dst.materials = [source]
        mat = dst.materials[0]
        mat.name = self.name
        return mat


def color_inputs(mat: bpy.types.Material) -> list[bpy.types.NodeSocket]:
    """
    Returns the inputs of ``mat`` that per-item colors are fed into.

    These are the inputs the node named :data:`COLOR_NODE` connects to if ``mat`` has
    one, and the ``Base Color`` of its Principled BSDF otherwise.

    Raises
    ------
    ValueError
        If ``mat`` has neither.
    """
    nodes = mat.node_tree.nodes
    n_color = nodes.get(COLOR_NODE)
    if n_color is not None:
        return [link.to_socket for out in n_color.outputs for link in out.links]
    n_pr = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)
    if n_pr is None:
        raise ValueError(
            f"Material '{mat.name}' can't be colored per item: it needs a node named "
            f"'{COLOR_NODE}' or a Principled BSDF"
        )
    return [n_pr.inputs["Base Color"]]


_REGISTRY: dict[str, MaterialSpec] = {}


def register[M: MaterialSpec](material: M, overwrite: bool = False) -> M:
    """
    Adds ``material`` to the registry, so it can be looked up by its name.

    Names are case-insensitive.

    Parameters
    ----------
    material : MaterialSpec
        Material to register.
    overwrite : bool, optional
        If true, replaces a material registered under the same name, by default False.

    Returns
    -------
    MaterialSpec
        The registered material, so that registering and assigning it can be one
        statement.

    Raises
    ------
    ValueError
        If a material of that name is registered already and ``overwrite`` is false.
    """
    if not isinstance(material, MaterialSpec):
        raise TypeError(f"Expected a material, got {type(material).__name__}")
    key = material.name.upper()
    if key in _REGISTRY and not overwrite:
        raise ValueError(
            f"A material named '{key}' is registered already, pass overwrite=True to "
            "replace it"
        )
    _REGISTRY[key] = material
    return material


def lookup(material: str | MaterialSpec) -> MaterialSpec:
    """
    Returns the registered material of the given name, or ``material`` itself if it
    is a material already.

    Raises
    ------
    ValueError
        If no material of that name is registered.
    """
    if not isinstance(material, str):
        if not isinstance(material, MaterialSpec):
            raise TypeError(
                f"Expected a material or its name, got {type(material).__name__}"
            )
        return material
    try:
        return _REGISTRY[material.upper()]
    except KeyError:
        raise ValueError(
            f"Unknown material '{material}', expected one of {', '.join(names())}"
        ) from None


def names() -> list[str]:
    """Returns the names of all registered materials, sorted alphabetically."""
    return sorted(_REGISTRY)


STRUCTURE = register(
    Material(
        "STRUCTURE",
        base_color="#58646E",
        metallic=0.4,
        roughness=0.5,
        specular=0.1,
        subsurface=0.1,
        sheen=0.1,
        sheen_roughness=0,
    )
)
"""Default material of the pore spheres, throat cylinders and pore clusters."""

SOLID = register(
    Material(
        "SOLID",
        base_color="#C6A87A",
        roughness=0.5,
        specular=0.5,
        subsurface=0.12,
        subsurface_scale=0.15,
        sheen=0.1,
        sheen_roughness=0.3,
        bevel=0.02,
        occlusion=0.3,
        occlusion_distance=0.5,
    )
)
"""
Default material of the solid. It is matte, with rounded edges and ambient occlusion
that brings out the depth of the pore space.
"""

SOLID_TRANSPARENT = register(
    Material(
        "SOLID_TRANSPARENT",
        base_color="#947C5E",
        roughness=1,
        specular=0.5,
        opacity=0.25,
    )
)
"""Mostly transparent solid, to show the structures inside it."""

VOID = register(
    Material(
        "VOID",
        base_color="#85A2E6",
        roughness=1,
        specular=1,
        subsurface=0.1,
        sheen_roughness=1,
    )
)
"""Default material of the void space."""

CELL = register(
    Material(
        "CELL",
        base_color="#947C5E",
        metallic=0.2,
        roughness=0.8,
        opacity=0.8,
        bevel=0.05,
    )
)
"""Default material of the tessellation cells."""

CELL_TRANSPARENT = register(
    Material(
        "CELL_TRANSPARENT",
        base_color="#947C5E",
        metallic=0.2,
        roughness=0.8,
        opacity=0.4,
        bevel=0.125,
    )
)
"""Mostly transparent tessellation cells."""

AXES = register(
    Material(
        "AXES",
        base_color="#000000",
        roughness=1,
        specular=0,
    )
)
"""Material of the axis lines, ticks and labels."""
