Scene configuration
===================

Instead of hard-coding every render setting in Python, PoreScene reads the parts of a
scene that you tend to stay constant between figures -- image resolution, axis calibration, and
per-property styling -- from a single JSON file. Keeping these values in a plain text file
makes a figure reproducible and easy to adjust: change a number, re-run the script, and the
same scene renders with the new setting.

The file is grouped into **sections**, each of which maps onto one of PoreScene's
configuration objects (see :mod:`porescene.config`). Every key is optional -- any key you
leave out falls back to the built-in default -- so a minimal config file is perfectly valid,
and you only add the keys you actually want to override.


Loading the configuration
--------------------------

A configuration file is loaded with :meth:`Scene.from_json
<porescene.scene.Scene.from_json>`. Besides the path to the JSON file, it takes the physical
domain dimensions ``dims`` as ``(x, y, z)`` **in metres** -- these calibrate the axes to the
real size of the sample, while the JSON only controls how that calibration is displayed:

.. code-block:: python

   from pathlib import Path

   from porescene.scene import Scene

   # physical domain size in metres (x, y, z)
   dims = (100e-06, 100e-06, 100e-06)

   # build a scene from the JSON configuration
   sc = Scene.from_json(dims, Path.cwd() / "data" / "porescene.json")

Individual settings can still be overridden afterwards on the returned scene, for example
``sc.config_scene.enable_cylinders = False``.


Example configuration
---------------------

The following ``porescene.json`` sets a 4096 × 4096 px image, calibrates the axes to
micrometres, and declares a single ``diameter`` property. It is a good starting point to copy
and adapt:

.. code-block:: json

   {
       "axes": {
           "font_size_labels": 1,
           "font_size_ticks": 0.6,
           "font_family": "Inter",
           "enable_ticks": [true, true, true],
           "enable_ticks_minor": true,
           "num_ticks_minor": 3,
           "line_width": 0.04,
           "tick_length": 0.15,
           "tick_interval": 20,
           "precision": [2, 2, 2],
           "distance": 0.06,
           "unit_display": "MICRO"
       },
       "image": {
           "width": 4096,
           "height": 4096
       },
       "properties": [
           {
               "id": "diameter",
               "heading": "Diameter [µm]",
               "factor": 2e6
           }
       ]
   }

The remaining sections describe every key in detail.


``image``
---------

Controls the resolution of the rendered image, mapping onto
:class:`~porescene.config.ImageConfiguration`. Both values are given in pixels.

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Key
     - Type
     - Default
     - Description
   * - ``width``
     - int
     - ``4096``
     - Image width in pixels.
   * - ``height``
     - int
     - ``4096``
     - Image height in pixels.


``axes``
--------

Controls the to-scale axes drawn around the scene, mapping onto
:class:`~porescene.config.AxesConfiguration`. The axes are calibrated from the physical
``dims`` passed to :meth:`Scene.from_json <porescene.scene.Scene.from_json>`; the keys below
only govern how that calibration is *displayed* -- the shown unit, tick spacing, precision,
and geometry.

Lengths such as ``line_width``, ``tick_length``, and ``distance`` are expressed in **scene
units**, where the longest edge of the model is normalised to a length of ``10``. Per-axis
keys accept either a single value (applied to all three axes) or a three-element list ordered
``[x, y, z]``.

.. list-table::
   :header-rows: 1
   :widths: 22 20 16 42

   * - Key
     - Type
     - Default
     - Description
   * - ``unit_display``
     - str
     - ``"MICRO"``
     - Metric prefix used for the displayed tick values and axis labels, e.g.
       ``"MICRO"`` → µm, ``"MILLI"`` → mm, ``"NANO"`` → nm. Must be one of the names of
       :class:`~porescene.utility.UnitPrefixMetric` (uppercase).
   * - ``tick_interval``
     - number
     - ``100``
     - Spacing between major ticks, in the displayed unit. With ``unit_display: "MICRO"`` a
       value of ``20`` places a major tick every 20 µm.
   * - ``precision``
     - int or list[int]
     - ``[0, 0, 0]``
     - Number of decimal places on the tick labels, per axis. Applied after the values are
       scaled into the displayed unit.
   * - ``enable_ticks``
     - bool or list[bool]
     - ``[true, true, true]``
     - Show or hide the major ticks, per axis.
   * - ``enable_ticks_minor``
     - bool or list[bool]
     - ``[true, true, true]``
     - Show or hide the minor ticks between major ticks, per axis.
   * - ``num_ticks_minor``
     - int
     - ``4``
     - Number of minor ticks drawn between two adjacent major ticks.
   * - ``font_size_labels``
     - float
     - ``1.5``
     - Font size of the axis labels, in scene units.
   * - ``font_size_ticks``
     - float
     - ``1``
     - Font size of the tick labels, in scene units.
   * - ``line_width``
     - float
     - ``0.1``
     - Thickness of the axis lines, in scene units.
   * - ``tick_length``
     - float
     - ``0.3``
     - Length of the tick marks, in scene units.
   * - ``distance``
     - float
     - ``0.2``
     - Gap between the model's bounding box and the axes, in scene units.
   * - ``label_x``, ``label_y``, ``label_z``
     - str
     - auto
     - Axis label text. If omitted, a label is generated automatically from
       ``unit_display``, e.g. ``"x [µm]"``.
   * - ``ticks_x``, ``ticks_y``, ``ticks_z``
     - list[number]
     - auto
     - Explicit major-tick positions, in the displayed unit. If omitted, ticks are generated
       from ``dims`` and ``tick_interval``.

.. note::

   The tick values and axis labels are derived from the ``dims`` you pass to
   :meth:`Scene.from_json <porescene.scene.Scene.from_json>` (in metres) together with
   ``unit_display`` and ``tick_interval``. To change the *shown* unit, adjust
   ``unit_display`` -- do not rescale ``dims``, which must always stay in metres.


``properties``
--------------

Each entry in the ``properties`` list describes one scalar property of the pore network that
can be mapped to color -- for example ``diameter``, ``radius``, or ``coordination_number`` --
and mirrors the fields of :class:`~porescene.config.PropertyConfiguration`.

.. list-table::
   :header-rows: 1
   :widths: 18 15 67

   * - Key
     - Type
     - Description
   * - ``id``
     - str
     - Name of the property. Must match the property stored on the
       :class:`~porescene.model.PoreNetwork`.
   * - ``heading``
     - str
     - Title shown above the colorbar, typically including the unit, e.g.
       ``"Diameter [µm]"``.
   * - ``factor``
     - float
     - Multiplier applied to the raw property values before they are displayed on the
       colorbar, e.g. ``2e6`` to turn a radius in metres into a diameter in micrometres.
       This affects the overlay only, not the rendered geometry.

.. note::

   The color mapping itself -- the palette or list of colors, the gradient type, alignment,
   and orientation -- is currently defined in Python by constructing a
   :class:`~porescene.config.PropertyConfiguration` and adding it with
   ``sc.config_scene.add_property(...)``. See the :doc:`examples <examples>` for complete,
   runnable scripts that build and color a property overlay.
