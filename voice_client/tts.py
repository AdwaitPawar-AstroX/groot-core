"""Text-to-speech via Piper (local, free, offline).

Piper needs its voice model files downloaded once — see README for the
one-time setup command. This module just shells out to the piper binary
and plays the resulting audio.
"""

import subprocess
import sounddevice as sd
import numpy as np
import io
import wave
from groot.config_loader import get_config


def speak(text: str) -> None:
    cfg = get_config()["tts"]
    voice = cfg["voice"]

    # piper reads text on stdin, writes WAV to stdout
    proc = subprocess.run(
        ["piper", "--model", voice, "--output-raw"],
        input=text.encode("utf-8"),
        capture_output=True,
    )
    if proc.returncode != 0:
        print(f"[tts] piper failed: {proc.stderr.decode(errors='ignore')}")
        return

    audio = np.frombuffer(proc.stdout, dtype=np.int16)
    sd.play(audio, samplerate=cfg["sample_rate"])
    sd.wait()
