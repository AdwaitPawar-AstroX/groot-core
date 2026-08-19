"""Groot home server.

Run with: uvicorn server.app:app --host 0.0.0.0 --port 8420

- POST /chat        -- any device (PC client, phone client, voice loop) sends
                        user text here; gets Groot's reply back.
- WS   /ws/{device}  -- device agents (pc_agent, phone_agent) connect here to
                        register their tools and receive tool-call dispatches.
- GET  /devices      -- debug: see what's currently connected.

This is what makes "one session, device-aware execution" real: the
conversation lives here (session_store), and tool calls get routed to
whichever device is currently active (device_registry).
"""

import json
import re
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from . import session_store, device_registry
from groot.llm_client import get_response

app = FastAPI(title="Groot Home Server")

# How the LLM signals it wants a device action, e.g.:
#   TOOL_CALL: {"tool": "open_app", "args": {"name": "chrome"}}
TOOL_CALL_PATTERN = re.compile(r"TOOL_CALL:\s*(\{.*\})", re.DOTALL)


class ChatRequest(BaseModel):
    device_id: str
    text: str


class ChatResponse(BaseModel):
    reply: str
    source: str
    tool_executed: dict | None = None
    tool_call: dict | None = None  # raw tool call for clients that self-execute (e.g. Tasker)


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    device_registry.touch(req.device_id)
    session_store.add_message("user", req.text, device_id=req.device_id)

    history = session_store.get_recent_history()
    result = get_response(req.text, history[:-2] if len(history) >= 2 else [])
    reply_text = result["text"]
    source = result["source"]

    tool_executed = None
    tool_call_out = None
    match = TOOL_CALL_PATTERN.search(reply_text)
    if match:
        try:
            tool_call = json.loads(match.group(1))
            dispatch_result = await _dispatch_tool_call(tool_call, req.device_id)
            reply_text = TOOL_CALL_PATTERN.sub("", reply_text).strip()

            if dispatch_result.get("status") == "self_execute":
                # No connected device agent (e.g. Tasker, which is stateless) —
                # hand the raw tool call back so the caller executes it itself.
                tool_call_out = tool_call
                if not reply_text:
                    reply_text = "On it."
            else:
                tool_executed = dispatch_result
                if not reply_text:
                    reply_text = f"Done — {tool_call.get('tool', 'action')} executed."
        except (json.JSONDecodeError, KeyError):
            pass  # malformed tool call — just speak the text as-is

    session_store.add_message("assistant", reply_text, device_id=req.device_id, source=source)

    return ChatResponse(
        reply=reply_text, source=source, tool_executed=tool_executed, tool_call=tool_call_out
    )


async def _dispatch_tool_call(tool_call: dict, requester_device_id: str) -> dict:
    """Sends a tool call to the currently active device and waits for the result.

    If no device is connected via WebSocket (e.g. Tasker on the phone, which
    is a stateless HTTP client), returns a 'self_execute' signal instead of
    an error — the requesting client is expected to run the tool itself.
    """
    tool_name = tool_call.get("tool")
    active_id, active_device = device_registry.get_active_device()

    if not active_device:
        return {"status": "self_execute", "tool_call": tool_call}

    if not device_registry.device_supports(active_id, tool_name):
        # Not supported by the connected agent — let the requester try locally
        return {"status": "self_execute", "tool_call": tool_call}

    ws = active_device["websocket"]
    await ws.send_json({"type": "tool_call", "payload": tool_call})
    response = await ws.receive_json()  # NOTE: simple request/response; see README caveat
    return response


@app.websocket("/ws/{device_id}")
async def device_socket(websocket: WebSocket, device_id: str):
    await websocket.accept()
    # First message from the device must be its capability announcement:
    # {"type": "register", "capabilities": ["open_app", "close_window", ...]}
    init = await websocket.receive_json()
    capabilities = init.get("capabilities", []) if init.get("type") == "register" else []
    device_registry.register(device_id, websocket, capabilities)
    print(f"[server] Device connected: {device_id} ({capabilities})")

    try:
        while True:
            # Keep the connection open; device agents may send unsolicited
            # status pings here later (e.g. "I'm now the active device").
            msg = await websocket.receive_json()
            if msg.get("type") == "set_active":
                device_registry.set_active(device_id)
    except WebSocketDisconnect:
        device_registry.unregister(device_id)
        print(f"[server] Device disconnected: {device_id}")


@app.get("/devices")
async def devices():
    active_id, _ = device_registry.get_active_device()
    return {"connected": device_registry.list_devices(), "active": active_id}
