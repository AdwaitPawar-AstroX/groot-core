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

## One-time setup: your API key

Copy `.env.example` to `.env` and fill in your real key:
```bash
cp .env.example .env
# edit .env, replace the placeholder with your real ANTHROPIC_API_KEY
```
This is loaded automatically now — no more manually setting
`$env:ANTHROPIC_API_KEY` in every new terminal. `.env` is gitignored, so
your real key never gets committed.

## Starting everything (organized)

Instead of manually opening 3 terminals and typing commands in each,
run one script that launches all three in clearly labeled windows:

```powershell
.\scripts\start_all.ps1
```

This opens **Groot - SERVER**, **Groot - PC AGENT**, and **Groot - VOICE**
as separate titled windows, in the right startup order. If you only need
one piece, run its script directly: `.\scripts\start_server.ps1`,
`.\scripts\start_pc_agent.ps1`, or `.\scripts\start_voice_client.ps1`.

**Remember:** if you restart the server, the PC agent needs a moment to
auto-reconnect (it retries every 3s) — no need to manually restart it
anymore, just give it a few seconds after the server comes back up.

## Backing this up (so a mistake never costs you the whole project)

```bash
git init                      # only if not already done
git add -A
git commit -m "Groot: working voice + PC agent + server, milestone reached"
```

Push to a **private** GitHub repo so you have an off-machine copy:
```bash
git remote add origin https://github.com/<you>/groot-core.git
git branch -M main
git push -u origin main
```

From here on, commit whenever something works — `git commit -m "..."`
after every real milestone (a new tool, a fix, a working feature) gives
you a restore point. If something breaks later, `git log --oneline` shows
your history and `git checkout <commit> -- <file>` recovers any single
file without touching the rest.

**What's NOT backed up by git (and shouldn't be):**
- `.env` (your API key — keep this safe yourself, e.g. a password manager)
- `venv/` (regenerate anytime with `pip install -r requirements.txt`)
- `data/` (your actual conversation history — back this up separately if
  you want to keep it; see below)

**Backing up your conversation data separately:**
`data/groot.sqlite3` holds your actual conversation history — this is
personal data, not code, so it doesn't belong in a git repo (especially
not a public one). Periodically copy it somewhere safe:
```powershell
Copy-Item data\groot.sqlite3 -Destination "$env:USERPROFILE\Documents\groot_backups\groot_$(Get-Date -Format yyyyMMdd_HHmm).sqlite3"
```



With the server and PC agent both running, in a third terminal:

```bash
curl -X POST http://localhost:8420/chat \
  -H "Content-Type: application/json" \
  -d '{"device_id": "pc-main", "text": "open notepad"}'
```

Check the PC agent's terminal — you should see it receive and execute the
`open_app` tool call. Check `curl http://localhost:8420/devices` to see
what's currently connected/active.

## Starting everything (recommended — replaces manual 3-terminal setup)

Instead of manually opening 3 PowerShell windows, activating the venv in
each, and remembering the right command for each one:

```powershell
.\start_all.ps1
```

This launches the server, PC agent, and voice client each in their own
window with the venv already activated. If you get a script-execution
error the first time, run this once (matches the earlier venv-activation
fix):
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

To restart everything cleanly after a code change: close all 3 windows
and re-run `.\start_all.ps1`. The PC agent now auto-reconnects if the
server restarts on its own, but a full clean restart is still the
simplest way to guarantee nothing's stale.

## Backing up your work (git)

Do this now, and after any change that actually works — it's the
difference between "reverting one bad edit" and "redoing an evening of
debugging."

**First-time setup:**
```powershell
git init
git add -A
git commit -m "Working voice loop + PC agent + Tailscale remote access"
```

**Push to GitHub for real off-machine backup** (create an empty private
repo on GitHub first, e.g. `groot-core`):
```powershell
git remote add origin https://github.com/<you>/groot-core.git
git branch -M main
git push -u origin main
```

**After any future change that works**, commit it:
```powershell
git add -A
git commit -m "describe what changed"
git push
```

`.gitignore` already excludes `venv/`, `data/` (your local conversation
history/session DB), and cache files — only your actual code and config
get backed up, nothing sensitive or huge.

## Running things individually

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
