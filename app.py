from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from src.audio_inputs import remove_temp_audio, save_audio_file
from src.demo_assets import DEMO_SENTENCE
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
        st.session_state.setdefault(key, value.copy() if isinstance(value, dict) else value)


def reset_audio_state() -> None:
    remove_temp_audio(st.session_state.get("audio_temp_path"))
    for key, value in SESSION_DEFAULTS.items():
        st.session_state[key] = value.copy() if isinstance(value, dict) else value


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
        ollama_model = st.selectbox("Ollama model", ["qwen3:8b", "gemma3:12b", "mistral:7b"])
        ollama_base_url = st.text_input("Ollama base URL", value=OLLAMA_DEFAULT_URL)
        lm_studio_model = st.text_input("LM Studio model", value="")
        lm_studio_base_url = st.text_input("LM Studio base URL", value=LM_STUDIO_DEFAULT_URL)
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
        st.info("Next phase will analyze the corrected transcript with local jargon detection and a real local LLM.")
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
            }
        )


if __name__ == "__main__":
    main()
