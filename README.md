# pathology-ai-pipeline

AI-assisted extraction of structured histology findings from free-text
polyp pathology reports, paired with deterministic safety rules and
guideline-based post-polypectomy surveillance interval calculators.

This repository accompanies the manuscript *"Artificial intelligence-assisted
pathology report processing for post-polypectomy surveillance"* (Kmeyha L,
Kandlikar-Bloch M, Moulla R, et al.; corresponding author: Daniel von Renteln,
MD). It's scoped to the manuscript's analysis only, and
contains the pipeline's actual logic, prompt, codebook, and statistical
methods - fully generic and re-runnable - but **no patient data** (see
[What this repository does not contain](#what-this-repository-does-not-contain)).

<img width="573" height="479" alt="Screenshot 2026-10-07 at 3 39 01 PM" src="https://github.com/user-attachments/assets/c3405954-9e9b-459a-9dbb-98b91a53fed5" />


## The clinical problem

How soon a patient should return for a colonoscopy depends on the
histology of every polyp removed, which lives in pathology
reports. Extracting pathology results at scale by hand is time-consuming. This pipeline uses an LLM for extraction, wrapped in deterministic
rules that force every high-stakes or ambiguous case to human review instead
of guessing. Surveillance intervals are then applied to any procedure in which all polyps were extracted by the LLM (no human review), and an automatic follow-up interval is assigned to that procedure based on USMSTF and ESGE guidelines.

## Pipeline overview

Starting from an already-structured target (a polyp's report text, segment,
and polyp number - see [What this repository does not contain](#what-this-repository-does-not-contain)):

1. **Specimen matching** ([`specimen_matching.py`](src/pathology_pipeline/specimen_matching.py)) -
   match a target polyp to its specimen in the report using a *local,
   within-segment* order instead of the database's (REDCap) global polyp number.
2. **LLM extraction** ([`prompt.py`](src/pathology_pipeline/prompt.py),
   [`llm_client.py`](src/pathology_pipeline/llm_client.py)) - send the report
   and specimen information to the model (Qwen 2.5 72B via Ollama), and get back the corresponding
   histology code(s) and diagnosis text as JSON.
3. **Deterministic validation** ([`validation_rules.py`](src/pathology_pipeline/validation_rules.py)) -
   accept the extraction or divert it to human review (mandatory for any
   high-grade dysplasia/cancer finding, impossible code combinations,
   likely multi-specimen mixups, or IHC/molecular addenda with no specimen).
4. **Surveillance calculation** ([`usmstf.py`](src/pathology_pipeline/usmstf.py),
   [`esge.py`](src/pathology_pipeline/esge.py)) - apply the USMSTF (2020) and
   ESGE guidelines to accepted findings for a recommended interval. For
   concordance scoring, two USMSTF recommendations agree when one interval falls
   within the other (e.g. 10 vs. 7-10 years); see `intervals_concordant()`. ESGE
   categories do not overlap and require an exact match.
5. **Evaluation** ([`stats.py`](src/pathology_pipeline/stats.py)) - precision/
   recall/F1 and confidence intervals against a reference standard, using the
   same methodology as the manuscript's reported results (see
   [Statistical methodology](#statistical-methodology)).

## Repository layout

```
src/pathology_pipeline/
  codebook.py              17 histology codes + high-stakes code set
  vocabulary.py            closed "Other" (code 99) vocabulary
  prompt.py                exact extraction prompt + build_prompt()
  validation_rules.py      the 4 deterministic post-extraction rules
  specimen_matching.py     local segment-order correction + hint building
  llm_client.py            Ollama client + model-response parsing
  usmstf.py / esge.py      surveillance interval calculators
  stats.py                 precision/recall/F1, bootstrap CI, Wilson CI
examples/                  synthetic reports + expected outputs + demo script
tests/                     unit tests for every module above
```

Each module is documented in its own docstrings; this README stays at the
overview level.

## How to run

```bash
git clone <this-repository>
cd pathology-ai-pipeline
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

python examples/run_demo.py   # synthetic demo, no model call required
pytest tests/ -v               # unit tests
```

`run_demo.py` runs the synthetic reports in `examples/synthetic_reports/`
through the real validation/specimen-matching/guideline modules (using a
stand-in for the model's output) and checks against `examples/expected_outputs.json`.

To run the extraction step against a real model, point
[`llm_client.OllamaClient`](src/pathology_pipeline/llm_client.py) at a local
[Ollama](https://ollama.com) instance running `qwen2.5:72b` (or swap in any
other model/endpoint) and chain it with `build_prompt()` /
`apply_validation_rules()` - see the docstrings in those modules for the
exact call shapes.

## Statistical methodology

Definitions match the manuscript's Methods and Supplementary Table 2s.

- **Routing to human review.** A target routed to review (any validation rule
  firing, or the model returning code 77 because no matching specimen was found)
  receives no automated histology code.
- **Automated coverage** - proportion of evaluable targets classified
  automatically. **Automated accuracy** - exact code agreement among
  automatically classified targets only.
- **Conditional recall and conditional F1** - calculated among automatically
  classified targets only; routed targets are excluded from all denominators.
  Precision is unaffected, because routed targets receive no code. To reproduce
  these with `precision_recall_f1()` / `micro_f1()` / `macro_f1()`, pass only
  non-diverted targets (or use `automated_recall()`).
- **Macro-averaged conditional F1** - mean over categories with a defined F1.
  High-grade dysplasia and cancer are excluded for both pipeline versions, since
  mandatory review makes their F1 undefined in the optimized pipeline; they are
  assessed separately as high-risk misses.
- **Surveillance concordance** - one recommendation per procedure, computed only
  for procedures in which every polyp was classified automatically
  (procedure-level automated coverage). USMSTF recommendations agree when one
  interval falls within the other (`usmstf.intervals_concordant()`); ESGE
  categories require an exact match. Disagreements involving "cancer" are not
  classified as longer or shorter intervals.
- **Confidence intervals** - nonparametric cluster bootstrap resampling patients
  (5,000 resamples, 2.5th-97.5th percentiles; `cluster_bootstrap_ci()`), with a
  Wilson score interval for zero-event proportions (`wilson_score_interval()`).

## Model/runtime configuration

| Setting | Value |
|---|---|
| Model | Qwen 2.5, 72B parameters |
| Serving runtime | Ollama |
| Quantization | Q4_K_M |
| Temperature | 0.1 |
| Context window | 8,192 tokens |
| `num_predict` (max output tokens) | 500 |
| Python | 3.10.20 / pandas 2.3.3 / NumPy 2.2.6 |

See [`requirements.txt`](requirements.txt) for exact package pins.

## What this repository does **not** contain

This repository is deliberately scoped to the pipeline logic itself: no
patient-level data, no real pathology reports, no REDCap exports or
integration code, no database schema, no hospital integrations, no
credentials, and no broader institutional infrastructure. Every file under
`examples/synthetic_reports/` is fabricated and labeled as such. There is
also no translation step and no data-ingestion/ETL step - this package
starts from an already-structured target (report text, segment, polyp
number). As such, anyone who wishes to use this code will first need to structure their data accordingly, or modify the existing pipeline.

## Citation

See [`CITATION.cff`](CITATION.cff). This release corresponds to the pipeline
version used to generate the results reported in the associated manuscript
(submitted; citation details to be finalized upon publication).

## License

[MIT](LICENSE).
