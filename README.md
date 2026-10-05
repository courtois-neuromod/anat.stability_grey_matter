# Stability of grey matter

The [CNeuroMod](https://www.cneuromod.ca/) participants completed an extensive brain and spine anatomical assessment approximately every 3 months for five years, resulting in over 10 anatomical sessions per participant. This analysis studies how stable grey matter volume is within the main Yeo networks (plus a few subcortical regions) for each participant across the course of the project.

Grey matter volumes come from the longitudinal FreeSurfer pipeline's per-session stats: the 68 Desikan cortical regions (surface-based `GrayVol`), 14 subcortical structures and the two cerebellar cortices (partial-volume-corrected `aseg` volumes). Each cortical region is coloured by the Yeo-7 network covering most of its voxels in the participant's native space; the volume itself is always that of the whole region. From these, the pipeline tracks grey matter volume over sessions (per network and per subject, as deviation from each participant's own mean) and compares intra- versus inter-subject variation per region. The figure follows the visual conventions of `cneuromod.all.connectome_stats`: canonical Yeo-7 colours, a glass-brain network key, and networks ordered from most to least stable.

Only the FreeSurfer *text* stats are used because they are tracked in git: the annexed volumes of `anat/freesurfer.longitudinal` live only on a cluster store and cannot be downloaded yet (see `source_data/CONTENT.md`).

The pipeline runs on the [`invoke`](https://www.pyinvoke.org/) task runner, with reusable tasks from [`airoh`](https://pypi.org/project/airoh/).

---

## ✨ TL;DR

```bash
uv sync
uv run invoke fetch
uv run invoke run
```

---

## 🚀 Quick Start

### **Step 1**: Install dependencies

```bash
uv sync
```
This creates a `.venv` and installs all dependencies from `pyproject.toml`. Fetching also needs the `datalad` and `git-annex` command-line tools; composing the final figure optionally needs [Inkscape](https://inkscape.org/).

---

### **Step 2**: Fetch the source data

```bash
uv run invoke fetch
```

Clones the CNeuroMod superdataset into `source_data/` (tree only), installs the anat subdatasets it needs — longitudinal FreeSurfer (branch `dev_rerun_t2`), smriprep and atlases (including the MNI group atlas drawn as the figure's network key) — and retrieves only the files matching the patterns under `anat:` in `invoke.yaml`.

Already have a `cneuromod.all` checkout on disk? Symlink it instead of cloning:

```bash
uv run invoke fetch --cneuromod-source /path/to/cneuromod.all
```

To re-point it later, run `uv run invoke clean-cneuromod` first: fetch never replaces an existing checkout.

**Data access.** sub-01, 02, 03, 05 and 06 are openly released (CC0). sub-04 is restricted: its files only download with CNeuroMod access keys exported in the shell. Without them, fetch warns and carries on: sub-04's FreeSurfer stats are plain git and always present, so its volumes still enter the analysis, but the region-to-network assignment is pooled over the five open subjects only. See [`source_data/CONTENT.md`](source_data/CONTENT.md) for details.

---

### **Step 3**: Run the full pipeline

```bash
uv run invoke run
```

Runs the full analysis in order: `run-gm-volumes` → `run-region-networks` → `run-stability` → `run-trajectories` → `run-figure-layout` → `run-notebooks` → `compose-figure`. `run` never downloads anything: if an input is missing, it tells you to run `invoke fetch`. Per-subject steps accept `--subjects sub-01,sub-02` to process a subset.

Steps that have already produced output are skipped. That caching is by file existence, not by content: **a step you just edited will still be skipped**, because its old output is sitting right there. When results start looking stale, force a clean rebuild:

```bash
uv run invoke run --force    # clean everything, then run from scratch
```

To redo a single step, remove its outputs and run again:

```bash
uv run invoke clean-stability
uv run invoke run
```

After resizing a panel in `output_data/fig_anat_stability.svg` with Inkscape, run `uv run invoke clean-figures` then `uv run invoke run` so the panel is redrawn at its new size.

`invoke run` also writes `output_data/PROVENANCE.json`, recording the project's git commit, the environment, the inputs it consumed and a checksum of every output.

---

### **Step 4**: Check that everything still agrees

```bash
uv run invoke run-smoke   # fast end-to-end pass on the first subject
uv run invoke verify      # code, config, data and docs still agree
uv run pytest             # unit tests for analysis/
uv run ruff check .       # linter
```

Run these before committing. `verify` is deliberately not part of `invoke run`: reproducing results should never depend on the documentation being tidy.

---

### **Step 5**: Clean outputs

```bash
uv run invoke clean          # remove all outputs
uv run invoke clean-{name}   # remove outputs of one specific step
uv run invoke clean-source   # remove all source data assets (e.g. before re-fetching)
```

---

## 🧠 Design principles

Airoh projects follow a few conventions that keep analyses fast, reproducible, and easy to pick up:

- **Analysis in code, visualization in notebooks.** Heavy computation lives in `analysis/` Python modules and is run by `invoke` tasks. Notebooks only read results and produce figures — so they stay fast.
- **Idempotent steps.** Each `run-{name}` task checks whether its outputs already exist and skips if they do. You can call `invoke run` repeatedly while working on a later step without re-running earlier ones. The flip side: caching is by existence, so `invoke run --force` is how you rebuild after editing something.
- **Mirrored clean tasks.** Every `run-{name}` has a matching `clean-{name}` that removes only its outputs. The top-level `clean` calls them all.
- **Smoke test.** `invoke run-smoke` does a fast minimal pass to verify the pipeline end-to-end.
- **Checked documentation.** `invoke verify` compares the project against its own docs, so drift is caught mechanically instead of by memory.
- **Recorded provenance.** `fetch` and `run` write `MANIFEST.json` and `PROVENANCE.json` — what the inputs actually were, and what produced the outputs.
- **Hand-authored montage, single source of truth for layout.** `output_data/fig_anat_stability.svg` places each notebook panel by relative path; `run-figure-layout` reads those boxes into `panel_sizes.json` so notebooks render every panel at exactly the size it will be placed at, and `compose-figure` renders the montage with Inkscape (optional — skipped with a warning if not installed). See `CLAUDE.md`, "Figures: the Inkscape montage pattern".

---

## 🧰 Task Overview

| Task                | Description                                              |
| ------------------- | -------------------------------------------------------- |
| `fetch`             | Gets all source data (`--cneuromod-source` symlinks an existing checkout) and writes `source_data/MANIFEST.json` |
| `fetch-cneuromod`   | Clones `cneuromod.all`, installs the anat subdatasets, retrieves only the files listed under `anat:` in `invoke.yaml` |
| `run`               | Runs the full pipeline in order; `--force` cleans first  |
| `run-gm-volumes`    | Grey matter volume per region and per session, per subject, from FreeSurfer stats (`--subjects`, `--smoke`) |
| `run-region-networks` | Majority Yeo-7 network of each Desikan region, pooled over subjects (`--subjects`, `--smoke`) |
| `run-stability`     | Intra- vs inter-subject variation per region, tagged with its network |
| `run-trajectories`  | Grey matter volume over sessions, per network and per subject (% deviation from own mean) |
| `run-figure-layout` | Writes the montage's panel geometry to `output_data/figures/panel_sizes.json`; always re-runs |
| `run-notebooks`     | Executes notebooks and saves figures to `output_data/figures/` |
| `compose-figure`    | Renders `fig_anat_stability.svg` to PNG with Inkscape (optional binary) |
| `run-smoke`         | Fast end-to-end pass on the first subject to check the pipeline is wired correctly |
| `verify`            | Checks that code, config, data and docs still agree      |
| `clean`             | Removes all generated outputs                            |
| `clean-gm-volumes`  | Removes the per-subject grey matter volume tables        |
| `clean-region-networks` | Removes the region-to-network table                  |
| `clean-stability`   | Removes the per-region stability table                   |
| `clean-trajectories` | Removes the volume trajectory tables                    |
| `clean-figures`     | Removes the figures dir (panels, notebook sentinels, panel_sizes.json) |
| `clean-figure`      | Removes the composed montage PNG (never the hand-authored SVG) |
| `clean-source`      | Removes all source data assets; routes to each `clean-{name}` |
| `clean-cneuromod`   | Removes the `cneuromod.all` checkout (unlinks a symlink, `datalad remove` for a clone) |

Use `uv run invoke --list` or `uv run invoke --help <task>` for descriptions and usage.

---

## 📁 Folder Structure

| Folder / File  | Description                              |
| -------------- | ---------------------------------------- |
| `analysis/`    | Pure Python analysis logic, called by invoke tasks |
| `notebooks/`   | Jupyter notebooks for visualization (one per figure) |
| `tests/`       | Unit tests for `analysis/` (pytest)      |
| `source_data/` | Raw source datasets — see [`source_data/CONTENT.md`](source_data/CONTENT.md) |
| `output_data/` | Generated results and figures — see [`output_data/CONTENT.md`](output_data/CONTENT.md) |
| `tasks.py`     | Project-specific invoke tasks            |
| `invoke.yaml`  | Config: paths, data sources, subjects, parameters |

---

## Built with airoh

This project was initialized from the [`airoh-template`](https://github.com/airoh-pipeline/airoh-template) and runs on [`airoh`](https://pypi.org/project/airoh/), a lightweight package of reusable `invoke` tasks. When working in this project, Claude Code responds as **Uncle Airoh**: patient, warm, and wise — with a calming cup of jasmine tea always on offer.
