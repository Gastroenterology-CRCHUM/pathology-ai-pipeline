"""
Specimen-matching logic, including the local segment-order correction.

Background: the clinical database assigns each polyp a global, procedure-level
number (e.g. "polyp #9"), but pathology reports typically number specimens
*locally within each anatomical segment* (e.g. "sigmoid polyp no. 2", "second
sigmoid polyp"). Matching on the global number alone causes the extraction
model to grab the wrong polyp's diagnosis whenever a patient has more than one
polyp in the same segment. `add_local_segment_order()` recomputes each
polyp's position within its own segment ("local segment order") so that
value - not the global number - is passed to the extraction model as the
specimen-identifying hint.

Scoped to polyp_assessment only (this manuscript's scope): other forms in the
original pipeline (biopsy_assessment, EMR, Barrett's, IBD biopsies) have their
own specimen-identification fields (e.g. biopsy_number, keyword-based margin/
base matching) that don't apply to polyp_assessment targets and are not
reproduced here.
"""

from typing import Any, List, Optional, Tuple

import pandas as pd

# Anatomical segment name aliases (English/French spelling variants and
# abbreviations seen in reports), used to normalize a segment name for
# matching and to generate additional specimen-identification hints for the
# extraction prompt. Reproduced in full from the locked pipeline (it's
# colonoscopy/EGD terminology, not patient data) even though EGD segments are
# out of scope for a colon-polyp surveillance analysis, for completeness.
SEGMENT_ALIASES = {
    # Colonoscopy segments
    "terminal ileum": ["terminal ileum", "ti", "ileum", "iléon terminal"],
    "caecum": ["caecum", "cecum", "caecal", "cæcum"],
    "ascending": ["ascending", "ascendant", "right colon", "côlon droit"],
    "hepatic flexure": ["hepatic flexure", "hepatic", "angle hépatique"],
    "transverse": ["transverse", "côlon transverse"],
    "splenic flexure": ["splenic flexure", "splenic", "angle splénique"],
    "descending": ["descending", "descendant", "left colon", "côlon gauche"],
    "sigmoid": ["sigmoid", "sigmoïde", "sigmoidal"],
    "rectum": ["rectum", "rectal"],
    "pouch": ["pouch", "poche", "j-pouch", "ileal pouch"],
    # EGD segments (polyp_assessment also covers EGD-found polyps for some
    # eligibility groups; out of scope for a colon-surveillance analysis, kept
    # here only because normalize_segment() is shared logic)
    "jejunum": ["jejunum", "jéjunum"],
    "d4": ["d4", "fourth duodenum", "4th duodenum", "duodenal bx", "duodenal biopsy", "duodenal biopsies"],
    "d3": ["d3", "third duodenum", "3rd duodenum", "duodenal bx", "duodenal biopsy", "duodenal biopsies"],
    "d2": ["d2", "second duodenum", "2nd duodenum", "duodenal bx", "duodenal biopsy", "duodenal biopsies"],
    "bulb": ["bulb", "bulbe", "duodenal bulb", "duodenal bx", "duodenal biopsy", "duodenal biopsies"],
    "pylorus": ["pylorus", "pylore", "pyloric"],
    "antrum": ["antrum", "antre", "antral"],
    "body": ["body", "corps", "gastric body", "corpus", "gastric corpus"],
    "fundus": ["fundus", "fundique"],
    "cardia": ["cardia", "cardiaque"],
    "esophagus": ["esophagus", "oesophagus", "œsophage", "esophageal"],
}


def normalize_segment(segment: Optional[Any]) -> Optional[str]:
    """Normalize a segment name to its canonical SEGMENT_ALIASES key, if known."""
    if segment is None or (isinstance(segment, float) and pd.isna(segment)):
        return None

    segment_str = str(segment).lower().strip()
    if segment_str == "" or segment_str == "nan":
        return None

    for canonical, aliases in SEGMENT_ALIASES.items():
        if segment_str in [a.lower() for a in aliases]:
            return canonical

    return segment_str


def add_local_segment_order(
    targets: pd.DataFrame,
    record_col: str = "record_id",
    segment_col: str = "segment",
    global_number_col: str = "polyp_number",
) -> pd.DataFrame:
    """
    Add a `local_segment_order` column to a dataframe of polyp-level targets.

    For each (record, segment) group, targets are sorted by their global polyp
    number and assigned a 1-indexed position within that segment. This local
    position - not the global number - should be used when building the
    extraction prompt's specimen-identification context (see
    build_specimen_context() below).

    Args:
        targets: one row per polyp-level target. Must contain record_col,
            segment_col, and global_number_col.
        record_col: column identifying the procedure/record.
        segment_col: column identifying the anatomical segment.
        global_number_col: column with the database's global, procedure-level
            polyp number.

    Returns:
        A copy of `targets` with an added `local_segment_order` column (int,
        1-indexed within each (record, segment) group).
    """
    targets = targets.copy()
    targets["local_segment_order"] = None

    for (_, _), group in targets.groupby([record_col, segment_col]):
        group_sorted = group.sort_values(global_number_col)
        for local_order, idx in enumerate(group_sorted.index, start=1):
            targets.at[idx, "local_segment_order"] = local_order

    return targets


def build_specimen_context(
    segment: Optional[str],
    polyp_number: Optional[int],
) -> Tuple[str, str]:
    """
    Build the extraction prompt's `context_text` and `hints_text` for one
    polyp_assessment target.

    `polyp_number` here must already be the *local segment order* when one is
    available (falling back to the original global polyp number only when a
    target has no segment, so no local order could be computed) - see
    add_local_segment_order(). This mirrors the locked pipeline exactly: it
    passes `local_segment_order` as the `polyp_number` argument into this same
    context-building logic, not a separately-shaped hint.

    Args:
        segment: the target's anatomical segment (raw, un-normalized).
        polyp_number: the local segment order (or global number fallback).

    Returns:
        (context_text, hints_text) - the exact strings to interpolate into
        PROMPT_TEMPLATE's {context_text} and {hints_text} placeholders.
    """
    context_parts: List[str] = []
    identification_hints: List[str] = []

    if segment:
        context_parts.append(f"- Anatomical segment: {segment}")
        identification_hints.append(f'"{segment}"')
        normalized_segment = normalize_segment(segment)
        if normalized_segment and normalized_segment in SEGMENT_ALIASES:
            for alias in SEGMENT_ALIASES[normalized_segment]:
                if alias.lower() != segment.lower():
                    identification_hints.append(f'"{alias}"')

    if polyp_number is not None:
        context_parts.append(f"- Polyp number: {polyp_number}")
        identification_hints.append(f'"polyp #{polyp_number}"')
        identification_hints.append(f'"polyp No. {polyp_number}"')
        identification_hints.append(f'"polyp {polyp_number}"')

    context_text = "\n".join(context_parts) if context_parts else "No specific context"
    hints_text = ", ".join(identification_hints) if identification_hints else "N/A"

    return context_text, hints_text
