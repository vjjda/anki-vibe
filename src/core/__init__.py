# Path: src/core/__init__.py
from .config import settings
from .logging_config import setup_logging
from .anki_detector import detect_active_profile

__all__ = ["settings", "setup_logging", "detect_active_profile"]