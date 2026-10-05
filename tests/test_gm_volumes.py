import pytest

from analysis.gm_volumes import (
    SUBCORTICAL_NETWORKS,
    extract_subject_gm_volumes,
    list_long_sessions,
    read_stats_table,
    session_label,
)


def make_session(root, name, with_stats=True):
    stats_dir = root / name / "stats"
    stats_dir.mkdir(parents=True)
    if with_stats:
        (stats_dir / "aseg.stats").write_text("")
    return root / name


def write_aparc_stats(stats_dir, hemisphere, volumes):
    lines = ["# Measure Cortex, NumVert, Number of Vertices, 1, unitless",
             "# ColHeaders StructName NumVert SurfArea GrayVol ThickAvg"]
    lines += [f"{name} 10 20 {volume} 2.5" for name, volume in volumes.items()]
    (stats_dir / f"{hemisphere}.aparc.stats").write_text("\n".join(lines) + "\n")


def write_aseg_stats(stats_dir, structures):
    lines = ["# ColHeaders  Index SegId NVoxels Volume_mm3 StructName normMean"]
    lines += [f"{i} {i} 100 {volume} {name} 50.0"
              for i, (name, volume) in enumerate(structures.items(), start=1)]
    (stats_dir / "aseg.stats").write_text("\n".join(lines) + "\n")


def test_session_label():
    assert session_label("sub-01_ses-004.long.sub-01") == "ses-004"


def test_list_long_sessions_keeps_retrieved_sessions_of_one_subject(tmp_path):
    make_session(tmp_path, "sub-01_ses-002.long.sub-01")
    make_session(tmp_path, "sub-01_ses-001.long.sub-01")
    make_session(tmp_path, "sub-01_ses-003.long.sub-01", with_stats=False)
    make_session(tmp_path, "sub-01_ses-001")  # cross-sectional, not longitudinal
    make_session(tmp_path, "sub-02_ses-001.long.sub-02")
    sessions = list_long_sessions(tmp_path, "sub-01")
    assert [session_label(s) for s in sessions] == ["ses-001", "ses-002"]


def test_read_stats_table_requires_col_headers(tmp_path):
    stats_file = tmp_path / "broken.stats"
    stats_file.write_text("# no headers here\nfoo 1 2\n")
    with pytest.raises(ValueError, match="ColHeaders"):
        read_stats_table(stats_file)


def test_extract_reads_desikan_and_subcortical_volumes(tmp_path):
    session = make_session(tmp_path, "sub-01_ses-001.long.sub-01")
    stats_dir = session / "stats"
    write_aparc_stats(stats_dir, "lh", {"bankssts": 2856, "insula": 6000})
    write_aparc_stats(stats_dir, "rh", {"bankssts": 2700, "insula": 6100})
    # Ventricles are in aseg.stats too, but are not grey matter: dropped.
    write_aseg_stats(stats_dir, {name: 1000.5 for name in SUBCORTICAL_NETWORKS}
                     | {"Left-Lateral-Ventricle": 9999.0})

    volumes = extract_subject_gm_volumes("sub-01", [session])
    by_region = volumes.set_index("region")["gm_volume"]
    assert by_region["ctx-lh-bankssts"] == 2856
    assert by_region["ctx-rh-insula"] == 6100
    assert by_region["Left-Thalamus"] == 1000.5
    assert "Left-Lateral-Ventricle" not in by_region
    assert len(volumes) == 4 + len(SUBCORTICAL_NETWORKS)
    assert set(volumes["session"]) == {"ses-001"}


def test_extract_fails_on_missing_subcortical_structure(tmp_path):
    session = make_session(tmp_path, "sub-01_ses-001.long.sub-01")
    write_aparc_stats(session / "stats", "lh", {"bankssts": 1})
    write_aparc_stats(session / "stats", "rh", {"bankssts": 1})
    write_aseg_stats(session / "stats", {"Left-Thalamus": 1.0})
    with pytest.raises(ValueError, match="lacks"):
        extract_subject_gm_volumes("sub-01", [session])
