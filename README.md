# Groot v2 — Home Server + Multi-Device Agents

This replaces the standalone voice loop from v1 with the architecture you
asked for: **one continuous conversation, execution on whichever device is
active.**

## How it fits together

```
                    ┌─────────────────────────────┐
                    │   HOME SERVER (your PC/box)   │
                    │                                │
                    │  server/app.py (FastAPI)       │
                    │   ├── session_store.py          │  <- ONE conversation,
                    │   │    (SQLite: groot.sqlite3)  │     persisted, shared
                    │   ├── device_registry.py         │  <- tracks who's
                    │   │    (who's connected/active)  │     online + active
                    │   └── groot/llm_client.py          │  <- Qwen3 + Claude
                    │        (Ollama + escalation)        │     fallback
                    └───────────┬───────────────┬────────┘
                                │                │
                     WebSocket  │                │  WebSocket
                     /ws/pc-main│                │  /ws/phone-main
                                │                │
                    ┌───────────▼──────┐  ┌──────▼────────────┐
                    │   pc_agent/       │  │   phone_agent      │
                    │   agent.py         │  │   (not built yet — │
                    │   open/close apps  │  │   see below)        │
                    └────────────────────┘  └──────────────────────┘
```

Any client — the PC agent, a future phone client, or the old voice loop —
talks to the server's `POST /chat` with plain text and gets a reply. The
server is the only thing that talks to the LLM and the only thing that
owns conversation history. Device agents only handle **executing actions**,
never the thinking.

## Running the home server

```bash
cd groot_v2
pip install -r requirements.txt
ollama pull qwen3:14b   # if not already pulled
export ANTHROPIC_API_KEY="your-key"   # optional, for Claude fallback

uvicorn server.app:app --host 0.0.0.0 --port 8420
```

`--host 0.0.0.0` matters — it makes the server reachable from other devices
on your network (and later, over Tailscale from anywhere), not just
`localhost`.

## Running the PC agent

On the PC you want Groot to control (can be the same machine as the server,
or a different one on your network):

```bash
cd groot_v2
python pc_agent/agent.py
```

Edit `SERVER_URL` in `pc_agent/agent.py` first if the agent is running on a
*different* machine than the server — point it at the server's actual IP
(or Tailscale hostname once that's set up).

## Testing it end-to-end (text only for now)

With the server and PC agent both running, in a third terminal:

```bash
curl -X POST http://localhost:8420/chat \
  -H "Content-Type: application/json" \
  -d '{"device_id": "pc-main", "text": "open notepad"}'
```

Check the PC agent's terminal — you should see it receive and execute the
`open_app` tool call. Check `curl http://localhost:8420/devices` to see
what's currently connected/active.

## Running the voice client

Needs a real mic and speaker — run this on the PC that has them (usually
the same machine as the server, since that's your current setup).

```bash
cd groot_v2
pip install -r requirements.txt   # if not already done — adds STT/TTS/wake-word libs
python -m voice_client.main
```

Say the wake word ("hey jarvis" — placeholder until a custom "groot" model
is trained), then speak. It transcribes locally, POSTs to the same
`/chat` endpoint the phone already uses, and speaks the reply back.

One-time setup Piper needs (if not already done from v1):
- Grab the Piper binary for your OS and put it on PATH
- Download a voice model (e.g. `en_US-lessac-medium.onnx` + `.onnx.json`)
  into wherever `tts.py` expects it — see `config.yaml`'s `tts.voice` value

## What's real vs. stubbed right now

**Real:**
- Persistent shared conversation (survives server restarts)
- Device registration and "active device" tracking
- PC agent can open apps / close windows (Windows/Mac/Linux, best-effort)
- Tool-call routing from LLM response → correct device
- Remote access from phone confirmed working over Tailscale
- Voice loop (wake word → STT → server → TTS) wired to the same server
  every other client uses — proven architecture, not yet voice-tested live

**Deliberately stubbed (per the safety requirements in the plan):**
- `run_command` on the PC agent refuses everything — arbitrary shell
  execution needs a reviewed allowlist and the confirmation-gate UI before
  it's safe to wire up for real
- No confirmation gate yet — right now if the LLM emits a TOOL_CALL, it
  executes immediately. Before this touches anything irreversible (or any
  hardware), add a confirm-before-execute step
- Phone agent doesn't exist yet — same protocol (`/ws/<device_id>`,
  `register` message, `tool_call` messages) will work for it once you
  decide what phone-side actions actually mean for you (notifications?
  Tasker integration? a companion app?)
- Phone agent isn't a real automated agent yet — proven reachable via
  manual HTTP Shortcuts trigger, but no voice trigger, no native call/SMS
  execution (see Tasker vs. custom app discussion for next steps)

## File map

```
groot_v2/
├── config.yaml            # single source of truth for models/devices/paths/server_url
├── system_prompt.md        # Groot's persona + anti-hallucination + safety + tool schemas
├── requirements.txt
├── server/
│   ├── app.py                # FastAPI: /chat, /devices, WebSocket device registration
│   ├── session_store.py       # SQLite — the one shared conversation
│   └── device_registry.py      # tracks connected devices + which is "active"
├── groot/
│   ├── config_loader.py        # shared config reader
│   └── llm_client.py            # Ollama (Qwen3) + Claude escalation
├── pc_agent/
│   └── agent.py                  # WebSocket client — executes tool calls on this PC
└── voice_client/
    ├── wake_word.py               # openWakeWord listener
    ├── record.py                    # mic capture with silence detection
    ├── stt.py                        # faster-whisper transcription
    ├── tts.py                         # Piper speech output
    └── main.py                         # wake word -> record -> STT -> /chat -> TTS
```

## Known simplification worth knowing about

`_dispatch_tool_call` in `server/app.py` does a simple
send-then-immediately-receive on the device's WebSocket. This works for a
single tool call per turn but will get confused if a device sends anything
else in between, or if two tool calls need to happen concurrently. Fine for
testing now — worth revisiting with proper request/response IDs once you're
issuing more complex multi-step commands.
