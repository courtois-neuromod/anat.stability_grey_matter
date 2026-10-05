"""Grey matter volume per region and per session, for one subject.

Read from the text stats of the longitudinal FreeSurfer sessions
(`sub-XX_ses-YYY.long.sub-XX/stats/`) of `anat/freesurfer.longitudinal`:

- cortex: the 34 Desikan regions per hemisphere, `GrayVol` column of
  `lh.aparc.stats` / `rh.aparc.stats` (surface-based volumes). Named like the
  FreeSurfer colour table, e.g. `ctx-lh-bankssts`, so they join with the
  `aparcaseg` labels `analysis.region_networks` reads.
- subcortex and cerebellum: the partial-volume-corrected `Volume_mm3` column of
  `aseg.stats`, for the structures in `SUBCORTICAL_NETWORKS`.

Only these stats files are used because they are tracked in git: the
annexed volumes (`aseg.mgz`, `ribbon.mgz`, ...) are not retrievable outside
the cluster store (see source_data/CONTENT.md). The output is one long-format
table per subject with the columns of `GM_VOLUME_COLUMNS`.
"""

from pathlib import Path

import pandas as pd

GM_VOLUME_COLUMNS = ["subject", "session", "region", "gm_volume"]

# aseg structures kept, and the network they are reported under.
SUBCORTICAL_NETWORKS = {
    f"{side}-{structure}": "subcortex"
    for side in ("Left", "Right")
    for structure in ("Thalamus", "Caudate", "Putamen", "Pallidum",
                      "Hippocampus", "Amygdala", "Accumbens-area")
} | {
    "Left-Cerebellum-Cortex": "cerebellum",
    "Right-Cerebellum-Cortex": "cerebellum",
}


def session_label(long_dir):
    """`ses-001` from a longitudinal session folder `sub-01_ses-001.long.sub-01`."""
    return Path(long_dir).name.split(".long.")[0].split("_", 1)[1]


def list_long_sessions(freesurfer_root, subject):
    """Longitudinal session folders of `subject` whose aseg.stats content is present.

    Sessions whose content was not retrieved (e.g. restricted data fetched
    without credentials) are left out rather than failing the subject.
    """
    pattern = f"{subject}_ses-*.long.{subject}"
    long_dirs = sorted(Path(freesurfer_root).glob(pattern))
    return [d for d in long_dirs if (d / "stats" / "aseg.stats").is_file()]


def read_stats_table(stats_file):
    """The body of a FreeSurfer `.stats` file as a DataFrame, named by its ColHeaders."""
    columns, rows = None, []
    for line in Path(stats_file).read_text().splitlines():
        if line.startswith("# ColHeaders"):
            columns = line.split()[2:]
        elif line.strip() and not line.startswith("#"):
            rows.append(line.split())
    if columns is None:
        raise ValueError(f"{stats_file} has no '# ColHeaders' line")
    return pd.DataFrame(rows, columns=columns)


def cortical_volumes(stats_dir):
    """Desikan grey matter volume (mm³) per region, both hemispheres."""
    tables = []
    for hemisphere in ("lh", "rh"):
        table = read_stats_table(Path(stats_dir) / f"{hemisphere}.aparc.stats")
        tables.append(pd.DataFrame({
            "region": f"ctx-{hemisphere}-" + table["StructName"],
            "gm_volume": table["GrayVol"].astype(float),
        }))
    return pd.concat(tables, ignore_index=True)


def subcortical_volumes(stats_dir):
    """Partial-volume-corrected volume (mm³) of each structure in `SUBCORTICAL_NETWORKS`."""
    table = read_stats_table(Path(stats_dir) / "aseg.stats")
    kept = table[table["StructName"].isin(SUBCORTICAL_NETWORKS)]
    missing = set(SUBCORTICAL_NETWORKS) - set(kept["StructName"])
    if missing:
        raise ValueError(f"{stats_dir}/aseg.stats lacks {sorted(missing)}")
    return pd.DataFrame({
        "region": kept["StructName"].to_numpy(),
        "gm_volume": kept["Volume_mm3"].astype(float).to_numpy(),
    })


def extract_subject_gm_volumes(subject, long_dirs):
    """Grey matter volume per region for every session of one subject.

    Returns a DataFrame with `GM_VOLUME_COLUMNS` (`gm_volume` in mm³).
    """
    tables = []
    for long_dir in long_dirs:
        stats_dir = Path(long_dir) / "stats"
        volumes = pd.concat([cortical_volumes(stats_dir), subcortical_volumes(stats_dir)],
                            ignore_index=True)
        volumes.insert(0, "session", session_label(long_dir))
        volumes.insert(0, "subject", subject)
        tables.append(volumes)
    return pd.concat(tables, ignore_index=True)[GM_VOLUME_COLUMNS]
