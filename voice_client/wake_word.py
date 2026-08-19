"""Wake word detection via openWakeWord.

Runs continuously on the CPU (tiny model, negligible resource use) and
only triggers the heavy STT -> LLM -> TTS pipeline when the keyword fires.

NOTE: openWakeWord ships a few pretrained keywords (e.g. "hey_jarvis") but
not "groot" out of the box — training a custom "groot" wake word is a
follow-up step (openWakeWord supports this). Using "hey_jarvis" as a
placeholder keyword until then; swap in config.yaml once trained.
"""

import numpy as np
import sounddevice as sd
from openwakeword.model import Model
from groot.config_loader import get_config

_CHUNK_SIZE = 1280  # openWakeWord expects 80ms chunks at 16kHz


def listen_for_wake_word():
    """Blocks until the configured wake word is detected, then returns."""
    cfg = get_config()
    ww_cfg = cfg["wake_word"]
    sample_rate = cfg["audio"]["sample_rate"]

    oww_model = Model(
        wakeword_models=[ww_cfg["keyword"]],
        inference_framework="onnx",
    )

    print(f"[wake_word] Listening for '{ww_cfg['keyword']}'...")

    with sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="int16",
        blocksize=_CHUNK_SIZE,
        device=cfg["audio"]["input_device"],
    ) as stream:
        while True:
            audio_chunk, _ = stream.read(_CHUNK_SIZE)
            audio_chunk = audio_chunk.flatten()
            predictions = oww_model.predict(audio_chunk)

            for keyword, score in predictions.items():
                if score > ww_cfg["threshold"]:
                    print(f"[wake_word] Detected '{keyword}' ({score:.2f})")
                    return
