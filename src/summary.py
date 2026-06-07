from __future__ import annotations

import json
from typing import Any

from src.review import approved_glossary_from_review, review_progress


def generate_final_summary(
    transcript: str,
    simplifications: dict[str, str],
    action_items: list[str],
    review_items: dict[str, dict[str, Any]],
    review_audit: list[dict[str, Any]],
    asr_status: dict[str, Any],
    llm_status: dict[str, Any],
) -> dict[str, Any]:
    approved_glossary = approved_glossary_from_review(review_items)
    glossary_entries = list(approved_glossary.values())
    pending_terms = [
        _review_term_summary(item)
        for item in review_items.values()
        if item.get("status") == "pending"
    ]

    return {
        "transcript": transcript.strip(),
        "plain_english_summary": _first_available_simplification(simplifications),
        "key_terms": [
            {"term": item["term"], "canonical": item["canonical"]}
            for item in glossary_entries
        ],
        "action_items": normalize_action_items(action_items),
        "human_approved_glossary": glossary_entries,
        "needs_review": pending_terms,
        "model_metadata": {
            "asr": {
                "provider": asr_status.get("provider"),
                "model": asr_status.get("model"),
                "last_transcribed_at": asr_status.get("last_transcribed_at"),
            },
            "llm": {
                "provider": llm_status.get("provider"),
                "model": llm_status.get("model"),
                "last_analyzed_at": llm_status.get("last_analyzed_at"),
            },
        },
        "review_progress": review_progress(review_items),
        "review_audit": list(review_audit),
    }


def final_summary_to_json(summary: dict[str, Any]) -> str:
    return json.dumps(summary, ensure_ascii=True, indent=2)


def normalize_action_items(action_items: list[str] | tuple[str, ...] | str | None) -> list[str]:
    if isinstance(action_items, str):
        candidates = action_items.splitlines()
    elif action_items is None:
        candidates = []
    else:
        candidates = list(action_items)
    return [item.strip("- \t") for item in candidates if isinstance(item, str) and item.strip("- \t")]


def final_summary_to_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# MeetingBridge AI Summary",
        "",
        "## Corrected Transcript",
        summary.get("transcript", "") or "No corrected transcript available.",
        "",
        "## Plain English Summary",
        summary.get("plain_english_summary", "") or "No summary generated.",
        "",
        "## Key Terms",
    ]

    key_terms = summary.get("key_terms") or []
    if key_terms:
        lines.extend(f"- **{term.get('term', '')}**: {term.get('canonical', '')}" for term in key_terms)
    else:
        lines.append("- No approved key terms yet.")

    lines.extend(["", "## Action Items"])
    action_items = summary.get("action_items") or []
    if action_items:
        lines.extend(f"- {item}" for item in action_items)
    else:
        lines.append("- No action items generated.")

    lines.extend(["", "## Human-Approved Glossary"])
    glossary = summary.get("human_approved_glossary") or []
    if glossary:
        for entry in glossary:
            lines.append(f"- **{entry.get('term', '')}** ({entry.get('canonical', '')}): {entry.get('explanation', '')}")
    else:
        lines.append("- No approved glossary entries yet.")

    lines.extend(["", "## Model Metadata"])
    metadata = summary.get("model_metadata", {})
    asr = metadata.get("asr", {})
    llm = metadata.get("llm", {})
    lines.append(f"- ASR: {_metadata_label(asr)}")
    lines.append(f"- LLM: {_metadata_label(llm)}")

    lines.extend(["", "## Review Audit"])
    audit = summary.get("review_audit") or []
    if audit:
        for entry in audit:
            lines.append(
                f"- {entry.get('timestamp', 'unknown time')} - "
                f"{entry.get('term', 'unknown term')}: {entry.get('action', 'unknown action')}"
            )
    else:
        lines.append("- No review actions recorded.")

    return "\n".join(lines).strip() + "\n"


def _first_available_simplification(simplifications: dict[str, str]) -> str:
    for key in ("simple", "professional", "expert"):
        value = simplifications.get(key, "")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _review_term_summary(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "term": item.get("term", ""),
        "canonical": item.get("canonical", ""),
        "status": item.get("status", "pending"),
    }


def _metadata_label(metadata: dict[str, Any]) -> str:
    provider = metadata.get("provider") or "unknown"
    model = metadata.get("model") or "unknown"
    return f"{provider} {model}"
