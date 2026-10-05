"""Which Yeo-7 network each grey matter region belongs to, for colouring.

Each Desikan cortical region is assigned the Yeo-7 network that covers most
of its voxels. The overlap is counted in each subject's native T1w space,
where two maps share one voxel grid:

- smriprep's `sub-XX_desc-aparcaseg_dseg.nii.gz` (`anat/smriprep`), the
  Desikan labels;
- `tpl-subXXT1w_res-anat_atlas-Schaefer2018_desc-1000Parcels7Networks_dseg`
  (`anat/atlases`), the Schaefer parcels warped to the subject, whose names in
  the MNI label table carry their network (`7Networks_LH_Vis_1` -> `Vis`).

Counts are pooled over every subject available before taking the majority, so
all subjects share one assignment. `network_fraction` records how much of the
region that network covers: a low value flags a region that straddles
networks. Subcortical and cerebellar structures are not in Schaefer; they take
their network from `analysis.gm_volumes.SUBCORTICAL_NETWORKS`.

The assignment only colours regions; volumes are always those of the whole
Desikan region (see analysis/gm_volumes.py).
"""

import numpy as np
import pandas as pd

from analysis.gm_volumes import SUBCORTICAL_NETWORKS

REGION_NETWORK_COLUMNS = ["region", "network", "network_fraction", "n_subjects"]
YEO7_NETWORKS = ["Vis", "SomMot", "DorsAttn", "SalVentAttn", "Limbic", "Cont", "Default"]


def read_label_table(path):
    """`{index: name}` from a BIDS `_dseg.tsv` (columns `index`, `name`, ...)."""
    table = pd.read_csv(path, sep="\t")
    names = table["name"].astype(str).str.strip('"')
    return dict(zip(table["index"].astype(int), names))


def schaefer_networks(schaefer_labels):
    """`{parcel index: network}` from Schaefer names like `7Networks_LH_Vis_1`."""
    return {index: name.split("_")[2] for index, name in schaefer_labels.items()}


def desikan_labels(aparcaseg_labels):
    """The 34 Desikan cortical labels per hemisphere of an aparc+aseg table.

    Excludes `ctx-?h-unknown` (1000/2000) and `ctx-?h-corpuscallosum`
    (1004/2004): both are in the colour table, but neither is a region of
    `aparc.stats`, so neither has a volume to colour.
    """
    return {
        index: name for index, name in aparcaseg_labels.items()
        if (1001 <= index <= 1035 or 2001 <= index <= 2035)
        and index not in (1004, 2004)
        and name.startswith("ctx-")
    }


def overlap_counts(desikan_volume, schaefer_volume, desikan_names, parcel_networks):
    """Voxel counts of each (Desikan region, Yeo network) pair in one subject.

    Voxels outside Schaefer (label 0) are ignored, so a region's counts only
    cover the part of it the parcellation reaches.
    """
    if desikan_volume.shape != schaefer_volume.shape:
        raise ValueError(f"grids differ: {desikan_volume.shape} vs {schaefer_volume.shape}")
    in_both = np.isin(desikan_volume, list(desikan_names)) & (schaefer_volume > 0)
    pairs = pd.DataFrame({
        "region": pd.Series(desikan_volume[in_both]).map(desikan_names),
        "network": pd.Series(schaefer_volume[in_both]).map(parcel_networks),
    })
    return pairs.value_counts().rename("n_voxels").reset_index()


def subject_overlap_counts(aparcaseg_file, schaefer_file, desikan_names, parcel_networks):
    """`overlap_counts` for one subject, read from its two native-space label volumes."""
    import nibabel

    aparcaseg_image = nibabel.load(str(aparcaseg_file))
    schaefer_image = nibabel.load(str(schaefer_file))
    if not np.allclose(aparcaseg_image.affine, schaefer_image.affine, atol=1e-3):
        raise ValueError(f"{aparcaseg_file} and {schaefer_file} are not on the same grid")
    return overlap_counts(np.asarray(aparcaseg_image.dataobj, dtype=np.int32),
                          np.asarray(schaefer_image.dataobj, dtype=np.int32),
                          desikan_names, parcel_networks)


def majority_networks(counts_per_subject):
    """One row per region (`REGION_NETWORK_COLUMNS`) from per-subject overlap counts.

    `counts_per_subject` maps a subject to its `overlap_counts` table. Cortical
    regions get their pooled majority network; the subcortical structures of
    `SUBCORTICAL_NETWORKS` are appended with `network_fraction` 1.
    """
    pooled = pd.concat(counts_per_subject.values()).groupby(["region", "network"])["n_voxels"]
    pooled = pooled.sum().reset_index()
    totals = pooled.groupby("region")["n_voxels"].transform("sum")
    pooled["network_fraction"] = pooled["n_voxels"] / totals
    cortical = pooled.loc[pooled.groupby("region")["n_voxels"].idxmax()]
    cortical = cortical.assign(n_subjects=len(counts_per_subject))
    subcortical = pd.DataFrame({
        "region": list(SUBCORTICAL_NETWORKS),
        "network": list(SUBCORTICAL_NETWORKS.values()),
        "network_fraction": 1.0,
        "n_subjects": len(counts_per_subject),
    })
    return pd.concat([cortical[REGION_NETWORK_COLUMNS], subcortical], ignore_index=True)
