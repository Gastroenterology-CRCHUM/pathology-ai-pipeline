import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pathology_pipeline.validation_rules import (  # noqa: E402
    apply_validation_rules,
    detect_conflicts,
    is_high_stakes,
    is_ihc_report,
)


def test_high_stakes_hgd_diverts_regardless_of_confidence():
    result = apply_validation_rules(codes=[8], specimen_found=True, full_text="High-grade dysplasia.")
    assert result.diverted is True
    assert result.codes == [77]
    assert "Mandatory high-stakes review" in result.diversion_reason


def test_high_stakes_cancer_diverts():
    result = apply_validation_rules(codes=[9], specimen_found=True, full_text="Invasive adenocarcinoma.")
    assert result.diverted is True


def test_compound_hgd_with_adenoma_still_diverts():
    result = apply_validation_rules(codes=[4, 8], specimen_found=True, full_text="")
    assert result.diverted is True


def test_impossible_combination_hp_and_ta_diverts():
    has_impossible, reason, _, _ = detect_conflicts([2, 3])
    assert has_impossible is True
    assert "Impossible combination" in reason
    result = apply_validation_rules(codes=[2, 3], specimen_found=True, full_text="")
    assert result.diverted is True
    assert "Impossible combination" in result.diversion_reason


def test_normal_excludes_any_pathological_finding():
    has_impossible, _, _, _ = detect_conflicts([1, 3])
    assert has_impossible is True


def test_multi_specimen_indicator_diverts_as_warning_not_conflict():
    # {3, 7} (TA + SSA/P) is a multi-specimen indicator pair but is NOT in any
    # mutually-exclusive group, so it must hit rule 3, not rule 2.
    has_impossible, _, has_multi, _ = detect_conflicts([3, 7])
    assert has_impossible is False
    assert has_multi is True
    result = apply_validation_rules(codes=[3, 7], specimen_found=True, full_text="")
    assert result.diverted is True
    assert "Multiple specimen types detected" in result.diversion_reason


def test_ihc_with_no_specimen_diverts():
    text = "Immunohistochemistry for mismatch repair proteins MLH1, MSH2, MSH6, PMS2."
    assert is_ihc_report(text) is True
    result = apply_validation_rules(codes=[77], specimen_found=False, full_text=text)
    assert result.diverted is True
    assert "IHC/molecular report with no specimen identified" in result.diversion_reason


def test_ihc_keywords_with_specimen_found_does_not_divert_on_ihc_rule():
    # Rule 4 requires BOTH no specimen found AND IHC language - specimen found
    # means this rule does not fire (a different rule might, independently).
    text = "Immunohistochemistry performed; MLH1 intact nuclear staining."
    result = apply_validation_rules(codes=[3], specimen_found=True, full_text=text)
    assert result.diverted is False


def test_no_specimen_without_other_trigger_is_accepted_not_diverted():
    # No standalone "no specimen" rule: if no specimen found and none of the
    # other three rules fire, the model's own code-77 answer is accepted as-is.
    result = apply_validation_rules(codes=[77], specimen_found=False, full_text="Unrelated report text.")
    assert result.diverted is False
    assert result.codes == [77]


def test_clean_single_code_accepted_high_confidence():
    result = apply_validation_rules(codes=[3], specimen_found=True, full_text="Tubular adenoma.")
    assert result.diverted is False
    assert result.confidence == "high"
    assert result.codes == [3]


def test_is_high_stakes_false_for_benign_codes():
    assert is_high_stakes([1, 2, 3, 10, 99]) is False


def test_rule_priority_high_stakes_beats_impossible_combination():
    # Codes include both a high-stakes code and an impossible-combination pair;
    # high-stakes must win (it is checked first).
    result = apply_validation_rules(codes=[2, 3, 8], specimen_found=True, full_text="")
    assert result.diverted is True
    assert "Mandatory high-stakes review" in result.diversion_reason
