# 📁 Output Data Contents

Once the pipeline is run, this folder will contain the following:

- `gm_volumes/sub-XX_gm_volumes.tsv` — grey matter volume (mm³) per region and
  per session for one subject; columns `subject, session, region, gm_volume`.
  84 regions: the 68 Desikan cortical regions (`ctx-lh-bankssts`, ...,
  `GrayVol` from `aparc.stats`), 14 subcortical structures and the two
  cerebellar cortices (`Left-Thalamus`, ..., PV-corrected `Volume_mm3` from
  `aseg.stats`). Written by `invoke run-gm-volumes`.
- `region_networks.tsv` — the network each region is coloured by; columns
  `region, network, network_fraction, n_subjects`. Cortical regions take the
  Yeo-7 network covering most of their voxels (native-space counts pooled over
  the `n_subjects` subjects whose label volumes were retrieved);
  `network_fraction` is that network's share, low for regions straddling
  networks. Subcortical structures are `subcortex`, cerebellar cortices
  `cerebellum`. Written by `invoke run-region-networks`.
- `stability_per_region.tsv` — one row per region, with its `network`: `n_subjects`,
  `n_sessions`, `intra_subject_cv` (CV across sessions, averaged over
  subjects), `inter_subject_cv` (CV across subjects of their mean volume) and
  `intra_inter_ratio`. Written by `invoke run-stability`.
- `volume_trajectories_subject.tsv` — grey matter volume over sessions per
  subject and network; columns `subject, network, session_rank,
  mean_deviation_pct, n_regions`. Each regional volume is a percent deviation
  from that subject's own mean for the region, averaged over the network's
  regions; `session_rank` 1 is the subject's first session (acquisition order,
  no dates). Written by `invoke run-trajectories`.
- `volume_trajectories.tsv` — the same averaged over subjects per `network` and
  `session_rank`, with `sem_deviation_pct` and `n_subjects`. Written by
  `invoke run-trajectories`.
- `trajectory_slopes.tsv` — least-squares slope of each subject's trajectory, in
  percent per session; columns `subject, network, slope_pct_per_session,
  n_sessions`. One row per subject and network, plus one per subject over all
  84 regions (`network` = `all`, network means weighted by their number of
  regions, as in panel C). A summary per participant, not volumes. Written by
  `invoke run-trajectories`.
- `figures/fig_anat_stability/` — the notebook's panels: `network_maps.png`
  (glass-brain network key), `trajectories_networks.png`,
  `trajectories_subjects.png`, `cv_bars.png`, and
  `*_legend.png` strips for the panels that need one.
- `figures/panel_sizes.json` — the `{panel: (width_mm, height_mm)}` box each
  panel is placed in inside `fig_anat_stability.svg`, written by
  `invoke run-figure-layout`. Read by the notebook via `airoh.figures.panel_size`
  so each panel renders at exactly its placed size.
- `fig_anat_stability.svg` — hand-authored in Inkscape, the single source of
  truth for panel layout. A pipeline **source**, not an output, despite living
  here: its `<image>` links are relative paths that resolve from this
  directory. See `CLAUDE.md`, "Figures: the Inkscape montage pattern".
- `fig_anat_stability.png` — the composed montage, rendered from
  `fig_anat_stability.svg` by `invoke compose-figure` via the Inkscape CLI
  (skipped with a warning if Inkscape isn't installed).
- `fig_anat_stability_caption.md` — hand-written caption for the montage, kept
  beside the hand-authored SVG so the numbers it quotes stay next to the tables
  they came from. Not produced by any pipeline step, and not regenerated: every
  figure quoted in it was read from the tables above by hand, so re-check it
  after a rerun on different data.
- `PROVENANCE.json` — what produced everything above: the project's git commit,
  the environment, the input manifest it consumed, and a checksum of every
  output file. Written by `invoke run`.

📝 Note: the notebook writes into `figures/fig_anat_stability/`, named after
itself. That folder doubles as the "already ran" marker `run-notebooks`
checks.

📝 Note: `gm_volumes/` and `volume_trajectories_subject.tsv` are per-participant
(including restricted sub-04) and are **not tracked by git**, nor are png files.
Tracked: `region_networks.tsv`, `stability_per_region.tsv` and
`volume_trajectories.tsv` (aggregates over subjects),
`trajectory_slopes.tsv` (one slope per participant and network),
`fig_anat_stability.svg` (hand-authored source),
`fig_anat_stability_caption.md` (hand-written caption) and `PROVENANCE.json` (small,
the record of where the untracked results came from — it changes on every run,
by design).
