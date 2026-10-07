"""
pathology-ai-pipeline: AI-assisted pathology report extraction for
post-polypectomy surveillance interval calculation.

Public API re-exports for convenience; see submodules for full documentation:
    - codebook: the 17 pathology codes + high-stakes code set
    - vocabulary: the closed "Other" (code 99) vocabulary
    - prompt: the exact extraction prompt + builder
    - validation_rules: the four deterministic post-extraction validation rules
    - specimen_matching: local segment-order correction + specimen hint formatting
    - usmstf: USMSTF (2020) surveillance interval calculator
    - esge: ESGE surveillance interval calculator
    - stats: precision/recall/F1, cluster bootstrap CI, Wilson score interval
    - llm_client: Ollama client + model-response parsing (the actual model call)

Report text is assumed to already be in the pipeline's expected language/
format (English) - there is no translation step in this repository. Data
export/ingestion is also out of scope here; this package starts from an
already-structured target (report text + segment/polyp_number).
"""

from .codebook import HIGH_STAKES_CODES, POLYP_CODES
from .llm_client import OllamaClient, ParsedResponse, parse_llm_response
from .validation_rules import ExtractionResult, apply_validation_rules

__all__ = [
    "POLYP_CODES",
    "HIGH_STAKES_CODES",
    "ExtractionResult",
    "apply_validation_rules",
    "OllamaClient",
    "ParsedResponse",
    "parse_llm_response",
]

__version__ = "1.0.0"
