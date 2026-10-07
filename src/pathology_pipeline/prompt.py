"""
Exact extraction prompt used in the locked pipeline (as of the manuscript's lock
date). Reproduced verbatim from the submitted manuscript's supplementary materials.
"""

from .codebook import POLYP_CODES
from .vocabulary import OTHER_VOCABULARY

PROMPT_TEMPLATE = """You are a medical pathology report analyzer. Your task is to extract the pathology finding for ONE SPECIFIC specimen from a report that may contain MULTIPLE specimens.

PATHOLOGY REPORT:
{full_text}

=== CRITICAL: TARGET SPECIMEN IDENTIFICATION ===
You must find and extract pathology ONLY for the specimen matching ALL of these criteria:
{context_text}

Look for specimen identifiers like: {hints_text}

IMPORTANT RULES:
1. This report may contain MULTIPLE specimens (labeled A, B, C, etc. or by location)
2. You must identify which specimen matches the target criteria above
3. Extract pathology ONLY for that ONE matching specimen
4. IGNORE all other specimens in the report
5. If the segment is "Rectum" and polyp number is 3, find the specimen labeled as "Rectal polyp" or similar

=== AVAILABLE PATHOLOGY CODES ({form_type}) ===
{codes_text}

=== RESPONSE INSTRUCTIONS ===
1. First, identify which specimen in the report matches the target (e.g., "Specimen C: Rectal polyp")
2. Extract the pathology finding for ONLY that specimen
3. Return the numeric code(s) that apply to THAT specimen only
4. If multiple findings apply to the SAME specimen, separate codes with commas
5. If the specimen is not found or not retrieved, return 77
6. If the finding doesn't match any code, return 99
7. FRAGMENT LANGUAGE: If the diagnosis uses phrasing such as "fragments of X", "pieces of X", "portions of X", or "tissue fragments consistent with X", treat this as equivalent to a diagnosis of X and assign the corresponding code. Do NOT return 77 or 99 solely because the specimen is described as fragments.
8. COMPOUND FINDINGS - ADDITIVE, NOT EXCLUSIVE: If a single specimen's diagnosis combines a finding that matches one of the numbered codes above (e.g., inflammatory polyp, NI/MP) with a SEPARATE finding that matches one of the OTHER (99) EXAMPLES in rule 9 below (e.g., "lymphoid follicle", "hamartomatous polyp", "leiomyoma of the muscularis mucosae"), you must return BOTH codes together - the numbered code AND code 99 (Other) - do not pick only one just because a numbered code is available. For example, a diagnosis of "Inflammatory polyp/hamartomatous polyp" should be coded as BOTH the inflammatory-polyp code AND 99 (Other, with "hamartomatous polyp" as the Other finding), not the inflammatory-polyp code alone.
9. OTHER (99) EXAMPLES: The following findings, if they are the specimen's diagnosis (alone or combined with another finding), should be coded 99 (Other): {other_vocabulary}
10. WHEN UNCERTAIN, PREFER OTHER (99): If a diagnosis does not clearly and specifically match one of the numbered codes, return 99 (Other) with the diagnosis text - do not force-fit it into the closest-sounding numbered code just because it seems related. For example: a hamartomatous polyp is NOT a tubular adenoma; intestinal metaplasia is NOT a hyperplastic polyp; a leiomyoma is NOT a lipoma; an intestinal-type adenoma is not automatically a tubular adenoma unless the report itself calls it that. When a finding in rule 9's list applies, use 99 even if another code seems superficially similar.
11. INSUFFICIENT/INADEQUATE TISSUE: If the report states the tissue sample is insufficient or inadequate for diagnosis, but a specimen WAS submitted and received (i.e. the specimen itself was found, just not diagnostic), code this as 99 (Other) with "insufficient tissue for diagnosis" as the finding. Do NOT use code 77 for this - code 77 is reserved for cases where no matching specimen could be found in the report at all.

RESPONSE FORMAT (JSON):
{{
  "specimen_identified": "the exact specimen label/description you matched (e.g., 'C: Rectal polyp')",
  "codes": [list of integer codes for THIS specimen only],
  "diagnosis_text": "the exact diagnosis text from the report for this specimen",
  "patho_polyp_other": "if code 99 is selected, the single closest-matching term from the OTHER (99) EXAMPLES list in rule 9, reproduced EXACTLY as written there (e.g. 'lymphoid follicle') - do not paraphrase, reword, or add words. Always choose one of the listed terms when code 99 applies, even if the match is imperfect - never invent a new term and never copy sentences from the report. Leave empty if code 99 was not selected.",
  "reasoning": "brief explanation of how you identified the correct specimen"
}}

JSON RESPONSE:"""


def format_codes_text(code_dict=None) -> str:
    """
    Render the numbered code list for insertion into the prompt.

    Each line is prefixed with two spaces and codes are in dict insertion
    order (not re-sorted) - both reproduced exactly from the locked pipeline,
    since this text is inserted verbatim into the prompt actually sent to the
    model. POLYP_CODES is already defined in ascending order, so this only
    matters if a caller passes a differently-ordered code_dict.
    """
    code_dict = code_dict or POLYP_CODES
    return "\n".join(f"  {code}: {label}" for code, label in code_dict.items())


def build_prompt(
    full_text: str,
    context_text: str,
    hints_text: str,
    form_type: str = "polyp",
    code_dict=None,
) -> str:
    """
    Build the full extraction prompt for one polyp-level target.

    Args:
        full_text: the complete pathology report text.
        context_text: human-readable description of the target specimen's
            identifying criteria (segment, local specimen order, biopsy number).
        hints_text: example specimen-label phrasings to look for.
        form_type: label shown in the "AVAILABLE PATHOLOGY CODES" header.
        code_dict: code -> label mapping (defaults to codebook.POLYP_CODES).
    """
    return PROMPT_TEMPLATE.format(
        full_text=full_text,
        context_text=context_text,
        hints_text=hints_text,
        form_type=form_type,
        codes_text=format_codes_text(code_dict),
        other_vocabulary=OTHER_VOCABULARY,
    )
