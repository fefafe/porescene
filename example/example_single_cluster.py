from pathlib import Path


# ============================================================================
# Import Parameters

# absolute data path
pth_abs_data = Path("/Data/")

# network id
# id_nwk = "R_100x100x100_r@1.66_36cae45e-eaab-4ecd-bdf2-ec1be02dbcd3"
# id_nwk = "A_13x13x13_r@1.66_88dc59ee-c3c1-467d-9201-60b56a3d45c3"
id_nwk = "R_250x50x500_r@14.56_c8228342-5c71-4307-93b1-749e072b4803"
id_sim = "e4833bb7-5652-49a6-bed2-9eac68406ea2"


# ============================================================================
# Data Import

# relative network path
pth_rel_nwk = Path("PNM/Network/", id_nwk)

# relative network path
pth_rel_sim = Path("PNM/FreezeDrying/", id_sim)

# relative CT scan path
pth_rel_scan = Path(
    "Scan",
    "Maltodextrin_DE12_w20",
    "MD_DE12_w20_I",
    "section_ori@1x1x1_res@100x100x100",
)
