# MeetingBridge AI

Local Streamlit MVP for real meeting audio transcription, local LLM simplification, and human-reviewed explanations.

Repository: https://github.com/kklike32/MeetingBridge-AI

This repo is currently scaffolded through Phase 2 only:

- Phase 1: runtime files and minimal Streamlit page
- Phase 2: dependency and local model preflight

Audio recording, upload, transcription, jargon detection, LLM analysis, human review, and export are intentionally not implemented yet.

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

MLX Whisper requires Apple Metal/GPU access. In sandboxed or headless sessions, the package can be installed but fail at runtime with a Metal device error. In that case, run the Streamlit app from a normal macOS Terminal session or use the real `faster-whisper` backup path when transcription is implemented.

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
