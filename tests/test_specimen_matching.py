import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pathology_pipeline.specimen_matching import (  # noqa: E402
    add_local_segment_order,
    build_specimen_context,
    normalize_segment,
)


def test_local_segment_order_resets_per_segment():
    df = pd.DataFrame({
        "record_id": [1, 1, 1, 1],
        "segment": ["Sigmoid", "Sigmoid", "Rectum", "Rectum"],
        "polyp_number": [5, 9, 2, 7],  # global, procedure-level numbers
    })
    result = add_local_segment_order(df)
    sigmoid_rows = result[result["segment"] == "Sigmoid"].sort_values("polyp_number")
    assert list(sigmoid_rows["local_segment_order"]) == [1, 2]
    rectum_rows = result[result["segment"] == "Rectum"].sort_values("polyp_number")
    assert list(rectum_rows["local_segment_order"]) == [1, 2]


def test_local_segment_order_is_independent_across_records():
    df = pd.DataFrame({
        "record_id": [1, 2],
        "segment": ["Sigmoid", "Sigmoid"],
        "polyp_number": [9, 1],
    })
    result = add_local_segment_order(df)
    # Each record's sigmoid segment has only one polyp -> local order 1 for both,
    # even though global numbers differ wildly (9 vs 1) and record 1's global
    # number is higher.
    assert list(result.sort_values("record_id")["local_segment_order"]) == [1, 1]


def test_single_polyp_in_segment_gets_local_order_one():
    df = pd.DataFrame({
        "record_id": [1],
        "segment": ["Cecum"],
        "polyp_number": [14],
    })
    result = add_local_segment_order(df)
    assert result.loc[0, "local_segment_order"] == 1


def test_normalize_segment_maps_alias_to_canonical():
    assert normalize_segment("sigmoïde") == "sigmoid"
    assert normalize_segment("Côlon Droit") == "ascending"
    assert normalize_segment(None) is None
    assert normalize_segment("") is None


def test_normalize_segment_passthrough_for_unknown_segment():
    assert normalize_segment("Some Unmapped Segment") == "some unmapped segment"


def test_build_specimen_context_uses_local_order_not_global_number():
    # Caller passes the already-computed local segment order as `polyp_number`
    # (mirroring extract_single()'s prompt_polyp_number = local_segment_order
    # or polyp_number fallback) - this function itself does no such fallback.
    context_text, hints_text = build_specimen_context(segment="Sigmoid", polyp_number=2)
    assert "Polyp number: 2" in context_text
    assert '"polyp #2"' in hints_text
    assert '"polyp No. 2"' in hints_text
    assert '"polyp 2"' in hints_text
    assert "9" not in hints_text


def test_build_specimen_context_includes_segment_aliases_as_hints():
    context_text, hints_text = build_specimen_context(segment="sigmoid", polyp_number=1)
    assert '"sigmoid"' in hints_text
    # Alias expansion adds other spellings of the same canonical segment,
    # excluding the one that's identical (case-insensitively) to the input.
    assert '"sigmoïde"' in hints_text
    assert '"sigmoidal"' in hints_text


def test_build_specimen_context_handles_no_segment_or_number():
    context_text, hints_text = build_specimen_context(segment=None, polyp_number=None)
    assert context_text == "No specific context"
    assert hints_text == "N/A"
