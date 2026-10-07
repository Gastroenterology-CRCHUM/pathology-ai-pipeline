"""
USMSTF post-polypectomy surveillance interval calculator.

Deterministic, rule-based implementation of the 2020 US Multi-Society Task Force on
Colorectal Cancer post-polypectomy surveillance guideline (Gupta S, Lieberman D,
Anderson JC, et al. Recommendations for follow-up after colonoscopy and polypectomy:
a consensus update by the US Multi-Society Task Force on colorectal cancer.
Am J Gastroenterol. 2020;115(3):415-434), cross-validated against the task force's
own risk-stratification flowchart.

Scope, deliberately excluded (no evidence/criteria provided in the source):
    - Piecemeal resection of large polyps
    - Serrated polyposis syndrome
    - Exam-quality gating (complete-to-cecum, adequate prep, adequate ADR) - this
      calculator assumes every exam meets the "high-quality colonoscopy"
      precondition the guideline requires before these intervals apply.

Each exam is treated independently (no cross-visit history), consistent with the
source guideline's own nested follow-up sub-table.
"""

from typing import Dict, List, Optional, Set

# Pathology codes (see codebook.py)
TA, TVA, VA, TSA, SSA_P, HGD, LGD, HP, CANCER = 3, 4, 5, 6, 7, 8, 15, 2, 9

ADENOMA_CODES = {TA, TVA, VA}
HIGH_RISK_HISTOLOGY_CODES = {TVA, VA}  # villous / tubulovillous

# Codes that don't carry USMSTF risk-stratification meaning: NI/MP(1), FGP(10),
# IP(11), MC(12), LI(13), UL(14), Not applicable(77), Other(99).
NON_RISK_CODES = {1, 10, 11, 12, 13, 14, 77, 99}

SIZE_SENTINEL_VALUES = {77, 88}  # source-database sentinels: 77 = N/A, 88 = not measured

INTERVAL_ORDER = ["1yr", "3yr", "3-5yr", "5-10yr", "7-10yr", "10yr"]


def clean_size(raw_size) -> Optional[float]:
    """Convert a raw polyp-size value to mm, or None if missing/sentinel."""
    if raw_size is None:
        return None
    try:
        size = float(raw_size)
    except (TypeError, ValueError):
        return None
    if size in SIZE_SENTINEL_VALUES:
        return None
    return size


def usmstf_interval(polyps: List[Dict]) -> str:
    """
    Determine the USMSTF-recommended surveillance interval for one colonoscopy exam.

    Args:
        polyps: one dict per specimen found at this exam, each with:
            - 'codes': Set[int] of histology codes for that specimen (may be
              compound, e.g. {7, 8} for SSA/P with high-grade dysplasia)
            - 'size_mm': Optional[float], already sentinel-cleaned (use clean_size())

    Returns:
        One of "1yr", "3yr", "3-5yr", "5-10yr", "7-10yr", "10yr" (most-aggressive-
        first evaluation, first match wins), or "CANCER" if any specimen carries
        the cancer code (outside surveillance-interval scope).
    """
    if any(CANCER in p["codes"] for p in polyps):
        return "CANCER"

    adenoma_count = 0
    ssap_count = 0
    high_risk_adenoma = False
    high_risk_ssap = False
    has_tsa = False
    hp_ge10 = False

    for p in polyps:
        codes: Set[int] = p["codes"]
        size_ge10 = (p.get("size_mm") is not None) and p["size_mm"] >= 10

        if codes & ADENOMA_CODES:
            adenoma_count += 1
            if size_ge10 or (codes & HIGH_RISK_HISTOLOGY_CODES) or (HGD in codes):
                high_risk_adenoma = True

        if SSA_P in codes:
            ssap_count += 1
            # Any dysplasia grade counts for SSA/P (unlike adenomas, which
            # require high-grade specifically), per the source table's wording.
            if size_ge10 or (HGD in codes) or (LGD in codes):
                high_risk_ssap = True

        if TSA in codes:
            has_tsa = True

        if HP in codes and size_ge10:
            hp_ge10 = True

    if adenoma_count > 10:
        return "1yr"
    if (
        (5 <= adenoma_count <= 10)
        or (5 <= ssap_count <= 10)
        or high_risk_adenoma
        or high_risk_ssap
        or has_tsa
    ):
        return "3yr"
    if (3 <= adenoma_count <= 4) or (3 <= ssap_count <= 4) or hp_ge10:
        return "3-5yr"
    if 1 <= ssap_count <= 2:
        return "5-10yr"
    if 1 <= adenoma_count <= 2:
        return "7-10yr"
    return "10yr"


def patient_recommendation(polyps: List[Dict], any_diverted: bool) -> str:
    """
    Wraps usmstf_interval() with the safety rule: if any polyp for this exam was
    diverted to manual review (uncertain/conflicting extraction), the whole
    patient's recommendation is flagged for manual review rather than computed
    from partial data - an unresolved polyp could itself be high-risk.
    """
    if any_diverted:
        return "NEEDS_MANUAL_REVIEW"
    return usmstf_interval(polyps)
