import numpy as np
import pandas as pd
import pytest

from analysis.gm_volumes import SUBCORTICAL_NETWORKS
from analysis.region_networks import (
    desikan_labels,
    majority_networks,
    overlap_counts,
    read_label_table,
    schaefer_networks,
)

DESIKAN = {1001: "ctx-lh-bankssts", 1035: "ctx-lh-insula"}
PARCEL_NETWORKS = {1: "Vis", 2: "Default", 3: "SalVentAttn"}


def test_read_label_table_strips_quotes(tmp_path):
    table = tmp_path / "dseg.tsv"
    table.write_text('index\tname\tcolor\n0\t"Unknown"\t#000\n1001\t"ctx-lh-bankssts"\t#111\n')
    assert read_label_table(table) == {0: "Unknown", 1001: "ctx-lh-bankssts"}


def test_schaefer_networks_reads_third_field():
    labels = {1: "7Networks_LH_Vis_1", 999: "7Networks_RH_Cont_PCC_1"}
    assert schaefer_networks(labels) == {1: "Vis", 999: "Cont"}


def test_desikan_labels_drops_non_regions():
    labels = {0: "Unknown", 17: "Left-Hippocampus", 1000: "ctx-lh-unknown",
              1001: "ctx-lh-bankssts", 1004: "ctx-lh-corpuscallosum",
              2035: "ctx-rh-insula", 2307: "ctx-rh-insula-lobe"}
    assert desikan_labels(labels) == {1001: "ctx-lh-bankssts", 2035: "ctx-rh-insula"}


def test_overlap_counts_ignores_voxels_outside_either_map():
    desikan = np.array([1001, 1001, 1001, 1035, 0, 17])
    schaefer = np.array([2, 2, 0, 3, 1, 1])
    counts = overlap_counts(desikan, schaefer, DESIKAN, PARCEL_NETWORKS)
    as_dict = {(r, n): v for r, n, v in counts.itertuples(index=False)}
    assert as_dict == {("ctx-lh-bankssts", "Default"): 2,
                       ("ctx-lh-insula", "SalVentAttn"): 1}


def test_overlap_counts_rejects_mismatched_grids():
    with pytest.raises(ValueError, match="grids differ"):
        overlap_counts(np.zeros(3), np.zeros(4), DESIKAN, PARCEL_NETWORKS)


def test_majority_is_taken_on_counts_pooled_over_subjects():
    def counts(rows):
        return pd.DataFrame(rows, columns=["region", "network", "n_voxels"])
    # sub-01 alone would say Vis; pooled, Default wins 7 to 5.
    per_subject = {
        "sub-01": counts([("ctx-lh-bankssts", "Vis", 5), ("ctx-lh-bankssts", "Default", 3)]),
        "sub-02": counts([("ctx-lh-bankssts", "Default", 4)]),
    }
    table = majority_networks(per_subject).set_index("region")
    row = table.loc["ctx-lh-bankssts"]
    assert row["network"] == "Default"
    assert row["network_fraction"] == pytest.approx(7 / 12)
    assert row["n_subjects"] == 2
    assert table.loc["Left-Thalamus", "network"] == "subcortex"
    assert table.loc["Right-Cerebellum-Cortex", "network"] == "cerebellum"
    assert len(table) == 1 + len(SUBCORTICAL_NETWORKS)
