from pathlib import Path
import PIL.Image
from PIL.Image import Image


def img_trim(pth: Path) -> Path:
    """
    Trims the transparent padding of an image.
    """

    img = PIL.Image.open(pth)

    region = img.getbbox()
    img = img.crop(region)
    right = 10
    left = 10
    top = 10
    bottom = 10

    width, height = img.size

    new_width = width + right + left
    new_height = height + top + bottom

    # filepath of the trimmed image
    pth_trimmed = pth.with_stem(pth.stem + "_trimmed")

    result = PIL.Image.new(img.mode, (new_width, new_height), (0, 0, 0, 0))
    result.paste(img, (left, top))
    result.save(pth_trimmed, "PNG")

    return pth_trimmed


def img_add_colorbar(pth_vis: Path, pth_cb: Path) -> Path:
    """
    Trims the transparent padding of an image.
    """

    # padding
    right = 10
    left = 10
    top = 10
    bottom = 10

    img_cb = PIL.Image.open(pth_cb)
    img_vis = PIL.Image.open(pth_vis)

    img_cb = img_cb.crop(img_cb.getbbox())
    img_vis = img_vis.crop(img_vis.getbbox())

    w_vis, h_vis = img_vis.size
    asp_cb = img_cb.width / img_cb.height

    w_cb = int(0.8 * w_vis)
    h_cb = int(w_cb / asp_cb)
    spacing = int(h_cb * 0.4)

    img_cb = img_cb.resize((w_cb, h_cb), PIL.Image.Resampling.LANCZOS)

    new_width = w_vis + right + left
    new_height = bottom + h_vis + spacing + h_cb + top
    pad_cb = int((new_width - right - left - w_cb) / 2)

    pth_comp = pth_vis.with_stem(pth_vis.stem + "_colorbar")

    img_comp = PIL.Image.new(img_vis.mode, (new_width, new_height), (0, 0, 0, 0))
    img_comp.paste(img_vis, (left, top))
    img_comp.paste(img_cb, (left + pad_cb, top + h_vis + spacing))
    img_comp.save(pth_comp, "PNG")

    return pth_comp
