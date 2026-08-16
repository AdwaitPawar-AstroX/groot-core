"""Groot core loop.

    wake word -> record -> STT -> LLM (local, escalate if needed) -> TTS

Run with: python -m groot.main
"""

from .wake_word import listen_for_wake_word
from .record import record_utterance
from .stt import transcribe
from .llm_client import get_response
from .tts import speak

# Short-term conversation memory (cleared on restart). Long-term project
# memory is a separate store (see config.yaml paths.memory_store) — not
# wired in yet, this is just the core voice loop.
conversation_history: list[dict] = []
MAX_HISTORY_TURNS = 6


def handle_one_turn():
    audio, sample_rate = record_utterance()

    user_text = transcribe(audio, sample_rate)
    if not user_text:
        print("[main] Heard nothing usable, going back to sleep.")
        return

    print(f"[user] {user_text}")

    result = get_response(user_text, conversation_history)
    reply_text = result["text"]
    print(f"[groot:{result['source']}] {reply_text}")

    conversation_history.append({"role": "user", "content": user_text})
    conversation_history.append({"role": "assistant", "content": reply_text})
    del conversation_history[: max(0, len(conversation_history) - MAX_HISTORY_TURNS * 2)]

    speak(reply_text)


def main():
    print("[main] Groot starting up.")
    while True:
        try:
            listen_for_wake_word()
            handle_one_turn()
        except KeyboardInterrupt:
            print("\n[main] Shutting down.")
            break
        except Exception as e:
            print(f"[main] Error during turn, recovering: {e}")


if __name__ == "__main__":
    main()
