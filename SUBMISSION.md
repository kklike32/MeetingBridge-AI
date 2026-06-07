# MeetingBridge AI Submission

## Project Title

MeetingBridge AI

## Name of the Team

MeetingBridge Builders

## Select the Track

TRACK 1: Human-in-the-Loop AI  
TRACK 2: AI for Accessibility

## Team Number

7

## One-Sentence Pitch

MeetingBridge AI turns meeting audio into readable, human-approved explanations for deaf and hard-of-hearing participants first, while also rescuing everyone else from phrases like "optimize the GTM motion."

## What problem are you solving?

Meetings still depend heavily on spoken language. For deaf and hard-of-hearing participants, that can mean missing context, tone, decisions, and follow-up items unless the meeting has strong accessibility support.

Transcription helps, but it is not always enough. A raw transcript can be fast, dense, messy, and full of jargon. MeetingBridge AI focuses on the full path from audio to understanding: capture the meeting, make it readable, explain the confusing parts, and let a human approve the final meaning.

## Who experiences this problem, and how often does it happen?

This project is intentionally weighted toward accessibility:

- 70%: deaf and hard-of-hearing people who need meeting audio converted into clear, reviewable text and explanations.
- 30%: people who can hear the meeting but still get lost in technical language, acronyms, and corporate shorthand.

It can happen daily in workplaces, classrooms, conferences, standups, customer calls, and project reviews. The meeting does not have to be hostile or badly run to exclude someone. Sometimes all it takes is fast speech, overlapping voices, missing captions, and one brave soul saying "PLG-led ARR expansion" like that is a normal thing humans say.

## What inspired the idea?

The idea came from a simple accessibility gap: a meeting can be important, fast-moving, and technically "documented," but still not truly accessible to someone who cannot rely on hearing the conversation live.

Captions and transcripts are a start. The next step is comprehension support: clearer text, glossary-style explanations, and a human review step so the final output is useful instead of just algorithmically confident.

## Describe your solution in simple language.

MeetingBridge AI is a local Streamlit app that starts with real meeting audio and turns it into accessible meeting support. The app checks whether local speech-to-text and local LLM models are ready, then the intended MVP flow is:

1. Record or upload meeting audio.
2. Transcribe the audio locally.
3. Let the user correct the transcript.
4. Detect important terms, confusing language, acronyms, and jargon.
5. Ask a real local LLM to explain the content at different simplicity levels.
6. Require a human to approve, edit, or reject each explanation.
7. Generate a final human-approved glossary and meeting summary that is easier to read after the meeting.

The AI helps convert and explain. The human decides what is accurate.

## Why does this matter?

Access to meetings is access to decisions. If deaf and hard-of-hearing participants cannot reliably follow what was said, they can be pushed out of the conversation even when they are invited to the calendar event.

MeetingBridge AI helps make meetings more inclusive by turning spoken discussion into text that can be reviewed, clarified, and trusted. The jargon support also matters, but the core mission is accessibility: helping people participate when audio alone is not enough.

## What makes your solution unique compared to existing alternatives?

Most tools stop at transcription. MeetingBridge AI focuses on accessibility plus comprehension.

It is human-in-the-loop by design. The app does not treat AI explanations as automatically correct, especially when accessibility is on the line. People can approve, rewrite, or reject explanations before anything becomes final.

The project is local-first, using real local ASR and local LLMs instead of sending sensitive meeting content to a hosted service. That matters for privacy, demos, and trust.

It also handles the second problem hiding inside many meetings: even once the words are visible, they may still be confusing. MeetingBridge AI can explain terms like GTM, ARR, PLG, churn, and other workplace vocabulary without pretending those are obvious to everyone.

## Current Status

Prototype

Current implementation status:

- Repo scaffold is in place.
- Streamlit app shell exists.
- Dependency and model preflight is implemented.
- Required microphone recording and audio upload are implemented.
- Real local ASR transcription is wired through MLX Whisper primary and faster-whisper backup.
- Transcript correction happens only after ASR output exists.
- Static, heuristic, acronym, and local LLM glossary candidates are merged for review.
- Real local LLM simplification is wired through Ollama or LM Studio with strict JSON validation and no mock fallback.
- Human review is implemented with approve, edit, reject, progress counts, a review gate, and an audit trail.
- Final accessible meeting notes are implemented with a readable corrected transcript, plain English summary, key terms, action items, human-approved glossary, ASR/LLM metadata, review audit, and JSON/Markdown downloads.
- Generated action items can be confirmed or edited before final notes.

## How was AI used in your solution?

AI-Assisted coding  
AI Functionality

AI was used in two ways:

- During development, AI helped scaffold the local app structure, model preflight checks, and project documentation.
- In the intended product flow, AI performs local speech-to-text transcription and local language simplification for accessibility-first meeting support, while human reviewers keep final authority over explanations.

## Paste the video demo link.

TBD

## Paste the GitHub repository link.

https://github.com/kklike32/MeetingBridge-AI
