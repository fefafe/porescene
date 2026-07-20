# PoreScene

PoreScene is a [Blender](https://docs.blender.org/api/current/)-based scientific
visualization toolkit for porous media. It renders tomographic images, generated and
reconstructed pore networks, as well as volume tessellations as photorealistic 3D scenes
– with pores, throats, Voronoi cells, and watershed clusters colored by properties such
as radius or coordination number using perceptually uniform colormaps, matching
colorbars, and calibrated, on-scale axes.

The advantage: instead of clicking through a 3D editor, you describe the entire scene in a
few lines of Python and render it reproducibly on Blender's GPU-accelerated *Cycles*
engine – so the same script always yields the same publication-quality figure, ready for
papers, presentations, and animations.

## Funding

This work was funded by the Deutsche Forschungsgemeinschaft (DFG, German Research Foundation) – Project-ID 422037413 – TRR 287.
