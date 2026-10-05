"""Grey matter volume over sessions, per network and per subject.

Regions differ in size by orders of magnitude, so each volume is expressed as
its percent deviation from the mean of that region over that subject's own
sessions: `100 * (volume / subject_region_mean - 1)`. A trajectory is then the
average deviation over a network's regions, at each session.

Sessions are counted in acquisition order per subject (`session_rank` 1 is the
first scan). Their dates are not available here, so the time axis is the
session order, not elapsed time.

Two tables:

- per subject: `subject, network, session_rank, mean_deviation_pct, n_regions`.
- per network: the same averaged over subjects at each session rank, with
  `n_subjects`, so a caller can drop late sessions only a few participants
  reach. Each subject counts once, whatever its number of regions.

`slope_pct_per_session` fits one least-squares line per subject and network:
its sign says whether that participant's volume declines in that network.
`slope_table` gathers those slopes, plus one per subject over all regions
(network `all`), into the table the paper quotes.
"""

import numpy as np
import pandas as pd

SUBJECT_TRAJECTORY_COLUMNS = ["subject", "network", "session_rank", "mean_deviation_pct",
                              "n_regions"]
SLOPE_COLUMNS = ["subject", "network", "slope_pct_per_session", "n_sessions"]
ALL_REGIONS = "all"
NETWORK_TRAJECTORY_COLUMNS = ["network", "session_rank", "mean_deviation_pct",
                              "sem_deviation_pct", "n_subjects"]


def volume_deviations(volumes, region_networks):
    """`volumes` with `network`, `session_rank` and `deviation_pct` columns."""
    deviations = volumes.merge(region_networks[["region", "network"]], on="region",
                               how="left")
    by_subject_region = deviations.groupby(["subject", "region"])
    deviations["session_rank"] = (by_subject_region["session"]
                                  .rank(method="dense").astype(int))
    deviations["deviation_pct"] = 100 * (
        deviations["gm_volume"] / by_subject_region["gm_volume"].transform("mean") - 1)
    return deviations


def subject_trajectories(deviations):
    """Mean deviation over each network's regions, per subject and session."""
    grouped = deviations.groupby(["subject", "network", "session_rank"])["deviation_pct"]
    trajectories = pd.DataFrame({
        "mean_deviation_pct": grouped.mean(),
        "n_regions": grouped.size(),
    }).reset_index()
    return trajectories[SUBJECT_TRAJECTORY_COLUMNS]


def network_trajectories(subject_table):
    """Average of the subject trajectories at each network and session rank."""
    grouped = subject_table.groupby(["network", "session_rank"])["mean_deviation_pct"]
    trajectories = pd.DataFrame({
        "mean_deviation_pct": grouped.mean(),
        "sem_deviation_pct": grouped.sem(),
        "n_subjects": grouped.size(),
    }).reset_index()
    return trajectories[NETWORK_TRAJECTORY_COLUMNS]


def slope_pct_per_session(subject_table):
    """Least-squares slope of each subject x network trajectory, in % per session."""
    def fit(trajectory):
        return np.polyfit(trajectory["session_rank"], trajectory["mean_deviation_pct"], 1)[0]

    slopes = {key: fit(group)
              for key, group in subject_table.groupby(["subject", "network"])}
    return pd.Series(slopes, name="slope_pct_per_session").rename_axis(["subject", "network"])


def all_region_trajectories(subject_table):
    """Per-subject trajectory over all regions, as network `all`.

    Network means are weighted by their number of regions, so this is the mean
    deviation over every region, not over networks.
    """
    weighted = subject_table.assign(
        weighted=subject_table["mean_deviation_pct"] * subject_table["n_regions"])
    summed = weighted.groupby(["subject", "session_rank"])[["weighted", "n_regions"]].sum()
    trajectories = pd.DataFrame({
        "network": ALL_REGIONS,
        "mean_deviation_pct": summed["weighted"] / summed["n_regions"],
        "n_regions": summed["n_regions"],
    }).reset_index()
    return trajectories[SUBJECT_TRAJECTORY_COLUMNS]


def slope_table(subject_table):
    """Slope of every subject x network trajectory, plus each subject over all regions."""
    trajectories = pd.concat([subject_table, all_region_trajectories(subject_table)],
                             ignore_index=True)
    slopes = slope_pct_per_session(trajectories)
    n_sessions = trajectories.groupby(["subject", "network"])["session_rank"].nunique()
    table = pd.DataFrame({"slope_pct_per_session": slopes,
                          "n_sessions": n_sessions}).reset_index()
    return table[SLOPE_COLUMNS]
