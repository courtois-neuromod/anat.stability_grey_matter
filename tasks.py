from pathlib import Path

from invoke import task


# --------------------------------------------------------------------------- #
# Fetch
# --------------------------------------------------------------------------- #
def cneuromod_root(c):
    """Path of the cneuromod.all checkout, from `datasets:` in invoke.yaml."""
    return Path(c.config.get("datasets")["cneuromod"]["output_dir"])

def anat_subdataset_root(c, name):
    """Path of the anat subdataset `name` (freesurfer, smriprep, atlases)."""
    return cneuromod_root(c) / c.config.get("anat")[name]["subdataset"]

def fetch_subdataset(c, name):
    """
    Install one anat subdataset (tree only), check out its configured branch,
    then retrieve the content matching its `patterns`.

    Tolerant: files that fail to download (restricted sub-04 content without
    credentials) are warned about, remembered in .fetch_failures.json, and
    not retried on the next fetch. Delete that file to retry them.
    """
    from airoh.datalad import (
        install_subdataset,
        load_known_failures,
        prefetch_pattern,
        save_known_failures,
    )

    entry = c.config.get("anat")[name]
    subdataset_root = anat_subdataset_root(c, name)
    install_subdataset(entry["subdataset"], cneuromod_root(c))
    if entry.get("branch"):
        c.run(f"git -C {subdataset_root} checkout --quiet {entry['branch']}")

    cache_dir = Path(c.config.get("source_data_dir"))
    failures = load_known_failures(cache_dir)
    for pattern in entry.get("patterns") or []:
        present, fetched, skipped, new_failures, resolved = prefetch_pattern(
            subdataset_root, pattern, skip_set=failures)
        failures = (failures - resolved) | new_failures
        print(f"📥 {name} {pattern}: {present} already present, {fetched} fetched, "
              f"{len(new_failures)} failed, {skipped} skipped (failed before)")
    save_known_failures(cache_dir, failures)

@task(help={
    "source": "Existing cneuromod.all checkout to symlink instead of cloning.",
})
def fetch_cneuromod(c, source=None):
    """
    Retrieve the anat inputs from the CNeuroMod superdataset.

    Clones cneuromod.all (or symlinks an existing checkout), installs the anat
    subdatasets configured under `anat:` in invoke.yaml, and retrieves only the
    files matching their patterns.
    """
    from airoh.datalad import install_dataset

    install_dataset(c, "cneuromod", source=source)
    for name in ("freesurfer", "smriprep", "atlases"):
        fetch_subdataset(c, name)

@task(help={
    "cneuromod_source": "Existing cneuromod.all checkout to symlink instead of cloning.",
})
def fetch(c, cneuromod_source=None):
    """
    Retrieve all data assets. Each asset has its own fetch-{name} task; this
    umbrella task routes a per-asset --{name}-source flag to the matching one.

    Records what each asset actually resolved to in source_data/MANIFEST.json,
    so the inputs a later run consumed stay identifiable — including the commit
    of a symlinked external checkout. See CLAUDE.md, "Recording asset versions".
    """
    from airoh.provenance import record_sources

    fetch_cneuromod(c, source=cneuromod_source)
    record_sources(c)

# --------------------------------------------------------------------------- #
# Analysis steps
# --------------------------------------------------------------------------- #
def select_subjects(c, subjects=None, smoke=False):
    """Subjects to process: --subjects if given, else all (only the first with --smoke)."""
    if subjects:
        return subjects.split(",")
    all_subjects = list(c.config.get("anat")["subjects"])
    return all_subjects[:1] if smoke else all_subjects

def require_input(path):
    """Fail with a pointer to `invoke fetch` when a source input is missing."""
    if not Path(path).exists():
        raise FileNotFoundError(f"❌ Missing input {path} — run `invoke fetch` first.")

@task(help={
    "subjects": "Comma-separated subjects to process (default: all in invoke.yaml).",
    "smoke": "Process only the first subject.",
})
def run_gm_volumes(c, subjects=None, smoke=False):
    """
    Grey matter volume per region (Desikan cortex, aseg subcortex and
    cerebellum) and per session, one table per subject.

    Reads only the FreeSurfer longitudinal text stats (`aparc.stats`,
    `aseg.stats`). Writes output_data/gm_volumes/sub-XX_gm_volumes.tsv. A
    subject whose table already exists is skipped; `invoke clean-gm-volumes`
    (or `run --force`) redoes them. Subjects with no retrieved sessions are
    skipped with a warning.
    """
    from analysis.gm_volumes import extract_subject_gm_volumes, list_long_sessions

    freesurfer_root = anat_subdataset_root(c, "freesurfer")
    require_input(freesurfer_root)
    output_dir = Path(c.config.get("output_data_dir")) / "gm_volumes"
    output_dir.mkdir(parents=True, exist_ok=True)

    for subject in select_subjects(c, subjects, smoke):
        output_file = output_dir / f"{subject}_gm_volumes.tsv"
        if output_file.is_file():
            print(f"🫧 Skipping {subject} (output exists)")
            continue
        long_dirs = list_long_sessions(freesurfer_root, subject)
        if not long_dirs:
            print(f"⚠️  {subject}: no retrieved longitudinal sessions, skipping")
            continue
        volumes = extract_subject_gm_volumes(subject, long_dirs)
        volumes.to_csv(output_file, sep="\t", index=False)
        print(f"✅ {subject}: {len(long_dirs)} sessions → {output_file}")

@task(help={
    "subjects": "Comma-separated subjects to pool (default: all in invoke.yaml).",
    "smoke": "Use only the first subject.",
})
def run_region_networks(c, subjects=None, smoke=False):
    """
    Majority Yeo-7 network of each Desikan region, used to colour regions.

    Counts, in each subject's native T1w space, how many voxels of each
    Desikan region (smriprep `aparcaseg`) fall in each network (native
    Schaefer 1000/7 from anat/atlases), pools the counts over subjects and
    keeps the majority. Subjects whose two label volumes are not retrieved
    are skipped with a warning. Writes output_data/region_networks.tsv;
    skipped when it exists.
    """
    from analysis.region_networks import (
        desikan_labels,
        majority_networks,
        read_label_table,
        schaefer_networks,
        subject_overlap_counts,
    )

    output_file = Path(c.config.get("output_data_dir")) / "region_networks.tsv"
    if output_file.is_file():
        print("🫧 Skipping region networks (output exists)")
        return
    smriprep_root = anat_subdataset_root(c, "smriprep")
    atlases_root = anat_subdataset_root(c, "atlases")
    schaefer_stem = "atlas-Schaefer2018_desc-1000Parcels7Networks_dseg"
    schaefer_table = (atlases_root / "tpl-MNI152NLin2009cAsym"
                      / f"tpl-MNI152NLin2009cAsym_{schaefer_stem}.tsv")
    aparcaseg_table = smriprep_root / "desc-aparcaseg_dseg.tsv"
    require_input(schaefer_table)
    require_input(aparcaseg_table)
    parcel_networks = schaefer_networks(read_label_table(schaefer_table))
    desikan_names = desikan_labels(read_label_table(aparcaseg_table))

    counts_per_subject = {}
    for subject in select_subjects(c, subjects, smoke):
        template = f"tpl-{subject.replace('-', '')}T1w"
        aparcaseg_file = smriprep_root / subject / "anat" / f"{subject}_desc-aparcaseg_dseg.nii.gz"
        schaefer_file = atlases_root / template / f"{template}_res-anat_{schaefer_stem}.nii.gz"
        if not (aparcaseg_file.is_file() and schaefer_file.is_file()):
            print(f"⚠️  {subject}: aparcaseg or native Schaefer not retrieved, skipping")
            continue
        counts_per_subject[subject] = subject_overlap_counts(
            aparcaseg_file, schaefer_file, desikan_names, parcel_networks)
    if not counts_per_subject:
        print("⚠️  No subject has both label volumes (run `invoke fetch`); skipping")
        return
    majority_networks(counts_per_subject).to_csv(output_file, sep="\t", index=False)
    print(f"✅ Wrote {output_file} (pooled over {len(counts_per_subject)} subjects)")

@task
def run_stability(c):
    """
    Intra- versus inter-subject variation per region, from all gm_volumes
    tables, each region tagged with its network from region_networks.tsv.

    Writes output_data/stability_per_region.tsv. Skipped when it exists, and
    when either input has not been produced yet.
    """
    import pandas as pd

    from analysis.stability import load_gm_volumes, region_stability

    output_dir = Path(c.config.get("output_data_dir"))
    output_file = output_dir / "stability_per_region.tsv"
    networks_file = output_dir / "region_networks.tsv"
    if output_file.is_file():
        print("🫧 Skipping stability (output exists)")
        return
    volumes = load_gm_volumes(output_dir / "gm_volumes")
    if volumes.empty:
        print("⚠️  No gm_volumes tables yet (run-gm-volumes); skipping stability")
        return
    if not networks_file.is_file():
        print(f"⚠️  {networks_file} missing (run-region-networks); skipping stability")
        return
    region_networks = pd.read_csv(networks_file, sep="\t")
    region_stability(volumes, region_networks).to_csv(output_file, sep="\t", index=False)
    print(f"✅ Wrote {output_file}")

@task
def run_trajectories(c):
    """
    Grey matter volume over sessions, as percent deviation from each subject's
    own regional mean, averaged per network: per subject and over subjects.

    Writes output_data/volume_trajectories.tsv (aggregate over subjects,
    tracked) and output_data/volume_trajectories_subject.tsv (per participant,
    untracked). Skipped when both exist, and when either input has not been
    produced yet.
    """
    import pandas as pd

    from analysis.stability import load_gm_volumes
    from analysis.trajectories import (
        network_trajectories,
        subject_trajectories,
        volume_deviations,
    )

    output_dir = Path(c.config.get("output_data_dir"))
    network_file = output_dir / "volume_trajectories.tsv"
    subject_file = output_dir / "volume_trajectories_subject.tsv"
    networks_file = output_dir / "region_networks.tsv"
    if network_file.is_file() and subject_file.is_file():
        print("🫧 Skipping trajectories (output exists)")
        return
    volumes = load_gm_volumes(output_dir / "gm_volumes")
    if volumes.empty:
        print("⚠️  No gm_volumes tables yet (run-gm-volumes); skipping trajectories")
        return
    if not networks_file.is_file():
        print(f"⚠️  {networks_file} missing (run-region-networks); skipping trajectories")
        return
    deviations = volume_deviations(volumes, pd.read_csv(networks_file, sep="\t"))
    per_subject = subject_trajectories(deviations)
    per_subject.to_csv(subject_file, sep="\t", index=False)
    network_trajectories(per_subject).to_csv(network_file, sep="\t", index=False)
    print(f"✅ Wrote {network_file} and {subject_file}")

def montage_dpi(c):
    """
    The DPI the montage is composed at, from `figures:` in invoke.yaml.

    This template has a single montage, so the first entry's `dpi` is the
    answer; a project with several would need to decide which one a given
    notebook's panels belong to. Defaults to 300, matching
    `airoh.figures.compose_figure`.
    """
    for entry in (c.config.get("figures") or {}).values():
        return entry.get("dpi", 300)
    return 300

@task
def run_figure_layout(c):
    """
    Write every montage's panel geometry to figures_dir/panel_sizes.json.

    Read by the notebook (see fig_anat_stability.ipynb) so every placed panel
    renders at exactly the physical size the montage allocates it. Always
    re-runs, never skipped: it is cheap, and a box resized in Inkscape must
    take effect on the very next `invoke run`.
    """
    from airoh.figures import figure_layout
    figure_layout(c)

@task(pre=[run_stability, run_trajectories, run_figure_layout])
def run_notebooks(c):
    """
    Generate the figure panels from stability_per_region.tsv,
    volume_trajectories*.tsv and the per-subject tables, using the notebooks.

    Skipped, with a message, while stability_per_region.tsv does not exist:
    a notebook that ran without its input would still leave its "already ran"
    folder behind, and the next `run` would then skip it for good.

    `run-figure-layout` runs first because the notebook sizes its placed
    panels from the geometry it writes — and `clean-figures` wipes that file
    along with the figures dir it lives in. (`run` calls both explicitly, in
    the same order; this `pre=` only covers invoking `run-notebooks` on its
    own.)

    Exports the montage's configured DPI as FIGURE_MONTAGE_DPI so notebooks
    save at it rather than hardcoding 300 — panel *pixels* must equal
    figsize × dpi for placement to stay 1:1, so the resolution has to come
    from the same config the montage is composed with.
    """
    import os

    from airoh.utils import ensure_dir_exist
    from airoh.utils import run_notebooks as airoh_run_notebooks

    notebooks_dir = Path(c.config.get("notebooks_dir"))
    figures_base = Path(c.config.get("figures_dir")).resolve()

    os.environ["FIGURE_MONTAGE_DPI"] = str(montage_dpi(c))

    stability_file = Path(c.config.get("output_data_dir")) / "stability_per_region.tsv"
    if not stability_file.is_file():
        print(f"⚠️  {stability_file} missing (run-stability); skipping notebooks")
        return

    ensure_dir_exist(c, "output_data_dir")
    airoh_run_notebooks(c, notebooks_dir, figures_base,
                         keys=["source_data_dir", "output_data_dir", "figures_dir"])

@task
def compose_figure(c):
    """
    Render the hand-authored fig_anat_stability.svg to PNG with Inkscape.

    Optional: Inkscape is only needed to recompose the final figure, never to
    reproduce a panel, so a missing binary warns and returns rather than
    failing the run.
    """
    from airoh.figures import compose_figure as airoh_compose_figure
    airoh_compose_figure(c)

# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #
@task(help={
    "force": "Delete every computed output first, then run from scratch.",
})
def run(c, force=False):
    """
    Full pipeline: gm volumes → region networks → stability → trajectories
    → figure layout → notebooks → composed figure.

    Steps are called directly rather than through `pre=`, so that flags like
    --force reach them: a `pre=` chain runs before this body, which would be
    too late.

    Every step caches by checking whether its output already exists, so a
    repeated `run` does nothing. That is deliberate — but it also means an
    edited script or notebook will NOT re-run on its own. `--force` is the
    sledgehammer: clean everything, then start over. To redo one step, call its
    `clean-{name}` task and run again. `run-figure-layout` is the one
    deliberate exception: it always re-runs (see its docstring).
    """
    from airoh.provenance import record_run

    if force:
        print("💥 --force: removing every computed output before running")
        clean(c)
    run_gm_volumes(c)
    run_region_networks(c)
    run_stability(c)
    run_trajectories(c)
    run_figure_layout(c)
    run_notebooks(c)
    compose_figure(c)
    record_run(c, tasks="run-gm-volumes,run-region-networks,run-stability,"
                        "run-trajectories,run-figure-layout,run-notebooks,"
                        "compose-figure")
    print("all analyses completed")

@task
def run_smoke(c):
    """
    Smoke test: a minimal end-to-end pass over the whole pipeline.

    Calls the steps directly (rather than via `pre=`) so each can be given a
    reduced workload. The point is to exercise the plumbing quickly, not to
    produce real results — so it processes only the first subject, and fails
    loudly if fetch retrieved none of that subject's FreeSurfer sessions.
    """
    from analysis.gm_volumes import list_long_sessions

    fetch(c)
    first_subject = select_subjects(c, smoke=True)[0]
    if not list_long_sessions(anat_subdataset_root(c, "freesurfer"), first_subject):
        raise RuntimeError(f"❌ fetch retrieved no FreeSurfer session for {first_subject}")
    run_gm_volumes(c, smoke=True)
    run_region_networks(c, smoke=True)
    run_stability(c)
    run_trajectories(c)
    run_figure_layout(c)
    run_notebooks(c)
    compose_figure(c)
    print("✅ Smoke test complete.")

@task(help={
    "skip": "Comma-separated check names to skip.",
    "strict": "Treat warnings as failures.",
})
def verify(c, skip=None, strict=False):
    """
    Check that the code, config, data and docs still agree.

    Run this before committing. It is deliberately NOT part of `run`:
    reproducing results should never depend on documentation hygiene. See
    CLAUDE.md, "Verification", for what each check covers.
    """
    from airoh.verify import verify as airoh_verify
    airoh_verify(c, skip=skip, strict=strict)

# --------------------------------------------------------------------------- #
# Clean
# --------------------------------------------------------------------------- #
@task
def clean_gm_volumes(c):
    """
    Remove the per-subject grey matter volume tables.
    """
    from airoh.utils import clean_folder
    clean_folder(c, "output_data_dir", "gm_volumes/sub-*_gm_volumes.tsv")

@task
def clean_region_networks(c):
    """
    Remove the region-to-network assignment table.
    """
    from airoh.utils import clean_folder
    clean_folder(c, "output_data_dir", "region_networks.tsv")

@task
def clean_stability(c):
    """
    Remove the per-region stability table.
    """
    from airoh.utils import clean_folder
    clean_folder(c, "output_data_dir", "stability_per_region.tsv")

@task
def clean_trajectories(c):
    """
    Remove the volume trajectory tables (per network and per subject).
    """
    from airoh.utils import clean_folder
    clean_folder(c, "output_data_dir", "volume_trajectories.tsv")
    clean_folder(c, "output_data_dir", "volume_trajectories_subject.tsv")

@task
def clean_figures(c):
    """
    Remove the figures dir (per-notebook panels, the "already ran" sentinels,
    and panel_sizes.json).

    Leaving a notebook's sentinel folder behind would make the next `run`
    skip it even though its figures are gone, so the whole figures_dir tree
    is removed, not just the PNGs inside it.
    """
    from airoh.utils import clean_folder
    clean_folder(c, "figures_dir")

@task
def clean_figure(c):
    """
    Remove the composed montage PNG (fig_anat_stability.png).

    Never the SVG: that one is hand-authored in Inkscape and is a pipeline
    *source*, despite living in output_data/ (its relative image links
    resolve from there).
    """
    from airoh.figures import clean_figure as airoh_clean_figure
    airoh_clean_figure(c)

@task
def clean(c):
    """
    Remove all computed outputs.

    The steps are called in the body rather than declared as `pre=`, because a
    `pre=` chain only fires when invoke runs the task from the command line.
    Calling `clean(c)` from Python — which is what `run --force` does — would
    otherwise execute an empty function and silently delete nothing.
    """
    clean_gm_volumes(c)
    clean_region_networks(c)
    clean_stability(c)
    clean_trajectories(c)
    clean_figures(c)
    clean_figure(c)

@task
def clean_cneuromod(c):
    """
    Remove the cneuromod.all checkout (a symlink, or a datalad clone).

    Not called by `clean` or `run --force` — those only touch output_data/.
    A symlink is simply unlinked. A clone goes through `datalad remove`,
    which refuses to drop content it cannot find another copy of. Run this
    before `invoke fetch-cneuromod --source ...` to re-point the checkout:
    fetch never replaces an existing one.
    """
    root = cneuromod_root(c)
    if root.is_symlink():
        root.unlink()
        print(f"🧹 Removed link: {root}")
    elif root.exists():
        c.run(f"datalad remove --recursive --dataset {root}")
    else:
        print(f"🫧 Skipping: {root} does not exist.")

@task
def clean_source(c):
    """
    Remove all source data assets. Body calls each clean-{name} task.
    """
    clean_cneuromod(c)
