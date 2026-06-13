"""Load the versioned assumptions file."""
from __future__ import annotations

import yaml

from .config import ASSUMPTIONS


def load(version: str = "v1") -> dict:
    return yaml.safe_load((ASSUMPTIONS / f"{version}.yaml").read_text())
