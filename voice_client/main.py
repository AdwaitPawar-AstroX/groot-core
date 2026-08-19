"""Groot voice client.

    wake word -> record -> STT -> POST /chat (home server) -> TTS

This is just another client of the server, same as the phone's HTTP
Shortcuts test or the PC agent's WebSocket connection — it doesn't talk to
Ollama/Claude directly. All the thinking still happens on the server, so
this can run on the same machine as the server, or a different one on
the network (mic/speaker permitting).

Run with: python -m voice_client.main
"""

import requests
from .wake_word import listen_for_wake_word
from .record import record_utterance
from .stt import transcribe
from .tts import speak
from groot.config_loader import get_config

DEVICE_ID = "voice-main"  # identifies this client to the server/device_registry


def send_to_server(text: str) -> dict:
    cfg = get_config()
    server_url = cfg.get("server_url", "http://localhost:8420")
    resp = requests.post(
        f"{server_url}/chat",
        json={"device_id": DEVICE_ID, "text": text},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def handle_one_turn():
    audio, sample_rate = record_utterance()

    user_text = transcribe(audio, sample_rate)
    if not user_text:
        print("[voice_client] Heard nothing usable, going back to sleep.")
        return

    print(f"[user] {user_text}")

    try:
        result = send_to_server(user_text)
    except requests.exceptions.RequestException as e:
        print(f"[voice_client] Couldn't reach the server: {e}")
        speak("I couldn't reach the server.")
        return

    reply_text = result.get("reply", "")
    source = result.get("source", "unknown")
    print(f"[groot:{source}] {reply_text}")

    if reply_text:
        speak(reply_text)


def main():
    print("[voice_client] Groot voice client starting up.")
    while True:
        try:
            listen_for_wake_word()
            handle_one_turn()
        except KeyboardInterrupt:
            print("\n[voice_client] Shutting down.")
            break
        except Exception as e:
            print(f"[voice_client] Error during turn, recovering: {e}")


if __name__ == "__main__":
    main()
