"""Per-network anatomical masks from the MNI group atlas — display only.

These masks exist for one purpose: drawing the nine glass-brain tiles that
serve as the montage's network key (`notebooks/fig_anat_stability.ipynb`).
Nothing in the analysis path reads them.

They show where each **network** lies, not which Desikan regions were assigned
to it: the volumes are measured per Desikan region, and those regions exist
only in each participant's native space (smriprep `aparcaseg`), which cannot be
drawn on a group glass brain. Each region takes the network covering most of it
(`analysis.region_networks`), so the key shows the territory a colour stands
for.

Ported from `cneuromod.all.connectome_stats` (`analysis/atlas_maps.py`), so the
two projects draw the same nine maps: `7Networks_*` names carry the Yeo network
in their third underscore field, `Cereb-*` is cerebellum, and the Tian
subcortical structures make up `subcortex`.
"""

from pathlib import Path

import numpy as np
import pandas as pd

ATLAS_SPACE = "MNI152NLin2009cAsym"
ATLAS_DESC = (
    "Schaefer2018TianS3NettekovenAsym_desc-1000Parcels7Networks50Subcort128Cereb"
)
ATLAS_SUBDIR = f"tpl-{ATLAS_SPACE}"
ATLAS_NII = f"tpl-{ATLAS_SPACE}_res-01_atlas-{ATLAS_DESC}_dseg.nii.gz"
ATLAS_TSV = f"tpl-{ATLAS_SPACE}_atlas-{ATLAS_DESC}.tsv"

YEO_NETWORKS = ("Vis", "SomMot", "DorsAttn", "SalVentAttn", "Limbic", "Cont", "Default")
# Tian S3 subcortical prefixes: every name that is neither `7Networks_*` nor
# `Cereb-*` starts with one of these.
SUBCORTEX_PREFIXES = (
    "PUT", "THA", "CAU", "HIP", "AMY", "lAMY", "mAMY", "NAc",
    "GP", "aGP", "pGP", "pTHA", "aTHA",
)


def atlas_paths(atlases_root):
    """`(dseg.nii.gz, labels.tsv)` paths for the MNI group atlas, unchecked."""
    atlas_dir = Path(atlases_root) / ATLAS_SUBDIR
    return atlas_dir / ATLAS_NII, atlas_dir / ATLAS_TSV


def classify_region(region_name):
    """Map one atlas region name to a network name, or None if it belongs to none.

    Returns the nine names used everywhere in this project: the seven Yeo
    networks plus `cerebellum` and `subcortex`.
    """
    if region_name.startswith("7Networks_"):
        network = region_name.split("_")[2]
        return network if network in YEO_NETWORKS else None
    if region_name.startswith("Cereb-"):
        return "cerebellum"
    structure = region_name.split("-")[0]
    return "subcortex" if structure in SUBCORTEX_PREFIXES else None


def network_label_ids(labels_tsv):
    """`{network: [label_id, ...]}` read from the atlas's own label table."""
    labels = pd.read_csv(labels_tsv, sep="\t").rename(
        columns={"index": "label_id", "name": "region_name"}
    )
    labels["network"] = labels["region_name"].map(classify_region)
    assigned = labels[labels["network"].notna()]
    return {
        network: group["label_id"].tolist()
        for network, group in assigned.groupby("network")
    }


def network_mask_images(dseg_path, labels_tsv, networks):
    """`{network: Nifti1Image}`, each a binary mask of that network's parcels.

    Networks with no matching label in the atlas are omitted rather than
    returned empty, so a caller can tell "not in this atlas" from "empty mask".
    """
    import nibabel as nib

    atlas_img = nib.load(str(dseg_path))
    atlas_data = np.asarray(atlas_img.dataobj)
    label_ids = network_label_ids(labels_tsv)

    masks = {}
    for network in networks:
        ids = label_ids.get(network)
        if not ids:
            continue
        mask = np.isin(atlas_data, ids)
        if mask.any():
            masks[network] = nib.Nifti1Image(mask.astype(np.int8), atlas_img.affine)
    return masks
