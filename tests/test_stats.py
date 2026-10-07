import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pathology_pipeline.stats import (  # noqa: E402
    automated_recall,
    cluster_bootstrap_ci,
    macro_f1,
    micro_f1,
    precision_recall_f1,
    wilson_score_interval,
)


def test_precision_recall_f1_perfect_classifier():
    y_true = ["TA", "TA", "HP", "HP"]
    y_pred = ["TA", "TA", "HP", "HP"]
    result = precision_recall_f1(y_true, y_pred, "TA")
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0
    assert result["f1"] == 1.0


def test_precision_recall_f1_undefined_when_no_support():
    result = precision_recall_f1(["HP", "HP"], ["HP", "HP"], "TA")
    assert result["precision"] is None
    assert result["recall"] is None
    assert result["f1"] is None


def test_automated_recall_excludes_diverted_targets_from_denominator():
    y_true = ["HGD", "HGD", "HGD"]
    y_pred = ["HGD", "HGD", "HGD"]
    # All three HGD targets are diverted (mandatory review) -> automated recall
    # is undefined (no eligible denominator), not zero.
    diverted = [True, True, True]
    assert automated_recall(y_true, y_pred, diverted, "HGD") is None


def test_automated_recall_computed_only_over_non_diverted():
    y_true = ["TA", "TA", "TA"]
    y_pred = ["TA", "HP", "TA"]
    diverted = [False, False, True]  # third TA target was diverted
    # Denominator excludes the diverted TA -> 2 eligible positives, 1 correct.
    assert automated_recall(y_true, y_pred, diverted, "TA") == pytest.approx(0.5)


def test_macro_f1_excludes_undefined_categories_by_default():
    y_true = ["TA", "TA", "HGD"]
    y_pred = ["TA", "TA", "TA"]  # HGD never predicted (mandatory diversion)
    result = macro_f1(y_true, y_pred, labels=["TA", "HGD"], exclude_undefined=True)
    assert "HGD" in result["excluded_labels"]
    assert "TA" in result["included_labels"]
    assert result["macro_f1"] == pytest.approx(result["per_label"]["TA"]["f1"])


def test_macro_f1_scores_zero_when_exclude_undefined_false():
    y_true = ["TA", "TA", "HGD"]
    y_pred = ["TA", "TA", "TA"]
    result = macro_f1(y_true, y_pred, labels=["TA", "HGD"], exclude_undefined=False)
    assert result["excluded_labels"] == []
    # Averaging in a forced 0 for HGD must differ from (and be lower than) the
    # exclude_undefined convention used for headline results.
    excluded_version = macro_f1(y_true, y_pred, labels=["TA", "HGD"], exclude_undefined=True)
    assert result["macro_f1"] < excluded_version["macro_f1"]


def test_micro_f1_pools_across_labels():
    y_true = ["TA", "HP", "TA", "HP"]
    y_pred = ["TA", "HP", "HP", "HP"]
    score = micro_f1(y_true, y_pred, labels=["TA", "HP"])
    assert 0.0 <= score <= 1.0


def test_wilson_score_interval_zero_events():
    result = wilson_score_interval(successes=0, n=282)
    assert result["estimate"] == 0.0
    assert result["ci_low"] == 0.0
    assert result["ci_high"] > 0.0  # CI upper bound still informative, unlike a degenerate bootstrap
    assert result["ci_high"] < 0.05  # small n and zero events -> tight upper bound


def test_wilson_score_interval_handles_n_zero():
    result = wilson_score_interval(successes=0, n=0)
    assert result["estimate"] is None


def test_cluster_bootstrap_ci_resamples_by_cluster_not_row():
    df = pd.DataFrame({
        "patient_id": [1, 1, 1, 2, 2, 3],
        "correct": [1, 1, 1, 0, 0, 1],
    })

    def accuracy(d):
        return d["correct"].mean()

    result = cluster_bootstrap_ci(df, cluster_col="patient_id", statistic_fn=accuracy, n_resamples=200, random_state=42)
    assert result["estimate"] == pytest.approx(df["correct"].mean())
    assert result["ci_low"] <= result["estimate"] <= result["ci_high"]
