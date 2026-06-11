"""
Verifier Agent — Self-Verification / Reflection Phase

Purpose: Validates the agent's final answer BEFORE it reaches the user.
Checks for:
  1. Number consistency — are cited numbers actually in the scratchpad data?
  2. Trend direction — does the conclusion match chronological data order?
  3. Reasonable ranges — are percentages, margins, ratios within sane bounds?
  4. Source attribution — are conclusions properly labeled by evidence type?

Paper basis: CRAG, Self-RAG, Reflexion

Input: final_answer (str), scratchpad (str), usage_metrics (dict)
Output: verified_answer (str), usage_metrics (dict)
"""

import re
import sentry_sdk
from typing import Dict, Any, Tuple

from api.constants import AIModel
from ..core.llm_client import call_llm
from ..services.prompts import VerifierAgentPrompt


async def verify_answer(
    final_answer: str,
    scratchpad: str,
    usage_metrics: Dict[str, Any]
) -> Tuple[str, Dict[str, Any]]:
    """
    Verifies the final answer against the scratchpad data.
    Returns the original or corrected answer.
    """
    try:
        prompt = VerifierAgentPrompt.prompt(final_answer, scratchpad[-3000:])

        response, usage_metrics = await call_llm(
            prompt=prompt,
            model=AIModel.LLAMA_31_8B,  # Use smaller model for verification (cost-efficient)
            max_tokens=800,
            usage_metrics=usage_metrics
        )

        # Parse the verification result
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if match:
            import json
            result = json.loads(match.group(0))

            if result.get("verified") is False and result.get("corrected_answer"):
                print(f"\n--- [VERIFIER STAGE: INTERVENED] ---")
                print(f"Issues detected: {result.get('issues', [])}")
                print(f"Answer has been auto-corrected before reaching user.\n--------------------------------------\n")
                return result["corrected_answer"], usage_metrics
            elif result.get("verified") is False:
                print(f"\n--- [VERIFIER STAGE: FLAG ONLY] ---")
                print(f"Issues detected: {result.get('issues', [])}")
                print(f"No correction provided by model. Passing original answer.\n--------------------------------------\n")
            else:
                print("\n--- [VERIFIER STAGE: PASSED] ---")
                print("No contradictions or hallucinations detected.\n--------------------------------------\n")

        # If verified or couldn't parse, return original
        return final_answer, usage_metrics

    except Exception as e:
        sentry_sdk.capture_exception(e)
        print(f"Verifier error (non-blocking): {str(e)}")
        # Verification is non-blocking — if it fails, return the original answer
        return final_answer, usage_metrics
