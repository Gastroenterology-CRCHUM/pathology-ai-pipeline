import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pathology_pipeline.llm_client import parse_llm_response  # noqa: E402


def test_parses_clean_json_response():
    response = '''Here is my analysis.
{"specimen_identified": "C: Rectal polyp", "codes": [3], "diagnosis_text": "Tubular adenoma", "patho_polyp_other": "", "reasoning": "Matched by segment"}
'''
    parsed = parse_llm_response(response)
    assert parsed.codes == [3]
    assert parsed.specimen_found is True
    assert parsed.specimen_identified == "C: Rectal polyp"
    assert parsed.diagnosis_text == "Tubular adenoma"


def test_drops_hallucinated_codes_not_in_codebook():
    response = '{"specimen_identified": "A", "codes": [3, 42], "diagnosis_text": "x", "patho_polyp_other": "", "reasoning": "x"}'
    parsed = parse_llm_response(response)
    assert parsed.codes == [3]


def test_specimen_not_found_variants_are_recognized():
    for phrase in ["Not found", "none", "N/A", ""]:
        response = f'{{"specimen_identified": "{phrase}", "codes": [77], "diagnosis_text": "", "patho_polyp_other": "", "reasoning": ""}}'
        parsed = parse_llm_response(response)
        assert parsed.specimen_found is False


def test_falls_back_to_bare_numbers_when_json_missing():
    response = "The specimen matches code 3 based on the tubular adenoma finding."
    parsed = parse_llm_response(response)
    assert parsed.codes == [3]
    assert parsed.specimen_found is True


def test_falls_back_to_99_when_nothing_parseable():
    response = "I could not determine a finding for this report."
    parsed = parse_llm_response(response)
    assert parsed.codes == [99]
