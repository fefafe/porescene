from pathlib import Path

from porescene.image import img_trim

# ============================================================================
# Parameters

# simulation id
id_sim = "e4833bb7-5652-49a6-bed2-9eac68406ea2"

# file name
fname = "colorbar_temperature.png"


# ============================================================================
# Trimming

# absolute data path
pth_abs_data = Path("/Data/")

# relative network path
pth_rel_sim = Path("PNM/FreezeDrying/", id_sim)

# img_trim(pth_abs_data / pth_rel_sim / "Image/" / fname)
img_trim(Path(r"C:\Data\Scan\Felt\Cell_III\section_ori@1x1x1_res@50x50x50\Image\solid_4096x4096.png"))
