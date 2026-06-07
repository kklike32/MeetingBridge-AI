from __future__ import annotations

from dataclasses import dataclass, replace
import json
import re
from typing import Any, Literal

import requests

from src.model_preflight import PreflightResult, check_lm_studio_model, check_ollama_model


LLMProvider = Literal["ollama", "lm_studio"]
APPROVED_OLLAMA_MODELS = ("qwen3:8b", "gemma3:12b", "mistral:7b")
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_LM_STUDIO_URL = "http://localhost:1234/v1"

SYSTEM_PROMPT = """/no_think
You make meetings easier to understand for accessibility users, non-native English speakers, interns, new hires, and cross-functional teammates.
Use plain English.
Do not invent facts.
Return only valid JSON."""

RETRY_INSTRUCTION = (
    "Your previous answer was not valid JSON for the required schema. "
    "Return only the JSON object. Do not include markdown, comments, or surrounding prose."
)


@dataclass(frozen=True)
class LLMConfig:
    provider: LLMProvider = "ollama"
    model: str = "qwen3:8b"
    base_url: str = DEFAULT_OLLAMA_URL
    timeout: float = 45.0


class LLMClientError(RuntimeError):
    def __init__(self, message: str, action: str = "", details: dict[str, Any] | None = None):
        super().__init__(message)
        self.action = action
        self.details = details or {}


def build_meeting_intelligence_prompt(
    transcript: str,
    terms: list[dict[str, Any]],
) -> tuple[str, str]:
    terms_json = json.dumps(terms, ensure_ascii=True, indent=2)
    user_prompt = f"""Rewrite the transcript at three levels, identify contextual jargon, create a concise glossary, and extract action items.

Levels:
- simple: very plain English for someone new to the topic.
- professional: clear workplace language that preserves business meaning.
- expert: precise language for experienced stakeholders.

Use these baseline detected terms as context:
{terms_json}

Return only JSON matching this schema:
{{
  "simplifications": {{
    "simple": "string",
    "professional": "string",
    "expert": "string"
  }},
  "glossary": [
    {{
      "term": "string",
      "canonical": "string",
      "explanation": "string",
      "confidence": 0.0,
      "needs_review": true
    }}
  ],
  "action_items": ["string"]
}}

Transcript:
{transcript}"""
    return SYSTEM_PROMPT, user_prompt


def build_contextual_jargon_prompt(
    transcript: str,
    baseline_terms: list[dict[str, Any]],
) -> tuple[str, str]:
    terms_json = json.dumps(baseline_terms, ensure_ascii=True, indent=2)
    user_prompt = f"""You are helping make a meeting accessible.
Find jargon, acronyms, corporate shorthand, technical terms, and phrases that may confuse non-native English speakers, interns, new hires, or cross-functional teammates.

Use the transcript and the baseline terms. Add contextual terms only when useful.
Return only valid JSON with this schema:
{{
  "terms": [
    {{
      "term": "string",
      "canonical": "string",
      "explanation": "plain English string",
      "category": "acronym|corporate|technical|metric|time|other",
      "confidence": 0.0,
      "needs_review": true
    }}
  ]
}}

Baseline terms:
{terms_json}

Transcript:
{transcript}"""
    return SYSTEM_PROMPT, user_prompt


def strip_thinking_blocks(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL).strip()


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = strip_thinking_blocks(text)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise LLMClientError("The local LLM did not return valid JSON.")
        try:
            parsed = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise LLMClientError("The local LLM returned malformed JSON.") from exc

    if not isinstance(parsed, dict):
        raise LLMClientError("The local LLM JSON response was not an object.")
    return parsed


def validate_meeting_intelligence_payload(payload: dict[str, Any]) -> dict[str, Any]:
    simplifications = payload.get("simplifications")
    if not isinstance(simplifications, dict):
        raise LLMClientError("LLM JSON is missing the simplifications object.")

    normalized_simplifications: dict[str, str] = {}
    for key in ("simple", "professional", "expert"):
        value = simplifications.get(key)
        if not isinstance(value, str) or not value.strip():
            raise LLMClientError(f"LLM JSON is missing simplifications.{key}.")
        normalized_simplifications[key] = value.strip()

    glossary_raw = payload.get("glossary", [])
    if not isinstance(glossary_raw, list):
        raise LLMClientError("LLM JSON glossary must be a list.")

    glossary: list[dict[str, Any]] = []
    for item in glossary_raw:
        if not isinstance(item, dict):
            continue
        term = str(item.get("term", "")).strip()
        canonical = str(item.get("canonical", "")).strip()
        explanation = str(item.get("explanation", "")).strip()
        if not term or not canonical or not explanation:
            continue
        confidence = _clamp_float(item.get("confidence", 0.70), 0.0, 1.0)
        glossary.append(
            {
                "term": term,
                "canonical": canonical,
                "explanation": explanation,
                "category": str(item.get("category", "other")).strip() or "other",
                "confidence": confidence,
                "needs_review": bool(item.get("needs_review", confidence < 0.70)),
                "source": "llm",
            }
        )

    action_items_raw = payload.get("action_items", [])
    if not isinstance(action_items_raw, list):
        raise LLMClientError("LLM JSON action_items must be a list.")
    action_items = [item.strip() for item in action_items_raw if isinstance(item, str) and item.strip()]

    return {
        "simplifications": normalized_simplifications,
        "glossary": glossary,
        "action_items": action_items,
    }


def validate_contextual_terms_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    terms = payload.get("terms")
    if not isinstance(terms, list):
        raise LLMClientError("LLM JSON is missing the terms list.")

    normalized: list[dict[str, Any]] = []
    for item in terms:
        if not isinstance(item, dict):
            continue
        term = str(item.get("term", "")).strip()
        canonical = str(item.get("canonical", "")).strip()
        explanation = str(item.get("explanation", "")).strip()
        if not term or not canonical or not explanation:
            continue
        confidence = _clamp_float(item.get("confidence", 0.70), 0.40, 0.95)
        normalized.append(
            {
                "term": term,
                "canonical": canonical,
                "explanation": explanation,
                "category": str(item.get("category", "other")).strip() or "other",
                "confidence": confidence,
                "needs_review": bool(item.get("needs_review", confidence < 0.70)),
                "source": "llm",
            }
        )
    return normalized


def call_ollama(system_prompt: str, user_prompt: str, config: LLMConfig) -> str:
    url = f"{config.base_url.rstrip('/')}/api/chat"
    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "format": "json",
        "think": False,
        "options": {
            "temperature": 0.2,
            "top_p": 0.8,
            "num_predict": 1200,
        },
    }
    try:
        response = requests.post(url, json=payload, timeout=config.timeout)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise LLMClientError(f"Ollama request failed for {config.model}.", details={"error": str(exc), "url": url}) from exc
    except ValueError as exc:
        raise LLMClientError("Ollama returned non-JSON HTTP output.", details={"url": url}) from exc

    message = data.get("message", {}) if isinstance(data, dict) else {}
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        thinking = message.get("thinking") if isinstance(message, dict) else None
        if isinstance(thinking, str) and thinking.strip():
            raise LLMClientError(
                "Ollama returned thinking text but no final JSON content. Retry after keeping Qwen thinking disabled.",
                details={"url": url, "done_reason": data.get("done_reason") if isinstance(data, dict) else None},
            )
        raise LLMClientError("Ollama response did not include message.content.", details={"url": url})
    return content


def call_lm_studio(system_prompt: str, user_prompt: str, config: LLMConfig) -> str:
    url = f"{config.base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    try:
        response = requests.post(url, json=payload, timeout=config.timeout)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise LLMClientError(
            f"LM Studio request failed for {config.model}.",
            details={"error": str(exc), "url": url},
        ) from exc
    except ValueError as exc:
        raise LLMClientError("LM Studio returned non-JSON HTTP output.", details={"url": url}) from exc

    choices = data.get("choices", []) if isinstance(data, dict) else []
    if not choices or not isinstance(choices[0], dict):
        raise LLMClientError("LM Studio response did not include choices.", details={"url": url})
    content = choices[0].get("message", {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise LLMClientError("LM Studio response did not include message.content.", details={"url": url})
    return content


def generate_meeting_intelligence(
    transcript: str,
    terms: list[dict[str, Any]],
    config: LLMConfig | None = None,
) -> dict[str, Any]:
    if not transcript.strip():
        raise LLMClientError("Transcript is empty. Transcribe and correct audio before LLM analysis.")

    config = config or LLMConfig()
    readiness = check_model_ready(config)
    if not readiness.ready:
        raise LLMClientError(readiness.message, action=readiness.action, details=readiness.as_dict())
    if readiness.model and readiness.model != config.model:
        config = replace(config, model=readiness.model)

    system_prompt, user_prompt = build_meeting_intelligence_prompt(transcript, terms)
    payload = _call_with_one_json_retry(system_prompt, user_prompt, config, validate_meeting_intelligence_payload)
    payload["provider"] = config.provider
    payload["model"] = readiness.model or config.model
    return payload


def generate_contextual_terms(
    transcript: str,
    baseline_terms: list[dict[str, Any]],
    config: LLMConfig | None = None,
) -> list[dict[str, Any]]:
    if not transcript.strip():
        raise LLMClientError("Transcript is empty. Transcribe and correct audio before LLM analysis.")

    config = config or LLMConfig()
    readiness = check_model_ready(config)
    if not readiness.ready:
        raise LLMClientError(readiness.message, action=readiness.action, details=readiness.as_dict())
    if readiness.model and readiness.model != config.model:
        config = replace(config, model=readiness.model)

    system_prompt, user_prompt = build_contextual_jargon_prompt(transcript, baseline_terms)
    return _call_with_one_json_retry(system_prompt, user_prompt, config, validate_contextual_terms_payload)


def check_model_ready(config: LLMConfig) -> PreflightResult:
    if config.provider == "ollama":
        if config.model not in APPROVED_OLLAMA_MODELS:
            return PreflightResult(
                name="Ollama model",
                ready=False,
                message=f"{config.model} is not an approved MeetingBridge AI Ollama model.",
                action="Select qwen3:8b, gemma3:12b, or mistral:7b.",
                provider="ollama",
                model=config.model,
            )
        return check_ollama_model(config.base_url, config.model)

    if config.provider == "lm_studio":
        return check_lm_studio_model(config.base_url, config.model)

    return PreflightResult(
        name="Local LLM",
        ready=False,
        message=f"Unsupported LLM provider: {config.provider}.",
        action="Select Ollama or LM Studio.",
        provider=str(config.provider),
        model=config.model,
    )


def _call_with_one_json_retry(system_prompt: str, user_prompt: str, config: LLMConfig, validator):
    last_error: LLMClientError | None = None
    prompt = user_prompt
    for attempt in range(2):
        raw_text = _call_provider(system_prompt, prompt, config)
        try:
            parsed = extract_json_object(raw_text)
            return validator(parsed)
        except LLMClientError as exc:
            last_error = exc
            if attempt == 1:
                break
            prompt = f"{RETRY_INSTRUCTION}\n\n{user_prompt}"

    raise LLMClientError(
        "The local LLM did not return valid JSON after one retry.",
        action="Retry the analysis or switch to another local model.",
        details={"last_error": str(last_error) if last_error else None},
    )


def _call_provider(system_prompt: str, user_prompt: str, config: LLMConfig) -> str:
    if config.provider == "ollama":
        return call_ollama(system_prompt, user_prompt, config)
    if config.provider == "lm_studio":
        return call_lm_studio(system_prompt, user_prompt, config)
    raise LLMClientError(f"Unsupported LLM provider: {config.provider}.")


def _clamp_float(value: Any, low: float, high: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = low
    return max(low, min(high, numeric))
