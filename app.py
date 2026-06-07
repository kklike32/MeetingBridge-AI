from __future__ import annotations

import streamlit as st

from src.model_preflight import (
    PreflightResult,
    check_faster_whisper_import,
    check_lm_studio_model,
    check_mlx_whisper_import,
    check_ollama_model,
    check_streamlit_audio_available,
)


OLLAMA_DEFAULT_URL = "http://localhost:11434"
LM_STUDIO_DEFAULT_URL = "http://localhost:1234/v1"


def render_result(result: PreflightResult) -> None:
    if result.ready:
        st.success(result.message)
        return

    st.error(result.message)
    if result.action:
        st.code(result.action, language="bash")


def main() -> None:
    st.set_page_config(page_title="MeetingBridge AI", layout="wide")
    st.title("MeetingBridge AI")
    st.caption("Local setup readiness")

    with st.sidebar:
        st.header("Models")
        ollama_model = st.selectbox("Ollama model", ["qwen3:8b", "gemma3:12b", "mistral:7b"])
        ollama_base_url = st.text_input("Ollama base URL", value=OLLAMA_DEFAULT_URL)
        lm_studio_model = st.text_input("LM Studio model", value="")
        lm_studio_base_url = st.text_input("LM Studio base URL", value=LM_STUDIO_DEFAULT_URL)
        run_checks = st.button("Run preflight checks", type="primary")

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

    st.info("Phase 1 and Phase 2 are implemented. Audio input, transcription, jargon detection, LLM analysis, review, and export are intentionally not wired yet.")


if __name__ == "__main__":
    main()
