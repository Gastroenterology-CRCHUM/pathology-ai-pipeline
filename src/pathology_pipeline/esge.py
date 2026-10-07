"""
ESGE post-polypectomy surveillance interval calculator.

Deterministic, rule-based implementation of ESGE surveillance criteria, confirmed
deliberately different from USMSTF in several respects (not gaps in this summary):

    - No villous/tubulovillous histology trigger for adenomas (USMSTF treats
      TVA/VA histology alone as high-risk regardless of size; ESGE does not).
    - No serrated-polyp count threshold (USMSTF has explicit count tiers for
      SSA/P; ESGE only uses size/dysplasia for serrated risk here).
    - Traditional serrated adenoma (TSA) has no separate ESGE guidance and is
      treated identically to SSA/P (same size/dysplasia rule).
    - Hyperplastic polyps (HP) never trigger ESGE surveillance in this scope
      (USMSTF has HP count/size rules; ESGE has none here).

Out of scope (same rationale as usmstf.py's exclusions):
    - Piecemeal resection of polyps >=20mm (3-6 month early repeat) - needs
      per-polyp resection-technique data this pipeline doesn't capture.
    - "First surveillance clear -> second surveillance in 5 years before
      returning to screening" - needs cross-visit history; each exam here is
      treated independently.

With those exclusions, a single exam's ESGE recommendation collapses to a binary
decision: low-risk (return to routine screening) vs. high-risk (3-year
surveillance). "Return to screening" is given a distinct qualitative label
(LOW_RISK_RETURN_TO_SCREENING) rather than an invented numeric interval, since
the guideline doesn't specify one for this case - unlike USMSTF's explicit
"10 years" for a normal colonoscopy.

Adenoma dysplasia trigger uses high-grade dysplasia only; serrated dysplasia
trigger uses any dysplasia grade (LGD or HGD) - mirroring the same adenoma-vs-
serrated asymmetry already established for USMSTF.
"""

from typing import Dict, List

from .usmstf import ADENOMA_CODES, CANCER, HGD, LGD, SSA_P, TSA, clean_size  # noqa: F401

LOW_RISK = "LOW_RISK_RETURN_TO_SCREENING"
HIGH_RISK = "3yr"


def esge_interval(polyps: List[Dict]) -> str:
    """
    Determine the ESGE-recommended surveillance category for one colonoscopy exam.

    Args:
        polyps: one dict per specimen found at this exam, each with:
            - 'codes': Set[int] of histology codes for that specimen
            - 'size_mm': Optional[float], already sentinel-cleaned (clean_size())

    Returns:
        "3yr" (high-risk), "LOW_RISK_RETURN_TO_SCREENING" (low-risk), or "CANCER"
        (outside surveillance-interval scope, different management pathway).
    """
    if any(CANCER in p["codes"] for p in polyps):
        return "CANCER"

    adenoma_count = 0
    high_risk = False

    for p in polyps:
        codes = p["codes"]
        size_ge10 = (p.get("size_mm") is not None) and p["size_mm"] >= 10

        if codes & ADENOMA_CODES:
            adenoma_count += 1
            if size_ge10 or (HGD in codes):
                high_risk = True

        # SSA/P and TSA share the same rule under ESGE (no distinct TSA guidance,
        # no adenoma-style villous-histology equivalent for serrated).
        if (SSA_P in codes) or (TSA in codes):
            if size_ge10 or (HGD in codes) or (LGD in codes):
                high_risk = True

        # HP intentionally never checked - never triggers ESGE surveillance here.

    if adenoma_count >= 5:
        high_risk = True

    return HIGH_RISK if high_risk else LOW_RISK


def patient_recommendation(polyps: List[Dict], any_diverted: bool) -> str:
    """Same diversion safety rule as usmstf.patient_recommendation."""
    if any_diverted:
        return "NEEDS_MANUAL_REVIEW"
    return esge_interval(polyps)
