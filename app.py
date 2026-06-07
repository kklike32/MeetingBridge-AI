from __future__ import annotations

from datetime import datetime, timezone
import json
import re

import streamlit as st

from src.audio_inputs import remove_temp_audio, save_audio_file
from src.demo_assets import DEMO_SENTENCE
from src.jargon import detect_terms
from src.llm_client import LLMClientError, LLMConfig, generate_meeting_intelligence
from src.model_preflight import (
    PreflightResult,
    check_faster_whisper_import,
    check_lm_studio_model,
    check_mlx_whisper_import,
    check_ollama_model,
    check_streamlit_audio_available,
)
from src.review import (
    apply_review_action,
    approved_glossary_from_review,
    initialize_review_items,
    review_gate_status,
    review_progress,
)
from src.summary import (
    build_participant_accessibility_view,
    final_summary_to_json,
    final_summary_to_markdown,
    generate_final_summary,
    normalize_action_items,
)
from src.transcription import FASTER_WHISPER_MODEL, MLX_WHISPER_MODEL, transcribe_audio


OLLAMA_DEFAULT_URL = "http://localhost:11434"
LM_STUDIO_DEFAULT_URL = "http://localhost:1234/v1"
SESSION_DEFAULTS = {
    "audio_source": None,
    "audio_filename": None,
    "audio_temp_path": None,
    "audio_bytes_count": 0,
    "asr_status": {
        "ready": False,
        "provider": None,
        "model": None,
        "last_error": None,
        "last_transcribed_at": None,
    },
    "transcript_raw": "",
    "transcript_corrected": "",
    "transcript_source": None,
    "asr_result": None,
    "baseline_terms": [],
    "merged_terms": [],
    "meeting_intelligence": None,
    "review_items": {},
    "review_audit": [],
    "approved_glossary": {},
    "action_items_review_text": "",
    "final_summary": None,
    "llm_status": {
        "ready": False,
        "provider": None,
        "model": None,
        "last_error": None,
        "action": None,
        "last_analyzed_at": None,
    },
}
WORKFLOW_STEPS = [
    "Audio",
    "Transcript",
    "Explain",
    "Review",
    "Notes",
    "Export",
]


def inject_accessible_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --mb-bg: #f7fbff;
            --mb-surface: #ffffff;
            --mb-surface-soft: #f1f8ff;
            --mb-ink: #162033;
            --mb-muted: #4d5b6f;
            --mb-border: #c8d8ea;
            --mb-primary: #2850b8;
            --mb-primary-dark: #17357f;
            --mb-mint: #dff8ef;
            --mb-lavender: #eee8ff;
            --mb-peach: #ffe7dc;
            --mb-yellow: #fff5cc;
            --mb-success: #176b45;
            --mb-warning: #755300;
            --mb-error: #a12828;
            --mb-shadow: 0 18px 45px rgba(46, 72, 112, 0.10);
        }

        .stApp {
            background:
                radial-gradient(circle at 12% 5%, rgba(194, 231, 255, 0.72), transparent 28rem),
                radial-gradient(circle at 84% 2%, rgba(238, 232, 255, 0.76), transparent 25rem),
                linear-gradient(180deg, var(--mb-bg) 0%, #ffffff 56%, #f9fbff 100%);
            color: var(--mb-ink);
        }

        .block-container {
            max-width: 1180px;
            padding-top: 1.25rem;
            padding-bottom: 4rem;
        }

        h1, h2, h3, h4, h5, h6, p, li, label, span {
            letter-spacing: 0;
        }

        h1 {
            color: var(--mb-ink);
            font-size: 2.35rem !important;
            line-height: 1.08 !important;
            margin-bottom: 0.2rem !important;
        }

        h2, h3 {
            color: var(--mb-ink);
        }

        p, li, .stMarkdown, [data-testid="stCaptionContainer"] {
            color: var(--mb-muted);
            font-size: 1rem;
            line-height: 1.6;
        }

        .mb-hero {
            background: linear-gradient(135deg, #ffffff 0%, #eef7ff 50%, #fff6ec 100%);
            border: 1px solid var(--mb-border);
            border-radius: 24px;
            box-shadow: var(--mb-shadow);
            padding: 1.15rem 1.35rem;
            margin-bottom: 0.8rem;
        }

        .mb-hero p {
            color: #33445f;
            font-size: 1.02rem;
            max-width: 820px;
            margin-bottom: 0;
        }

        .mb-stepper {
            align-items: center;
            display: flex;
            gap: 0.4rem;
            margin: 0.6rem 0 0.9rem;
        }

        .mb-step {
            align-items: center;
            background: rgba(255, 255, 255, 0.88);
            border: 2px solid var(--mb-border);
            border-radius: 999px;
            display: inline-flex;
            gap: 0.45rem;
            min-height: 42px;
            padding: 0.45rem 0.75rem;
            white-space: nowrap;
        }

        .mb-step strong {
            color: var(--mb-ink);
            display: inline;
            font-size: 0.94rem;
            line-height: 1;
            margin-top: 0;
        }

        .mb-stepper-separator {
            color: #6b7890;
            font-weight: 800;
        }

        .mb-step .mb-bubble {
            align-items: center;
            background: #eef3ff;
            border: 2px solid #bccbf3;
            border-radius: 999px;
            color: var(--mb-primary-dark);
            display: inline-flex;
            font-weight: 800;
            height: 1.6rem;
            justify-content: center;
            width: 1.6rem;
        }

        .mb-step.current {
            border-color: var(--mb-primary);
            background: #eef4ff;
            box-shadow: 0 0 0 3px rgba(40, 80, 184, 0.14);
        }

        .mb-step.done {
            border-color: #78c6a3;
            background: var(--mb-mint);
        }

        .mb-section-intro {
            background: rgba(255, 255, 255, 0.82);
            border: 1px solid var(--mb-border);
            border-radius: 20px;
            padding: 0.7rem 0.9rem;
            margin: 0.8rem 0 0.55rem;
        }

        .mb-section-intro h2 {
            font-size: 1.18rem !important;
            margin: 0 0 0.2rem !important;
        }

        .mb-section-intro p {
            margin: 0;
        }

        .mb-status-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.65rem;
            margin: 0.4rem 0 0.6rem;
        }

        .mb-status-card {
            border: 2px solid var(--mb-border);
            border-radius: 18px;
            padding: 0.75rem;
            background: var(--mb-surface);
            min-height: 104px;
            box-shadow: 0 8px 22px rgba(46, 72, 112, 0.07);
        }

        .mb-status-card strong {
            color: var(--mb-ink);
            display: block;
            font-size: 1.02rem;
        }

        .mb-status-card p {
            margin: 0.4rem 0 0;
        }

        .mb-status-ready {
            border-color: #68b68f;
            background: #eefaf5;
        }

        .mb-status-blocked {
            border-color: #e29292;
            background: #fff1f1;
        }

        .mb-status-warn {
            border-color: #d7b855;
            background: var(--mb-yellow);
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: var(--mb-border);
            border-radius: 20px;
            box-shadow: 0 8px 22px rgba(46, 72, 112, 0.07);
            background: rgba(255, 255, 255, 0.90);
        }

        div.stButton > button,
        div[data-testid="stDownloadButton"] > button {
            border-radius: 999px;
            min-height: 44px;
            padding: 0.58rem 1.05rem;
            font-weight: 800;
            border: 2px solid var(--mb-primary);
        }

        div.stButton > button[kind="primary"],
        div[data-testid="stDownloadButton"] > button[kind="primary"] {
            background: var(--mb-primary);
            color: #ffffff;
        }

        div.stButton > button[kind="primary"] p,
        div[data-testid="stDownloadButton"] > button[kind="primary"] p {
            color: #ffffff;
        }

        div.stButton > button:not([kind="primary"]) p,
        div[data-testid="stDownloadButton"] > button:not([kind="primary"]) p {
            color: var(--mb-primary-dark);
        }

        div.stButton > button:focus-visible,
        div[data-testid="stDownloadButton"] > button:focus-visible,
        textarea:focus,
        input:focus,
        [role="combobox"]:focus-visible {
            outline: 4px solid #ffbf47 !important;
            outline-offset: 3px !important;
            box-shadow: none !important;
        }

        textarea, input, [data-baseweb="select"] {
            border-radius: 16px !important;
            font-size: 1rem !important;
        }

        [data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid var(--mb-border);
            border-radius: 18px;
            padding: 0.85rem;
        }

        .stAlert {
            border-radius: 18px;
        }

        .stDataFrame {
            border-radius: 18px;
            overflow: hidden;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_result(result: PreflightResult) -> None:
    if result.ready:
        st.success(result.message)
        return

    st.error(result.message)
    if result.action:
        st.code(result.action, language="bash")


def render_preflight_cards(results: dict[str, PreflightResult]) -> None:
    cards = []
    for label, result in results.items():
        status = "Ready" if result.ready else "Setup blocker"
        icon = "OK" if result.ready else "!"
        state_class = "mb-status-ready" if result.ready else "mb-status-blocked"
        action = ""
        if result.action:
            action = f"<p><strong>Next step:</strong> <code>{_html_escape(result.action)}</code></p>"
        cards.append(
            f'<div class="mb-status-card {state_class}">'
            f"<strong>{icon} {status}: {_html_escape(label)}</strong>"
            f"<p>{_html_escape(result.message)}</p>"
            f"{action}</div>"
        )
    st.markdown(f"<div class=\"mb-status-grid\">{''.join(cards)}</div>", unsafe_allow_html=True)


def render_section_intro(title: str, description: str) -> None:
    st.markdown(
        f"""
        <div class="mb-section-intro">
            <h2>{_html_escape(title)}</h2>
            <p>{_html_escape(description)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def current_workflow_index() -> int:
    if st.session_state.get("final_summary"):
        return 5
    if st.session_state.get("meeting_intelligence"):
        gate_ready = review_gate_status(st.session_state.get("review_items", {}))["ready"]
        if gate_ready and st.session_state.get("action_items_review_text", "").strip():
            return 4
        return 3
    if st.session_state.get("transcript_corrected"):
        return 2
    if st.session_state.get("asr_status", {}).get("last_transcribed_at"):
        return 1
    if st.session_state.get("audio_temp_path"):
        return 1
    return 0


def render_workflow_stepper() -> None:
    current = current_workflow_index()
    step_markup = []
    for index, label in enumerate(WORKFLOW_STEPS):
        if index < current:
            state = "done"
            marker = "OK"
            state_text = "Completed"
        elif index == current:
            state = "current"
            marker = str(index + 1)
            state_text = "Current step"
        else:
            state = ""
            marker = str(index + 1)
            state_text = "Upcoming"
        if step_markup:
            step_markup.append('<span class="mb-stepper-separator">/</span>')
        step_markup.append(
            f'<div class="mb-step {state}" aria-label="{_html_escape(label)}: {state_text}">'
            f'<span class="mb-bubble">{marker}</span>'
            f"<strong>{_html_escape(label)}</strong>"
            f"</div>"
        )
    st.markdown(f"<div class=\"mb-stepper\">{''.join(step_markup)}</div>", unsafe_allow_html=True)


def render_hero() -> None:
    st.markdown(
        """
        <div class="mb-hero">
            <h1>MeetingBridge AI</h1>
            <p>
                Record or upload meeting audio, then turn it into reviewed accessible notes.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _html_escape(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def initialize_session_state() -> None:
    for key, value in SESSION_DEFAULTS.items():
        st.session_state.setdefault(key, _session_default_value(value))


def reset_audio_state() -> None:
    remove_temp_audio(st.session_state.get("audio_temp_path"))
    for key, value in SESSION_DEFAULTS.items():
        st.session_state[key] = _session_default_value(value)


def _session_default_value(value):
    if isinstance(value, dict):
        return value.copy()
    if isinstance(value, list):
        return list(value)
    return value


def selected_audio(recorded_audio, uploaded_audio):
    if recorded_audio is not None:
        return recorded_audio, "microphone"
    if uploaded_audio is not None:
        return uploaded_audio, "upload"
    return None, None


def widget_key(prefix: str, term: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", term.strip().lower()).strip("_")
    return f"{prefix}_{normalized or 'term'}"


def render_review_panel() -> None:
    review_items = st.session_state.get("review_items", {})
    if not review_items:
        st.info("Run local LLM analysis to create review items.")
        return

    progress = review_progress(review_items)
    gate = review_gate_status(review_items)
    metric_columns = st.columns(5)
    for column, status in zip(metric_columns, ["pending", "approved", "edited", "rejected", "total"]):
        column.metric(status.title(), progress[status])

    st.markdown(
        f"**Review gate:** {gate['reviewed']} of {gate['total']} explanations reviewed. "
        f"{gate['pending']} pending."
    )
    if gate["ready"]:
        st.success("Review gate is complete. Final notes will use only approved or edited glossary items.")
    else:
        st.warning("Approve, edit, or reject every explanation before generating final accessible notes.")

    for term, item in review_items.items():
        status_label = item["status"].title()
        with st.expander(f"{item['term']} - Review status: {status_label}", expanded=item["status"] == "pending"):
            st.markdown(f"**Meaning:** {item['canonical']}")
            st.markdown(f"**Review status:** {status_label}")
            st.markdown(f"**Review required:** {'Yes' if item.get('needs_review') else 'No'}")
            st.markdown("**Current explanation:**")
            st.write(item["current_explanation"])
            st.caption(
                f"Source: {item.get('source', 'unknown')} | "
                f"Confidence: {float(item.get('confidence', 0.0)):.0%} | "
                f"Model: {item.get('model') or 'unknown'}"
            )

            edit_key = widget_key("edit", term)
            st.text_area(
                "Edit explanation",
                value=item["current_explanation"],
                key=edit_key,
                height=90,
            )
            approve_col, edit_col, reject_col = st.columns(3)
            with approve_col:
                if st.button("Approve", key=widget_key("approve", term)):
                    apply_review_action(review_items, st.session_state["review_audit"], term, "approve")
                    st.session_state["approved_glossary"] = approved_glossary_from_review(review_items)
                    st.session_state["final_summary"] = None
                    st.rerun()
            with edit_col:
                if st.button("Save Edit", key=widget_key("save_edit", term)):
                    try:
                        apply_review_action(
                            review_items,
                            st.session_state["review_audit"],
                            term,
                            "edit",
                            edited_text=st.session_state.get(edit_key, ""),
                        )
                    except ValueError as exc:
                        st.warning(str(exc))
                    else:
                        st.session_state["approved_glossary"] = approved_glossary_from_review(review_items)
                        st.session_state["final_summary"] = None
                        st.rerun()
            with reject_col:
                if st.button("Reject", key=widget_key("reject", term)):
                    apply_review_action(review_items, st.session_state["review_audit"], term, "reject")
                    st.session_state["approved_glossary"] = approved_glossary_from_review(review_items)
                    st.session_state["final_summary"] = None
                    st.rerun()

    with st.expander("Review audit trail"):
        if st.session_state["review_audit"]:
            st.json(st.session_state["review_audit"])
            st.download_button(
                "Export review audit JSON",
                data=json.dumps(st.session_state["review_audit"], ensure_ascii=True, indent=2),
                file_name="meetingbridge_review_audit.json",
                mime="application/json",
            )
        else:
            st.info("No review actions recorded yet.")


def render_action_item_review(intelligence: dict) -> None:
    render_section_intro(
        "Confirm action items",
        "Review the local LLM's next-step suggestions. The final notes use only the action items left in this field.",
    )
    with st.container(border=True):
        st.text_area(
            "Confirmed action items, one per line",
            key="action_items_review_text",
            height=140,
        )
        action_items = normalize_action_items(st.session_state.get("action_items_review_text", ""))
        st.caption(f"{len(action_items)} action item(s) will be included in the final notes.")
        if action_items:
            for item in action_items:
                st.write(f"- {item}")
        elif intelligence.get("action_items"):
            st.warning("No confirmed action items are currently selected for the final notes.")
        else:
            st.info("The local LLM did not generate action items for this transcript.")


def render_participant_accessibility_view(participant_view: dict) -> None:
    sections = participant_view.get("sections", {})
    checklist = participant_view.get("understanding_checklist", {})
    risk_flags = participant_view.get("risk_flags", {})

    render_section_intro(
        "Participant notes",
        "A plain-language version of the reviewed meeting notes for participants.",
    )

    st.markdown("### What was said")
    st.write(sections.get("what_was_said") or "No reviewed transcript available.")

    st.markdown("### What it means")
    st.write(sections.get("what_it_means") or "No plain-language summary available.")

    st.markdown("### Terms I may not know")
    glossary = sections.get("terms_i_may_not_know") or []
    if glossary:
        for entry in glossary:
            st.markdown(f"**{entry.get('term', '')}** - {entry.get('canonical', '')}")
            st.write(entry.get("explanation", ""))
    else:
        st.write("No reviewed glossary terms are included.")

    st.markdown("### What I need to do next")
    action_items = sections.get("what_i_need_to_do_next") or []
    if action_items:
        for item in action_items:
            st.write(f"- {item}")
    else:
        st.write("No confirmed action items are included.")

    st.markdown("### Understanding checklist")
    checklist_labels = [
        ("transcript_reviewed", "Transcript reviewed"),
        ("glossary_terms_reviewed", "Glossary terms reviewed"),
        ("action_items_confirmed", "Action items confirmed"),
        ("final_notes_ready", "Final notes ready"),
    ]
    for key, label in checklist_labels:
        st.checkbox(label, value=bool(checklist.get(key)), disabled=True, key=f"participant_check_{key}")

    st.markdown("### Accessibility risk flags")
    for flag in risk_flags.values():
        status = "Needs attention" if flag.get("active") else "Clear"
        count = flag.get("count", 0)
        st.markdown(f"**{flag.get('label', 'Risk flag')}**: {status} ({count})")
        st.write(flag.get("details", ""))


def render_final_summary(intelligence: dict) -> None:
    review_items = st.session_state.get("review_items", {})
    approved_glossary = approved_glossary_from_review(review_items)
    gate = review_gate_status(review_items)
    st.session_state["approved_glossary"] = approved_glossary

    if not approved_glossary:
        st.warning("No terms have been approved or edited. The final glossary will be empty.")

    if not gate["ready"]:
        st.warning(
            "Final notes and exports are locked until review is complete. "
            f"{gate['pending']} of {gate['total']} explanation(s) are still pending."
        )

    if st.button("Generate Final Accessible Notes", type="primary", disabled=not intelligence or not gate["ready"]):
        st.session_state["final_summary"] = generate_final_summary(
            transcript=st.session_state["transcript_corrected"],
            simplifications=intelligence["simplifications"],
            action_items=normalize_action_items(st.session_state.get("action_items_review_text", "")),
            review_items=review_items,
            review_audit=st.session_state["review_audit"],
            asr_status=st.session_state["asr_status"],
            llm_status=st.session_state["llm_status"],
        )
        st.session_state["final_summary"]["participant_accessibility_view"] = build_participant_accessibility_view(
            st.session_state["final_summary"],
            transcript_raw=st.session_state.get("transcript_raw", ""),
        )

    summary = st.session_state.get("final_summary")
    if not summary:
        return
    if "participant_accessibility_view" not in summary:
        summary["participant_accessibility_view"] = build_participant_accessibility_view(
            summary,
            transcript_raw=st.session_state.get("transcript_raw", ""),
        )

    st.subheader("Final Accessible Meeting Notes")
    st.markdown("**Readable corrected transcript**")
    st.text_area(
        "Corrected transcript used for final notes",
        value=summary["transcript"],
        height=170,
        disabled=True,
    )

    st.markdown("**Plain English summary**")
    st.write(summary["plain_english_summary"])

    st.markdown("**Key terms**")
    if summary["key_terms"]:
        for term in summary["key_terms"]:
            st.write(f"- **{term['term']}**: {term['canonical']}")
    else:
        st.write("- No approved key terms yet.")

    st.markdown("**Action items**")
    if summary["action_items"]:
        for item in summary["action_items"]:
            st.write(f"- {item}")
    else:
        st.write("- No action items generated.")

    st.markdown("**Human-approved glossary**")
    if summary["human_approved_glossary"]:
        for entry in summary["human_approved_glossary"]:
            st.write(f"- **{entry['term']}** ({entry['canonical']}): {entry['explanation']}")
    else:
        st.write("- No approved glossary entries yet.")

    render_participant_accessibility_view(summary["participant_accessibility_view"])

    metadata = summary["model_metadata"]
    st.caption(
        f"ASR: {metadata['asr'].get('provider')} `{metadata['asr'].get('model')}` | "
        f"LLM: {metadata['llm'].get('provider')} `{metadata['llm'].get('model')}`"
    )

    with st.expander("Review audit"):
        if summary["review_audit"]:
            st.json(summary["review_audit"])
        else:
            st.write("No review actions recorded.")

    st.download_button(
        "Download summary as JSON",
        data=final_summary_to_json(summary),
        file_name="meetingbridge_summary.json",
        mime="application/json",
    )
    st.download_button(
        "Download summary as Markdown",
        data=final_summary_to_markdown(summary),
        file_name="meetingbridge_summary.md",
        mime="text/markdown",
    )


def main() -> None:
    st.set_page_config(page_title="MeetingBridge AI", layout="wide")
    initialize_session_state()
    inject_accessible_theme()

    render_hero()
    render_workflow_stepper()

    with st.sidebar:
        st.header("Models")
        st.caption("Local-only model controls. Missing setup is shown as a blocker in the main flow.")
        asr_provider_label = st.selectbox(
            "ASR provider",
            ["Auto: MLX Whisper, then faster-whisper", "MLX Whisper", "faster-whisper"],
        )
        provider_map = {
            "Auto: MLX Whisper, then faster-whisper": "auto",
            "MLX Whisper": "mlx_whisper",
            "faster-whisper": "faster_whisper",
        }
        asr_provider = provider_map[asr_provider_label]
        mlx_model = st.text_input("MLX Whisper model", value=MLX_WHISPER_MODEL)
        faster_model = st.selectbox("faster-whisper model", ["small.en", "base.en"], index=0)
        if not faster_model:
            faster_model = FASTER_WHISPER_MODEL

        st.divider()
        llm_provider_label = st.selectbox("LLM provider", ["Ollama", "LM Studio"])
        llm_provider = "ollama" if llm_provider_label == "Ollama" else "lm_studio"
        ollama_model = st.selectbox("Ollama model", ["qwen3:8b", "gemma3:12b", "mistral:7b"])
        ollama_base_url = st.text_input("Ollama base URL", value=OLLAMA_DEFAULT_URL)
        lm_studio_model = st.text_input("LM Studio model", value="", help="Leave blank to use the first loaded LM Studio model.")
        lm_studio_base_url = st.text_input("LM Studio base URL", value=LM_STUDIO_DEFAULT_URL)
        llm_timeout = st.number_input("LLM timeout seconds", min_value=5, max_value=180, value=45, step=5)
        run_checks = st.button("Run preflight checks", type="primary")
        show_diagnostics = st.checkbox("Show model diagnostics")
        if st.button("Reset session", use_container_width=True):
            reset_audio_state()
            st.rerun()

    if not run_checks and "preflight_results" in st.session_state:
        results = st.session_state["preflight_results"]
    else:
        results = {
            "Streamlit audio": check_streamlit_audio_available(),
            "MLX Whisper": check_mlx_whisper_import(),
            "faster-whisper backup": check_faster_whisper_import(),
            "Ollama": check_ollama_model(ollama_base_url, ollama_model),
        }
        if lm_studio_model.strip():
            results["LM Studio"] = check_lm_studio_model(lm_studio_base_url, lm_studio_model.strip())
        st.session_state["preflight_results"] = results

    has_setup_blocker = any(not result.ready for result in results.values())
    if has_setup_blocker:
        st.warning("Setup blocker detected. Open readiness details for the exact fix.")
    with st.expander("Setup readiness", expanded=has_setup_blocker):
        st.write("Local model checks stay here so audio capture remains the main workspace.")
        render_preflight_cards(results)
    if show_diagnostics:
        with st.expander("Detailed readiness messages"):
            for label, result in results.items():
                st.markdown(f"**{label}**")
                render_result(result)

    render_section_intro(
        "Meeting audio",
        "Record with the browser microphone or upload a meeting clip. The transcript field appears only after local ASR runs.",
    )

    with st.container(border=True):
        audio_columns = st.columns([1.1, 1])
        with audio_columns[0]:
            recorded_audio = st.audio_input("Record meeting audio", sample_rate=16000)
        with audio_columns[1]:
            uploaded_audio = st.file_uploader(
                "Upload meeting audio",
                type=["wav", "mp3", "m4a", "mp4"],
            )
        with st.expander("Demo sentence"):
            st.code(DEMO_SENTENCE, language="text")

    audio_obj, audio_source = selected_audio(recorded_audio, uploaded_audio)
    if recorded_audio is not None and uploaded_audio is not None:
        st.info("Both sources are present. The microphone recording will be transcribed.")

    transcribe_disabled = audio_obj is None
    if transcribe_disabled:
        st.warning("Record microphone audio or upload an audio file before transcription.")

    with st.container(border=True):
        col_transcribe, col_clear = st.columns([2, 1])
        with col_transcribe:
            transcribe_clicked = st.button(
                "Transcribe audio",
                type="primary",
                disabled=transcribe_disabled,
                use_container_width=True,
            )
        with col_clear:
            if st.button("Clear audio and transcript", use_container_width=True):
                reset_audio_state()
                st.rerun()

    if transcribe_clicked and audio_obj is not None and audio_source is not None:
        try:
            remove_temp_audio(st.session_state.get("audio_temp_path"))
            saved_audio = save_audio_file(audio_obj, audio_source)
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.session_state["audio_source"] = saved_audio.source
            st.session_state["audio_filename"] = saved_audio.filename
            st.session_state["audio_temp_path"] = saved_audio.path
            st.session_state["audio_bytes_count"] = saved_audio.bytes_count
            st.session_state["transcript_source"] = saved_audio.source

            with st.spinner("Transcribing locally with the selected real ASR model..."):
                result = transcribe_audio(
                    saved_audio.path,
                    provider=asr_provider,
                    mlx_model=mlx_model.strip() or MLX_WHISPER_MODEL,
                    faster_model=faster_model,
                )

            st.session_state["asr_result"] = result
            st.session_state["asr_status"] = {
                "ready": bool(result["ok"]),
                "provider": result.get("provider"),
                "model": result.get("model"),
                "last_error": result.get("error"),
                "last_transcribed_at": datetime.now(timezone.utc).isoformat(),
            }
            if result["ok"]:
                st.session_state["transcript_raw"] = result["text"]
                st.session_state["transcript_corrected"] = result["text"]
                st.session_state["baseline_terms"] = []
                st.session_state["merged_terms"] = []
                st.session_state["meeting_intelligence"] = None
                st.session_state["review_items"] = {}
                st.session_state["review_audit"] = []
                st.session_state["approved_glossary"] = {}
                st.session_state["action_items_review_text"] = ""
                st.session_state["final_summary"] = None
            else:
                st.session_state["transcript_raw"] = ""
                st.session_state["transcript_corrected"] = ""

    if st.session_state["asr_status"]["last_transcribed_at"]:
        render_section_intro(
            "Transcript",
            "Correct recognition errors before jargon detection or LLM simplification runs.",
        )
        status = st.session_state["asr_status"]
        st.markdown(
            f"**Source:** {st.session_state['audio_source']} | "
            f"**File:** {st.session_state['audio_filename']} | "
            f"**ASR:** {status['provider']} `{status['model']}`"
        )

    asr_result = st.session_state.get("asr_result")
    if asr_result and asr_result.get("fallback_errors"):
        with st.expander("MLX primary fallback details"):
            for error in asr_result["fallback_errors"]:
                st.error(error)

    if st.session_state["transcript_raw"]:
        transcript_columns = st.columns(2)
        with transcript_columns[0]:
            with st.container(border=True):
                st.markdown("**Raw ASR transcript**")
                st.write(st.session_state["transcript_raw"])
        with transcript_columns[1]:
            with st.container(border=True):
                st.markdown("**Corrected transcript**")
                st.session_state["transcript_corrected"] = st.text_area(
                    "Correct transcript before AI analysis",
                    value=st.session_state["transcript_corrected"],
                    height=180,
                )
        corrected_transcript = st.session_state["transcript_corrected"].strip()
        baseline_terms = detect_terms(corrected_transcript)
        st.session_state["baseline_terms"] = baseline_terms

        render_section_intro(
            "Explain",
            "Run the selected local LLM after the transcript looks right.",
        )
        with st.expander("Baseline jargon candidates", expanded=False):
            if baseline_terms:
                st.dataframe(
                    [
                        {
                            "term": term["term"],
                            "canonical": term["canonical"],
                            "source": term["source"],
                            "confidence": term["confidence"],
                            "needs_review": term["needs_review"],
                        }
                        for term in baseline_terms
                    ],
                    hide_index=True,
                    use_container_width=True,
                )
            else:
                st.info("No baseline jargon candidates were found in the corrected transcript.")

        llm_model = ollama_model if llm_provider == "ollama" else lm_studio_model.strip()
        llm_base_url = ollama_base_url if llm_provider == "ollama" else lm_studio_base_url
        analyze_clicked = st.button(
            "Analyze with local LLM",
            type="primary",
            disabled=not corrected_transcript,
            use_container_width=True,
        )
        if analyze_clicked:
            config = LLMConfig(
                provider=llm_provider,
                model=llm_model,
                base_url=llm_base_url,
                timeout=float(llm_timeout),
            )
            with st.spinner("Running real local LLM analysis..."):
                try:
                    intelligence = generate_meeting_intelligence(corrected_transcript, baseline_terms, config)
                except LLMClientError as exc:
                    st.session_state["meeting_intelligence"] = None
                    st.session_state["merged_terms"] = baseline_terms
                    st.session_state["review_items"] = {}
                    st.session_state["approved_glossary"] = {}
                    st.session_state["action_items_review_text"] = ""
                    st.session_state["final_summary"] = None
                    st.session_state["llm_status"] = {
                        "ready": False,
                        "provider": llm_provider,
                        "model": llm_model or None,
                        "last_error": str(exc),
                        "action": exc.action,
                        "last_analyzed_at": datetime.now(timezone.utc).isoformat(),
                    }
                else:
                    merged_terms = detect_terms(corrected_transcript, llm_terms=intelligence["glossary"])
                    st.session_state["meeting_intelligence"] = intelligence
                    st.session_state["merged_terms"] = merged_terms
                    st.session_state["review_items"] = initialize_review_items(
                        merged_terms,
                        model=intelligence["model"],
                    )
                    st.session_state["review_audit"] = []
                    st.session_state["approved_glossary"] = {}
                    st.session_state["action_items_review_text"] = "\n".join(intelligence.get("action_items", []))
                    st.session_state["final_summary"] = None
                    st.session_state["llm_status"] = {
                        "ready": True,
                        "provider": intelligence["provider"],
                        "model": intelligence["model"],
                        "last_error": None,
                        "action": None,
                        "last_analyzed_at": datetime.now(timezone.utc).isoformat(),
                    }

        llm_status = st.session_state["llm_status"]
        if llm_status["last_analyzed_at"]:
            if llm_status["ready"]:
                st.success(f"LLM analysis used {llm_status['provider']} `{llm_status['model']}`.")
            else:
                st.error(llm_status["last_error"])
                if llm_status.get("action"):
                    st.code(llm_status["action"], language="bash")

        intelligence = st.session_state.get("meeting_intelligence")
        if intelligence:
            st.markdown("**LLM simplification levels**")
            simple_tab, professional_tab, expert_tab = st.tabs(["Simple", "Professional", "Expert"])
            with simple_tab:
                st.write(intelligence["simplifications"]["simple"])
            with professional_tab:
                st.write(intelligence["simplifications"]["professional"])
            with expert_tab:
                st.write(intelligence["simplifications"]["expert"])

            if intelligence["action_items"]:
                st.markdown("**Action items**")
                for item in intelligence["action_items"]:
                    st.write(f"- {item}")

        merged_terms = st.session_state.get("merged_terms") or baseline_terms
        if intelligence and merged_terms:
            with st.expander("Merged glossary candidates", expanded=False):
                st.dataframe(
                    [
                        {
                            "term": term["term"],
                            "canonical": term["canonical"],
                            "explanation": term["explanation"],
                            "source": term["source"],
                            "confidence": term["confidence"],
                            "needs_review": term["needs_review"],
                        }
                        for term in merged_terms
                    ],
                    hide_index=True,
                    use_container_width=True,
                )

        if intelligence:
            render_section_intro(
                "Review",
                "AI output stays pending until a human approves, edits, or rejects each explanation.",
            )
            render_review_panel()

            if review_gate_status(st.session_state.get("review_items", {}))["ready"]:
                render_action_item_review(intelligence)
                render_section_intro(
                    "Notes and export",
                    "Generate participant notes after review, then download JSON, Markdown, or audit records.",
                )
                render_final_summary(intelligence)
    elif st.session_state["asr_status"]["last_error"]:
        render_section_intro(
            "Transcript",
            "Local ASR did not complete. Fix the setup issue and transcribe again.",
        )
        st.error(st.session_state["asr_status"]["last_error"])
        st.code(
            "pip install -r requirements.txt\n"
            "python -c \"import mlx_whisper; print('mlx ready')\"\n"
            "python -c \"import faster_whisper; print('faster-whisper ready')\"",
            language="bash",
        )

    if show_diagnostics:
        st.subheader("Diagnostics")
        st.json(
            {
                "audio_source": st.session_state["audio_source"],
                "audio_filename": st.session_state["audio_filename"],
                "audio_bytes_count": st.session_state["audio_bytes_count"],
                "asr_status": st.session_state["asr_status"],
                "llm_status": st.session_state["llm_status"],
                "baseline_terms": st.session_state["baseline_terms"],
                "merged_terms": st.session_state["merged_terms"],
                "review_items": st.session_state["review_items"],
                "review_audit": st.session_state["review_audit"],
                "action_items_review_text": st.session_state["action_items_review_text"],
                "final_summary": st.session_state["final_summary"],
            }
        )


if __name__ == "__main__":
    main()
