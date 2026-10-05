"""Intra- versus inter-subject variation of grey matter volume, per region.

Both are coefficients of variation (standard deviation over mean), so regions
of very different sizes can be compared:

- `intra_subject_cv`: for each subject, the CV across their sessions; then
  averaged over subjects. How much one brain's measure moves over time.
- `inter_subject_cv`: the CV across subjects of each subject's mean volume
  over sessions. How much brains differ from each other.

A ratio well below 1 means the measure is stable within a participant
relative to how much participants differ. Each region carries the network it
is coloured by (from `analysis.region_networks`).
"""

from pathlib import Path

import pandas as pd

from analysis.gm_volumes import GM_VOLUME_COLUMNS

STABILITY_COLUMNS = ["region", "network", "n_subjects", "n_sessions", "intra_subject_cv",
                     "inter_subject_cv", "intra_inter_ratio"]


def load_gm_volumes(volumes_dir):
    """Concatenate every per-subject `sub-*_gm_volumes.tsv` in `volumes_dir`."""
    tables = sorted(Path(volumes_dir).glob("sub-*_gm_volumes.tsv"))
    if not tables:
        return pd.DataFrame(columns=GM_VOLUME_COLUMNS)
    return pd.concat([pd.read_csv(path, sep="\t") for path in tables], ignore_index=True)


def coefficient_of_variation(values):
    """Sample standard deviation over mean; NaN with fewer than two values."""
    return values.std(ddof=1) / values.mean()


def region_stability(volumes, region_networks):
    """One row per region with the columns of `STABILITY_COLUMNS`.

    `region_networks` has one row per region (`region`, `network`); a region
    missing from it keeps a NaN network rather than being dropped.
    """
    by_subject = volumes.groupby(["region", "subject"])["gm_volume"]
    per_subject = pd.DataFrame({
        "cv": by_subject.agg(coefficient_of_variation),
        "mean": by_subject.mean(),
        "n_sessions": by_subject.size(),
    }).reset_index()

    by_region = per_subject.groupby("region")
    stability = pd.DataFrame({
        "n_subjects": by_region.size(),
        "n_sessions": by_region["n_sessions"].sum(),
        "intra_subject_cv": by_region["cv"].mean(),
        "inter_subject_cv": by_region["mean"].agg(coefficient_of_variation),
    }).reset_index()
    stability["intra_inter_ratio"] = (stability["intra_subject_cv"]
                                      / stability["inter_subject_cv"])
    stability = stability.merge(region_networks[["region", "network"]], on="region",
                                how="left")
    return stability[STABILITY_COLUMNS]
