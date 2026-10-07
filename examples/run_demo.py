#!/usr/bin/env python
"""
Demonstration script: runs the deterministic parts of the pipeline (validation
rules, specimen matching, USMSTF/ESGE calculators) against the synthetic
pathology reports in synthetic_reports/, and checks the result against
expected_outputs.json.

This script does NOT call an LLM. The synthetic reports stand in for what a
report looks like; `simulated_raw_codes` in expected_outputs.json stands in for
what a model extraction looks like, so this demo can run anywhere with no
Ollama / model dependency, exercising exactly the same deterministic logic
(validation_rules, usmstf, esge, specimen_matching) that the real pipeline
applies downstream of the model call.

Usage:
    python examples/run_demo.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from pathology_pipeline.esge import esge_interval  # noqa: E402
from pathology_pipeline.specimen_matching import (  # noqa: E402
    build_specimen_context,
)
from pathology_pipeline.usmstf import usmstf_interval  # noqa: E402
from pathology_pipeline.validation_rules import apply_validation_rules  # noqa: E402

EXAMPLES_DIR = Path(__file__).resolve().parent
REPORTS_DIR = EXAMPLES_DIR / "synthetic_reports"


def check(label: str, actual, expected) -> bool:
    ok = actual == expected
    status = "OK" if ok else "MISMATCH"
    print(f"    [{status}] {label}: expected={expected!r} actual={actual!r}")
    return ok


def run_example(name: str, spec: dict) -> bool:
    print(f"\n--- {name} ---")
    all_ok = True

    if spec.get("_demonstrates") == "specimen_matching.add_local_segment_order / build_specimen_context only - target is sigmoid polyp local order 2, which must resolve to specimen C, not B":
        context_text, hints_text = build_specimen_context(spec["segment"], spec["local_segment_order"])
        print(f"    specimen context: {context_text!r}")
        print(f"    specimen hints generated for matching: {hints_text!r}")
        all_ok &= check(
            "specimen label hint present",
            ('"polyp no. 2"'.lower() in hints_text.lower()) or ('"polyp #2"'.lower() in hints_text.lower()),
            True,
        )
        codes = set(spec["simulated_raw_codes_for_specimen_C"])
    else:
        codes = set(spec["simulated_raw_codes"])

    report_path = REPORTS_DIR / name
    full_text = report_path.read_text(encoding="utf-8")

    result = apply_validation_rules(
        codes=sorted(codes),
        specimen_found=spec["specimen_found"],
        full_text=full_text,
    )

    all_ok &= check("diverted", result.diverted, spec["expected_diverted"])
    if spec.get("expected_diversion_reason_contains"):
        contains = spec["expected_diversion_reason_contains"] in (result.diversion_reason or "")
        all_ok &= check("diversion_reason contains expected text", contains, True)
    all_ok &= check("final codes", sorted(result.codes), sorted(spec["expected_final_codes"]))

    if not result.diverted and spec.get("size_mm") is not None and "expected_usmstf_interval" in spec:
        polyps = [{"codes": set(result.codes), "size_mm": spec["size_mm"]}]
        all_ok &= check("USMSTF interval", usmstf_interval(polyps), spec["expected_usmstf_interval"])
        all_ok &= check("ESGE interval", esge_interval(polyps), spec["expected_esge_interval"])

    return all_ok


def main() -> int:
    with open(EXAMPLES_DIR / "expected_outputs.json", encoding="utf-8") as f:
        all_specs = json.load(f)

    all_ok = True
    for name, spec in all_specs.items():
        if name.startswith("_"):
            continue
        all_ok &= run_example(name, spec)

    print("\n" + ("All examples matched expected output." if all_ok else "SOME EXAMPLES DID NOT MATCH - see above."))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
