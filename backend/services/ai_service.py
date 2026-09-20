"""Optional AI-assisted analysis via a local Ollama instance.

This is an assistive layer only: it augments the rule-based
violation_service triage with a natural-language reasoning summary. It
NEVER fabricates evidence, and any field it cannot support from the given
context is returned as "UNKNOWN" rather than guessed. If Ollama is
unreachable or misconfigured, callers fall back to the rule-based engine
untouched — the system remains fully functional without AI configured.
"""

import json

import httpx

from config import get_settings

settings = get_settings()

SYSTEM_PROMPT = (
    "You are assisting a trust & safety analyst in reviewing PUBLICLY sourced evidence "
    "against a specific platform policy rule. You must not invent facts. If information is "
    "not present in the provided evidence/context, respond with \"UNKNOWN\" for that field. "
    "Your output is a triage aid for a human reviewer, not a final decision. "
    "Respond ONLY with strict JSON: "
    '{"detected_category": str, "reasoning_summary": str, "relevant_evidence": [str], '
    '"policy_match": str, "confidence": float, "missing_evidence": [str], '
    '"recommended_human_review": true}'
)


def is_available() -> bool:
    try:
        r = httpx.get(f"{settings.ollama_url}/api/tags", timeout=2.0)
        return r.status_code == 200
    except httpx.HTTPError:
        return False


def analyze(content: str, context: str, platform: str, policy_description: str, evidence_ids: list[str]) -> dict:
    if not is_available():
        return {
            "detected_category": "UNKNOWN",
            "reasoning_summary": "AI analysis unavailable (Ollama not reachable). Falling back to rule-based triage only.",
            "relevant_evidence": evidence_ids,
            "policy_match": "UNKNOWN",
            "confidence": 0.0,
            "missing_evidence": ["AI service connectivity"],
            "recommended_human_review": True,
            "source": "UNAVAILABLE",
        }

    user_prompt = (
        f"Platform: {platform}\nPolicy rule: {policy_description}\n"
        f"Content: {content}\nContext: {context}\nEvidence IDs: {evidence_ids}"
    )
    try:
        response = httpx.post(
            f"{settings.ollama_url}/api/generate",
            json={
                "model": settings.ollama_model,
                "system": SYSTEM_PROMPT,
                "prompt": user_prompt,
                "stream": False,
                "format": "json",
            },
            timeout=30.0,
        )
        response.raise_for_status()
        raw = response.json().get("response", "{}")
        parsed = json.loads(raw)
        parsed["recommended_human_review"] = True
        parsed["source"] = "OLLAMA"
        return parsed
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        return {
            "detected_category": "UNKNOWN",
            "reasoning_summary": f"AI analysis failed: {exc}",
            "relevant_evidence": evidence_ids,
            "policy_match": "UNKNOWN",
            "confidence": 0.0,
            "missing_evidence": ["Valid AI response"],
            "recommended_human_review": True,
            "source": "ERROR",
        }
