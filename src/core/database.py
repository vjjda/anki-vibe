import sqlite3
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Quản lý kết nối và schema của SQLite database cho local state.
    """
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            # Tạo thư mục cha nếu chưa tồn tại
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row
        return self._connection

    def _init_db(self):
        """Khởi tạo bảng nếu chưa có."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Bảng lưu trạng thái Notes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS note_states (
                note_id INTEGER PRIMARY KEY,
                hash TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Bảng lưu trạng thái Models
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_states (
                model_name TEXT PRIMARY KEY,
                hash TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()

    def close(self):
        if self._connection:
            self._connection.close()
            self._connection = None

    # --- Note Operations ---

    def get_note_hash(self, note_id: int) -> Optional[str]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT hash FROM note_states WHERE note_id = ?", (note_id,))
        row = cursor.fetchone()
        return row["hash"] if row else None

    def update_note_hash(self, note_id: int, new_hash: str):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO note_states (note_id, hash, updated_at) 
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(note_id) DO UPDATE SET 
                hash=excluded.hash, 
                updated_at=CURRENT_TIMESTAMP
        """, (note_id, new_hash))
        conn.commit()

    # --- Model Operations ---

    def get_model_hash(self, model_name: str) -> Optional[str]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT hash FROM model_states WHERE model_name = ?", (model_name,))
        row = cursor.fetchone()
        return row["hash"] if row else None

    def update_model_hash(self, model_name: str, new_hash: str):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO model_states (model_name, hash, updated_at) 
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(model_name) DO UPDATE SET 
                hash=excluded.hash, 
                updated_at=CURRENT_TIMESTAMP
        """, (model_name, new_hash))
        conn.commit()
