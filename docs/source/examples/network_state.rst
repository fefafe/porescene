Network states
==============

A pore network rarely sits still. When a transport or phase-change simulation runs on it,
every pore and throat carries field values -- a concentration, a saturation, a temperature
-- that evolve from one time step to the next. A single *state* is a snapshot of those
fields at one simulation step. PoreScene can load a whole series of states from a MATLAB
file and render each one on the same stick-and-ball geometry, so an evolving simulation
turns into a comparable sequence of images.

This example loads a pore network together with several of its states, configures the
state field ``concentration`` on both the pores and the throats, and renders every
selected step on one fixed color scale. A simple diffusion problem based on a regular pore network is visualized in this example; the accompanying state data lives in
PoreScene's repository on GitHub:
`data/pnm-states.mat <https://github.com/fefafe/porescene/tree/main/data>`_

.. carousel::
   :interval: 2000
   :copyright: Felix Faber / OVGU, Transport in Porous Media

   .. figure:: /_static/image/carousel/example/cylinder-concentration+sphere-concentration+axes+state-0.png
      :alt: Pores and throats colored by concentration at state 0

      State 0

   .. figure:: /_static/image/carousel/example/cylinder-concentration+sphere-concentration+axes+state-500.png
      :alt: Pores and throats colored by concentration at state 500

      State 500

   .. figure:: /_static/image/carousel/example/cylinder-concentration+sphere-concentration+axes+state-600.png
      :alt: Pores and throats colored by concentration at state 600

      State 600

   .. figure:: /_static/image/carousel/example/cylinder-concentration+sphere-concentration+axes+state-700.png
      :alt: Pores and throats colored by concentration at state 700

      State 700

   .. figure:: /_static/image/carousel/example/cylinder-concentration+sphere-concentration+axes+state-800.png
      :alt: Pores and throats colored by concentration at state 800

      State 800

   .. figure:: /_static/image/carousel/example/cylinder-concentration+sphere-concentration+axes+state-930.png
      :alt: Pores and throats colored by concentration at state 930

      State 930

The rendered result, one slide per state: the pore spheres and throat cylinders colored by
concentration on a fixed ``[0, 50] mol/l`` scale, with on-scale axes and the matching
colorbar. The same geometry is recolored for every state, so the frames can be compared
directly.

Step-by-step guide
------------------

1. Import required modules
^^^^^^^^^^^^^^^^^^^^^^^^^^

Make sure to have ``porescene`` installed (see :doc:`../installation`). At first, required modules need to be imported:

.. code-block:: python

   import json
   from pathlib import Path

   import numpy as np

   from porescene import image, worker
   from porescene.color.palette import Colormap, Palette
   from porescene.config import QuantityConfiguration
   from porescene.model import PoreNetwork, StateVariableMap
   from porescene.scene import Scene
   from porescene.utility import CompassDirection, Orientation

:class:`~porescene.model.PoreNetwork` holds the pore and throat data together with the list
of states, while :class:`~porescene.scene.Scene` sets up the rendering stage. Module
:mod:`~porescene.worker` provides the high-level helpers that build the stick-and-ball
geometry and render every state. :class:`~porescene.model.StateVariableMap` tells the
importer which ``.mat`` variables hold each state field, and
:class:`~porescene.config.QuantityConfiguration` describes how the field is colored and
labelled -- with :class:`~porescene.utility.Orientation` and
:class:`~porescene.utility.CompassDirection` placing the colorbar.
:class:`~porescene.color.palette.Palette` and :class:`~porescene.color.palette.Colormap`
supply the colors. File paths are handled with the built-in :mod:`pathlib` module,
:mod:`json` reads the variable mapping, and :mod:`numpy` is on hand to generate the list
of simulation steps.


2. Set utility variables
^^^^^^^^^^^^^^^^^^^^^^^^

After that, the directory holding the input data and the directory receiving the rendered
images are specified:

.. code-block:: python

   # data directory
   pth_data = Path.cwd() / "data"

   # frames directory
   pth_frames = pth_data / "frames"

``pth_data`` holds the input files -- the pore network and its states -- while
``pth_frames`` collects the rendered states together with their colorbars. Keeping the
frames in their own subdirectory pays off as soon as a series grows: one file per state
piles up quickly, and they stay separated from the input data.


3. Load the pore network and its states
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The geometry and the state fields share one MATLAB file. As with the other examples, the
network geometry is mapped through ``map_vars.json`` (see
:doc:`network coordination number <network_coordination_number>`):

.. code-block:: python

   # load variable mapping for variable import from .mat file
   with open(pth_data / "map_vars.json") as f:
       map_vars = json.load(f)

The state fields need their own mapping. A :class:`~porescene.model.StateVariableMap` ties
a quantity name -- the name the coloring is configured under later -- to the ``.mat``
variables that store its per-pore (sphere) and per-throat (cylinder) values. Here the
concentration is available for both, so both variables are set:

.. code-block:: python

   # map the concentration state field to its per-pore and per-throat .mat variables
   concentration = StateVariableMap("concentration")
   concentration.variable_sphere = "C_p_storage"
   concentration.variable_cylinder = "C_t_storage"

   vars_state = [concentration]

.. note::

   A variable left unset is simply skipped, so a field may carry pore data, throat data,
   or both. Further fields -- a saturation or a temperature, say -- are added by appending
   more :class:`~porescene.model.StateVariableMap` instances to ``vars_state``; every one
   of them is then rendered as its own image series.

Each state field is stored as a two-dimensional array in the ``.mat`` file: the first
dimension runs over the pores (or throats) and the second over the simulation steps. Only
a handful of those steps usually need to be visualized, so the wanted step indices are
listed explicitly and wrapped into :class:`~porescene.model.PoreNetworkState` instances by
the importer:

.. code-block:: python

   # simulation steps to visualize
   no_states = (0, 500, 600, 700, 800, 930)

   # load the pore network together with the selected states from the MAT file
   pn = PoreNetwork.from_mat(
       pth_data / "pnm-states.mat",
       map_vars["data_network"],
       vars_state,
       no_states,
   )

The steps are picked by hand here, because the interesting part of this simulation happens
late: one step at the very beginning, then four steps bunched around the transition, and
the final step 930.

.. tip::

   For an evenly sampled series, the step indices can just as well be generated, e.g. with
   :func:`numpy.linspace` -- ``np.linspace(0, 930, 5, dtype=int)`` yields five steps spread
   across the whole simulation. The example keeps that variant as a comment next to the
   explicit list.

The loaded :class:`~porescene.model.PoreNetwork` now carries the geometry *and* an ordered
list of states, each holding the concentration values at one simulation step.

.. note::

   The state fields can also be attached to an already-loaded network with
   :meth:`~porescene.model.PoreNetwork.load_states_from_mat`, which takes the same
   ``vars_state`` and ``no_states`` arguments. This is handy when the geometry and the
   simulation results live in separate ``.mat`` files.


4. Scene setup
^^^^^^^^^^^^^^

The scene is created directly from the physical ``extent`` of the network, which sizes it
and calibrates the axes to the real dimensions of the sample (see :doc:`../concepts`):

.. code-block:: python

   # initialize scene
   sc = Scene(pn.extent)

.. tip::

   A series of states is a good reason to pin the camera down: with
   :meth:`Scene.from_json() <porescene.scene.Scene.from_json>` the same camera, lighting
   and axis configuration is reused on every run, so frames rendered at different times
   still line up (see :doc:`../config`).

The concentration field is registered on the scene with a
:class:`~porescene.config.QuantityConfiguration`. Its first argument is the quantity name
and has to match the name given to the :class:`~porescene.model.StateVariableMap` above --
that is how the coloring finds its data. The remaining arguments shape the colorbar and,
most importantly for a series, its bounds:

.. code-block:: python

   # settings for concentration visualizations
   sc.config_scene.add_quantity(
       QuantityConfiguration(
           "concentration",  # key that should match with the StateVariableMap
           Palette.load(Colormap.MATTER).all(),  # colormap
           heading="Concentration [mol/l]",  # colorbar label
           orientation=Orientation.VERTICAL,  # colorbar orientation
           align=CompassDirection.WEST,  # colorbar position around the rendering
           precision=3,  # precision of colorbar ticks
           # pinned colorbar limits, in place of the series minimum/maximum
           limit_lower=0,
           limit_upper=50,
       )
   )

:meth:`Palette.load(Colormap.MATTER).all() <porescene.color.palette.Palette.all>` hands
the full ``MATTER`` colormap to a smooth gradient, ``heading`` sets the colorbar title, and
``orientation`` together with ``align`` stands it vertically on the west (left) side.
``limit_lower`` and ``limit_upper`` fix the color scale at ``[0, 50] mol/l``, so every frame gets the same
colorbar and equal concentrations map to equal colors from step to step.

.. tip::

   Both bounds are optional. Left out, they are computed from the data -- and from the
   *whole series*, not from the state at hand, so the frames stay comparable either way
   (see :meth:`~porescene.config.QuantityConfiguration.resolve_limits`). Pin them when the scale
   should be a round, reportable range rather than whatever the simulation happened to
   produce, or when several figures have to share one scale. Each side stands on its own:
   an explicit ``limit_lower=0`` with the top left to follow the data is a common
   choice.

:func:`~porescene.worker.build_structure` then builds the stick-and-ball geometry, and
calibrated axes are added around it:

.. code-block:: python

   # add cylinders and spheres to the scene
   worker.build_structure(sc, pn)

   # add axes around the scene
   sc.create_axes()

Both layers stay enabled, so each state is drawn with its pore spheres *and* its throat
cylinders colored -- which is exactly why the concentration was mapped for both in the
step before.


5. Render each state
^^^^^^^^^^^^^^^^^^^^

:func:`~porescene.worker.make_state_quantity` renders one field of one state: it fits
the gradient (here once, from the pinned limits), colors the enabled layers, and returns
the path of the image. A state carrying several fields is drawn by calling it once per
field -- here the loop runs over the scene configuration itself, which iterates over the
:class:`~porescene.config.QuantityConfiguration` of every quantity added to it:

.. code-block:: python

   # render every selected state, coloring the pore spheres by concentration
   for no_state in no_states:
       for conf in sc.config_scene:
           pth_vis = worker.make_state_quantity(
               pth_frames, pn, sc, conf.name, no_state=no_state
           )

Composing the finished image is a separate step: :func:`~porescene.worker.make_colorbar`
draws the colorbar on the scale the render was colored on, and
:func:`~porescene.image.compose_colorbar` joins the two. The alignment and orientation
it is placed at come straight off the ``conf`` the loop hands out, so no second lookup
is needed. Since the limits are pinned here, every state ends up on one and the same
color scale:

.. code-block:: python

           pth_cb = worker.make_colorbar(pth_frames, pn, sc, conf.name)
           image.compose_colorbar(pth_vis, pth_cb, conf.align, conf.orientation)

Each render is named after the layers it shows, the field they are colored by, and the
state index, so the frames of the series end up next to each other in ``pth_frames`` as
``cylinder-concentration+sphere-concentration+axes+state-0.png``,
``...+state-500.png``, and so on -- the sequence shown in the carousel at the top of this
page, where the concentration front moves through the network on one and the same color
scale.

.. tip::

   The rendered states are a ready-made frame sequence: passing the image paths (in
   order) to :func:`~porescene.image.frames2mp4` or :func:`~porescene.image.frames2gif`
   turns the series into a video, the same way the :doc:`solid animation
   <animation_solid>` example does it. To carry the colorbar into the video, join it
   onto the series with :func:`~porescene.image.compose_colorbar_frames` -- which trims
   the renders against one another, so the colorbar keeps its size and place from frame
   to frame -- and pass those composites; pass the bare renders to leave it out.


Full script
-----------

The complete example, also available on GitHub:
`example/network_state.py <https://github.com/fefafe/porescene/blob/main/example/network_state.py>`_.

.. literalinclude:: ../../../example/network_state.py
   :language: python
   :caption: example/network_state.py
   :linenos:


References
----------

.. footbibliography::
