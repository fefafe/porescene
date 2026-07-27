Rotating solid structure
========================

A single render shows one view of a porous structure. Depth, connectivity and the shape of
the pore space, however, are much easier to grasp when the structure is seen from all
sides. PoreScene builds such an animation the same way it builds a static image: the scene
is set up once, the camera is rotated around it in small steps, and every step is rendered
as one frame. Module :mod:`~porescene.image` provides functions based on
`FFmpeg <https://ffmpeg.org/>`_ that encode a frame sequence into an MP4 video or GIF
animation.

This example takes the solid mesh from the :doc:`solid structure <solid>` tutorial and
turns it into a seamless turntable animation -- a full 360-degree orbit of the camera
around the stationary scene, with the axes staying readable throughout.

.. raw:: html

   <figure class="ps-figure">
     <video class="ps-video" autoplay loop muted playsinline controls
            preload="metadata"
            poster="../_static/image/example/solid+axes.png">
       <source src="../_static/video/solid+axes.mp4" type="video/mp4">
       Your browser does not support the video tag.
       <a href="../_static/video/solid+axes.mp4">Download the video (MP4)</a>.
     </video>
     <figcaption>
       <p>The rendered result: a 12-second turntable video of the microstructure of a
       freeze-dried sugar solution, captured with X-ray micro-computed tomography. The
       camera orbits the stationary sample by 360 degrees, so the last frame joins the
       first one and the video loops seamlessly – a perfect animation for PowerPoint
       presentations.</p>
     </figcaption>
   </figure>

Step-by-step guide
------------------

1. Import required modules
^^^^^^^^^^^^^^^^^^^^^^^^^^

Make sure to have ``porescene`` installed (see :doc:`../installation`). At first, required modules need to be imported:

.. code-block:: python

   from pathlib import Path

   import numpy as np

   from porescene import image
   from porescene.scene import Scene

:class:`~porescene.scene.Scene` sets up the rendering stage and renders each individual
frame, while module :mod:`~porescene.image` provides :func:`~porescene.image.frames2mp4`,
which encodes the rendered frames into a video. :mod:`numpy` holds the domain size, and
file paths and directories are handled throughout PoreScene with the built-in
:mod:`pathlib` module.


2. Set utility variables
^^^^^^^^^^^^^^^^^^^^^^^^

An animation produces a lot of intermediate files (each frame is saved as a single PNG
file), so besides the path to read the PLY file from (``pth_data``), a seperate directory
``pth_frames`` is specified to store the rendered frames:

.. code-block:: python

    # data directory
    pth_data = Path.cwd() / "data"

    # frames directory
    pth_frames = pth_data / "frames"

Next, the physical size of the sample is specified, which is necessary to construct the
scene (``extent`` is the physical size of the volume in **meters** -- here 100 µm along
each edge.):

.. code-block:: python

    # [m] domain size
    extent = np.array((100e-06, 100e-06, 100e-06))

.. note::

   ``extent`` has to be a :class:`numpy.ndarray` rather than a plain tuple: the scene
   derives its scale, shift and aspect from it element by element.

Furthermore, parameters for the resulting video need to be specified:

.. code-block:: python

    # [s] video duration
    duration = 12

    # [frame/second] video frame rate
    fps = 30

    # [-] total number of frames in the video
    frames_total = duration * fps

``duration`` give the length of the final video/animation in seconds and ``fps`` holds the number of frames per second that are included in the video. The overall frame count is computed by multiplying both together, so that the number of fames that need to be rendered is known.

.. tip::

   The frame count drives the render time, and every frame is a full Cycles render. Start
   with a short, coarse animation (e.g. ``duration = 4`` and ``fps = 12``) to check
   camera, lighting and framing, and only raise the numbers once the result looks right.


3. Scene setup
^^^^^^^^^^^^^^

For turntable videos, a :class:`Scene` is initialized once, and desired
:doc:`scene components <../concepts>` are added:

.. code-block:: python

   # create a new scene
   sc = Scene(extent)

   # add axes around the scene
   sc.create_axes()

   # add a solid object to the scene
   sc.create_solid(pth_data / "solid.ply")

For this example, only the mesh and scalebars are added into the scene. The mesh comes
from the PLY file written in the :doc:`solid structure <solid>` tutorial.

4. Rendering
^^^^^^^^^^^^

The animation loop itself is deliberately plain: rotate, render, repeat.
:meth:`~porescene.scene.Scene.rotate_azimuth` orbits the camera and all lights around the
scene's vertical center axis by the given angle in degrees, keeping the camera aimed
on the stage. Depending on set vie angle, the axis rulers move automatically on the visible sides of the sample:

.. code-block:: python

   for no_frame in range(frames_total):
       # move camera and lights further around the stage
       sc.rotate_azimuth(360 / frames_total)
       # render the scene
       sc.render(pth_frames / f"solid+axes_{no_frame:05d}.png", trim=False)

Two details matter for the frames to form a stable video:

* **Zero-padded frame numbers.** ``{no_frame:05d}`` names the files
  ``solid+axes_00000.png``, ``solid+axes_00001.png``, ... so that the frames sort
  alphabetically into the correct playback order. Without the padding, frame ``100`` would
  sort before frame ``2``.

* **No per-frame trimming.** :meth:`~porescene.scene.Scene.render` crops the image to its
  content by default, which is what you want for a static image. Across a sequence, each frame
  would be cropped to its *own* silhouette, so the structure would jitter and the frames
  would differ in size. Passing ``trim=False`` keeps every frame on the full, identical
  canvas.

.. note::

   Rendering is by far the most expensive part of this example: 360 frames at the default
   ``4096 × 4096`` resolution take a while. Lower the resolution for a quick preview by
   setting ``sc.config_image.width`` and ``sc.config_image.height``, or by building the
   scene from a JSON configuration with :meth:`Scene.from_json
   <porescene.scene.Scene.from_json>` (see :doc:`../config`). The frames are written to
   disk one by one, so an interrupted run can be resumed by rendering only the missing
   frames.


1. Encode the video
^^^^^^^^^^^^^^^^^^^

With all frames on disk, :func:`~porescene.image.frames2mp4` encodes them into an MP4
(H.264) video. It takes the ordered frame paths, the output path, and the frame rate the
animation was planned for:

.. code-block:: python

   image.frames2mp4(
       sorted(pth_frames.glob("solid+axes_*.png")),
       pth_data / "solid+axes.mp4",
       fps=fps,
       trim=True,
   )

The frames are passed through :func:`sorted`, because the video follows the order it is
given and :meth:`Path.glob <pathlib.Path.glob>` returns entries in filesystem order rather
than sorted -- together with the zero-padded frame numbers, sorting them alphabetically is
what puts them back into their rendered order.

Passing the same ``fps`` that was used to compute ``frames_total`` is what makes the video
run for the intended ``duration``. Here ``trim=True`` is safe -- and useful: unlike the
per-frame cropping above, :func:`~porescene.image.frames2mp4` measures the transparent
padding of *all* frames and removes only the margin they have in common, so the frames stay
aligned and equally sized while the empty border around the animation disappears. MP4
cannot store transparency, so the frames are flattened onto a solid background -- white by
default, and adjustable with the ``background`` argument.

.. tip::

   :func:`~porescene.image.frames2gif` takes the same arguments and writes an animated GIF
   instead. A GIF keeps the frame transparency and plays anywhere without a video player,
   but is limited to 256 colors and produces a considerably larger file -- prefer the MP4
   for smooth, full-color turntables like this one.


Full script
-----------

The complete example, also available on GitHub:
`example/animation_solid.py <https://github.com/fefafe/porescene/blob/main/example/animation_solid.py>`_.

.. literalinclude:: ../../../example/animation_solid.py
   :language: python
   :caption: example/animation_solid.py
   :linenos:


References
----------

.. footbibliography::
