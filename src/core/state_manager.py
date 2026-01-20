# Path: src/core/state_manager.py
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from src.core.config import settings

logger = logging.getLogger(__name__)

class StateManager:
    """
    Quản lý file .sync_state.json để theo dõi thay đổi (Change Tracking).
    """
    def __init__(self, profile_name: str):
        self.profile = profile_name
        self.state_file = settings.ANKI_DATA_DIR / profile_name / ".sync_state.json"
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        if not self.state_file.exists():
            return {"models": {}, "notes": {}}
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Corrupted state file, resetting: {e}")
            return {"models": {}, "notes": {}}

    def save_state(self) -> None:
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save state file: {e}")

    # --- Methods ---
    def get_note_hash(self, note_id: int) -> Optional[str]:
        return self.state.get("notes", {}).get(str(note_id))

    def update_note_hash(self, note_id: int, new_hash: str) -> None:
        if "notes" not in self.state: self.state["notes"] = {}
        self.state["notes"][str(note_id)] = new_hash

    def get_model_hash(self, model_name: str) -> Optional[str]:
        return self.state.get("models", {}).get(model_name)

    def update_model_hash(self, model_name: str, new_hash: str) -> None:
        if "models" not in self.state: self.state["models"] = {}
        self.state["models"][model_name] = new_hash