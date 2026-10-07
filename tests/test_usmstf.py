import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pathology_pipeline.usmstf import clean_size, usmstf_interval  # noqa: E402


def poly(codes, size_mm=None):
    return {"codes": set(codes), "size_mm": size_mm}


def test_no_polyps_is_normal_interval():
    assert usmstf_interval([]) == "10yr"


def test_cancer_overrides_everything():
    assert usmstf_interval([poly([9]), poly([3], size_mm=20)]) == "CANCER"


def test_single_small_tubular_adenoma_is_7_10yr():
    assert usmstf_interval([poly([3], size_mm=4)]) == "7-10yr"


def test_tubulovillous_histology_alone_is_high_risk_regardless_of_size():
    # USMSTF-specific: TVA/VA histology triggers high-risk even if small.
    assert usmstf_interval([poly([4], size_mm=3)]) == "3yr"


def test_adenoma_ge_10mm_is_high_risk():
    assert usmstf_interval([poly([3], size_mm=10)]) == "3yr"


def test_more_than_ten_adenomas_is_1yr():
    polyps = [poly([3], size_mm=3) for _ in range(11)]
    assert usmstf_interval(polyps) == "1yr"


def test_five_to_ten_adenomas_is_3yr():
    polyps = [poly([3], size_mm=3) for _ in range(5)]
    assert usmstf_interval(polyps) == "3yr"


def test_three_to_four_adenomas_is_3_5yr():
    polyps = [poly([3], size_mm=3) for _ in range(3)]
    assert usmstf_interval(polyps) == "3-5yr"


def test_one_to_two_small_ssap_is_5_10yr():
    assert usmstf_interval([poly([7], size_mm=4)]) == "5-10yr"


def test_ssap_with_dysplasia_is_high_risk_even_if_small():
    # Any dysplasia grade (not just high-grade) counts for SSA/P, unlike adenomas.
    assert usmstf_interval([poly([7, 15], size_mm=3)]) == "3yr"


def test_tsa_is_always_high_risk():
    assert usmstf_interval([poly([6], size_mm=2)]) == "3yr"


def test_hp_under_10mm_does_not_trigger_surveillance():
    assert usmstf_interval([poly([2], size_mm=5)]) == "10yr"


def test_hp_ge_10mm_is_3_5yr():
    assert usmstf_interval([poly([2], size_mm=10)]) == "3-5yr"


def test_clean_size_handles_sentinel_values():
    assert clean_size(77) is None
    assert clean_size(88) is None
    assert clean_size(None) is None
    assert clean_size("12.5") == 12.5


def test_diverted_polyp_forces_manual_review_not_a_computed_interval():
    from pathology_pipeline.usmstf import patient_recommendation
    assert patient_recommendation([poly([3], size_mm=4)], any_diverted=True) == "NEEDS_MANUAL_REVIEW"
