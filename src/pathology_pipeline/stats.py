"""
Statistical analysis utilities used to generate the main performance results.

Implements:
    - per-category precision / recall / F1 ("automated" convention: diverted
      targets are excluded from the denominator, consistent with "automated
      accuracy" - see `automated_recall`)
    - micro- and macro-averaged F1, with the macro average computed only over
      categories that have a *defined* F1 (categories where mandatory
      high-stakes diversion structurally prevents any non-diverted true
      positive - e.g. high-grade dysplasia, cancer - are excluded from the
      macro average rather than scored as 0; this must be stated explicitly
      wherever macro-F1 is reported, see README "Statistical methodology")
    - cluster bootstrap confidence intervals, resampling by a cluster identifier
      (e.g. patient) rather than by row, so that multiple polyps/targets from
      the same patient move together in each resample
    - a Wilson score interval for the zero-event edge case where a cluster
      bootstrap would be degenerate (e.g. 0/n diversions)

None of this module touches real data; it operates on whatever label arrays /
dataframes the caller supplies.
"""

import math
from typing import Dict, List, Optional, Sequence, Set

import numpy as np
import pandas as pd


def automated_recall(y_true: Sequence, y_pred: Sequence, diverted: Sequence[bool], positive_label) -> Optional[float]:
    """
    Recall for `positive_label`, conditional on automated classification: targets
    routed to human review (diverted=True) are excluded from the denominator,
    consistent with "automated accuracy" - a target the pipeline declined to
    classify automatically is not a miss by the classifier, it's a deferral.

    Returns None if there are no non-diverted true-positive-eligible targets
    (undefined recall), e.g. a category under mandatory diversion.
    """
    eligible = [
        (t, p) for t, p, d in zip(y_true, y_pred, diverted) if not d
    ]
    positives = [t for t, _ in eligible if t == positive_label]
    if not positives:
        return None
    correct = sum(1 for t, p in eligible if t == positive_label and p == positive_label)
    return correct / len(positives)


def precision_recall_f1(y_true: Sequence, y_pred: Sequence, label) -> Dict[str, Optional[float]]:
    """Standard (non-diversion-aware) precision/recall/F1 for one label."""
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)

    precision = tp / (tp + fp) if (tp + fp) > 0 else None
    recall = tp / (tp + fn) if (tp + fn) > 0 else None
    if precision is None or recall is None or (precision + recall) == 0:
        f1 = None
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return {"precision": precision, "recall": recall, "f1": f1, "support": tp + fn}


def micro_f1(y_true: Sequence, y_pred: Sequence, labels: Sequence) -> float:
    """Micro-averaged F1 across `labels` (pools TP/FP/FN before computing)."""
    tp = fp = fn = 0
    for label in labels:
        tp += sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
        fp += sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
        fn += sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def macro_f1(
    y_true: Sequence,
    y_pred: Sequence,
    labels: Sequence,
    exclude_undefined: bool = True,
) -> Dict[str, object]:
    """
    Macro-averaged F1 across `labels`.

    exclude_undefined=True (the convention used for the headline results):
        categories with no defined F1 (no eligible positives to compute recall
        from - e.g. a category under mandatory diversion, so no non-diverted
        true positive can ever exist) are dropped from the average rather than
        scored as 0. This must always be reported alongside which labels were
        excluded and why - silently dropping categories would overstate
        performance.
    """
    per_label = {label: precision_recall_f1(y_true, y_pred, label) for label in labels}
    if exclude_undefined:
        included = {l: r for l, r in per_label.items() if r["f1"] is not None}
    else:
        included = {l: {**r, "f1": r["f1"] if r["f1"] is not None else 0.0} for l, r in per_label.items()}

    if not included:
        return {"macro_f1": None, "per_label": per_label, "included_labels": [], "excluded_labels": list(labels)}

    macro = sum(r["f1"] for r in included.values()) / len(included)
    return {
        "macro_f1": macro,
        "per_label": per_label,
        "included_labels": list(included.keys()),
        "excluded_labels": [l for l in labels if l not in included],
    }


def cluster_bootstrap_ci(
    df: pd.DataFrame,
    cluster_col: str,
    statistic_fn,
    n_resamples: int = 5000,
    alpha: float = 0.05,
    random_state: Optional[int] = None,
) -> Dict[str, float]:
    """
    Cluster bootstrap confidence interval.

    Resamples whole clusters (e.g. patients, identified by `cluster_col`) with
    replacement - not individual rows - so that correlated observations from
    the same cluster (e.g. multiple polyps from one patient) move together,
    avoiding the artificially narrow CIs that row-level bootstrapping would
    produce for clustered data.

    Args:
        df: one row per observation (e.g. per polyp-level target).
        cluster_col: column identifying the cluster (e.g. patient id).
        statistic_fn: callable(df_resampled) -> float, the statistic to
            bootstrap (e.g. a recall or F1 computed on the resampled rows).
        n_resamples: number of bootstrap resamples (5000 used throughout the
            manuscript's analyses).
        alpha: 1 - confidence level (0.05 -> 95% CI).
        random_state: seed for reproducibility; None for non-reproducible draws.

    Returns:
        {"estimate": point estimate on the full data, "ci_low": ..., "ci_high": ...}
    """
    rng = np.random.default_rng(random_state)
    clusters = df[cluster_col].unique()
    n_clusters = len(clusters)

    point_estimate = statistic_fn(df)

    boot_stats = []
    for _ in range(n_resamples):
        sampled_clusters = rng.choice(clusters, size=n_clusters, replace=True)
        resampled = pd.concat(
            [df[df[cluster_col] == c] for c in sampled_clusters],
            ignore_index=True,
        )
        boot_stats.append(statistic_fn(resampled))

    boot_stats = np.array([b for b in boot_stats if b is not None])
    ci_low = float(np.percentile(boot_stats, 100 * (alpha / 2)))
    ci_high = float(np.percentile(boot_stats, 100 * (1 - alpha / 2)))
    return {"estimate": point_estimate, "ci_low": ci_low, "ci_high": ci_high}


def wilson_score_interval(successes: int, n: int, alpha: float = 0.05) -> Dict[str, float]:
    """
    Wilson score interval for a binomial proportion.

    Used specifically for genuinely zero-event cells (e.g. 0/282 diversions in
    a held-out cohort), where a cluster/row bootstrap would be degenerate
    (every resample also has 0 events, giving a collapsed, uninformative CI).
    """
    if n == 0:
        return {"estimate": None, "ci_low": None, "ci_high": None}

    z = 1.959963984540054 if abs(alpha - 0.05) < 1e-9 else _z_for_alpha(alpha)
    p_hat = successes / n
    denom = 1 + z**2 / n
    center = (p_hat + z**2 / (2 * n)) / denom
    half_width = (z * math.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * n)) / n)) / denom
    return {
        "estimate": p_hat,
        "ci_low": max(0.0, center - half_width),
        "ci_high": min(1.0, center + half_width),
    }


def _z_for_alpha(alpha: float) -> float:
    """Two-sided z critical value via the inverse normal CDF (no scipy dependency)."""
    # Acklam's algorithm (rational approximation), accurate to ~1.15e-9.
    p = 1 - alpha / 2
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    p_low = 0.02425
    p_high = 1 - p_low
    if p < p_low:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p <= p_high:
        q = p - 0.5
        r = q * q
        return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
               (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
    q = math.sqrt(-2 * math.log(1 - p))
    return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
            ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
