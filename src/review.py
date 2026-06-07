from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


REVIEW_STATUSES = ("pending", "approved", "edited", "rejected")
REVIEW_ACTIONS = ("approve", "edit", "reject")


def initialize_review_items(
    detected_terms: list[dict[str, Any]],
    existing_items: dict[str, dict[str, Any]] | None = None,
    model: str | None = None,
) -> dict[str, dict[str, Any]]:
    existing_items = existing_items or {}
    initialized: dict[str, dict[str, Any]] = {}

    for term_candidate in detected_terms:
        term = str(term_candidate.get("term", "")).strip()
        canonical = str(term_candidate.get("canonical", "")).strip()
        explanation = str(term_candidate.get("explanation", "")).strip()
        if not term or not canonical or not explanation:
            continue

        existing = _find_item(existing_items, term)
        if existing:
            initialized[term] = _merge_existing_item(existing, term_candidate, model)
            continue

        initialized[term] = {
            "term": term,
            "canonical": canonical,
            "original_explanation": explanation,
            "current_explanation": explanation,
            "status": "pending",
            "confidence": _safe_float(term_candidate.get("confidence", 0.0)),
            "source": str(term_candidate.get("source", "")).strip() or "unknown",
            "model": model or str(term_candidate.get("model", "")).strip() or None,
            "updated_at": None,
            "needs_review": bool(term_candidate.get("needs_review", False)),
        }

    return initialized


def apply_review_action(
    review_items: dict[str, dict[str, Any]],
    audit: list[dict[str, Any]],
    term: str,
    action: str,
    edited_text: str | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    if action not in REVIEW_ACTIONS:
        raise ValueError(f"Unsupported review action: {action}")

    item = _find_item(review_items, term)
    if item is None:
        raise KeyError(f"No review item exists for term: {term}")

    before = str(item.get("current_explanation", ""))
    after = before
    if action == "approve":
        item["status"] = "approved"
    elif action == "edit":
        after = (edited_text or "").strip()
        if not after:
            raise ValueError("Edited explanation cannot be empty.")
        item["current_explanation"] = after
        item["status"] = "edited"
    elif action == "reject":
        item["status"] = "rejected"

    updated_at = timestamp or _utc_now()
    item["updated_at"] = updated_at
    audit.append(
        {
            "timestamp": updated_at,
            "term": item["term"],
            "action": action,
            "before": before,
            "after": after,
            "source_model": item.get("model"),
        }
    )
    return item


def approved_glossary_from_review(review_items: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    glossary: dict[str, dict[str, Any]] = {}
    for term, item in review_items.items():
        if item.get("status") not in {"approved", "edited"}:
            continue
        glossary[term] = {
            "term": item.get("term", term),
            "canonical": item.get("canonical", ""),
            "explanation": item.get("current_explanation", ""),
            "confidence": item.get("confidence", 0.0),
            "source": item.get("source", ""),
            "model": item.get("model"),
            "status": item.get("status"),
            "updated_at": item.get("updated_at"),
        }
    return glossary


def review_progress(review_items: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts = {status: 0 for status in REVIEW_STATUSES}
    for item in review_items.values():
        status = item.get("status", "pending")
        if status not in counts:
            status = "pending"
        counts[status] += 1
    counts["total"] = len(review_items)
    return counts


def review_gate_status(review_items: dict[str, dict[str, Any]]) -> dict[str, int | bool]:
    progress = review_progress(review_items)
    reviewed = progress["approved"] + progress["edited"] + progress["rejected"]
    return {
        **progress,
        "reviewed": reviewed,
        "ready": progress["pending"] == 0,
    }


def _find_item(review_items: dict[str, dict[str, Any]], term: str) -> dict[str, Any] | None:
    if term in review_items:
        return review_items[term]
    normalized = _normalize_term(term)
    for key, item in review_items.items():
        if _normalize_term(key) == normalized or _normalize_term(str(item.get("term", ""))) == normalized:
            return item
    return None


def _merge_existing_item(
    existing: dict[str, Any],
    term_candidate: dict[str, Any],
    model: str | None,
) -> dict[str, Any]:
    merged = dict(existing)
    merged["confidence"] = _safe_float(term_candidate.get("confidence", merged.get("confidence", 0.0)))
    merged["source"] = str(term_candidate.get("source", merged.get("source", ""))).strip() or "unknown"
    merged["needs_review"] = bool(term_candidate.get("needs_review", merged.get("needs_review", False)))
    if model:
        merged["model"] = model
    return merged


def _normalize_term(term: str) -> str:
    return " ".join(term.strip().lower().split())


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
