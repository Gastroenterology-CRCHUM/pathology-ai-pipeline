import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pathology_pipeline.prompt import build_prompt, format_codes_text  # noqa: E402
from pathology_pipeline.vocabulary import OTHER_VOCABULARY  # noqa: E402


def test_build_prompt_includes_report_text_and_hints():
    prompt = build_prompt(
        full_text="SAMPLE REPORT TEXT",
        context_text="Segment: Sigmoid, local order: 2",
        hints_text='"sigmoid polyp no. 2"',
    )
    assert "SAMPLE REPORT TEXT" in prompt
    assert "Segment: Sigmoid, local order: 2" in prompt
    assert '"sigmoid polyp no. 2"' in prompt


def test_build_prompt_includes_other_vocabulary():
    prompt = build_prompt(full_text="x", context_text="x", hints_text="x")
    assert OTHER_VOCABULARY in prompt


def test_build_prompt_includes_json_response_schema_fields():
    prompt = build_prompt(full_text="x", context_text="x", hints_text="x")
    assert '"specimen_identified"' in prompt
    assert '"codes"' in prompt
    assert '"patho_polyp_other"' in prompt


def test_format_codes_text_lists_all_codes_sorted():
    text = format_codes_text()
    lines = text.splitlines()
    codes = [int(line.split(":", 1)[0]) for line in lines]
    assert codes == sorted(codes)
    assert 77 in codes
    assert 99 in codes
