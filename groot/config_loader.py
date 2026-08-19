"""Loads config.yaml once and exposes it as a plain dict.

Every other module imports get_config() instead of reading YAML itself,
so there's exactly one place that knows about the config file's path/shape.
"""

import yaml
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
_config = None


def get_config() -> dict:
    global _config
    if _config is None:
        with open(_CONFIG_PATH, "r") as f:
            _config = yaml.safe_load(f)
    return _config
