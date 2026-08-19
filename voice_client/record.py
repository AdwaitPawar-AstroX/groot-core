"""Records a single utterance after wake-word trigger.

Simple energy-based silence detection: stops recording after a short
period of quiet, so the user doesn't have to press a button.
"""

import numpy as np
import sounddevice as sd
from groot.config_loader import get_config

_SILENCE_THRESHOLD = 500     # int16 amplitude below this = "quiet"
_SILENCE_DURATION_S = 1.2    # how long it must be quiet before we stop
_MAX_DURATION_S = 15         # hard cap so a stuck mic can't loop forever


def record_utterance() -> tuple[np.ndarray, int]:
    cfg = get_config()["audio"]
    sample_rate = cfg["sample_rate"]
    chunk_size = 1600  # 100ms chunks

    frames = []
    silence_chunks = 0
    silence_chunks_needed = int(_SILENCE_DURATION_S * sample_rate / chunk_size)
    max_chunks = int(_MAX_DURATION_S * sample_rate / chunk_size)

    print("[record] Listening...")

    with sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="int16",
        blocksize=chunk_size,
        device=cfg["input_device"],
    ) as stream:
        for _ in range(max_chunks):
            chunk, _ = stream.read(chunk_size)
            chunk = chunk.flatten()
            frames.append(chunk)

            if np.abs(chunk).mean() < _SILENCE_THRESHOLD:
                silence_chunks += 1
                if silence_chunks >= silence_chunks_needed and len(frames) > silence_chunks_needed:
                    break
            else:
                silence_chunks = 0

    print("[record] Done.")
    audio_int16 = np.concatenate(frames)
    audio_float32 = audio_int16.astype(np.float32) / 32768.0
    return audio_float32, sample_rate
