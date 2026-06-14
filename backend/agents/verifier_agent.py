"""
Verifier agent — self-reflection pass before the answer reaches the user.

Checks:
  1. Number consistency — cited figures exist in the scratchpad
  2. Trend direction — conclusion matches chronological data order
  3. Reasonable ranges — margins, percentages, ratios within sane bounds
  4. Unsupported claims — conclusions not backed by retrieved data

Verification is always non-blocking: if the model or parse fails, the
original answer is returned unchanged.
"""

import re
import json
import sentry_sdk
from typing import Dict, Any, Tuple

from api.config import settings
from api.constants import AIModel
from ..core.llm_client import call_llm
from ..services.prompts import VerifierAgentPrompt


async def verify_answer(
    final_answer: str,
    scratchpad: str,
    usage_metrics: Dict[str, Any]
) -> Tuple[str, Dict[str, Any]]:

    scratchpad_tail = scratchpad[-settings.VERIFIER_SCRATCHPAD_CHARS:]

    try:
        prompt = VerifierAgentPrompt.prompt(final_answer, scratchpad_tail)

        response, usage_metrics = await call_llm(
            prompt=prompt,
            model=AIModel.LLAMA_31_8B,
            max_tokens=800,
            usage_metrics=usage_metrics
        )

        match = re.search(r"\{.*\}", response, re.DOTALL)
        if not match:
            print("Verifier agent: could not find JSON in response — passing original answer.")
            return final_answer, usage_metrics

        try:
            result = json.loads(match.group(0))
        except json.JSONDecodeError as e:
            print(f"Verifier agent: JSON parse failed ({e}) — passing original answer.")
            return final_answer, usage_metrics

        if result.get("verified") is False and result.get("corrected_answer"):
            print("\n--- [VERIFIER: INTERVENED] ---")
            print(f"Issues: {result.get('issues', [])}")
            print("Answer auto-corrected before reaching user.\n")
            return result["corrected_answer"], usage_metrics

        if result.get("verified") is False:
            print("\n--- [VERIFIER: FLAGGED, NO CORRECTION] ---")
            print(f"Issues: {result.get('issues', [])}")
            print("No corrected_answer provided — passing original.\n")
        else:
            print("\n--- [VERIFIER: PASSED] ---")

        return final_answer, usage_metrics

    except Exception as e:
        sentry_sdk.capture_exception(e)
        print(f"Verifier agent error (non-blocking): {e}")
        return final_answer, usage_metrics
