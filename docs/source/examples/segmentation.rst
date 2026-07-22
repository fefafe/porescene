Pore space segmentation
=======================

Once the void phase of a porous material has been segmented into  individual pore clusters, PoreScene can render every cluster as a separate object
and color each one on its own. This makes the connectivity of the pore space
immediately visible and is a natural companion to the :doc:`solid structure <solid>`
visualization.

This example shows how to turn a segmented 3D voxel image -- in which every void voxel
carries the integer label of the cluster it belongs to -- into one mesh per cluster,
load them into the scene, and give each cluster a random color from a colormap.

As an example, this tutorial uses the segmented void space of the same freeze-dried
sugar solution captured with X-ray micro-computed tomographic imaging
:footcite:p:`2025_faber_Porescale` that is used in the :doc:`solid structure <solid>`
example, available in PoreScene's repository on GitHub:
`data/img_seg.raw <https://github.com/fefafe/porescene/tree/main/data>`_


.. figure:: ../_static/image/examples/cluster-random+axes.png
   :alt: Segmented pore space with each void cluster colored individually
   :figclass: ps-figure

   The rendered result: the segmented pore space, with every void cluster colored
   individually from a random selection of the configured colormap.

Step-by-step guide
------------------

1. Import required modules
^^^^^^^^^^^^^^^^^^^^^^^^^^

Make sure to have ``porescene`` installed (see :doc:`../installation`). At first, required modules need to be imported:

.. code-block:: python

   from pathlib import Path

   import numpy as np

   from porescene import io, utility
   from porescene.color.palette import Colormap, Palette
   from porescene.scene import Scene

Module :mod:`~porescene.utility` provides a function that converts the segmented
volume image into one mesh per cluster, which can be subsequently saved with functions
from :mod:`~porescene.io`. :class:`Palette <porescene.color.palette.Palette>` and
:class:`Colormap <porescene.color.palette.Colormap>` supply the colors, and
:class:`Scene <porescene.scene.Scene>` loads and renders the created meshes. File paths
and directories are handled throughout PoreScene with the built-in :mod:`pathlib`
module.


2. Set utility variables
^^^^^^^^^^^^^^^^^^^^^^^^

After that, a directory for saving the mesh file and the rendered images is specified:

.. code-block:: python

   # data subdirectory
   pth_data = Path.cwd() / "data"

Next, some required information about the volume image is saved:

.. code-block:: python

   # [m] edge length of a single voxel
   L_vxl = 1e-6

   # [vxl] image resolution
   res_img = np.array((100, 100, 100))

   # [m] domain dimensions
   extent = res_img * L_vxl

``extent`` is the physical extent of the volume in **meters** -- here 100 voxels of
1 µm along each edge. It calibrates the axis ticks and sets the aspect ratio of the
scene, so it always stays in meters regardless of the unit you display (see
:doc:`../concepts`).


3. Mesh the segmented volume
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The segmented volume data is loaded from file and reshaped into its original
resolution. Unlike the binarized solid image, it is stored as ``uint32``, because each
void voxel holds the label of its cluster. Label ``0`` is reserved for the surrounding
solid phase, so the cluster labels are all non-zero values:

.. code-block:: python

   # load and reshape segmented volume image
   img_seg = np.fromfile(pth_data / "img_seg.raw", dtype=np.uint32)
   img_seg = img_seg.reshape(res_img)

   # void clusters carry labels 1..N; label 0 is the surrounding solid phase
   labels = np.unique(img_seg)
   labels = labels[labels != 0]

:func:`~porescene.utility.volume2mesh` builds the meshes. With ``per_label=True`` it
returns a separate mesh per label instead of merging everything into one surface, as a
``{label: Mesh}`` mapping. The ``name`` becomes the object name of each mesh, with the
label appended -- here ``"label_1"``, ``"label_2"`` and so on, the naming that
:meth:`~porescene.scene.Scene.create_clusters` expects.
:func:`~porescene.io.mesh2obj` then writes all clusters as separate objects into a
single OBJ file. You can skip this step in case you already have such a geometric
object file of your segmented pore space.

.. code-block:: python

   # one mesh per void cluster, named "label_1", "label_2", ...
   meshes = utility.volume2mesh(img_seg, L_vxl, labels, per_label=True, name="label")

   # export all clusters as separate objects in a single OBJ file
   io.mesh2obj(pth_data / "segmentation-void.obj", meshes)

.. tip::

   The clusters are written to OBJ rather than PLY because the OBJ format stores
   several named objects in one file, which is what
   :meth:`~porescene.scene.Scene.create_clusters` relies on to keep the clusters apart
   and color them individually.


4. Scene setup
^^^^^^^^^^^^^^

:class:`~porescene.scene.Scene` initializes the rendering stage with camera
and lighting. The scene is empty by default -- every visible element is added
explicitly in the next steps.

.. code-block:: python

   # initialize a new scene
   sc = Scene(extent)

For the rendering, the axes and the previously generated cluster meshes are added to
the :class:`Scene`. :meth:`~porescene.scene.Scene.apply_colors` then assigns a color to
every cluster -- here a random selection from the ``TURBO`` colormap, one color per
label:

.. code-block:: python

   # add axes to the scene
   sc.create_axes()

   # add the void clusters to the scene
   sc.create_clusters(pth_data / "segmentation-void.obj")

   # color each cluster with a random color drawn from a colormap
   sc.apply_colors("Clusters", Palette.load(Colormap.TURBO).random(len(labels)))

   # render the scene
   pth_img = sc.render(pth_data / "segmentation-void.png")


With the final line, Blender renders the scene and saves the image as
``segmentation-void.png`` in the given data directory.


Full script
-----------

The complete example, also available on GitHub:
`example/segmentation.py <https://github.com/fefafe/porescene/blob/main/example/segmentation.py>`_.

.. literalinclude:: ../../../example/segmentation.py
   :language: python
   :caption: example/segmentation.py
   :linenos:


References
----------

.. footbibliography::
