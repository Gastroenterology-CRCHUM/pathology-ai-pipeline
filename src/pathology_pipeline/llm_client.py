"""
Ollama client and model-response parsing.

This is the actual code that calls the model and turns its raw text response
into structured fields - the piece between `prompt.build_prompt()` and
`validation_rules.apply_validation_rules()`. It has no dependency on any
institutional system: it is a plain HTTP client against a local Ollama
server, and a regex/JSON parser over whatever string comes back.
"""

import json
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests


class OllamaClient:
    """Minimal client for Ollama's /api/generate endpoint."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5:72b",
        timeout: int = 120,
    ):
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.generate_url = f"{base_url}/api/generate"

    def generate(self, prompt: str, temperature: float = 0.1) -> str:
        """
        Send `prompt` to the model and return its raw text response.

        Uses the same generation settings as the locked pipeline: temperature
        0.1, num_predict 500, num_ctx 8192 (see README "Model/runtime
        configuration").
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 500,
                "num_ctx": 8192,
            },
        }
        response = requests.post(self.generate_url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.json().get("response", "")


@dataclass
class ParsedResponse:
    codes: List[int]
    specimen_identified: str
    specimen_found: bool
    diagnosis_text: str
    other_text: str
    reasoning: str


def parse_llm_response(response: str, valid_codes: Optional[Dict[int, str]] = None) -> ParsedResponse:
    """
    Parse a raw model response into structured fields.

    Tries to extract and parse the JSON object the prompt asks for; any code
    not in `valid_codes` is dropped (a model can hallucinate a code number
    outside the codebook). If no valid JSON object can be found, falls back
    to pulling any bare numbers out of the response text that happen to be
    valid codes - and if even that finds nothing, defaults to [99] (Other)
    rather than silently returning no finding at all.

    Args:
        response: raw text returned by OllamaClient.generate().
        valid_codes: code -> label mapping to validate extracted codes
            against (defaults to codebook.POLYP_CODES).

    Returns:
        ParsedResponse with the extracted fields.
    """
    if valid_codes is None:
        from .codebook import POLYP_CODES
        valid_codes = POLYP_CODES

    json_match = re.search(r"\{[^{}]*\}", response, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError:
            data = None
        if data is not None:
            codes = data.get("codes", [])
            specimen_identified = data.get("specimen_identified", "")
            diagnosis_text = data.get("diagnosis_text", "")
            other_text = data.get("patho_polyp_other", "")
            reasoning = data.get("reasoning", "")

            specimen_found = bool(specimen_identified) and specimen_identified.strip().lower() not in (
                "not found", "none", "n/a",
            )
            valid = [c for c in codes if c in valid_codes]

            return ParsedResponse(
                codes=valid,
                specimen_identified=specimen_identified,
                specimen_found=specimen_found,
                diagnosis_text=diagnosis_text,
                other_text=other_text,
                reasoning=reasoning,
            )

    # Fallback: no parseable JSON object - look for bare valid code numbers.
    numbers = re.findall(r"\b(\d+)\b", response)
    valid = [int(n) for n in numbers if int(n) in valid_codes]
    return ParsedResponse(
        codes=valid if valid else [99],
        specimen_identified="Unknown",
        specimen_found=True,
        diagnosis_text="",
        other_text="",
        reasoning=response[:200],
    )
