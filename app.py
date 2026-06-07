from __future__ import annotations

from datetime import datetime, timezone

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
    "llm_status": {
        "ready": False,
        "provider": None,
        "model": None,
        "last_error": None,
        "action": None,
        "last_analyzed_at": None,
    },
}


def render_result(result: PreflightResult) -> None:
    if result.ready:
        st.success(result.message)
        return

    st.error(result.message)
    if result.action:
        st.code(result.action, language="bash")


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


def main() -> None:
    st.set_page_config(page_title="MeetingBridge AI", layout="wide")
    initialize_session_state()

    st.title("MeetingBridge AI")
    st.caption("Real meeting audio to local transcript and human-corrected meeting language")

    with st.sidebar:
        st.header("Models")
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
        if st.button("Reset session"):
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

    st.subheader("Readiness")
    columns = st.columns(2)
    for index, (label, result) in enumerate(results.items()):
        with columns[index % 2]:
            st.markdown(f"**{label}**")
            render_result(result)

    st.subheader("Required Audio")
    st.write("Speak or upload this meeting sentence:")
    st.code(DEMO_SENTENCE, language="text")

    audio_columns = st.columns(2)
    with audio_columns[0]:
        recorded_audio = st.audio_input("Record the meeting sentence", sample_rate=16000)
    with audio_columns[1]:
        uploaded_audio = st.file_uploader(
            "Upload meeting audio",
            type=["wav", "mp3", "m4a", "mp4"],
        )

    audio_obj, audio_source = selected_audio(recorded_audio, uploaded_audio)
    if recorded_audio is not None and uploaded_audio is not None:
        st.info("Both sources are present. The microphone recording will be transcribed.")

    transcribe_disabled = audio_obj is None
    if transcribe_disabled:
        st.warning("Record microphone audio or upload an audio file before transcription.")

    col_transcribe, col_clear = st.columns([1, 1])
    with col_transcribe:
        transcribe_clicked = st.button(
            "Transcribe audio",
            type="primary",
            disabled=transcribe_disabled,
        )
    with col_clear:
        if st.button("Clear audio and transcript"):
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
            else:
                st.session_state["transcript_raw"] = ""
                st.session_state["transcript_corrected"] = ""

    st.subheader("Transcription")
    if st.session_state["asr_status"]["last_transcribed_at"]:
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
        st.markdown("**Raw ASR transcript**")
        st.write(st.session_state["transcript_raw"])
        st.session_state["transcript_corrected"] = st.text_area(
            "Correct transcript before AI analysis",
            value=st.session_state["transcript_corrected"],
            height=140,
        )
        corrected_transcript = st.session_state["transcript_corrected"].strip()
        baseline_terms = detect_terms(corrected_transcript)
        st.session_state["baseline_terms"] = baseline_terms

        st.subheader("Baseline Jargon Detection")
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
            st.subheader("LLM Simplification")
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
        if merged_terms:
            st.subheader("Merged Glossary Candidates")
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
    elif st.session_state["asr_status"]["last_error"]:
        st.error(st.session_state["asr_status"]["last_error"])
        st.code(
            "pip install -r requirements.txt\n"
            "python -c \"import mlx_whisper; print('mlx ready')\"\n"
            "python -c \"import faster_whisper; print('faster-whisper ready')\"",
            language="bash",
        )
    else:
        st.info("Transcribe a recorded or uploaded clip to unlock the correction field.")

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
            }
        )


if __name__ == "__main__":
    main()
