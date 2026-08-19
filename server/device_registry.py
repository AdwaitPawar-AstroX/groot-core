"""Device registry.

Tracks which device agents (PC, phone, ...) are currently connected via
WebSocket, and which one is "active" — the one that should receive the
next tool-call/action. Active device is set either explicitly ("I'm on my
PC now") or implicitly (whichever device just sent a message/wake word).
"""

import time

# device_id -> {"websocket": <ws>, "capabilities": [...], "last_seen": float}
_connected_devices: dict[str, dict] = {}
_active_device_id: str | None = None


def register(device_id: str, websocket, capabilities: list[str]):
    _connected_devices[device_id] = {
        "websocket": websocket,
        "capabilities": capabilities,
        "last_seen": time.time(),
    }
    global _active_device_id
    if _active_device_id is None:
        _active_device_id = device_id


def unregister(device_id: str):
    _connected_devices.pop(device_id, None)
    global _active_device_id
    if _active_device_id == device_id:
        _active_device_id = next(iter(_connected_devices), None)


def touch(device_id: str):
    """Call whenever a device sends a message.

    Only marks it 'active' (i.e. the execution target for tool calls) if
    it's an actual connected agent with registered tools. A device that's
    just talking (like the voice client, which has no tools of its own)
    should NOT bump the real execution target (e.g. the PC agent) out of
    the active slot — otherwise every voice message breaks tool dispatch.
    """
    if device_id in _connected_devices:
        _connected_devices[device_id]["last_seen"] = time.time()
        global _active_device_id
        _active_device_id = device_id


def set_active(device_id: str):
    global _active_device_id
    if device_id in _connected_devices:
        _active_device_id = device_id


def get_active_device():
    if _active_device_id and _active_device_id in _connected_devices:
        return _active_device_id, _connected_devices[_active_device_id]
    return None, None


def list_devices() -> dict:
    return {
        device_id: {"capabilities": d["capabilities"], "last_seen": d["last_seen"]}
        for device_id, d in _connected_devices.items()
    }


def device_supports(device_id: str, tool_name: str) -> bool:
    device = _connected_devices.get(device_id)
    return bool(device and tool_name in device["capabilities"])
