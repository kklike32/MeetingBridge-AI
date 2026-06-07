
## Prompts For Next Codex Sessions

Use these prompts in order when starting fresh Codex sessions.

### Prompt 1: Scaffold And Preflight

```text
You are Codex in /Users/keenankalra/Documents/Personal/MeetingBridgeAI.
Read AGENTS.md, PRD.md, and .agents/plans/08_execution_order.md.
Implement only Phase 1 and Phase 2 from the execution order:
1. scaffold the repo files
2. add dependency/model preflight

Do not initialize git.
Do not implement audio transcription or LLM analysis yet.
No mock demo path.
After editing, run the lightest available syntax/import checks and report what works and what is still blocked by missing dependencies or models.
```

### Prompt 2: Required Audio And ASR

```text
You are Codex in /Users/keenankalra/Documents/Personal/MeetingBridgeAI.
Read AGENTS.md and .agents/plans/05_transcription_plan.md.
Implement Phase 3 and Phase 4:
1. required microphone recording with st.audio_input
2. required audio upload with st.file_uploader
3. temporary audio file handling
4. real ASR transcription with MLX Whisper primary and faster-whisper backup
5. transcript correction field after ASR

Do not initialize git.
Do not add a text-only demo path.
Do not add fake transcription.
Verify with syntax/import checks and, if possible, run Streamlit locally.
```

### Prompt 3: Jargon And Real LLM

```text
You are Codex in /Users/keenankalra/Documents/Personal/MeetingBridgeAI.
Read AGENTS.md plus .agents/plans/03_jargon_detection_plan.md and .agents/plans/04_llm_simplification_plan.md.
Implement Phase 5 and Phase 6:
1. static dictionary and acronym detection
2. heuristic candidate detection
3. Ollama qwen3:8b real LLM client
4. JSON-only prompts with /no_think
5. one retry for malformed JSON
6. real backup model selection for gemma3:12b, mistral:7b, or LM Studio
7. merge LLM glossary terms with baseline detections

Do not initialize git.
Do not add mock simplification.
If the LLM is unavailable, show a setup/model readiness error instead of fake output.
Run targeted checks and report the exact model readiness status.
```

### Prompt 4: Human Review And Final Summary

```text
You are Codex in /Users/keenankalra/Documents/Personal/MeetingBridgeAI.
Read AGENTS.md plus .agents/plans/06_human_review_plan.md and .agents/plans/07_demo_script_plan.md.
Implement Phase 7 and Phase 8:
1. review state model
2. approve/edit/reject flow
3. review audit trail
4. approved glossary generation
5. final summary with plain English summary, key terms, action items, human-approved glossary, and model metadata
6. JSON and Markdown export

Do not initialize git.
Ensure rejected terms are excluded and edited explanations appear in the final output.
Run the app or the closest possible verification and report the demo path status.
```

### Prompt 5: Demo Polish

```text
You are Codex in /Users/keenankalra/Documents/Personal/MeetingBridgeAI.
Read AGENTS.md and .agents/plans/07_demo_script_plan.md.
Implement Phase 9:
1. README quick start
2. required model setup commands
3. exact demo sentence
4. audio recording/upload instructions
5. two-minute demo script
6. concise UI label polish

Do not initialize git.
Do not add mock/demo shortcuts.
Run a final verification pass and report exactly what was tested.
```
