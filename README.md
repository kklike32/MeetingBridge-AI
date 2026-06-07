<p align="center">
  <img src="./assets/meetingbridge-logo.svg" alt="MeetingBridge AI logo" width="760">
</p>

<h1 align="center">MeetingBridge AI</h1>

<p align="center">
  <strong>Real meeting audio in. Human-approved plain English out.</strong>
</p>

<p align="center">
  <a href="#quick-start"><img alt="Run locally" src="https://img.shields.io/badge/Run-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white"></a>
  <a href="#required-models"><img alt="Local AI" src="https://img.shields.io/badge/AI-Local_Models-2850B8?style=for-the-badge"></a>
  <a href="#two-minute-demo"><img alt="Two minute demo" src="https://img.shields.io/badge/Demo-2_Minutes-20B486?style=for-the-badge"></a>
  <a href="#human-review"><img alt="Human in the loop" src="https://img.shields.io/badge/Human-Review_Required-FF8A4C?style=for-the-badge"></a>
</p>

## The Problem

Meetings can be technically "accessible" and still be hard to understand.

Transcripts capture words, but they do not explain what those words mean. A new hire, intern, non-native English speaker, hard-of-hearing participant, or cross-functional teammate can read every line and still get stuck on shorthand like:

- `GTM`
- `ARR`
- `PLG`
- `churn`
- `enterprise accounts`

MeetingBridge AI turns that gap into a demo-ready accessibility workflow: real audio, local transcription, local LLM explanation, and a human reviewer before anything becomes final.

## The Solution

MeetingBridge AI is a local Streamlit app that helps people understand meetings without sending the demo path to cloud AI services.

| Stage | What Happens | Why It Matters |
| --- | --- | --- |
| Audio | Record in the browser or upload a meeting clip | The demo starts from real meeting audio, not pasted text |
| ASR | Transcribe with MLX Whisper or faster-whisper | Participants get an editable transcript from a real local speech model |
| Explain | Generate simple, professional, and expert rewrites with a local LLM | Meeting language becomes understandable at multiple levels |
| Review | Approve, edit, or reject every explanation | AI is helpful, but the human remains the final authority |
| Notes | Export reviewed participant notes, glossary, action items, and audit trail | The final output reflects human-approved meaning |

## Demo Flow

```text
Microphone or audio upload
  -> local ASR transcript
  -> transcript correction
  -> local LLM simplification
  -> human glossary review
  -> final accessible notes
```

No mock output. No fake transcript. No paste-only demo shortcut.

## Quick Start

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt
ollama pull qwen3:8b
./.venv/bin/streamlit run app.py
```

Open the Streamlit URL and click `Check setup`. The app will show readiness blockers for missing local models or dependencies.

## Required Models

Primary LLM:

```bash
ollama pull qwen3:8b
```

Real LLM backups:

```bash
ollama pull gemma3:12b
ollama pull mistral:7b
```

Primary ASR:

```text
mlx-whisper
model: mlx-community/whisper-large-v3-turbo
```

Real ASR backup:

```text
faster-whisper
model: small.en or base.en
```

Import checks:

```bash
./.venv/bin/python -c "import mlx_whisper; print('mlx-whisper ready')"
./.venv/bin/python -c "import faster_whisper; print('faster-whisper ready')"
```

MLX Whisper may need normal macOS Metal/GPU access. If MLX is unavailable during the demo, switch to the real `faster-whisper` backup in the sidebar.

## Exact Demo Sentence

Speak this sentence into the microphone or upload an audio clip containing it:

```text
Let's revisit our GTM motion before Q3 and improve ARR through our PLG initiative while reducing churn across enterprise accounts.
```

Expected terms:

`GTM` | `Q3` | `ARR` | `PLG` | `churn` | `enterprise accounts`

## Audio Instructions

1. Click `Record audio` and speak the exact demo sentence.
2. If browser microphone permission fails, use `Upload audio` with a short WAV, MP3, M4A, or MP4 recording of the same sentence.
3. Click `Transcribe audio`.
4. Correct only ASR mistakes in the transcript field.
5. Click `Analyze locally`.
6. Review every glossary explanation.
7. Click `Generate notes`.

Text correction exists only after real ASR has produced a transcript.

## Human Review

The demo should visibly show that the AI does not get the last word.

Suggested review sequence:

- Approve `GTM`.
- Edit `ARR` to: `The predictable subscription revenue the business expects each year.`
- Reject one ambiguous term if it appears, such as `motion`.

The final notes should include approved and edited terms only. Rejected terms stay out of the human-approved glossary.

## Two-Minute Demo

**0:00-0:15 - Problem**

"Meeting transcripts capture words, but they do not explain meaning. If you are new to a team, joining from another function, or using transcripts for accessibility, acronyms like GTM, ARR, PLG, and churn can block participation."

**0:15-0:30 - Real Audio**

"MeetingBridge AI starts from real meeting audio. I can record through the browser or upload a clip. I will record a short meeting sentence now."

Speak the exact demo sentence.

**0:30-0:50 - Local Transcription**

"The audio is transcribed locally. ASR can mishear acronyms, so I can correct the transcript before analysis."

**0:50-1:15 - Local LLM**

"Now the corrected transcript goes to a real local LLM. Qwen3 8B generates three versions: simple, professional, and expert."

**1:15-1:35 - Human Review**

"AI suggestions stay pending until a human approves, edits, or rejects them."

Approve `GTM`, edit `ARR`, and reject an ambiguous term if one appears.

**1:35-2:00 - Final Notes**

"The final notes use the reviewed glossary, not raw AI output. Participants get a plain-English summary, key terms, action items, and a review audit."

Show the edited `ARR` explanation in the final glossary.

## Why It Fits The Track

- **AI for Accessibility:** Meeting content becomes understandable for people who need more than a transcript.
- **Human-in-the-Loop AI:** Every explanation must pass human review before final output.
- **Local AI:** The demo path uses local ASR and local LLM models.
- **Hackathon Feasibility:** The app is one Streamlit workflow with session state and export buttons, not production infrastructure.

## Verification

Run the lightest checks before committing:

```bash
./.venv/bin/python -m compileall app.py src tests
./.venv/bin/python -m unittest discover tests
```

For live validation:

```bash
./.venv/bin/streamlit run app.py
```

Then complete the real-audio flow in the browser. If a model is missing, the app should show setup instructions instead of fabricating AI output.

## Repository Rules

Commit source, tests, docs, and docs assets only. Do not commit `.venv/`, `__pycache__/`, generated audio, model files, exported review logs, `AGENTS.md`, `.agents/`, or runtime artifacts.
