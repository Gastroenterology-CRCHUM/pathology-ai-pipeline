"""
Deterministic post-extraction validation rules.

Applied to every model output, in order (first match wins). This is the exact
logic used in the locked pipeline described in the manuscript.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple

from .codebook import HIGH_STAKES_CODES, POLYP_CODES

# --- Rule 2: mutually exclusive code combinations (impossible) ---------------
MUTUALLY_EXCLUSIVE_GROUPS = [
    # Normal/MP excludes any pathological finding
    ({1}, {2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15}),
    # Conventional adenoma types - one architectural type per polyp
    ({3}, {4, 5}),  # TA excludes TVA, VA
    ({4}, {5}),     # TVA excludes VA
    # HP vs adenomas - fundamentally different histologies
    ({2}, {3, 4, 5}),
    # Serrated polyp types - distinct entities
    ({6}, {7}),   # TSA excludes SSA/P
    ({2}, {7}),   # HP excludes SSA/P
    ({2}, {6}),   # HP excludes TSA
    # Lipoma (submucosal) vs epithelial polyps - different tissue layers
    ({13}, {2, 3, 4, 5, 6, 7, 10, 11}),
]

# --- Rule 3: combinations suggesting multiple specimens in one container -----
MULTI_SPECIMEN_INDICATORS = [
    {2, 3}, {2, 4}, {2, 5}, {2, 6}, {2, 7},
    {3, 7}, {4, 7}, {5, 7}, {6, 7}, {3, 6},
    {10, 3}, {10, 7},
]

# --- Rule 4: IHC/molecular-report keywords ------------------------------------
IHC_KEYWORDS = [
    "immunohistochemical analysis",
    "immunohistochemistry",
    "immunostaining",
    "mismatch repair",
    "MMR proteins",
    "MMR",
    "nuclear staining",
    "nuclear labeling",
    "MLH1",
    "MSH2",
    "MSH6",
    "PMS2",
    "loss of nuclear immunostaining",
    "absence of protein expression",
    "intact nuclear staining",
    "intact nuclear labeling",
    "Lynch syndrome",
    "HNPCC",
    "MLH1 promoter methylation",
    "hypermethylation",
]


@dataclass
class ExtractionResult:
    codes: List[int]
    labels: List[str]
    specimen_identified: str
    specimen_found: bool
    diagnosis_text: str = ""
    other_text: Optional[str] = None
    confidence: str = "high"
    diverted: bool = False
    diversion_reason: Optional[str] = None


def is_high_stakes(codes: List[int]) -> bool:
    """Any candidate high-grade dysplasia or cancer code -> mandatory review."""
    return any(c in HIGH_STAKES_CODES for c in codes)


def detect_conflicts(codes: List[int]) -> Tuple[bool, Optional[str], bool, Optional[str]]:
    """
    Check extracted codes for impossible combinations or multi-specimen indicators.

    Returns (has_impossible, impossible_reason, has_multi_specimen, warning_reason).
    """
    if len(codes) <= 1:
        return False, None, False, None

    code_set = set(codes)

    for group_a, group_b in MUTUALLY_EXCLUSIVE_GROUPS:
        in_a = code_set & group_a
        in_b = code_set & group_b
        if in_a and in_b:
            labels_a = [POLYP_CODES.get(c, f"Code {c}") for c in in_a]
            labels_b = [POLYP_CODES.get(c, f"Code {c}") for c in in_b]
            reason = f"Impossible combination: {', '.join(labels_a)} + {', '.join(labels_b)}"
            return True, reason, False, None

    for indicator_set in MULTI_SPECIMEN_INDICATORS:
        hit = code_set & indicator_set
        if len(hit) >= 2:
            labels = [POLYP_CODES.get(c, f"Code {c}") for c in hit]
            reason = f"Multiple specimen types detected (possible multi-polyp pot): {', '.join(labels)}"
            return False, None, True, reason

    return False, None, False, None


def is_ihc_report(text: str) -> bool:
    """Heuristic: does this report look like an IHC/molecular addendum?"""
    if not text:
        return False
    text_upper = text.upper()
    return any(kw.upper() in text_upper for kw in IHC_KEYWORDS)


def apply_validation_rules(
    codes: List[int],
    specimen_found: bool,
    full_text: str,
) -> ExtractionResult:
    """
    Apply the four deterministic validation rules to a raw model extraction,
    in order (first match wins). Returns the final ExtractionResult: either the
    original extraction (accepted) or a diverted result (code 77, flagged for
    human review) with the reason recorded.
    """
    labels = [POLYP_CODES.get(c, f"Unknown ({c})") for c in codes]
    has_impossible, impossible_reason, has_multi, multi_reason = detect_conflicts(codes)

    if is_high_stakes(codes):
        return ExtractionResult(
            codes=[77], labels=["Not applicable / Not retrieved"],
            specimen_identified="", specimen_found=specimen_found,
            confidence="low", diverted=True,
            diversion_reason=f"Mandatory high-stakes review: model extracted {labels}",
        )
    if has_impossible:
        return ExtractionResult(
            codes=[77], labels=["Not applicable / Not retrieved"],
            specimen_identified="", specimen_found=specimen_found,
            confidence="low", diverted=True,
            diversion_reason=impossible_reason,
        )
    if has_multi:
        return ExtractionResult(
            codes=[77], labels=["Not applicable / Not retrieved"],
            specimen_identified="", specimen_found=specimen_found,
            confidence="low", diverted=True,
            diversion_reason=multi_reason,
        )
    if (not specimen_found) and is_ihc_report(full_text):
        return ExtractionResult(
            codes=[77], labels=["Not applicable / Not retrieved"],
            specimen_identified="", specimen_found=specimen_found,
            confidence="low", diverted=True,
            diversion_reason="IHC/molecular report with no specimen identified",
        )

    confidence = "high" if (specimen_found and not has_impossible and not has_multi) else "medium"
    return ExtractionResult(
        codes=codes, labels=labels, specimen_identified="",
        specimen_found=specimen_found, confidence=confidence, diverted=False,
    )
