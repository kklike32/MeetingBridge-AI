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


def build_participant_accessibility_view(
    summary: dict[str, Any],
    transcript_raw: str | None = None,
) -> dict[str, Any]:
    action_items = normalize_action_items(summary.get("action_items"))
    glossary = list(summary.get("human_approved_glossary") or [])
    progress = summary.get("review_progress") or {}
    pending_terms = list(summary.get("needs_review") or [])
    pending_count = _safe_count(progress, "pending", len(pending_terms))
    rejected_count = _safe_count(progress, "rejected", 0)
    edited_count = _safe_count(progress, "edited", _count_glossary_status(glossary, "edited"))
    transcript = str(summary.get("transcript", "") or "").strip()
    plain_summary = str(summary.get("plain_english_summary", "") or "").strip()

    transcript_reviewed = bool(transcript)
    glossary_terms_reviewed = pending_count == 0
    action_items_confirmed = bool(action_items)
    final_notes_ready = transcript_reviewed and glossary_terms_reviewed and action_items_confirmed and bool(plain_summary)
    transcript_corrected = bool(
        transcript_raw is not None
        and _normalize_for_comparison(str(transcript_raw)) != _normalize_for_comparison(transcript)
    )

    return {
        "sections": {
            "what_was_said": transcript,
            "what_it_means": plain_summary,
            "terms_i_may_not_know": glossary,
            "what_i_need_to_do_next": action_items,
        },
        "understanding_checklist": {
            "transcript_reviewed": transcript_reviewed,
            "glossary_terms_reviewed": glossary_terms_reviewed,
            "action_items_confirmed": action_items_confirmed,
            "final_notes_ready": final_notes_ready,
        },
        "risk_flags": {
            "pending_review_terms": {
                "active": pending_count > 0,
                "count": pending_count,
                "label": "Pending review terms",
                "details": _pluralized_detail(pending_count, "term still needs review", "terms still need review"),
            },
            "rejected_terms_excluded": {
                "active": rejected_count > 0,
                "count": rejected_count,
                "label": "Rejected terms excluded",
                "details": _pluralized_detail(rejected_count, "rejected term was excluded", "rejected terms were excluded"),
            },
            "edited_explanations_used": {
                "active": edited_count > 0,
                "count": edited_count,
                "label": "Edited explanations used",
                "details": _pluralized_detail(edited_count, "human-edited explanation is used", "human-edited explanations are used"),
            },
            "transcript_corrected_after_asr": {
                "active": transcript_corrected,
                "count": 1 if transcript_corrected else 0,
                "label": "Transcript corrected after ASR",
                "details": "The final notes use the corrected transcript." if transcript_corrected else "The final notes match the ASR transcript.",
            },
            "missing_or_unconfirmed_action_items": {
                "active": not action_items_confirmed,
                "count": 0 if action_items_confirmed else 1,
                "label": "Missing or unconfirmed action items",
                "details": "Confirmed action items are included." if action_items_confirmed else "No confirmed action items are included.",
            },
        },
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

    participant_view = summary.get("participant_accessibility_view")
    if participant_view:
        lines.extend(_participant_view_markdown_lines(participant_view))

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


def _participant_view_markdown_lines(participant_view: dict[str, Any]) -> list[str]:
    sections = participant_view.get("sections") or {}
    checklist = participant_view.get("understanding_checklist") or {}
    risk_flags = participant_view.get("risk_flags") or {}
    lines = ["", "## Participant Mode / Accessibility View", "", "### What was said"]
    lines.append(sections.get("what_was_said") or "No reviewed transcript available.")
    lines.extend(["", "### What it means"])
    lines.append(sections.get("what_it_means") or "No plain-language summary available.")
    lines.extend(["", "### Terms I may not know"])
    terms = sections.get("terms_i_may_not_know") or []
    if terms:
        for entry in terms:
            lines.append(f"- **{entry.get('term', '')}** ({entry.get('canonical', '')}): {entry.get('explanation', '')}")
    else:
        lines.append("- No reviewed glossary terms are included.")
    lines.extend(["", "### What I need to do next"])
    action_items = sections.get("what_i_need_to_do_next") or []
    if action_items:
        lines.extend(f"- {item}" for item in action_items)
    else:
        lines.append("- No confirmed action items are included.")
    lines.extend(["", "### Understanding checklist"])
    checklist_labels = [
        ("transcript_reviewed", "Transcript reviewed"),
        ("glossary_terms_reviewed", "Glossary terms reviewed"),
        ("action_items_confirmed", "Action items confirmed"),
        ("final_notes_ready", "Final notes ready"),
    ]
    for key, label in checklist_labels:
        marker = "x" if checklist.get(key) else " "
        lines.append(f"- [{marker}] {label}")
    lines.extend(["", "### Accessibility risk flags"])
    if risk_flags:
        for flag in risk_flags.values():
            status = "Active" if flag.get("active") else "Clear"
            lines.append(f"- **{flag.get('label', 'Risk flag')}**: {status}. {flag.get('details', '')}")
    else:
        lines.append("- No risk flags available.")
    return lines


def _safe_count(progress: dict[str, Any], key: str, default: int) -> int:
    try:
        return int(progress.get(key, default))
    except (TypeError, ValueError):
        return default


def _count_glossary_status(glossary: list[dict[str, Any]], status: str) -> int:
    return sum(1 for entry in glossary if entry.get("status") == status)


def _normalize_for_comparison(value: str) -> str:
    return " ".join(value.split()).strip()


def _pluralized_detail(count: int, singular: str, plural: str) -> str:
    if count == 0:
        return "No " + plural + "."
    if count == 1:
        return f"1 {singular}."
    return f"{count} {plural}."
