# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Felix Faber /
# Otto von Guericke University Magdeburg, Thermal Process Engineering

import subprocess
import tempfile
from collections.abc import Iterator
from pathlib import Path

import imageio_ffmpeg
import PIL.Image

from porescene.utility import (
    CompassDirection,
    Orientation,
    filepath_add_id,
    filepath_read_id,
    make_id,
)


def img_trim(pth_img: Path) -> Path:
    """
    Trims the transparent padding of an image.
    """

    img = PIL.Image.open(pth_img)
    img = img.crop(img.getbbox())
    img.save(pth_img, "PNG")

    return pth_img


def img_pad(
    pth_img: Path,
    pad: int | float | tuple[int | float, int | float, int | float, int | float] = (
        0,
        0,
        0,
        0,
    ),
    /,
    trim: bool = True,
) -> Path:
    """
    Adds padding to the given image

    Parameters
    ----------
    pth_img : Path
        Path of the image file
    pad : int | tuple[int, int, int, int], optional
        Amount of padding to add on each side (top, right, bottom, left),
        by default (0, 0, 0, 0)
    trim: bool
        If ``True``, existing whitespace gets trimmed from the image before padding gets
        applied, by default True

    Returns
    -------
    Path
        File path of the padded image.
    """
    if isinstance(pad, int | float):
        pad = (pad, pad, pad, pad)

    img_trimmed = PIL.Image.open(pth_img)

    if trim:
        img_trimmed = img_trimmed.crop(img_trimmed.getbbox())

    width, height = img_trimmed.size
    top, right, bottom, left = pad

    if top < 1:
        pad_top = int(round(top * height))
    if bottom < 1:
        pad_bottom = int(round(bottom * height))
    if left < 1:
        pad_left = int(round(left * width))
    if right < 1:
        pad_right = int(round(right * width))

    new_width = width + pad_right + pad_left
    new_height = height + pad_top + pad_bottom

    parts_fname = pth_img.stem.split("_")
    parts_fname.append("padded")

    pth_padded = pth_img.with_stem("_".join(parts_fname))

    img_padded = PIL.Image.new(img_trimmed.mode, (new_width, new_height), (0, 0, 0, 0))
    img_padded.paste(img_trimmed, (pad_left, pad_top))
    img_padded.save(pth_padded, "PNG")

    return pth_img


def compose_colorbar(
    pth_vis: Path,
    pth_cb: Path,
    align: CompassDirection = CompassDirection.SOUTH,
    orientation: Orientation = Orientation.HORIZONTAL,
    *,
    center_rendering: bool = False,
) -> Path:
    """
    Composites the colorbar next to the visualization image.

    The counterpart to the rendering step: :func:`porescene.worker.make_state_quantity`
    and its siblings render the scene, :func:`porescene.worker.make_colorbar` renders
    the colorbar, and this joins the two finished images.

    Both images are trimmed to their content before being placed on a common,
    transparent canvas. The colorbar is scaled to 60 % of the visualization's extent
    along the edge it is stacked against -- its height for a vertical colorbar, its
    width for a horizontal one -- keeping its aspect ratio, and is set off from the
    visualization by a quarter of its own thickness.

    Where the colorbar lands is read off ``align`` one component at a time: the
    component along the stacking axis picks the side -- west or east for a vertical
    colorbar, north or south for a horizontal one -- while the perpendicular component
    flushes both images against that edge of the canvas, centering them where it is
    absent. :attr:`~porescene.utility.CompassDirection.SOUTHWEST` on a vertical
    colorbar therefore puts the colorbar to the west and aligns both images with the
    bottom edge.

    The composite is written next to ``pth_vis`` under the same stem, extended by the
    identifier the colorbar was named after when it was rendered (see
    :func:`~porescene.utility.filepath_add_id`). Compositing a different colorbar --
    another color palette, other limits, ticks or label -- onto the same visualization
    therefore yields its own file instead of overwriting the earlier one. ``pth_vis``
    itself is left untouched.

    Parameters
    ----------
    pth_vis : Path
        Path of the rendered visualization image.
    pth_cb : Path
        Path of the rendered colorbar image.
    align : CompassDirection, optional
        Placement of the colorbar relative to the visualization, by default
        :attr:`~porescene.utility.CompassDirection.SOUTH`.
    orientation : Orientation, optional
        Whether the colorbar is stacked beside the visualization
        (:attr:`~porescene.utility.Orientation.VERTICAL`) or above respectively below
        it (:attr:`~porescene.utility.Orientation.HORIZONTAL`), by default
        :attr:`~porescene.utility.Orientation.HORIZONTAL`.
    center_rendering : bool, optional
        If ``True``, a second, empty colorbar slot is reserved on the side opposite
        the colorbar, leaving the visualization horizontally centered on the canvas
        instead of pushed aside by the colorbar. Only honored for vertical colorbars,
        by default ``False``.

    Returns
    -------
    Path
        File path of the written composite image.
    """

    img_cb = PIL.Image.open(pth_cb).convert("RGBA")
    img_vis = PIL.Image.open(pth_vis).convert("RGBA")

    img_cb = img_cb.crop(img_cb.getbbox())
    img_vis = img_vis.crop(img_vis.getbbox())

    img_comp = _compose_colorbar(
        img_vis, img_cb, align, orientation, center_rendering=center_rendering
    )

    pth_comp = _filepath_composite(pth_vis, pth_cb, center_rendering=center_rendering)
    img_comp.save(pth_comp, "PNG")

    return pth_comp


def compose_colorbar_frames(
    pth_frames: Iterator[Path],
    pth_cb: Path,
    align: CompassDirection = CompassDirection.SOUTH,
    orientation: Orientation = Orientation.HORIZONTAL,
    *,
    center_rendering: bool = False,
    trim: bool = True,
) -> list[Path]:
    """
    Composites one colorbar onto every frame of a series.

    The counterpart to :func:`compose_colorbar` for a frame sequence, e.g. the one
    :func:`porescene.worker.make_frames` renders: the colorbar reports a scale spanning
    the whole series, so one and the same image is joined onto every frame.

    The frames are trimmed as a series rather than one by one -- only the padding common
    to all of them is cropped, and the results are put on one canvas (see
    :func:`frames_trim`) -- and the colorbar is composed on afterwards. Trimming each
    frame to its own content first would size the colorbar off a canvas that changes
    from frame to frame, leaving it to grow, shrink and wander through the video while
    the network jumps around underneath it.

    Layout follows :func:`compose_colorbar`, from which ``align``, ``orientation`` and
    ``center_rendering`` carry their meaning unchanged. Since every frame reaches it at
    the same size, the colorbar comes out identical in size and position throughout.

    Each composite is written next to its frame under the frame's own stem, extended by
    the identifier of the colorbar, so the sequence keeps the common prefix and the
    padded counter that sorting it into playback order relies on. The frames themselves
    are left untouched.

    Parameters
    ----------
    pth_frames : Iterator[Path]
        Ordered paths of the frame images.
    pth_cb : Path
        Path of the rendered colorbar image, see
        :func:`porescene.worker.make_colorbar`.
    align : CompassDirection, optional
        Placement of the colorbar relative to the frames, by default
        :attr:`~porescene.utility.CompassDirection.SOUTH`.
    orientation : Orientation, optional
        Whether the colorbar is stacked beside the frames
        (:attr:`~porescene.utility.Orientation.VERTICAL`) or above respectively below
        them (:attr:`~porescene.utility.Orientation.HORIZONTAL`), by default
        :attr:`~porescene.utility.Orientation.HORIZONTAL`.
    center_rendering : bool, optional
        If ``True``, a second, empty colorbar slot is reserved on the side opposite the
        colorbar, leaving the frames horizontally centered on the canvas. Only honored
        for vertical colorbars, by default ``False``.
    trim : bool, optional
        If ``True``, the padding common to all frames is cropped away before the
        colorbar is composed on, by default ``True``. Pass ``False`` for frames that
        are already trimmed to a common canvas.

    Returns
    -------
    list[Path]
        File paths of the written composites, in the order the frames were given.

    Raises
    ------
    ValueError
        If no frames are given.

    Examples
    --------
    .. code-block:: python
        :caption: Python
        :linenos:

        pths = worker.make_frames(pth_frames, pn, sc, "saturation", fps=30, duration=12)
        pth_cb = worker.make_colorbar(pth_frames, pn, sc, "saturation")
        pths = image.compose_colorbar_frames(pths, pth_cb, conf.align, conf.orientation)
        image.frames2mp4(pths, pth_data / "saturation.mp4", fps=30)
    """
    frames = list(pth_frames)
    if not frames:
        raise ValueError("compose_colorbar_frames requires at least one frame")

    images = _frames_common_canvas(
        [PIL.Image.open(frame).convert("RGBA") for frame in frames], trim=trim
    )

    img_cb = PIL.Image.open(pth_cb).convert("RGBA")
    img_cb = img_cb.crop(img_cb.getbbox())

    pths_comp = []
    for pth_frame, img_vis in zip(frames, images, strict=True):
        img_comp = _compose_colorbar(
            img_vis, img_cb, align, orientation, center_rendering=center_rendering
        )
        pth_comp = _filepath_composite(
            pth_frame, pth_cb, center_rendering=center_rendering
        )
        img_comp.save(pth_comp, "PNG")
        pths_comp.append(pth_comp)

    return pths_comp


def img_add_axes(pth_vis: Path, pth_ax: Path) -> Path:
    """
    Combines a visualization image with the axes image.
    """

    if not pth_ax.exists():
        return pth_vis

    img_ax = PIL.Image.open(pth_ax)
    img_vis = PIL.Image.open(pth_vis)

    parts_fname = pth_vis.stem.split("_")
    parts_fname.insert(-1, "axes")

    pth_comp = pth_vis.with_stem("_".join(parts_fname))

    img_comp = PIL.Image.new(img_vis.mode, img_vis.size, (0, 0, 0, 0))
    img_comp.alpha_composite(img_ax, (0, 0))
    img_comp.alpha_composite(img_vis, (0, 0))
    img_comp.save(pth_comp, "PNG")

    return pth_comp


def img_pp(pth_img: Path) -> None:
    """
    Visualization image post-processing

    Parameters
    ----------
    pth_img : Path
        Filename of the visualization image to be trimmed and axes added.
    """
    img_trim(pth_img)
    pth_img = img_add_axes(
        pth_img, pth_img.with_stem("axes_" + pth_img.stem.split("_")[-1])
    )
    img_trim(pth_img)


def img_side_by_side(pth_img_left: Path, pth_img_right: Path, pth_merged: Path):

    img_left = PIL.Image.open(pth_img_left)
    img_right = PIL.Image.open(pth_img_right)

    sz_left = img_left.size
    sz_right = img_right.size

    sz_new = (sz_left[0] + sz_right[0], max([sz_left[1], sz_right[1]]))

    img_comp = PIL.Image.new("RGBA", sz_new, (0, 0, 0, 0))
    img_comp.alpha_composite(img_left, (0, 0))
    img_comp.alpha_composite(img_right, (sz_left[0], 0))
    img_comp.save(pth_merged, "PNG")


def iterate_side_by_side(pthlist_left, pthlist_right, pth_merged):

    pthlist_left = [i for i in pthlist_left]
    pthlist_right = [i for i in pthlist_right]

    for i in range(len(pthlist_left)):
        img_side_by_side(
            pthlist_left[i], pthlist_right[i], pth_merged / f"frame_{i:03d}.png"
        )


def frames_trim(pth_frames: Iterator[Path]) -> list[Path]:
    """
    Trims a series of frames to their common bounding box, in place.

    The counterpart to :func:`img_trim` for a frame sequence. Trimming each frame on its
    own crops it to its own content, which moves the content about from frame to frame
    and leaves the frames differing in size -- unusable as a sequence. This measures the
    transparent margin of every frame instead and crops each side by the smallest margin
    found on it across the whole series, so the empty border goes away while the content
    stays put. The frames are then put on the extent of the largest one, leaving the
    series uniform in size.

    Applied by :func:`frames2mp4`, :func:`frames2gif` and
    :func:`compose_colorbar_frames` on their own; call it directly to trim a series that
    is handed on elsewhere, or to work on the files rather than on a copy of them.

    Parameters
    ----------
    pth_frames : Iterator[Path]
        Paths of the frame images. Order does not matter, since every frame is cropped
        by the same margins.

    Returns
    -------
    list[Path]
        The paths of the trimmed frames, in the order they were given.

    Raises
    ------
    ValueError
        If no frames are given.

    .. attention::

        The frames are overwritten with their trimmed version, so the untrimmed
        originals are lost -- as with :func:`img_trim`.
    """
    frames = list(pth_frames)
    if not frames:
        raise ValueError("frames_trim requires at least one frame")

    images = _frames_common_canvas(
        [PIL.Image.open(frame).convert("RGBA") for frame in frames]
    )

    for pth_frame, img in zip(frames, images, strict=True):
        img.save(pth_frame, "PNG")

    return frames


def frames2gif(
    pth_frames: Iterator[Path],
    pth_gif: Path,
    fps: int = 24,
    trim: bool = True,
) -> Path:
    """
    Exports an animated GIF from the given frames.

    The frames are encoded with the ``ffmpeg`` binary shipped with
    ``imageio-ffmpeg`` using a two-pass palette (``palettegen`` / ``paletteuse``)
    for good color fidelity. Frame transparency is preserved and the GIF loops
    indefinitely.

    Parameters
    ----------
    pth_frames : Iterator[Path]
        Ordered paths of the frame images. The animation follows this order.
    pth_gif : Path
        Output path of the GIF file.
    fps : int, optional
        Playback speed in frames per second, by default 24.
    trim : bool, optional
        If ``True``, the transparent padding common to all frames is cropped away
        before encoding (see :func:`frames_trim`), by default ``True``.

    Returns
    -------
    Path
        File path of the written GIF.
    """
    frames = list(pth_frames)
    if not frames:
        raise ValueError("frames2gif requires at least one frame")

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)

        # Normalize every frame onto a common transparent canvas and write them as
        # a sequentially numbered stack, which is what ffmpeg's image demuxer expects.
        images = [PIL.Image.open(frame).convert("RGBA") for frame in frames]
        images = _frames_common_canvas(images, trim=trim)
        for i, img in enumerate(images):
            img.save(tmp / f"{i:05d}.png")

        pth_palette = tmp / "palette.png"
        frame_input = ["-framerate", str(fps), "-i", (tmp / "%05d.png").as_posix()]

        def run(args: list[str]) -> None:
            result = subprocess.run([ffmpeg, "-y", *args], capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg failed:\n{result.stderr}")

        # pass 1: derive an optimal palette from all frames (one slot reserved for
        # transparency); pass 2: encode the looping gif using that palette.
        run(
            [
                *frame_input,
                "-vf",
                "palettegen=reserve_transparent=1:stats_mode=diff",
                pth_palette.as_posix(),
            ]
        )
        run(
            [
                *frame_input,
                "-i",
                pth_palette.as_posix(),
                "-lavfi",
                "paletteuse=alpha_threshold=128:dither=bayer:bayer_scale=5",
                "-loop",
                "0",
                pth_gif.as_posix(),
            ]
        )

    return pth_gif


def frames2mp4(
    pth_frames: Iterator[Path],
    pth_mp4: Path,
    fps: int = 24,
    background: tuple[int, int, int] = (255, 255, 255),
    trim: bool = True,
) -> Path:
    """
    Exports an MP4 (H.264) video from the given frames.

    The frames are encoded with the ``ffmpeg`` binary shipped with
    ``imageio-ffmpeg`` using the ``libx264`` codec and the ``yuv420p`` pixel format
    for broad player and browser compatibility. MP4 cannot store an alpha channel,
    so each frame is flattened onto a solid ``background`` color.

    Parameters
    ----------
    pth_frames : Iterator[Path]
        Ordered paths of the frame images. The video follows this order.
    pth_mp4 : Path
        Output path of the MP4 file.
    fps : int, optional
        Playback speed in frames per second, by default 24.
    background : tuple[int, int, int], optional
        RGB color the (transparent) frames are composited onto, by default white
        ``(255, 255, 255)``.
    trim : bool, optional
        If ``True``, the transparent padding common to all frames is cropped away
        before encoding (see :func:`frames_trim`), by default ``True``.

    Returns
    -------
    Path
        File path of the written MP4.
    """
    frames = list(pth_frames)
    if not frames:
        raise ValueError("frames2mp4 requires at least one frame")

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)

        # Flatten every frame onto a common, solid background and write them as a
        # sequentially numbered stack, which is what ffmpeg's image demuxer expects.
        # The canvas is rounded up to even dimensions, as the yuv420p H.264 encoder
        # requires.
        images = [PIL.Image.open(frame).convert("RGBA") for frame in frames]
        images = _frames_common_canvas(images, trim=trim, even=True)
        for i, img in enumerate(images):
            canvas = PIL.Image.new("RGBA", img.size, (*background, 255))
            canvas.alpha_composite(img)
            canvas.convert("RGB").save(tmp / f"{i:05d}.png")

        result = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-framerate",
                str(fps),
                "-i",
                (tmp / "%05d.png").as_posix(),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-crf",
                "18",
                "-movflags",
                "+faststart",
                pth_mp4.as_posix(),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed:\n{result.stderr}")

    return pth_mp4


def _trim_common_padding(images: list[PIL.Image.Image]) -> list[PIL.Image.Image]:
    """
    Crops every image by the padding shared by all of them on each side.

    Each image's transparent margin (top, right, bottom, left) is measured
    individually, and the minimum margin found on a given side across all images
    is cropped from that side of every image -- so e.g. margins of 10, 12, 14, 8
    and 12 px on one side are all trimmed down to 8 px, keeping every frame the
    same size and its content aligned.
    """
    boxes = [img.getbbox() or (0, 0, img.width, img.height) for img in images]
    left = min(box[0] for box in boxes)
    top = min(box[1] for box in boxes)
    right = min(img.width - box[2] for img, box in zip(images, boxes, strict=False))
    bottom = min(img.height - box[3] for img, box in zip(images, boxes, strict=False))
    return [
        img.crop((left, top, img.width - right, img.height - bottom)) for img in images
    ]


def _frames_common_canvas(
    images: list[PIL.Image.Image],
    *,
    trim: bool = True,
    even: bool = False,
) -> list[PIL.Image.Image]:
    """
    Puts every frame of a series onto one and the same transparent canvas.

    The padding shared by all frames is cropped away, see :func:`_trim_common_padding`,
    and each frame is then centered on the extent of the largest one, so that the series
    comes out uniform in size however its frames were trimmed before. What
    :func:`frames_trim` exposes, and what the encoders and
    :func:`compose_colorbar_frames` build on.

    Parameters
    ----------
    images
        The frames, in any order.
    trim
        Whether to crop the common padding, by default ``True``. With ``False`` the
        frames are only brought onto a common canvas.
    even
        Whether to round the canvas up to even dimensions, by default ``False``. Set by
        :func:`frames2mp4`, whose yuv420p H.264 encoder requires them.

    Returns
    -------
    list[PIL.Image.Image]
        The frames, all of one size, in the order they were given.
    """
    if trim:
        images = _trim_common_padding(images)

    canvas_w = max(img.width for img in images)
    canvas_h = max(img.height for img in images)

    if even:
        canvas_w += canvas_w % 2
        canvas_h += canvas_h % 2

    out = []
    for img in images:
        canvas = PIL.Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        canvas.alpha_composite(
            img, ((canvas_w - img.width) // 2, (canvas_h - img.height) // 2)
        )
        out.append(canvas)

    return out


def _compose_colorbar(
    img_vis: PIL.Image.Image,
    img_cb: PIL.Image.Image,
    align: CompassDirection,
    orientation: Orientation,
    *,
    center_rendering: bool = False,
) -> PIL.Image.Image:
    """
    Places a colorbar next to a visualization on a common, transparent canvas.

    The layout :func:`compose_colorbar` and :func:`compose_colorbar_frames` share, see
    the former for how the colorbar is sized and where ``align``, ``orientation`` and
    ``center_rendering`` put it.

    Both images are expected to be trimmed to their content already: the colorbar is
    scaled off the extent of ``img_vis``, so a margin left on either of them would grow
    into the composite rather than be cropped from it.
    """
    w_vis, h_vis = img_vis.size
    asp_cb = img_cb.width / img_cb.height

    compass = align.value

    if orientation is Orientation.VERTICAL:
        # Tall colorbar stacked to the left/right of the visualization.
        h_cb = int(0.6 * h_vis)
        w_cb = int(h_cb * asp_cb)
        spacing = int(w_cb * 0.25)
        img_cb = img_cb.resize((w_cb, h_cb), PIL.Image.Resampling.LANCZOS)

        canvas_w = w_vis + spacing + w_cb
        canvas_h = max(h_vis, h_cb)

        if center_rendering:
            canvas_w += spacing + w_cb

        # left for a westward direction, right otherwise (default east side)
        if "W" in compass:
            cb_x, vis_x = 0, w_cb + spacing
        else:
            vis_x, cb_x = 0, w_vis + spacing
            if center_rendering:
                vis_x += spacing + w_cb
                cb_x += spacing + w_cb

        # north -> top, south -> bottom, else vertically centered
        def vpos(h: int) -> int:
            if "N" in compass:
                return 0
            if "S" in compass:
                return canvas_h - h
            return (canvas_h - h) // 2

        vis_y, cb_y = vpos(h_vis), vpos(h_cb)
    else:
        # Wide colorbar stacked above/below the visualization.
        w_cb = int(0.6 * w_vis)
        h_cb = int(w_cb / asp_cb)
        spacing = int(h_cb * 0.25)
        img_cb = img_cb.resize((w_cb, h_cb), PIL.Image.Resampling.LANCZOS)

        canvas_w = max(w_vis, w_cb)
        canvas_h = h_vis + spacing + h_cb

        # north -> top, south -> bottom (default south side)
        if "N" in compass:
            cb_y, vis_y = 0, h_cb + spacing
        else:
            vis_y, cb_y = 0, h_vis + spacing

        # west -> left, east -> right, else horizontally centered
        def hpos(w: int) -> int:
            if "W" in compass:
                return 0
            if "E" in compass:
                return canvas_w - w
            return (canvas_w - w) // 2

        vis_x, cb_x = hpos(w_vis), hpos(w_cb)

    img_comp = PIL.Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    img_comp.alpha_composite(img_vis, (vis_x, vis_y))
    img_comp.alpha_composite(img_cb, (cb_x, cb_y))

    return img_comp


def _filepath_composite(
    pth_vis: Path,
    pth_cb: Path,
    *,
    center_rendering: bool = False,
) -> Path:
    """
    Names a composite after the visualization it shows and the colorbar joined onto it.

    The stem of ``pth_vis`` extended by the identifier ``pth_cb`` carries, so that
    compositing a different colorbar -- another color palette, other limits, ticks or
    label -- onto the same visualization yields its own file instead of overwriting the
    earlier one.
    """
    id_cb = filepath_read_id(pth_cb) or make_id(pth_cb.stem)

    return filepath_add_id(pth_vis, id_cb + "-centered" if center_rendering else id_cb)
