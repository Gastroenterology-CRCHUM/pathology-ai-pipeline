"""
Closed vocabulary of histology codes used for polyp-level pathology extraction.

These codes correspond to the structured "polyp assessment" case-report-form fields
used as the reference standard in the associated manuscript. Codes 1-15 are specific
histology diagnoses; 77 and 99 are sentinel values (specimen not found / unclassified
"Other" finding).
"""

from typing import Dict

POLYP_CODES: Dict[int, str] = {
    1: "NI/MP - normal/mucosal prolapse",
    2: "HP - hyperplastic polyp",
    3: "TA - tubular adenoma",
    4: "TVA - tub-villous adenoma",
    5: "VA - villous adenoma",
    6: "TSA - traditional serrated adenoma",
    7: "SSA/P - sessile serrated adenoma/polyp",
    8: "HGD - high-grade dysplasia",
    9: "Ca - cancer",
    10: "FGP - Fundic gland polyp",
    11: "IP - Inflammatory polyp",
    12: "MC - Melanosis coli",
    13: "LI - Lipoma",
    14: "UL - Ulcer",
    15: "LGD - Low-grade dysplasia",
    77: "Not applicable / Not retrieved",
    99: "Other",
}
# Labels are reproduced verbatim (including the mixed casing of codes 1-9 vs.
# 10-15) from the locked pipeline's polyp_assessment code dictionary, since
# this exact text is inserted into the extraction prompt sent to the model -
# see prompt.py's format_codes_text(). Don't "clean up" the casing; it would
# silently change what the model actually sees relative to what was run for
# the manuscript.

# Codes representing a malignant or high-grade finding. Any of these triggers
# mandatory human review regardless of model confidence (see
# validation_rules.py). For polyp_assessment, HGD is always 8 and Cancer is
# always 9.
HIGH_STAKES_CODES = {8, 9}  # HGD, Cancer
