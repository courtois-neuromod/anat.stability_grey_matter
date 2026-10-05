# 📁 Source Data Contents

After `invoke fetch` is complete, expect the following content:

- `cneuromod.all/` — a datalad clone of the CNeuroMod superdataset
  (<https://github.com/courtois-neuromod/cneuromod.all>), or a symlink to an
  existing checkout (`invoke fetch --cneuromod-source /path`). Only the tree is
  cloned; content is retrieved for three anat subdatasets, narrowed to the
  glob patterns listed under `anat:` in `invoke.yaml`:
  - `anat/freesurfer.longitudinal/` — longitudinal FreeSurfer, checked out on
    branch `dev_rerun_t2`, which merges all per-subject template and
    longitudinal job branches (`main` holds only code). One folder
    `sub-XX_ses-YYY.long.sub-XX/` per session (76 in all: sub-01 14, sub-02 15,
    sub-03 15, sub-04 5, sub-05 13, sub-06 14); `stats/aseg.stats`,
    `stats/lh.aparc.stats` and `stats/rh.aparc.stats` are read from each.
    These text stats are plain git, so they are present for all six
    subjects, sub-04 included. **Every annexed file of this dataset** (all of
    `mri/`, `surf/`, ...) has its only copy on the cluster store
    `ria-beluga-storage`; its S3 remote is registered but empty, so no
    volume or surface can be retrieved here until that content is pushed.
  - `anat/smriprep/` — `sub-XX/anat/sub-XX_desc-aparcaseg_dseg.nii.gz`, the
    Desikan labels in each subject's native T1w space (the 2020 sMRIPrep run
    that every functional dataset used as its anatomical reference), plus its
    label table `desc-aparcaseg_dseg.tsv`.
  - `anat/atlases/` — `tpl-subXXT1w/*_res-anat_atlas-Schaefer2018_desc-1000Parcels7Networks_dseg.nii.gz`,
    the Schaefer 1000/7 parcellation warped to each subject's native T1w space
    (same grid as the smriprep `aparcaseg`), and the MNI label table
    `tpl-MNI152NLin2009cAsym/*_atlas-Schaefer2018_desc-1000Parcels7Networks_dseg.tsv`
    that names each parcel's network. Display only: the MNI group atlas
    `tpl-MNI152NLin2009cAsym/*_res-01_atlas-Schaefer2018TianS3NettekovenAsym_desc-1000Parcels7Networks50Subcort128Cereb_dseg.nii.gz`
    and its label table, whose network masks draw the figure's glass-brain key
    (`analysis/atlas_maps.py`); no analysis reads them.
- `MANIFEST.json` — what each declared asset actually resolved to, including
  the commit of the cneuromod.all checkout. Written by `invoke fetch`.
- `.fetch_failures.json` (hidden) — files that failed to download last time,
  skipped on the next fetch. Delete it to retry them.

## Access requirements

- **sub-01, sub-02, sub-03, sub-05, sub-06** are openly released (CC0): a
  fresh clone retrieves them with no credentials.
- **sub-04** is under a restricted CNeuroMod data-use agreement. Its content
  is only retrievable with the CNeuroMod access keys exported in the shell
  that runs `invoke fetch` (see the CNeuroMod documentation on data access).
  Without them, fetch prints `⚠️ datalad get returned errors` and continues,
  and `run-region-networks` reports `sub-04: aparcaseg or native Schaefer not
  retrieved` and pools the network assignment over the five open subjects.
  sub-04's FreeSurfer *stats* are plain git and always present, so sub-04
  still enters `run-gm-volumes` and `run-stability`. That is expected, not a
  pipeline bug.

📝 Note: nothing in this folder except `MANIFEST.json` and this file is tracked
by git (see `.gitignore`, which also guards imaging and FreeSurfer formats).
Never commit sub-04 data here or anywhere in this repository.
