from pathlib import Path

import PIL.Image


def img_trim(pth_vis: Path, pad: tuple[int, int, int, int] = (0, 0, 0, 0)) -> Path:
    """
    Trims the transparent padding of an image.
    """

    img_vis = PIL.Image.open(pth_vis)

    img_vis = img_vis.crop(img_vis.getbbox())

    width, height = img_vis.size
    top, right, bottom, left = pad

    new_width = width + right + left
    new_height = height + top + bottom

    # filepath of the trimmed image
    parts_fname = pth_vis.stem.split("_")
    del parts_fname[-1]

    pth_trimmed = pth_vis.with_stem("_".join(parts_fname))

    result = PIL.Image.new(img_vis.mode, (new_width, new_height), (0, 0, 0, 0))
    result.paste(img_vis, (left, top))
    result.save(pth_trimmed, "PNG")

    return pth_trimmed


def img_add_colorbar(pth_vis: Path, pth_cb: Path) -> Path:
    """
    Trims the transparent padding of an image.
    """

    # padding
    right = 0
    left = 0
    top = 0
    bottom = 0

    img_ax = PIL.Image.open(pth_cb)
    img_vis = PIL.Image.open(pth_vis).convert("RGBA")

    img_ax = img_ax.crop(img_ax.getbbox())
    img_vis = img_vis.crop(img_vis.getbbox())

    w_vis, h_vis = img_vis.size
    asp_cb = img_ax.width / img_ax.height

    w_cb = int(0.5 * w_vis)
    h_cb = int(w_cb / asp_cb)
    spacing = int(h_cb * 0.25)

    img_ax = img_ax.resize((w_cb, h_cb), PIL.Image.Resampling.LANCZOS)

    new_width = w_vis + right + left
    new_height = bottom + h_vis + spacing + h_cb + top
    pad_cb = int((new_width - right - left - w_cb) / 2)

    pth_comp = pth_vis.with_stem(pth_vis.stem + "_colorbar")

    img_comp = PIL.Image.new(img_vis.mode, (new_width, new_height), (0, 0, 0, 0))
    img_comp.paste(img_vis, (left, top))
    img_comp.paste(img_ax, (left + pad_cb, top + h_vis + spacing))
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
