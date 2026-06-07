# MeetingBridge AI Submission

## Project Title

MeetingBridge AI

## Team Name

MeetingBridge Builder

## Team Number

7

## Track

TRACK 2: AI for Accessibility

## One-Sentence Pitch

MeetingBridge AI turns real meeting audio into human-approved plain English notes, so participants are not left behind by fast speech, acronyms, or workplace jargon.

## Short Pitch

Meetings can be technically documented and still be hard to understand. Captions and transcripts capture words, but they often do not explain meaning. MeetingBridge AI starts with real browser-recorded or uploaded audio, transcribes it locally, explains jargon with a local LLM, and requires a human to approve, edit, or reject every explanation before final notes are generated.

The core promise is simple: real audio in, human-approved understanding out.

## The Problem

Modern meetings move quickly. People use acronyms, shorthand, metrics, and domain-specific phrases as if everyone in the room has the same context.

That creates an accessibility and inclusion gap for:

- Deaf and hard-of-hearing participants who rely on transcripts or notes.
- Non-native English speakers.
- New hires and interns.
- Cross-functional teammates.
- Students or conference attendees joining a specialized conversation.

The problem is not only hearing the words. The problem is understanding what the words mean quickly enough to participate.

## The Solution

MeetingBridge AI is a local Streamlit app that converts a short meeting clip into accessible meeting notes through a human-in-the-loop workflow:

1. Record meeting audio in the browser or upload an audio file.
2. Transcribe the audio with a real local ASR model.
3. Correct the transcript only after ASR produces text.
4. Detect acronyms, jargon, and confusing phrases.
5. Generate simple, professional, and expert explanations with a real local LLM.
6. Let a human approve, edit, or reject every explanation.
7. Generate final participant notes with a reviewed glossary, action items, metadata, and audit trail.

MeetingBridge AI does not create a text-only shortcut, fake transcript, or mock LLM path for the demo.

## Demo Sentence

```text
Let's revisit our GTM motion before Q3 and improve ARR through our PLG initiative while reducing churn across enterprise accounts.
```

Expected highlighted terms:

`GTM` | `Q3` | `ARR` | `PLG` | `churn` | `enterprise accounts`

## Demo Flow

```text
Microphone or uploaded audio
  -> local ASR transcript
  -> transcript correction
  -> local LLM simplification
  -> human glossary review
  -> final accessible notes
```

Suggested one-minute demo:

- Explain that transcripts show words but not always meaning.
- Record or upload the exact demo sentence.
- Transcribe with local ASR.
- Correct any ASR acronym mistakes.
- Analyze locally with Qwen3 8B through Ollama.
- Approve `GTM`, edit `ARR`, and reject an ambiguous term if one appears.
- Generate final notes and show that only approved or edited explanations appear.

## Technical Implementation

Frontend and orchestration:

- Streamlit single-page app.
- `st.audio_input` for microphone recording.
- `st.file_uploader` for audio upload.
- Session-state workflow instead of a database.
- JSON and Markdown exports.

Speech-to-text:

- Primary: `mlx-whisper`.
- Primary model: `mlx-community/whisper-large-v3-turbo`.
- Backup: `faster-whisper` with `small.en` or `base.en`.

Local LLM:

- Primary: Ollama `qwen3:8b`.
- Backups: Ollama `gemma3:12b`, Ollama `mistral:7b`, or LM Studio if a real local model is loaded.
- Prompts use `/no_think` and require strict JSON.
- Invalid JSON retries once, then shows an actionable setup/model error.

Human review:

- Every explanation starts pending.
- Review actions: approve, edit, reject.
- Edited explanations flow into the final glossary.
- Rejected explanations are excluded.
- Review audit is exportable as JSON.

Final output:

- Corrected transcript.
- Plain-English summary.
- Key terms.
- Confirmed action items.
- Human-approved glossary.
- Participant accessibility view.
- Model metadata.
- Review audit.

## Current Status

Prototype ready for live mock testing.

Implemented:

- Streamlit app shell and accessible visual theme.
- Model setup/readiness checks.
- Required microphone recording.
- Required audio upload.
- Real local ASR transcription path.
- Post-ASR transcript correction.
- Static, regex, heuristic, and LLM-assisted jargon detection.
- Real local LLM simplification with strict JSON handling.
- Human review gate with approve, edit, reject, progress counts, and audit trail.
- Action-item confirmation.
- Final accessible meeting notes.
- Participant accessibility view.
- JSON, Markdown, and audit exports.
- README, one-minute live script, and local logo asset.
- Unit tests for core helpers.

## What Makes It Different

Most meeting tools stop at transcription. MeetingBridge AI continues to comprehension.

The project is intentionally local-first for the demo path. It uses local ASR and local LLMs rather than hiding behind a hosted API. It is also human-in-the-loop by design: AI can suggest explanations, but the final glossary is controlled by the human reviewer.

That matters for accessibility because a confidently wrong explanation can be worse than no explanation. The app makes review visible and mandatory.

## AI Use

AI-assisted coding was used to help build and refine the app, documentation, and demo materials.

AI functionality inside the product includes:

- Local speech-to-text transcription.
- Local language simplification.
- Contextual jargon and acronym explanation.
- Action-item extraction.

Human reviewers remain responsible for the final approved meaning.

## Impact

Access to meetings is access to decisions. MeetingBridge AI helps participants understand what happened, what terms meant, and what to do next.

The accessibility-first benefit is for deaf and hard-of-hearing users who need clear reviewed meeting notes. The broader inclusion benefit is for anyone blocked by jargon, fast speech, or unfamiliar business language.

## Links

GitHub repository:

https://github.com/kklike32/MeetingBridge-AI

Video demo:

TBD

## Judging Rubric Mapping

- **Impact:** Helps people participate when transcripts alone are not enough.
- **Creativity:** Combines real audio, local ASR, local LLM simplification, jargon detection, and human approval in one short workflow.
- **Technical Execution:** Uses real local model paths, structured JSON validation, review state, exports, and automated helper tests.
- **Human-AI Collaboration:** AI proposes explanations; humans approve, edit, reject, and confirm the final meaning.
- **Presentation:** The live demo can be completed in about one minute using the exact required sentence and visible model readiness checks.
