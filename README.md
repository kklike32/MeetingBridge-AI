# MeetingBridge AI

Local Streamlit MVP for real meeting audio transcription, local LLM simplification, and human-reviewed explanations.

Repository: https://github.com/kklike32/MeetingBridge-AI

This repo is currently implemented through Phase 8:

- Phase 1: runtime files and minimal Streamlit page
- Phase 2: dependency and local model preflight
- Phase 3: required microphone recording and audio upload
- Phase 4: real local ASR transcription with MLX Whisper primary and faster-whisper backup
- Phase 5: static dictionary, acronym detection, and baseline heuristic jargon detection
- Phase 6: real local LLM simplification, JSON validation, retry handling, and merged glossary candidates
- Phase 7: human review with approve, edit, reject, session-state audit trail, and approved glossary generation
- Phase 8: final summary with model metadata plus JSON, Markdown, and review audit exports

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

This project uses the repo-local `.venv`. Run app and verification commands through that environment:

```bash
./.venv/bin/streamlit run app.py
./.venv/bin/python -m unittest tests/test_model_preflight.py
./.venv/bin/python -m unittest tests/test_audio_inputs.py tests/test_transcription.py
```

Primary local LLM:

```bash
ollama pull qwen3:8b
```

Optional real LLM backups:

```bash
ollama pull gemma3:12b
ollama pull mistral:7b
```

Primary ASR package:

```bash
pip install mlx-whisper mlx
```

Real ASR backup:

```bash
pip install faster-whisper
```

## Run

```bash
./.venv/bin/streamlit run app.py
```

The app shows readiness for Streamlit microphone support, MLX Whisper, faster-whisper, Ollama, and optionally LM Studio. Missing dependencies or models are shown as setup blockers rather than silently falling back to fake output.

The demo must start from real audio:

1. Record the demo sentence with the browser microphone, or upload a short WAV/MP3/M4A/MP4 clip.
2. Click `Transcribe audio`.
3. Review the raw ASR transcript.
4. Correct the transcript only after ASR has produced text.
5. Review baseline jargon candidates.
6. Click `Analyze with local LLM` to generate real model simplifications and merged glossary candidates.
7. Review terms: approve `GTM`, edit `ARR` to `The predictable subscription revenue the business expects each year.`, and reject an ambiguous term such as `motion` if it appears.
8. Generate the final summary and confirm rejected terms are excluded while edited explanations appear in the human-approved glossary.
9. Download the summary as JSON or Markdown, or export the review audit JSON.

There is no paste-only transcript route and no fake transcription fallback.

LLM analysis uses the selected real local model only. If Ollama or LM Studio is unavailable, or if the selected model is missing or returns malformed JSON after one retry, the app shows the setup/model error and does not generate fake simplifications.

Review state is local to the current Streamlit session. The app does not write a database; review decisions and audit entries are available through explicit download buttons.

MLX Whisper requires Apple Metal/GPU access. In sandboxed or headless sessions, the package can be installed but fail at runtime with a Metal device error. In that case, run the Streamlit app from a normal macOS Terminal session or use the real `faster-whisper` backup path.

## Git Workflow

The repository is initialized on `main` and tracks `origin/main`.

Commit only required source, tests, and documentation:

- `app.py`
- `requirements.txt`
- `src/`
- `tests/`
- tracked project `.md` files such as `README.md`, `PRD.md`, `PROMPTS.md`, and `SUBMISSION.md`

Do not commit `.venv/`, `__pycache__/`, generated audio, model files, `data/` exports, `AGENTS.md`, `.agents/`, or other local runtime artifacts.

Before pushing, run the lightest relevant checks, then:

```bash
git status --short
git add <required-files>
git commit -m "<clear message>"
git push
```

## Demo Sentence

```text
Let's revisit our GTM motion before Q3 and improve ARR through our PLG initiative while reducing churn across enterprise accounts.
```
