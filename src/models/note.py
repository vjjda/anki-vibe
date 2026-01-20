# Path: src/models/note.py
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

__all__ = ["AnkiNote"]

class AnkiNote(BaseModel):
    """
    Đại diện cho một Note (Ghi chú) trong hệ thống Anki.
    Model này map trực tiếp với các entry trong file YAML dữ liệu.
    """
    
    # ID là Optional vì Note mới tạo sẽ chưa có ID.
    # Nhưng khi đã sync về (Pull), ID là bắt buộc để tracking.
    id: Optional[int] = Field(
        default=None, 
        description="Anki Note ID (Unique Identifier). Null for new notes."
    )
    
    deck: str = Field(
        ..., 
        min_length=1, 
        description="Target Deck name in Anki (e.g. 'English::Vocabulary')"
    )
    
    tags: List[str] = Field(
        default_factory=list, 
        description="List of tags associated with the note"
    )
    
    # Fields là dict dynamic: {"Front": "...", "Back": "..."}
    fields: Dict[str, str] = Field(
        ..., 
        description="Key-value pairs matching the Note Type fields"
    )

    @field_validator('fields')
    @classmethod
    def check_fields_not_empty(cls, v: Dict[str, str]) -> Dict[str, str]:
        if not v:
            raise ValueError('Fields dictionary cannot be empty')
        return v

    def get_field_content(self, field_name: str) -> str:
        """Helper để lấy nội dung field an toàn."""
        return self.fields.get(field_name, "")