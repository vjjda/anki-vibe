# Path: src/core/state_manager.py
import logging
from pathlib import Path
from typing import Optional
from src.core.database import DatabaseManager

logger = logging.getLogger(__name__)

class StateManager:
    """
    Quản lý state của quá trình sync (Hash của Notes và Models).
    Sử dụng SQLite backend (thông qua DatabaseManager).
    """
    def __init__(self, db_path: Path):
        self.db = DatabaseManager(db_path)

    def get_note_hash(self, note_id: int) -> Optional[str]:
        return self.db.get_note_hash(note_id)

    def update_note_hash(self, note_id: int, new_hash: str) -> None:
        self.db.update_note_hash(note_id, new_hash)

    def get_model_hash(self, model_name: str) -> Optional[str]:
        return self.db.get_model_hash(model_name)

    def update_model_hash(self, model_name: str, new_hash: str) -> None:
        self.db.update_model_hash(model_name, new_hash)
    
    def save_state(self) -> None:
        """
        No-op for SQLite implementation as data is persisted immediately.
        Kept for compatibility with existing service calls.
        """
        pass

    def close(self) -> None:
        self.db.close()
