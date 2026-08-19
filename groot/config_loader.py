"""Loads config.yaml once and exposes it as a plain dict.

Every other module imports get_config() instead of reading YAML itself,
so there's exactly one place that knows about the config file's path/shape.
"""

import yaml
from pathlib import Path
from dotenv import load_dotenv

_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
_ENV_PATH = Path(__file__).parent.parent / ".env"
_config = None

load_dotenv(_ENV_PATH)  # loads ANTHROPIC_API_KEY etc. once, at import time


def get_config() -> dict:
    global _config
    if _config is None:
        with open(_CONFIG_PATH, "r") as f:
            _config = yaml.safe_load(f)
    return _config
