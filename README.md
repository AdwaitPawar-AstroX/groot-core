# Groot — Core Voice Loop (v0.1)

Minimal JARVIS-style loop: **wake word → record → STT → local LLM (Qwen3, escalates to Claude) → TTS**.

This is the foundation only — no tools, no hardware bridge, no memory store yet.
Everything else from the plan (MCP hardware bridge, project memory, safety
confirmation gate, proactivity) layers on top of this once it's running.

## 1. System dependencies (Linux)

```bash
# Ollama (local LLM runtime)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3:14b

# Piper TTS binary + a voice
# (grab the linux x86_64 build from the Piper releases page, put it on PATH)
mkdir -p ~/.local/share/piper-voices
# download en_US-lessac-medium.onnx + .onnx.json into that folder,
# then point tts.py's --model path at it (see groot/tts.py)

# Audio libs
sudo apt install -y portaudio19-dev
```

## 2. Python environment

```bash
cd groot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 3. Configure

Edit `config.yaml`:
- `stt.device`: set to `"cpu"` if you don't have CUDA available in this environment
- `wake_word.keyword`: starts as `"hey_jarvis"` (openWakeWord's pretrained keyword) —
  train a custom "groot" model later, see openWakeWord's training docs
- `tts.voice`: path to your downloaded Piper voice model

## 4. Claude fallback (optional but recommended)

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

Without this set, Groot still works fully locally — it just can't escalate,
and `_call_ollama` failures will raise instead of falling back.

## 5. Run it

```bash
python -m groot.main
```

Say the wake word, then speak. It'll transcribe, think (locally by default),
and reply out loud.

## What's NOT wired in yet (next steps per the plan)

- Long-term project memory (SQLite store) — `conversation_history` is
  in-memory only right now, lost on restart
- MCP hardware bridge (servo control, sensor reads)
- Safety confirmation gate for irreversible actions
- Proactivity / pattern noticing
- The smarter escalation router (`_needs_escalation` in `llm_client.py`
  is intentionally simple — a placeholder to refine once you see real
  local-model failure cases)

## File map

```
groot/
├── config.yaml           # single source of truth for models/devices/paths
├── system_prompt.md       # Groot's persona + anti-hallucination + safety rules
├── requirements.txt
└── groot/
    ├── config_loader.py   # reads config.yaml once
    ├── wake_word.py        # openWakeWord listener
    ├── record.py            # mic capture with silence detection
    ├── stt.py                 # faster-whisper transcription
    ├── llm_client.py          # Ollama (Qwen3) + Claude escalation
    ├── tts.py                  # Piper speech output
    └── main.py                  # the actual loop
```
