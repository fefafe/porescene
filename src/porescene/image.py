# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 Felix Faber /
# Otto von Guericke University Magdeburg, Thermal Process Engineering

import subprocess
import tempfile
from pathlib import Path
from typing import Iterator

import imageio_ffmpeg
import PIL.Image

from porescene.utility import CompassDirection, Orientation


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


def img_add_colorbar(
    pth_vis: Path,
    pth_cb: Path,
    direction: CompassDirection = CompassDirection.SOUTH,
    orientation: Orientation = Orientation.HORIZONTAL,
    *,
    center_rendering: bool = False,
) -> Path:
    """
    Composites the colorbar next to the visualization image.
    """

    img_ax = PIL.Image.open(pth_cb).convert("RGBA")
    img_vis = PIL.Image.open(pth_vis).convert("RGBA")

    img_ax = img_ax.crop(img_ax.getbbox())
    img_vis = img_vis.crop(img_vis.getbbox())

    w_vis, h_vis = img_vis.size
    asp_cb = img_ax.width / img_ax.height

    compass = direction.value  # e.g. "N", "SE", "W"

    if orientation is Orientation.VERTICAL:
        # Tall colorbar stacked to the left/right of the visualization.
        h_cb = int(0.6 * h_vis)
        w_cb = int(h_cb * asp_cb)
        spacing = int(w_cb * 0.25)
        img_ax = img_ax.resize((w_cb, h_cb), PIL.Image.Resampling.LANCZOS)

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
        w_cb = int(0.5 * w_vis)
        h_cb = int(w_cb / asp_cb)
        spacing = int(h_cb * 0.25)
        img_ax = img_ax.resize((w_cb, h_cb), PIL.Image.Resampling.LANCZOS)

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

    parts_fname = pth_vis.stem.split("_")
    del parts_fname[-1]
    parts_fname.append("colorbar")

    pth_comp = pth_vis.with_stem("_".join(parts_fname))

    img_comp = PIL.Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    img_comp.alpha_composite(img_vis, (vis_x, vis_y))
    img_comp.alpha_composite(img_ax, (cb_x, cb_y))
    img_comp.save(pth_comp, "PNG")

    return pth_comp


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


def frames2gif(pth_frames: Iterator[Path], pth_gif: Path, fps: int = 24) -> Path:
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
        # a sequentially numbered stack. Frames trimmed to their content can differ
        # in size, which ffmpeg's image demuxer rejects mid-sequence; centering
        # each frame on the maximum extent yields the uniform sequence it expects.
        images = [PIL.Image.open(frame).convert("RGBA") for frame in frames]
        canvas_w = max(img.width for img in images)
        canvas_h = max(img.height for img in images)
        for i, img in enumerate(images):
            canvas = PIL.Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            canvas.alpha_composite(
                img, ((canvas_w - img.width) // 2, (canvas_h - img.height) // 2)
            )
            canvas.save(tmp / f"{i:05d}.png")

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
        # sequentially numbered stack. Frames trimmed to their content can differ
        # in size (which ffmpeg's image demuxer rejects mid-sequence), so they are
        # centered on the maximum extent; the canvas is rounded up to even
        # dimensions, as required by the yuv420p H.264 encoder.
        images = [PIL.Image.open(frame).convert("RGBA") for frame in frames]
        canvas_w = max(img.width for img in images)
        canvas_h = max(img.height for img in images)
        canvas_w += canvas_w % 2
        canvas_h += canvas_h % 2
        for i, img in enumerate(images):
            canvas = PIL.Image.new("RGBA", (canvas_w, canvas_h), (*background, 255))
            canvas.alpha_composite(
                img, ((canvas_w - img.width) // 2, (canvas_h - img.height) // 2)
            )
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
