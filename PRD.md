Product Requirements Document (PRD)

MeetingBridge AI

Real-Time Meeting Translation for Humans

Track

AI for Accessibility + Human-in-the-Loop AI

⸻

Vision

MeetingBridge AI makes meetings understandable for everyone.

The system listens to a meeting in real time and automatically:

* Transcribes speech
* Detects jargon, acronyms, and technical terminology
* Simplifies language into plain English
* Generates contextual explanations
* Allows a human participant to approve, reject, or improve AI explanations

The goal is not to replace human understanding.

The goal is to help participants understand discussions they would otherwise struggle to follow.

⸻

Problem Statement

Modern workplaces are filled with:

* Corporate jargon
* Technical terminology
* Acronyms
* Domain-specific language

Examples:

“We need to revisit our GTM motion before Q3 and improve cross-functional alignment.”

Many participants do not fully understand:

* Non-native English speakers
* Junior employees
* Interns
* New hires
* Accessibility users
* Cross-functional teams

Current meeting transcription tools capture words.

They do not explain meaning.

⸻

Proposed Solution

MeetingBridge AI acts as a real-time translation layer between experts and everyone else.

Input:

“We should leverage our PLG strategy to increase ARR before the next board review.”

Output:

Original:
“We should leverage our PLG strategy to increase ARR before the next board review.”

Plain English:
“We should use a product-led growth strategy to increase recurring revenue before the next board meeting.”

Glossary:

PLG
Product-Led Growth

ARR
Annual Recurring Revenue

Human Review:
✓ Approve
✎ Edit Explanation

⸻

Human-in-the-Loop Design

Human involvement is mandatory.

AI never becomes the final source of truth.

When confidence is low:

* Explanation highlighted yellow
* User review required

Example:

AI confidence: 61%

“Potentially ambiguous business terminology detected.”

User can:

* Approve explanation
* Edit explanation
* Reject explanation

The human correction becomes the final explanation.

⸻

Target Users

Primary:

* Non-native English speakers
* Junior employees
* New hires

Secondary:

* Hard-of-hearing users
* Students
* Conference attendees

⸻

Core Features

1. Live Transcription

Audio input

↓

Whisper

↓

Live transcript

Example:

“Let’s revisit the GTM strategy before Q3.”

⸻

2. Jargon Detection Engine

The system identifies:

* Acronyms
* Technical phrases
* Corporate buzzwords
* Industry-specific terminology

Examples:

GTM

ARR

EBITDA

SOC2

MLOps

Kubernetes

RAG

Multi-agent architecture

Synergy

Bandwidth

Leverage

Circle back

Deep dive

⸻

3. Context-Aware Simplification

The system generates:

Level 1:
Very Simple

Level 2:
Professional

Level 3:
Expert

Example:

Original:
“Let’s leverage our GTM motion.”

Simple:
“Let’s improve our plan for bringing the product to customers.”

Professional:
“Let’s improve our go-to-market strategy.”

Expert:
“Let’s optimize acquisition and revenue channels.”

⸻

4. Dynamic Glossary

Every detected term is clickable.

Clicking ARR shows:

ARR

Annual Recurring Revenue

Revenue expected from subscriptions over a year.

Generated automatically.

⸻

5. Human Review Panel

Each explanation includes:

Approve

Edit

Reject

Feedback stored locally.

⸻

6. Meeting Summary

Generated at the end.

Sections:

Key Topics

Decisions

Action Items

Glossary

Human Corrections

⸻

Open Source Model Selection

Transcription

Model:
Whisper Large-v3

Why:

* State-of-the-art open-source speech recognition
* Excellent speaker robustness
* Handles accents well
* Runs locally

Alternative:

Faster-Whisper Large-v3

Recommended for demo.

⸻

Language Model

Recommended:

Qwen3-8B-Instruct

Requirements:

* Released within the last 12 months
* Strong instruction following
* Strong reasoning
* Fits comfortably on local hardware
* Fast enough for live inference

Why not larger models?

Qwen3-30B:
Too slow for live demo

DeepSeek-R1:
Too large

Llama 4:
Not practical for local deployment during a hackathon

Gemma 3 12B:
Strong alternative

Final recommendation:

Qwen3-8B-Instruct

⸻

Jargon Detection Architecture

Do NOT use only a static dictionary.

Static dictionaries fail because:

Every company invents new terminology.

Instead use a hybrid approach.

Step 1

Preloaded glossary:

~100 common terms

Examples:

GTM

ARR

KPI

OKR

MLOps

SOC2

Bandwidth

Leverage

Synergy

⸻

Step 2

LLM Detection

Prompt:

Identify words or phrases that would likely confuse:

* a new employee
* a non-native English speaker
* someone outside the industry

Return:

* term
* category
* confidence
* explanation

This catches:

“Agentic workflow”

“Knowledge graph”

“Prompt chaining”

even if absent from dictionary.

⸻

Demo Flow

Speak:

“Let’s revisit our GTM motion before Q3 and improve ARR through our PLG initiative.”

System shows:

Transcript

Detected Terms:

* GTM
* ARR
* PLG

Plain English Version

Generated Glossary

Human Review Panel

Approve

Judge edits one explanation.

System updates summary.

⸻

Success Criteria

Demo completes within 60 seconds.

Jargon detection accuracy >80%.

Human correction workflow visible.

Summary generated successfully.

No internet dependency required.

Runs entirely on a local laptop.

⸻

Stretch Goal

Personalized Glossary Learning

If user repeatedly edits:

“ARR”

from:

“Annual recurring revenue”

to:

“Subscription revenue”

System remembers preference for future meetings.
