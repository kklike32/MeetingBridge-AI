from __future__ import annotations

from collections.abc import Iterable
import re
from typing import Any


STATIC_GLOSSARY: dict[str, dict[str, Any]] = {
    "gtm": {
        "display": "GTM",
        "canonical": "Go-to-Market",
        "explanation": "The plan for bringing a product to customers and driving adoption.",
        "category": "business_acronym",
        "confidence": 0.95,
    },
    "arr": {
        "display": "ARR",
        "canonical": "Annual Recurring Revenue",
        "explanation": "Revenue expected from subscriptions over a year.",
        "category": "business_metric",
        "confidence": 0.95,
    },
    "plg": {
        "display": "PLG",
        "canonical": "Product-Led Growth",
        "explanation": "A growth strategy where product usage helps attract, convert, and retain users.",
        "category": "business_acronym",
        "confidence": 0.95,
    },
    "churn": {
        "display": "churn",
        "canonical": "Customer Churn",
        "explanation": "The rate at which customers stop using or paying for a product.",
        "category": "business_metric",
        "confidence": 0.90,
    },
    "enterprise accounts": {
        "display": "enterprise accounts",
        "canonical": "Large business customers",
        "explanation": "Large organizations that buy and use the product.",
        "category": "business_phrase",
        "confidence": 0.85,
    },
    "q3": {
        "display": "Q3",
        "canonical": "Third quarter",
        "explanation": "The third three-month period of a fiscal or calendar year.",
        "category": "time_acronym",
        "confidence": 0.90,
    },
}

ACRONYM_PATTERN = re.compile(r"\b(?:[A-Z]{2,6}\d?|Q[1-4])\b")

CORPORATE_TERMS = {
    "leverage": "Use something to get a better result.",
    "revisit": "Look at something again to decide what should change.",
    "optimize": "Improve something so it works better.",
    "align": "Make sure people or teams agree and work toward the same goal.",
    "operationalize": "Turn an idea or process into regular practical work.",
}
BUSINESS_PHRASES = {
    "go-to-market": "The strategy for bringing a product to customers.",
    "growth motion": "A repeatable strategy for growing the business.",
    "board review": "A meeting or checkpoint with company board members.",
    "cross-functional alignment": "Agreement and coordination across different teams.",
    "motion": "A strategy or operating approach for doing business.",
}
TECHNICAL_PHRASES = {
    "multi-agent": "A system where multiple AI agents coordinate on work.",
    "retrieval augmented generation": "An AI approach that uses retrieved reference material before answering.",
    "kubernetes": "A platform for running and managing containerized applications.",
    "mlops": "Practices for deploying and managing machine learning systems.",
    "rag": "Retrieval-Augmented Generation, an AI approach that uses retrieved context.",
}


def normalize_text(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value.strip().lower())
    return normalized.strip(".,;:!?()[]{}\"'")


def dictionary_matches(transcript: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for key, entry in STATIC_GLOSSARY.items():
        if _contains_term(transcript, key):
            matches.append(_term_from_dictionary(key, entry, source="dictionary"))
    return matches


def regex_acronym_matches(transcript: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for match in ACRONYM_PATTERN.finditer(transcript):
        term = match.group(0)
        key = normalize_text(term)
        if key in STATIC_GLOSSARY:
            matches.append(_term_from_dictionary(key, STATIC_GLOSSARY[key], source="dictionary"))
            continue

        matches.append(
            {
                "term": term,
                "canonical": "Unknown acronym",
                "explanation": "This acronym needs a human-provided or LLM-confirmed explanation.",
                "category": "acronym",
                "source": "regex",
                "confidence": 0.55,
                "needs_review": True,
            }
        )
    return matches


def heuristic_matches(transcript: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for terms, category in (
        (CORPORATE_TERMS, "corporate"),
        (BUSINESS_PHRASES, "business_phrase"),
        (TECHNICAL_PHRASES, "technical"),
    ):
        for term, explanation in terms.items():
            if not _contains_term(transcript, term):
                continue
            if normalize_text(term) in STATIC_GLOSSARY:
                continue
            matches.append(
                {
                    "term": _display_from_transcript(transcript, term),
                    "canonical": term.title() if term.islower() else term,
                    "explanation": explanation,
                    "category": category,
                    "source": "heuristic",
                    "confidence": 0.60,
                    "needs_review": True,
                }
            )
    return matches


def merge_terms(*term_lists: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for term_list in term_lists:
        for raw_term in term_list:
            term = _normalize_candidate(raw_term)
            if not term:
                continue

            key = normalize_text(term["term"])
            if key not in merged:
                merged[key] = term
                order.append(key)
                continue

            merged[key] = _merge_pair(merged[key], term)

    return [_finalize_term(merged[key]) for key in order]


def detect_terms(transcript: str, llm_terms: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    if not transcript.strip():
        return []

    return merge_terms(
        dictionary_matches(transcript),
        regex_acronym_matches(transcript),
        heuristic_matches(transcript),
        llm_terms or [],
    )


def _term_from_dictionary(key: str, entry: dict[str, Any], source: str) -> dict[str, Any]:
    confidence = float(entry.get("confidence", 0.85))
    return {
        "term": entry.get("display", key),
        "canonical": entry["canonical"],
        "explanation": entry["explanation"],
        "category": entry.get("category", "other"),
        "source": source,
        "confidence": confidence,
        "needs_review": confidence < 0.70,
    }


def _normalize_candidate(raw_term: dict[str, Any]) -> dict[str, Any] | None:
    term = str(raw_term.get("term", "")).strip()
    canonical = str(raw_term.get("canonical", "")).strip()
    explanation = str(raw_term.get("explanation", "")).strip()
    if not term or not canonical or not explanation:
        return None

    confidence = _clamp_float(raw_term.get("confidence", 0.60), low=0.0, high=1.0)
    source = str(raw_term.get("source", "llm")).strip() or "llm"
    return {
        "term": term,
        "canonical": canonical,
        "explanation": explanation,
        "category": str(raw_term.get("category", "other")).strip() or "other",
        "source": source,
        "confidence": confidence,
        "needs_review": bool(raw_term.get("needs_review", confidence < 0.70)),
    }


def _merge_pair(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    existing_sources = _split_sources(existing["source"])
    incoming_sources = _split_sources(incoming["source"])
    sources = _ordered_sources([*existing_sources, *incoming_sources])

    existing_is_dictionary = "dictionary" in existing_sources
    incoming_is_dictionary = "dictionary" in incoming_sources
    keep_canonical = existing_is_dictionary and not incoming_is_dictionary

    merged = dict(existing)
    if not keep_canonical and incoming_is_dictionary:
        merged["canonical"] = incoming["canonical"]
        merged["term"] = incoming["term"]
        merged["category"] = incoming["category"]
    elif not keep_canonical and incoming["confidence"] > existing["confidence"]:
        merged["canonical"] = incoming["canonical"]
        merged["category"] = incoming["category"]

    if _should_replace_explanation(existing, incoming):
        merged["explanation"] = incoming["explanation"]

    merged["confidence"] = max(existing["confidence"], incoming["confidence"])
    merged["source"] = ",".join(sources)
    merged["needs_review"] = existing["needs_review"] or incoming["needs_review"]
    return merged


def _should_replace_explanation(existing: dict[str, Any], incoming: dict[str, Any]) -> bool:
    incoming_sources = _split_sources(incoming["source"])
    if "llm" not in incoming_sources:
        return incoming["confidence"] > existing["confidence"]
    if incoming["confidence"] < 0.80:
        return False
    return len(incoming["explanation"]) >= len(existing["explanation"])


def _finalize_term(term: dict[str, Any]) -> dict[str, Any]:
    finalized = dict(term)
    sources = _split_sources(finalized["source"])
    finalized["source"] = ",".join(_ordered_sources(sources))
    source_set = set(sources)
    finalized["needs_review"] = (
        finalized["confidence"] < 0.70
        or source_set == {"regex"}
        or source_set == {"heuristic"}
        or bool(finalized.get("needs_review", False)) and "dictionary" not in source_set and "llm" not in source_set
    )
    return finalized


def _contains_term(transcript: str, term: str) -> bool:
    escaped = re.escape(term)
    pattern = re.compile(rf"(?<![\w-]){escaped}(?![\w-])", re.IGNORECASE)
    return bool(pattern.search(transcript))


def _display_from_transcript(transcript: str, term: str) -> str:
    escaped = re.escape(term)
    pattern = re.compile(rf"(?<![\w-]){escaped}(?![\w-])", re.IGNORECASE)
    match = pattern.search(transcript)
    return match.group(0) if match else term


def _split_sources(source: str) -> list[str]:
    return [part.strip() for part in source.split(",") if part.strip()]


def _ordered_sources(sources: list[str]) -> list[str]:
    preferred = ["dictionary", "regex", "heuristic", "llm"]
    result: list[str] = []
    for source in preferred:
        if source in sources and source not in result:
            result.append(source)
    for source in sources:
        if source not in result:
            result.append(source)
    return result


def _clamp_float(value: Any, low: float, high: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = low
    return max(low, min(high, numeric))
