Scene configuration
===================

Instead of hard-coding every render setting in Python, PoreScene reads the parts of a
scene that tend to stay constant between figures -- image resolution, render quality,
axis calibration, and per-quantity styling -- from a single JSON file. Keeping these values in a plain text file
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
domain dimensions ``dims`` as ``(x, y, z)`` **in meters** -- these calibrate the axes to the
real size of the sample, while the JSON only controls how that calibration is displayed:

.. code-block:: python

   from pathlib import Path

   from porescene.scene import Scene

   # physical domain size in meters (x, y, z)
   dims = (100e-06, 100e-06, 100e-06)

   # build a scene from the JSON configuration
   sc = Scene.from_json(dims, Path.cwd() / "data" / "porescene.json")

Individual settings can still be overridden afterwards on the returned scene, for example
``sc.config_scene.enable_cylinders = False``.


Example configuration
---------------------

The following ``porescene.json`` sets a 4096 × 4096 px image, calibrates the axes to
micrometers, and declares a single ``diameter`` quantity. It is a good starting point to copy
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
           "spacing": 0.06,
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


``render``
----------

Controls how Blender's *Cycles* engine renders the scene, mapping onto
:class:`~porescene.config.RenderConfiguration`: the device, the effort spent per pixel, and
how the rendered light is turned into colors. The defaults are meant for figures in a
publication; to check quickly whether a script does what it should, set ``samples`` to
``16`` and lower the ``image`` size.

.. code-block:: json

   {
       "render": {
           "device": "AUTO",
           "samples": 1024,
           "noise_threshold": 0.01
       }
   }

.. list-table::
   :header-rows: 1
   :widths: 22 16 14 48

   * - Key
     - Type
     - Default
     - Description
   * - ``device``
     - str
     - ``"AUTO"``
     - Device to render on, one of the names of :class:`~porescene.utility.RenderDevice`.
       ``"AUTO"`` uses the first GPU backend with a device on this machine -- ``OPTIX``,
       ``CUDA``, ``HIP``, ``ONEAPI``, ``METAL`` in this order -- and falls back to the
       CPU with a warning. ``"CPU"`` forces the CPU. Naming a GPU backend fails if it has
       no device, so keep ``"AUTO"`` in a configuration shared between machines.
   * - ``samples``
     - int
     - ``1024``
     - Largest number of samples per pixel. With ``noise_threshold`` set, most pixels
       stop well before.
   * - ``samples_min``
     - int
     - ``32``
     - Samples every pixel takes before ``noise_threshold`` may stop it, so that small
       features such as thin throats aren't missed.
   * - ``noise_threshold``
     - float or null
     - ``0.01``
     - Noise level at which a pixel stops sampling (adaptive sampling). Lower is cleaner
       and slower. ``null`` turns adaptive sampling off.
   * - ``enable_denoising``
     - bool
     - ``true``
     - Denoise the render with OpenImageDenoise. The denoiser is guided by the surface
       colors and normals, so boundaries between differently colored pores stay sharp.
   * - ``seed``
     - int
     - ``0``
     - Seed of the sampling noise. The same seed, samples and device reproduce an image,
       and the frames of an animation share one noise pattern instead of flickering.
   * - ``bounces_transmission``
     - int
     - ``12``
     - Maximum number of refractions along a light path.
   * - ``bounces_transparent``
     - int
     - ``64``
     - Maximum number of transparent surfaces a light path passes through. A path that
       runs out renders black, so raise it if a transparent solid shows dark patches.
   * - ``view_transform``
     - str
     - ``"Standard"``
     - Blender view transform from rendered light to display colors. ``"Standard"`` keeps
       the colors on the colorbar: shading darkens a color but doesn't shift its hue.
       ``"AgX"``, Blender's own default, compresses highlights like film, which pulls
       bright colors toward white and shifts their hue by up to about 10°.
   * - ``exposure``
     - float
     - ``0``
     - Brightness adjustment in stops, applied before ``view_transform``. At ``0`` the
       most brightly lit surfaces show their base color. Positive values brighten the
       image, but with ``"Standard"`` they clip the brightest colors. Use about ``1.6``
       together with ``"AgX"``.

.. note::

   A colorbar can only be trusted if the colors in the render are the ones it shows. The
   light rig of PoreScene is calibrated for ``"Standard"`` at an ``exposure`` of ``0``: a
   surface facing the lights renders in its base color, and every other surface in
   a darker shade of the same hue. With ``"AgX"``, the same surface comes out up to 15
   units of CIEDE2000 color difference away from its colorbar color, where about 2 is
   already visible side by side.


``axes``
--------

Controls the to-scale axes drawn around the scene, mapping onto
:class:`~porescene.config.AxesConfiguration`. The axes are calibrated from the physical
``dims`` passed to :meth:`Scene.from_json <porescene.scene.Scene.from_json>`; the keys below
only govern how that calibration is *displayed* -- the shown unit, tick spacing, precision,
and geometry.

Lengths such as ``line_width``, ``tick_length``, and ``spacing`` are expressed in **scene
units**, where the longest edge of the model is normalized to a length of ``10``. Per-axis
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
     - auto
     - Metric prefix used for the displayed tick values and axis labels, e.g.
       ``"MICRO"`` → µm, ``"MILLI"`` → mm, ``"NANO"`` → nm, ``"BASE"`` → m. Must be one of
       the names of :class:`~porescene.utility.UnitPrefixMetric` (uppercase). If omitted,
       the prefix is derived from ``dims``: the one of the engineering series --
       ``NANO``, ``MICRO``, ``MILLI``, ``BASE``, ``KILO``, ... -- that scales the longest
       axis to a value between ``10`` and ``10000``, so the tick values stay two to four
       digits long.
   * - ``tick_interval``
     - number
     - auto
     - Spacing between major ticks, in the displayed unit. With ``unit_display: "MICRO"`` a
       value of ``20`` places a major tick every 20 µm. If omitted, the spacing is derived
       from ``dims``: the value from the 1-2-5-10 series that puts roughly ``num_ticks``
       ticks on the longest axis. All three axes share one spacing, so the ticks stay to
       scale and a shorter axis carries fewer of them.
   * - ``precision``
     - int or list[int]
     - auto
     - Number of decimal places on the tick labels, per axis. Applied after the values are
       scaled into the displayed unit. If omitted, it is derived per axis from the tick
       values: just enough decimals to write every tick of that axis exactly, capped at
       ``6``. Ticks calibrated from ``dims`` are whole numbers and need none, while a
       fractional ``tick_interval``, an explicit tick list, or a ``unit_display`` coarser
       than the sample get the decimals they need. Trailing zeros are dropped when a label
       is rendered, so a value above what a tick needs is harmless.
   * - ``enable_ticks``
     - bool or list[bool]
     - ``[true, true, true]``
     - Show or hide the major ticks, per axis.
   * - ``enable_ticks_minor``
     - bool or list[bool]
     - ``[true, true, true]``
     - Show or hide the minor ticks between major ticks, per axis.
   * - ``enable_labels_ticks``
     - bool or list[bool]
     - auto
     - Show or hide the labels of the major ticks, per axis. If omitted, an axis is
       labelled only when its ticks are calibrated, i.e. when they come from ``dims`` and
       ``tick_interval`` or from an explicit ``ticks_x``/``ticks_y``/``ticks_z``. An axis
       falling back to ``num_ticks`` is drawn with bare ticks.
   * - ``num_ticks``
     - int
     - ``6``
     - Number of major ticks aimed for along the longest axis. Sizes the derived
       ``tick_interval``, and is met only approximately there, since the interval is
       rounded to a value the ticks read well at. Ignored when ``tick_interval`` is given,
       except for an axis that has no ticks at all, where exactly this many are spread
       evenly over the full axis length. Minimum ``2``.
   * - ``num_ticks_minor``
     - int
     - auto
     - Number of minor ticks drawn between two adjacent major ticks. If omitted, the
       number is derived from the major tick spacing so that the minor ticks fall on
       round values: a step whose leading digit is 1 or 5 (e.g. ``100`` or ``50``) is
       split into 5 intervals, giving 4 minor ticks, any other step into 4 intervals,
       giving 3 minor ticks.
   * - ``font_size_labels``
     - float
     - ``0.6``
     - Font size of the axis labels, in scene units.
   * - ``font_size_ticks``
     - float
     - ``0.5``
     - Font size of the tick labels, in scene units.
   * - ``line_width``
     - float
     - ``0.04``
     - Thickness of the axis lines, in scene units.
   * - ``spacing``
     - float
     - ``0.06``
     - Gap kept around the axes, in scene units. Offsets the axis lines from the model's
       bounding box and the tick labels from the outer end of their ticks.
   * - ``tick_length``
     - float
     - ``0.2``
     - Length of the tick marks, in scene units.
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
   :meth:`Scene.from_json <porescene.scene.Scene.from_json>` (in meters) together with
   ``unit_display`` and ``tick_interval``. To change the *shown* unit, adjust
   ``unit_display`` -- do not rescale ``dims``, which must always stay in meters.


``properties``
--------------

Each entry in the ``properties`` list describes one scalar quantity of the pore network that
can be mapped to color -- for example ``diameter``, ``radius``, or ``coordination_number`` --
and mirrors the fields of :class:`~porescene.config.QuantityConfiguration`.

.. list-table::
   :header-rows: 1
   :widths: 18 15 67

   * - Key
     - Type
     - Description
   * - ``id``
     - str
     - Name of the quantity. Must match the quantity stored on the
       :class:`~porescene.model.PoreNetwork`.
   * - ``heading``
     - str
     - Title shown above the colorbar, typically including the unit, e.g.
       ``"Diameter [µm]"``.
   * - ``factor``
     - float
     - Multiplier applied to the raw quantity values before they are displayed on the
       colorbar, e.g. ``2e6`` to turn a radius in meters into a diameter in micrometers.
       This affects the overlay only, not the rendered geometry.

.. note::

   The color mapping itself -- the palette or list of colors, the gradient type, alignment,
   and orientation -- is currently defined in Python by constructing a
   :class:`~porescene.config.QuantityConfiguration` and adding it with
   ``sc.config_scene.add_quantity(...)``. See the :doc:`examples <examples>` for complete,
   runnable scripts that build and color a quantity overlay.
