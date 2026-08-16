"""Speech-to-text via faster-whisper, running locally."""

import numpy as np
from faster_whisper import WhisperModel
from .config_loader import get_config

_model = None


def _get_model():
    global _model
    if _model is None:
        cfg = get_config()["stt"]
        _model = WhisperModel(
            cfg["model_size"],
            device=cfg["device"],
            compute_type="float16" if cfg["device"] == "cuda" else "int8",
        )
    return _model


def transcribe(audio: np.ndarray, sample_rate: int) -> str:
    """audio: mono float32 numpy array in [-1, 1]."""
    model = _get_model()
    segments, _info = model.transcribe(audio, language="en", beam_size=1)
    return " ".join(seg.text.strip() for seg in segments).strip()
