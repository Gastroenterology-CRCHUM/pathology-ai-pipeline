import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pathology_pipeline.esge import esge_interval  # noqa: E402


def poly(codes, size_mm=None):
    return {"codes": set(codes), "size_mm": size_mm}


def test_no_polyps_is_low_risk():
    assert esge_interval([]) == "LOW_RISK_RETURN_TO_SCREENING"


def test_cancer_overrides_everything():
    assert esge_interval([poly([9])]) == "CANCER"


def test_small_tubular_adenoma_is_low_risk():
    assert esge_interval([poly([3], size_mm=4)]) == "LOW_RISK_RETURN_TO_SCREENING"


def test_tubulovillous_histology_alone_is_NOT_high_risk_under_esge():
    # Deliberate divergence from USMSTF: ESGE has no villous-histology trigger.
    assert esge_interval([poly([4], size_mm=3)]) == "LOW_RISK_RETURN_TO_SCREENING"


def test_adenoma_with_high_grade_dysplasia_is_high_risk():
    assert esge_interval([poly([3, 8], size_mm=3)]) == "3yr"


def test_adenoma_ge_10mm_is_high_risk():
    assert esge_interval([poly([3], size_mm=10)]) == "3yr"


def test_five_or_more_adenomas_is_high_risk_regardless_of_size():
    polyps = [poly([3], size_mm=2) for _ in range(5)]
    assert esge_interval(polyps) == "3yr"


def test_four_adenomas_is_still_low_risk_no_count_threshold_below_five():
    polyps = [poly([3], size_mm=2) for _ in range(4)]
    assert esge_interval(polyps) == "LOW_RISK_RETURN_TO_SCREENING"


def test_ssap_with_any_dysplasia_is_high_risk():
    assert esge_interval([poly([7, 15], size_mm=2)]) == "3yr"


def test_tsa_follows_same_rule_as_ssap():
    assert esge_interval([poly([6, 8], size_mm=2)]) == "3yr"


def test_hp_never_triggers_esge_surveillance():
    assert esge_interval([poly([2], size_mm=25)]) == "LOW_RISK_RETURN_TO_SCREENING"


def test_diverted_polyp_forces_manual_review():
    from pathology_pipeline.esge import patient_recommendation
    assert patient_recommendation([poly([3], size_mm=4)], any_diverted=True) == "NEEDS_MANUAL_REVIEW"
