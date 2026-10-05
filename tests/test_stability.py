import math

import pandas as pd
import pytest

from analysis.stability import load_gm_volumes, region_stability


def make_volumes(rows):
    return pd.DataFrame(rows, columns=["subject", "session", "region", "gm_volume"])


def stability_of(volumes, networks=None):
    regions = sorted(volumes["region"].unique())
    networks = networks or {region: "Vis" for region in regions}
    region_networks = pd.DataFrame({"region": list(networks),
                                    "network": list(networks.values())})
    return region_stability(volumes, region_networks)


def test_perfectly_stable_subjects_have_zero_intra_cv():
    volumes = make_volumes([
        ("sub-01", "ses-001", "Visual", 100.0),
        ("sub-01", "ses-002", "Visual", 100.0),
        ("sub-02", "ses-001", "Visual", 200.0),
        ("sub-02", "ses-002", "Visual", 200.0),
    ])
    row = stability_of(volumes).iloc[0]
    assert row["intra_subject_cv"] == 0
    # subject means 100 and 200: std (ddof=1) = 70.71, mean = 150
    assert row["inter_subject_cv"] == pytest.approx(math.sqrt(5000) / 150)
    assert row["intra_inter_ratio"] == 0
    assert (row["n_subjects"], row["n_sessions"]) == (2, 4)


def test_intra_cv_is_averaged_over_subjects():
    volumes = make_volumes([
        ("sub-01", "ses-001", "DMN", 90.0),
        ("sub-01", "ses-002", "DMN", 110.0),
        ("sub-02", "ses-001", "DMN", 100.0),
        ("sub-02", "ses-002", "DMN", 100.0),
    ])
    row = stability_of(volumes).iloc[0]
    sub01_cv = math.sqrt(200) / 100
    assert row["intra_subject_cv"] == pytest.approx(sub01_cv / 2)
    assert row["inter_subject_cv"] == 0


def test_regions_are_kept_separate():
    volumes = make_volumes([
        (subject, session, region, volume)
        for region, volume in [("Visual", 10.0), ("DMN", 20.0)]
        for subject in ["sub-01", "sub-02"]
        for session in ["ses-001", "ses-002"]
    ])
    stability = stability_of(volumes)
    assert sorted(stability["region"]) == ["DMN", "Visual"]


def test_single_session_subject_gives_nan_intra_cv():
    volumes = make_volumes([
        ("sub-01", "ses-001", "Visual", 100.0),
        ("sub-02", "ses-001", "Visual", 120.0),
    ])
    assert math.isnan(stability_of(volumes).iloc[0]["intra_subject_cv"])


def test_load_gm_volumes_concatenates_subject_tables(tmp_path):
    for subject in ["sub-01", "sub-02"]:
        make_volumes([(subject, "ses-001", "Visual", 1.0)]).to_csv(
            tmp_path / f"{subject}_gm_volumes.tsv", sep="\t", index=False)
    assert len(load_gm_volumes(tmp_path)) == 2
    assert load_gm_volumes(tmp_path / "missing").empty


def test_each_region_carries_its_network():
    volumes = make_volumes([
        (subject, "ses-001", region, 10.0)
        for region in ["ctx-lh-cuneus", "Left-Thalamus"]
        for subject in ["sub-01", "sub-02"]
    ])
    networks = {"ctx-lh-cuneus": "Vis"}  # Left-Thalamus deliberately unassigned
    stability = stability_of(volumes, networks).set_index("region")
    assert stability.loc["ctx-lh-cuneus", "network"] == "Vis"
    assert pd.isna(stability.loc["Left-Thalamus", "network"])
