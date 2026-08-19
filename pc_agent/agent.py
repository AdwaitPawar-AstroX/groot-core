"""Groot PC agent.

Connects to the home server over WebSocket, announces what it can do, and
executes tool calls the server sends it. Run this on any PC you want Groot
to be able to act on — your desktop, laptop, workshop machine, etc. Each
instance needs a unique DEVICE_ID.

Run with: python pc_agent/agent.py
"""

import asyncio
import json
import subprocess
import sys
import platform
import websockets

SERVER_URL = "ws://localhost:8420/ws"  # change to your home server's Tailscale IP
DEVICE_ID = "pc-main"  # give each PC a unique name if you run this on more than one

# Registered tools this agent can execute. Extend this dict as you add more.
# Keep it SAFETY-GATED per the plan: no destructive commands without review.
CAPABILITIES = ["open_app", "close_window", "run_command"]


def open_app(args: dict) -> dict:
    name = args.get("name", "").strip()
    if not name:
        return {"status": "error", "reason": "no app name provided in args"}
    try:
        if platform.system() == "Windows":
            subprocess.Popen(["start", "", name], shell=True)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", "-a", name])
        else:  # Linux
            subprocess.Popen([name])
        return {"status": "ok", "action": f"opened {name}"}
    except Exception as e:
        return {"status": "error", "reason": str(e)}


def close_window(args: dict) -> dict:
    name = args.get("name", "").strip()
    if not name:
        return {"status": "error", "reason": "no app name provided in args"}
    try:
        if platform.system() == "Windows":
            subprocess.run(
                ["taskkill", "/IM", f"{name}.exe", "/F"],
                capture_output=True,
            )
        elif platform.system() == "Darwin":
            subprocess.run(["osascript", "-e", f'quit app "{name}"'])
        else:  # Linux
            subprocess.run(["wmctrl", "-c", name])
        return {"status": "ok", "action": f"closed {name}"}
    except Exception as e:
        return {"status": "error", "reason": str(e)}


def run_command(args: dict) -> dict:
    """DELIBERATELY NOT WIRED TO ARBITRARY SHELL EXECUTION YET.

    Per the safety requirements in the plan (confirmation gate for
    irreversible actions, no blind command execution), this is a stub.
    Wire this up to a real, reviewed allowlist of commands before using it
    for anything beyond testing.
    """
    return {
        "status": "refused",
        "reason": "run_command is disabled until a safety allowlist is built",
    }


TOOL_HANDLERS = {
    "open_app": open_app,
    "close_window": close_window,
    "run_command": run_command,
}


async def connect_and_serve():
    uri = f"{SERVER_URL}/{DEVICE_ID}"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"type": "register", "capabilities": CAPABILITIES}))
        print(f"[pc_agent] Registered as '{DEVICE_ID}' with tools: {CAPABILITIES}")

        async for raw_msg in ws:
            msg = json.loads(raw_msg)
            if msg.get("type") != "tool_call":
                continue

            payload = msg["payload"]
            tool_name = payload.get("tool")
            args = payload.get("args", {})
            print(f"[pc_agent] Executing: {tool_name}({args})")

            handler = TOOL_HANDLERS.get(tool_name)
            if handler is None:
                result = {"status": "error", "reason": f"unknown tool '{tool_name}'"}
            else:
                result = handler(args)

            await ws.send(json.dumps(result))
            print(f"[pc_agent] Result: {result}")


async def main():
    print(f"[pc_agent] Connecting to {SERVER_URL}/{DEVICE_ID} ...")
    while True:
        try:
            await connect_and_serve()
        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError, OSError) as e:
            print(f"[pc_agent] Connection lost ({e}). Reconnecting in 3s...")
            await asyncio.sleep(3)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[pc_agent] Shutting down.")
        sys.exit(0)
