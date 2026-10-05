import pandas as pd
import pytest

from analysis.trajectories import (
    NETWORK_TRAJECTORY_COLUMNS,
    SLOPE_COLUMNS,
    all_region_trajectories,
    network_trajectories,
    slope_pct_per_session,
    slope_table,
    subject_trajectories,
    volume_deviations,
)

REGION_NETWORKS = pd.DataFrame({"region": ["A", "B"], "network": ["Vis", "Vis"]})


def make_volumes(rows):
    return pd.DataFrame(rows, columns=["subject", "session", "region", "gm_volume"])


def test_deviation_is_relative_to_the_subject_region_mean():
    volumes = make_volumes([
        ("sub-01", "ses-001", "A", 110.0),
        ("sub-01", "ses-002", "A", 90.0),
    ])
    deviations = volume_deviations(volumes, REGION_NETWORKS)
    assert deviations["deviation_pct"].tolist() == pytest.approx([10.0, -10.0])


def test_session_rank_follows_acquisition_order_with_gaps():
    volumes = make_volumes([
        ("sub-01", "ses-003", "A", 100.0),
        ("sub-01", "ses-001", "A", 100.0),
    ])
    deviations = volume_deviations(volumes, REGION_NETWORKS)
    assert dict(zip(deviations["session"], deviations["session_rank"])) == {
        "ses-001": 1, "ses-003": 2}


def test_subject_trajectory_averages_regions_of_a_network():
    volumes = make_volumes([
        ("sub-01", "ses-001", "A", 110.0), ("sub-01", "ses-002", "A", 90.0),
        ("sub-01", "ses-001", "B", 102.0), ("sub-01", "ses-002", "B", 98.0),
    ])
    table = subject_trajectories(volume_deviations(volumes, REGION_NETWORKS))
    assert table["mean_deviation_pct"].tolist() == pytest.approx([6.0, -6.0])
    assert table["n_regions"].tolist() == [2, 2]


def test_network_trajectory_weights_each_subject_once():
    subject_table = pd.DataFrame({
        "subject": ["sub-01", "sub-02"], "network": ["Vis", "Vis"],
        "session_rank": [1, 1], "mean_deviation_pct": [2.0, 4.0], "n_regions": [10, 1],
    })
    table = network_trajectories(subject_table)
    assert list(table.columns) == NETWORK_TRAJECTORY_COLUMNS
    row = table.iloc[0]
    assert (row["mean_deviation_pct"], row["n_subjects"]) == (3.0, 2)


def test_slope_is_negative_for_a_declining_trajectory():
    subject_table = pd.DataFrame({
        "subject": ["sub-01"] * 3, "network": ["Vis"] * 3,
        "session_rank": [1, 2, 3], "mean_deviation_pct": [1.0, 0.0, -1.0],
        "n_regions": [1] * 3,
    })
    assert slope_pct_per_session(subject_table).loc[("sub-01", "Vis")] == pytest.approx(-1.0)


def test_all_region_trajectory_weights_networks_by_their_regions():
    subject_table = pd.DataFrame({
        "subject": ["sub-01", "sub-01"], "network": ["Vis", "Limbic"],
        "session_rank": [1, 1], "mean_deviation_pct": [3.0, 0.0], "n_regions": [2, 1],
    })
    table = all_region_trajectories(subject_table)
    row = table.iloc[0]
    assert (row["network"], row["mean_deviation_pct"], row["n_regions"]) == ("all", 2.0, 3)


def test_slope_table_adds_an_all_regions_row_per_subject():
    subject_table = pd.DataFrame({
        "subject": ["sub-01"] * 4, "network": ["Vis", "Vis", "Limbic", "Limbic"],
        "session_rank": [1, 2, 1, 2], "mean_deviation_pct": [1.0, -1.0, 0.0, 0.0],
        "n_regions": [1] * 4,
    })
    table = slope_table(subject_table).set_index("network")
    assert list(slope_table(subject_table).columns) == SLOPE_COLUMNS
    assert table.loc["Vis", "slope_pct_per_session"] == pytest.approx(-2.0)
    assert table.loc["all", "slope_pct_per_session"] == pytest.approx(-1.0)
    assert table.loc["all", "n_sessions"] == 2
